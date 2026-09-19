import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app

@pytest.mark.asyncio
async def test_spa_routes_serve_index_html():
    """Verify that all SPA routes serve the single-page application entrypoint."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        routes = ["/", "/login", "/signup", "/verify-otp", "/onboarding", "/home", "/finance", "/voice", "/reviewer-login"]
        for route in routes:
            resp = await client.get(route, headers={"Accept": "text/html"})
            assert resp.status_code == 200, f"Route {route} returned status {resp.status_code}"
            assert "authLoadingSplash" in resp.text
            assert "authView" in resp.text
            assert "dashboardView" in resp.text

@pytest.mark.asyncio
async def test_auth_me_requires_authentication():
    """Verify that GET /api/v1/auth/me rejects unauthenticated callers with 401."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/v1/auth/me")
        assert resp.status_code == 401

@pytest.mark.asyncio
async def test_reviewer_login_and_auth_me_flow():
    """Verify reviewer login returns valid JWT and GET /auth/me returns valid identity."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        login_res = await client.post("/api/v1/auth/login", json={
            "phone_number": "9988776655",
            "password": "SecureReviewerPass123"
        })
        assert login_res.status_code == 200
        data = login_res.json()
        assert "access_token" in data
        token = data["access_token"]

        # Validate token against GET /api/v1/auth/me
        me_res = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert me_res.status_code == 200
        me_data = me_res.json()
        assert me_data["phone_number"] == "+919988776655" or me_data["phone_number"] == "9988776655"
        assert "onboarding_required" in me_data

        # Logout revokes session
        logout_res = await client.post("/api/v1/auth/logout", headers={"Authorization": f"Bearer {token}"})
        assert logout_res.status_code == 200

        # After client logout, unauthenticated client receives 401
        post_logout_me = await client.get("/api/v1/auth/me")
        assert post_logout_me.status_code == 401

@pytest.mark.asyncio
async def test_tampered_token_rejected_by_auth_me():
    """Verify that tampered, malformed, or fake tokens are rejected."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        for fake_token in ["demo_fake_token_123", "invalid.jwt.token", "Bearer forged"]:
            resp = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {fake_token}"})
            assert resp.status_code == 401

@pytest.mark.asyncio
async def test_login_page_renders_sms_status_notice_and_demo_button():
    """Verify that login page displays the exact SMS status notice and Reviewer Demo Login button."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/login", headers={"Accept": "text/html"})
        assert resp.status_code == 200
        html = resp.text

        # Verify exact SMS status notice
        assert "SMS OTP is not configured yet." in html
        assert "Reviewers can use Demo Login to access the prototype." in html

        # Verify Reviewer Demo Login button
        assert "btnReviewerDemoLogin" in html
        assert "Reviewer Demo Login" in html

        # Verify Farmer Login remains distinct
        assert "Farmer Login" in html
        assert "btnSendOtp" in html
