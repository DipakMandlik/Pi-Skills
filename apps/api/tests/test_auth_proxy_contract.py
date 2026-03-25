from __future__ import annotations

import json
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from apps.api.routers import auth as auth_router


class _MockUpstreamResponse:
    def __init__(self, payload: dict, status: int = 200):
        self.payload = payload
        self.status = status

    def read(self) -> bytes:
        return json.dumps(self.payload).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


def _build_app() -> FastAPI:
    app = FastAPI()
    app.include_router(auth_router.router)
    return app


def test_apps_api_auth_login_returns_410_outside_dev() -> None:
    app = _build_app()
    client = TestClient(app)

    with patch("apps.api.main.settings") as mock_settings:
        mock_settings.app_env = "production"
        mock_settings.apps_api_auth_proxy_enabled = True
        mock_settings.governance_backend_url = "http://localhost:8000"
        mock_settings.governance_auth_timeout_seconds = 5

        response = client.post(
            "/auth/login",
            json={"email": "user@platform.local", "password": "user123"},
        )

    assert response.status_code == 410
    body = response.json()
    assert "disabled outside dev/test" in str(body["detail"])


def test_apps_api_auth_login_proxies_and_preserves_canonical_token_shape() -> None:
    app = _build_app()
    client = TestClient(app)

    canonical_payload = {
        "access_token": "access-token-123",
        "token_type": "Bearer",
        "expires_in": 3600,
        "role": "ORG_ADMIN",
        "user_id": "user-1",
        "display_name": "Platform Admin",
    }

    with patch("apps.api.main.settings") as mock_settings, patch(
        "apps.api.routers.auth.urllib_request.urlopen",
        return_value=_MockUpstreamResponse(canonical_payload),
    ):
        mock_settings.app_env = "development"
        mock_settings.apps_api_auth_proxy_enabled = True
        mock_settings.governance_backend_url = "http://localhost:8000"
        mock_settings.governance_auth_timeout_seconds = 5

        response = client.post(
            "/auth/login",
            json={"email": "admin@platform.local", "password": "admin123"},
        )

    assert response.status_code == 200
    body = response.json()
    assert body["access_token"] == "access-token-123"
    assert body["token_type"] == "Bearer"
    assert body["expires_in"] == 3600

    # Deprecation signaling stays explicit during transition.
    assert response.headers.get("Deprecation") == "true"
