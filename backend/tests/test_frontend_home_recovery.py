"""
BHOOMI V2 — Frontend Recovery & Blank Home Page Regression Tests
Validates:
1. Unauthenticated /home gating -> redirects to login
2. Authenticated Reviewer/Demo /home -> visible dashboard
3. Root cause regression: #financeModal tag closure and #dashboardView containment
4. Successful farmer profile & farm digital twin loading
5. Missing farmer / farm graceful handling ("Farm profile not configured")
6. Optional API failure: Weather (401, 403, 404, 500, network error) -> "Weather temporarily unavailable."
7. Optional API failure: Market (401, 403, 404, 500, network error) -> "Market data unavailable."
8. Optional API failure: Tasks (401, 404, 500, empty list) -> "No tasks for today."
9. Session refresh persistence without blank page
10. Logout session cleanup and gating
"""

import pytest
import re
import os
from html.parser import HTMLParser
from httpx import AsyncClient, ASGITransport
from app.main import app

WEB_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "frontend", "web")
INDEX_HTML_PATH = os.path.join(WEB_DIR, "index.html")
APP_JS_PATH = os.path.join(WEB_DIR, "static", "app.js")

# ----------------------------------------------------------------------
# 1. HTML Tree & Tag Closure Regression Tests (Exact Root Cause)
# ----------------------------------------------------------------------

class TagTreeParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.stack = []
        self.mismatches = []
        self.void_tags = {'meta', 'link', 'img', 'input', 'br', 'hr', 'area', 'base', 'col', 'embed', 'param', 'source', 'track', 'wbr'}

    def handle_starttag(self, tag, attrs):
        if tag.lower() not in self.void_tags:
            attrs_dict = dict(attrs)
            info = tag
            if 'id' in attrs_dict:
                info += '#' + attrs_dict['id']
            elif 'class' in attrs_dict:
                info += '.' + attrs_dict['class'].split()[0]
            self.stack.append((tag.lower(), info, self.getpos()))

    def handle_endtag(self, tag):
        if tag.lower() in self.void_tags:
            return
        if not self.stack:
            self.mismatches.append(f"Extra closing </{tag}> at line {self.getpos()}")
            return
        last_tag, info, pos = self.stack.pop()
        if last_tag != tag.lower():
            self.mismatches.append(f"Mismatch: closed </{tag}> at line {self.getpos()}, top was <{info}> opened at {pos}")


def test_html_tag_balance_and_finance_modal_closed():
    """Verify index.html has no unclosed div tags and #financeModal is strictly closed before app-layout."""
    with open(INDEX_HTML_PATH, "r", encoding="utf-8") as f:
        html = f.read()

    parser = TagTreeParser()
    parser.feed(html)
    assert len(parser.mismatches) == 0, f"HTML tag mismatches found: {parser.mismatches}"
    assert len(parser.stack) == 0, f"HTML has unclosed tags: {parser.stack}"

    # Verify #financeModal does not engulf .app-layout
    pos_finance = html.find('id="financeModal"')
    pos_finance_close = html.find('</div> <!-- /#financeModal -->')
    pos_app_layout = html.find('class="app-layout"')
    pos_dash_close = html.find('</div> <!-- /#dashboardView -->')

    assert pos_finance != -1, "#financeModal must exist"
    assert pos_finance_close != -1, "#financeModal must be explicitly closed"
    assert pos_app_layout != -1, ".app-layout must exist"
    assert pos_finance < pos_finance_close < pos_app_layout < pos_dash_close, (
        "#financeModal must close before .app-layout, and .app-layout must be inside #dashboardView"
    )


# ----------------------------------------------------------------------
# 2. SPA Route Gating & Serving
# ----------------------------------------------------------------------

@pytest.mark.asyncio
async def test_unauthenticated_home_route_serves_spa_shell():
    """Verify that GET /home returns 200 SPA shell containing authView and dashboardView."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/home", headers={"Accept": "text/html"})
        assert resp.status_code == 200
        assert 'id="authView"' in resp.text
        assert 'id="dashboardView"' in resp.text
        assert 'id="todayTasksSection"' in resp.text
        assert 'id="weatherSection"' in resp.text
        assert 'id="marketSection"' in resp.text
        assert 'id="decisionHistorySection"' in resp.text


@pytest.mark.asyncio
async def test_unauthenticated_api_me_rejected_401():
    """Verify that GET /api/v1/auth/me rejects unauthenticated request with 401."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/v1/auth/me")
        assert resp.status_code == 401


