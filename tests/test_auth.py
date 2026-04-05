import pytest
import uuid

from app.services.auth_service import validate_password_strength


@pytest.mark.asyncio
async def test_register_weak_password_fails(async_client):
    resp = await async_client.post("/auth/register", json={"email":"weak@example.com","password":"weak","full_name":"Weak"})
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_register_success(async_client):
    email = f"{uuid.uuid4()}@example.com"
    resp = await async_client.post("/auth/register", json={"email": email, "password": "Strong1!", "full_name": "Test User"})
    assert resp.status_code == 201
    assert resp.json()["success"]
    assert resp.json()["data"]["role"] == "viewer"


@pytest.mark.asyncio
async def test_register_ignores_role_field(async_client):
    email = f"{uuid.uuid4()}@example.com"
    resp = await async_client.post("/auth/register", json={"email": email, "password": "Strong1!", "full_name": "Role Check", "role": "admin"})
    assert resp.status_code == 201
    assert resp.json()["data"]["role"] == "viewer"


@pytest.mark.asyncio
async def test_login_succeeds_and_returns_tokens(async_client):
    await async_client.post("/auth/register", json={"email":"loginuser@example.com","password":"Strong1!","full_name":"Login User"})
    resp = await async_client.post("/auth/login", json={"email":"loginuser@example.com","password":"Strong1!"})
    assert resp.status_code == 200
    assert "access_token" in resp.json()["data"]


@pytest.mark.asyncio
async def test_login_wrong_password_returns_generic_error(async_client):
    resp = await async_client.post("/auth/login", json={"email":"loginuser@example.com","password":"Wrong1!x"})
    assert resp.status_code == 401
    assert resp.json()["error"]


@pytest.mark.asyncio
async def test_refresh_succeeds_and_revokes_old_token(async_client):
    await async_client.post("/auth/register", json={"email":"refreshuser@example.com","password":"Strong1!","full_name":"Refresh User"})
    login_resp = await async_client.post("/auth/login", json={"email":"refreshuser@example.com","password":"Strong1!"})
    assert login_resp.status_code == 200
    refresh_token = login_resp.json()["data"]["refresh_token"]

    refresh_resp = await async_client.post("/auth/refresh", json={"refresh_token": refresh_token})
    assert refresh_resp.status_code == 200
    assert refresh_resp.json()["data"]["access_token"]
    assert refresh_resp.json()["data"]["refresh_token"]

    refresh_resp2 = await async_client.post("/auth/refresh", json={"refresh_token": refresh_token})
    assert refresh_resp2.status_code == 401
    assert refresh_resp2.json()["error"]
    assert refresh_resp2.json()["code"] == "TOKEN_REVOKED"


@pytest.mark.asyncio
async def test_password_strength_validator():
    with pytest.raises(Exception):
        validate_password_strength("weak")
