from __future__ import annotations

from dataclasses import replace
from typing import Any

from fastapi.testclient import TestClient

import server.main as main
from server.secretbox import encrypt_json


class _DummyTool:
    name = "dummy_tool"
    description = "Dummy tool for tests"
    input_schema: dict[str, Any] = {"type": "object"}
    output_schema: dict[str, Any] = {"type": "object"}


class _DummyRegistry:
    def list_tools(self) -> list[_DummyTool]:
        return [_DummyTool()]

    def run_tool(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        return {"echo": {"name": name, "arguments": arguments}}


def _auth_header(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _reset_state() -> None:
    main.session_store.clear_all_sessions_for_tests()
    with main._rate_limit_lock:
        main._rate_limits.clear()


def _set_test_settings(**overrides: Any) -> None:
    values = {
        "jwt_secret": "0123456789abcdef0123456789abcdef",
        "mcp_auth_required": True,
        "mcp_rate_limit_per_minute": 60,
        "mcp_max_arguments_bytes": 50_000,
        "mcp_max_argument_length": 10_000,
    }
    values.update(overrides)
    main.settings = replace(
        main.settings,
        **values,
    )


def test_mcp_tools_requires_authentication() -> None:
    _set_test_settings()
    _reset_state()
    main.registry = _DummyRegistry()
    client = TestClient(main.app)

    response = client.get("/mcp/tools")

    assert response.status_code == 401
    assert response.json()["detail"] == "Missing bearer token"


def test_mcp_tools_rate_limit_enforced_per_token() -> None:
    _set_test_settings(mcp_rate_limit_per_minute=2)
    _reset_state()
    main.registry = _DummyRegistry()
    client = TestClient(main.app)

    token, _ = main._store_token({"id": "u1", "email": "u1@example.com"})
    headers = _auth_header(token)

    assert client.get("/mcp/tools", headers=headers).status_code == 200
    assert client.get("/mcp/tools", headers=headers).status_code == 200

    limited = client.get("/mcp/tools", headers=headers)
    assert limited.status_code == 429
    assert "Rate limit exceeded" in limited.json()["detail"]


def test_mcp_call_rejects_oversized_payload() -> None:
    _set_test_settings(mcp_auth_required=False, mcp_max_arguments_bytes=40)
    _reset_state()
    main.registry = _DummyRegistry()
    client = TestClient(main.app)

    response = client.post(
        "/mcp/call",
        json={
            "name": "dummy_tool",
            "arguments": {"payload": "x" * 200},
        },
    )

    assert response.status_code == 400
    assert "payload exceeds limit" in response.json()["detail"]["message"]


def test_mcp_call_rejects_oversized_nested_string() -> None:
    _set_test_settings(
        mcp_auth_required=False,
        mcp_max_arguments_bytes=100_000,
        mcp_max_argument_length=5,
    )
    _reset_state()
    main.registry = _DummyRegistry()
    client = TestClient(main.app)

    response = client.post(
        "/mcp/call",
        json={
            "name": "dummy_tool",
            "arguments": {"nested": {"value": "abcdef"}},
        },
    )

    assert response.status_code == 400
    assert "arguments.nested.value" in response.json()["detail"]["message"]


def test_invalid_token_is_rejected() -> None:
    _set_test_settings()
    _reset_state()
    main.registry = _DummyRegistry()
    client = TestClient(main.app)

    response = client.get("/mcp/tools", headers=_auth_header("invalid-token"))

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid or expired token"


def test_expired_token_is_rejected() -> None:
    _set_test_settings()
    _reset_state()
    main.registry = _DummyRegistry()
    client = TestClient(main.app)

    token, _ = main._store_token({"id": "u2", "email": "u2@example.com"})
    main.session_store.expire_access_token_for_tests(token)

    response = client.get("/mcp/tools", headers=_auth_header(token))

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid or expired token"


def test_startup_checks_reject_weak_jwt_secret() -> None:
    _set_test_settings(jwt_secret="too-short")

    try:
        main._run_startup_checks()
        assert False, "Expected ValueError for weak JWT secret"
    except ValueError as exc:
        assert "JWT_SECRET" in str(exc)


def test_startup_checks_reject_missing_jwt_secret() -> None:
    _set_test_settings(jwt_secret="")

    try:
        main._run_startup_checks()
        assert False, "Expected ValueError for missing JWT secret"
    except ValueError as exc:
        assert "JWT_SECRET" in str(exc)


def test_startup_checks_reject_placeholder_jwt_secret() -> None:
    _set_test_settings(jwt_secret="change-me-in-production-please")

    try:
        main._run_startup_checks()
        assert False, "Expected ValueError for placeholder JWT secret"
    except ValueError as exc:
        assert "JWT_SECRET" in str(exc)


def test_startup_checks_emit_structured_remediation_messages() -> None:
    for bad_value in ("", "too-short", "change-me-in-production-please"):
        _set_test_settings(jwt_secret=bad_value)

        try:
            main._run_startup_checks()
            assert False, "Expected startup preflight validation error"
        except ValueError as exc:
            message = str(exc)
            assert "startup_preflight_failed" in message
            assert "code=JWT_SECRET_" in message
            assert "remediation='Set JWT_SECRET in .env.local" in message


def test_refresh_token_reuse_revokes_chain() -> None:
    _set_test_settings()
    _reset_state()
    main.registry = _DummyRegistry()
    client = TestClient(main.app)

    access_token, refresh_token = main._store_token({"id": "u3", "email": "u3@example.com"})

    refresh_ok = client.post("/auth/refresh", json={"refreshToken": refresh_token})
    assert refresh_ok.status_code == 200
    refreshed = refresh_ok.json()
    new_access_token = refreshed["token"]

    # Reuse attack: old refresh token should now revoke the whole chain.
    refresh_reuse = client.post("/auth/refresh", json={"refreshToken": refresh_token})
    assert refresh_reuse.status_code == 401

    # Original and refreshed access tokens must both be invalid after chain revocation.
    original_probe = client.get("/mcp/tools", headers=_auth_header(access_token))
    refreshed_probe = client.get("/mcp/tools", headers=_auth_header(new_access_token))
    assert original_probe.status_code == 401
    assert refreshed_probe.status_code == 401


def test_logout_revokes_entire_token_chain() -> None:
    _set_test_settings()
    _reset_state()
    main.registry = _DummyRegistry()
    client = TestClient(main.app)

    _, refresh_token = main._store_token({"id": "u4", "email": "u4@example.com"})
    refresh_ok = client.post("/auth/refresh", json={"refreshToken": refresh_token})
    assert refresh_ok.status_code == 200
    refreshed = refresh_ok.json()
    access_token_2 = refreshed["token"]
    refresh_token_2 = refreshed["refreshToken"]

    logout = client.post("/auth/logout", headers=_auth_header(access_token_2), json={"refreshToken": refresh_token_2})
    assert logout.status_code == 200
    assert logout.json()["revoked"] is True

    # Chain-wide revocation verification: latest access and refresh should both fail.
    post_logout_access = client.get("/mcp/tools", headers=_auth_header(access_token_2))
    post_logout_refresh = client.post("/auth/refresh", json={"refreshToken": refresh_token_2})
    assert post_logout_access.status_code == 401
    assert post_logout_refresh.status_code == 401


def test_mcp_call_uses_session_scoped_snowflake_context() -> None:
    _set_test_settings()
    _reset_state()

    captured: dict[str, Any] = {}

    class _ContextRegistry:
        def list_tools(self) -> list[_DummyTool]:
            return [_DummyTool()]

        def run_tool(
            self,
            name: str,
            arguments: dict[str, Any],
            execution_context: dict[str, Any] | None = None,
        ) -> dict[str, Any]:
            captured["name"] = name
            captured["arguments"] = arguments
            captured["execution_context"] = execution_context or {}
            sf_client = captured["execution_context"].get("sf_client")
            runtime_credentials = getattr(sf_client, "runtime_credentials", {}) if sf_client else {}
            return {"runtime_credentials": runtime_credentials}

    main.registry = _ContextRegistry()
    client = TestClient(main.app)

    session_ctx = {
        "account": "acc1",
        "username": "user1",
        "password": "pw1",
        "role": "ACCOUNTADMIN",
        "warehouse": "WH1",
        "database": "DB1",
        "schema": "SC1",
    }
    token, _ = main._store_token(
        {
            "id": "u5",
            "email": "u5@example.com",
            "role": "ORG_ADMIN",
            "_snowflake_ctx_encrypted": encrypt_json(session_ctx, main.settings.jwt_secret),
        }
    )

    response = client.post(
        "/mcp/call",
        headers=_auth_header(token),
        json={"name": "dummy_tool", "arguments": {"x": 1}},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert body["result"]["runtime_credentials"]["account"] == "acc1"
    assert body["result"]["runtime_credentials"]["username"] == "user1"
    assert body["result"]["runtime_credentials"]["role"] == "ACCOUNTADMIN"