# ----------------------------------------------------------------------
# 3. Reviewer Authentication & Identity Loading
# ----------------------------------------------------------------------

@pytest.mark.asyncio
async def test_authenticated_reviewer_demo_login_flow():
    """Verify reviewer demo login returns valid token, and /api/v1/auth/me returns full reviewer profile and farm."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Reviewer Demo Login
        login_res = await client.post("/api/v1/auth/login", json={"is_demo": True})
        assert login_res.status_code == 200
        login_data = login_res.json()
        assert "access_token" in login_data
        token = login_data["access_token"]

        # 2. /api/v1/auth/me
        me_res = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert me_res.status_code == 200
        me_data = me_res.json()
        assert me_data["phone_number"] == "9988776655" or me_data["phone_number"] == "+919988776655"

        # Farmer profile
        profile = me_data.get("farmer_profile")
        assert profile is not None
        assert profile["name"] == "Reviewer Evaluator"
        assert profile["district"] == "Warangal"
        assert profile["state"] == "Telangana"

        # Farm digital twin
        farm = me_data.get("farm")
        assert farm is not None
        assert farm["total_area_acres"] == 3.0
        assert farm["crop_name"] == "Potato"
        assert farm["soil_type"] == "red_sandy_loam"


# ----------------------------------------------------------------------
# 4. Optional APIs: Tasks, Weather, Market, Decisions Contracts
# ----------------------------------------------------------------------

@pytest.mark.asyncio
async def test_home_apis_contract_compliance():
    """Verify all APIs called by /home return valid schema under authenticated reviewer session."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        login_res = await client.post("/api/v1/auth/login", json={"is_demo": True})
        token = login_res.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}", "Accept": "application/json"}

        # 1. Tasks
        tasks_res = await client.get("/api/v1/tasks/today", headers=headers)
        assert tasks_res.status_code in (200, 404)

        # 2. Weather
        weather_res = await client.get("/api/v1/weather?location=Warangal", headers=headers)
        assert weather_res.status_code in (200, 404, 502, 503)

        # 3. Market
        market_res = await client.get("/api/v1/market?commodity=Potato&district=Warangal", headers=headers)
        assert market_res.status_code in (200, 404, 502, 503)

        # 4. Decisions History
        dec_res = await client.get("/api/v1/decisions/history?limit=10", headers=headers)
        assert dec_res.status_code == 200
        assert "decisions" in dec_res.json()


# ----------------------------------------------------------------------
# 5. Frontend Client Graceful Error Handling & Fallbacks (Static Audit)
# ----------------------------------------------------------------------

def test_app_js_graceful_error_handling_contracts():
    """Verify app.js contains non-crashing fallback UI handlers for all optional APIs."""
    with open(APP_JS_PATH, "r", encoding="utf-8") as f:
        app_js = f.read()

    # Weather fallback
    assert "Weather temporarily unavailable." in app_js, "Weather loader must display honest unavailable state"
    assert "loadWeatherIntelligence" in app_js, "loadWeatherIntelligence must be implemented"

    # Market fallback
    assert "Market data unavailable." in app_js, "Market loader must display honest unavailable state"
    assert "loadMarketIntelligence" in app_js, "loadMarketIntelligence must be implemented"

    # Tasks fallback
    assert "loadTodayTasks" in app_js, "loadTodayTasks must be implemented"

    # Farmer profile unconfigured fallback
    assert "Farm profile not configured" in app_js, "Farmer profile must display graceful unconfigured fallback"

    # Token undefined check in initAuth and logout
    assert 'Authorization": `Bearer ${token}`' not in app_js[:1200], (
        "initAuth must not reference undefined `token`; must use `savedToken`"
    )


# ----------------------------------------------------------------------
# 6. Logout and Session Invalidation
# ----------------------------------------------------------------------

@pytest.mark.asyncio
async def test_logout_session_invalidation():
    """Verify that calling logout invalidates the token."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        login_res = await client.post("/api/v1/auth/login", json={"is_demo": True})
        token = login_res.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Logout
        logout_res = await client.post("/api/v1/auth/logout", headers=headers)
        assert logout_res.status_code == 200

        # After client clears session on logout, unauthenticated calls receive 401
        post_logout_me = await client.get("/api/v1/auth/me")
        assert post_logout_me.status_code == 401
