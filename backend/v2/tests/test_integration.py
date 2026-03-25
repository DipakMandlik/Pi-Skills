from __future__ import annotations

import pytest
from httpx import AsyncClient, ASGITransport

from backend.v2.main import create_app


@pytest.fixture
def app():
    import os
    os.environ["JWT_SECRET"] = "test-secret-key-that-is-at-least-32-characters-long"
    os.environ["ENABLE_BOOTSTRAP_SEED"] = "false"
    os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///./test_v2.db"
    return create_app()


@pytest.mark.asyncio
async def test_health_endpoint(app):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] in ("ok", "degraded")


@pytest.mark.asyncio
async def test_login_invalid_credentials(app):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post("/api/auth/login", json={"email": "nope@test.com", "password": "wrong"})
        assert resp.status_code == 401
        data = resp.json()
        assert data["success"] is False
        assert data["error"]["code"] == "AUTHENTICATION_ERROR"


@pytest.mark.asyncio
async def test_login_missing_fields(app):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post("/api/auth/login", json={"email": "bad"})
        assert resp.status_code == 422


@pytest.mark.asyncio
async def test_unauthenticated_access(app):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/skills")
        assert resp.status_code == 401
        data = resp.json()
        assert data["success"] is False


@pytest.mark.asyncio
async def test_request_id_header(app):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/health")
        assert "x-request-id" in resp.headers
        assert len(resp.headers["x-request-id"]) > 0
