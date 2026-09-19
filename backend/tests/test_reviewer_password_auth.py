"""
BHOOMI — Option A: Secure Reviewer Password Authentication Test Suite
Verifies:
1. Reviewer login with valid credentials -> PASS
2. Wrong reviewer password -> rejected
3. Unknown reviewer phone -> rejected
4. Missing phone -> rejected
5. Missing password -> rejected
6. Malformed credentials -> rejected
7. Successful login produces valid JWT
8. JWT authenticates dashboard/API requests
9. No JWT without valid credentials
10. Reviewer password is not returned by API
11. Password is not stored plaintext
12. Production still rejects 1234
13. Evaluator OTP remains disabled in production
14. Idempotent reviewer provisioning
"""

import os
import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient

from app.main import app
from app.core.config import settings
from app.core.security import get_password_hash, verify_password
from app.db.session import AsyncSessionLocal
from app.models.user import User
from app.services.reviewer_provisioning import ensure_reviewer_account
from sqlalchemy.future import select

client = TestClient(app)

TEST_REVIEWER_PHONE = "9988776655"
TEST_REVIEWER_PW = "SecureReviewerPass123"


@pytest.fixture(scope="module", autouse=True)
def setup_test_reviewer():
    """Ensure a test reviewer is provisioned in the database."""
    import asyncio

    async def _provision():
        async with AsyncSessionLocal() as session:
            with patch.dict(os.environ, {
                "REVIEWER_PHONE": TEST_REVIEWER_PHONE,
                "REVIEWER_PASSWORD": TEST_REVIEWER_PW
            }):
                await ensure_reviewer_account(session)

    asyncio.run(_provision())


class TestReviewerPasswordAuthentication:
    """Covers reviewer password authentication & security guarantees."""

    # 1. Valid credentials -> PASS (HTTP 200, JWT returned)
    def test_01_valid_reviewer_login_success(self):
        res = client.post("/api/v1/auth/login", json={
            "phone_number": TEST_REVIEWER_PHONE,
            "password": TEST_REVIEWER_PW
        })
        assert res.status_code == 200, f"Login failed: {res.text}"
        data = res.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert len(data["access_token"]) > 20
        assert data["name"] == "Reviewer Evaluator"
        assert data["crop_name"] == "Potato"
        assert data["farm_id"] is not None

    # 2. Valid credentials with +91 prefix -> PASS
    def test_02_valid_reviewer_login_with_prefix(self):
        res = client.post("/api/v1/auth/login", json={
            "phone_number": f"+91{TEST_REVIEWER_PHONE}",
            "password": TEST_REVIEWER_PW
        })
        assert res.status_code == 200
        data = res.json()
        assert "access_token" in data

    # 3. Wrong password -> rejected (HTTP 401)
    def test_03_wrong_reviewer_password_rejected(self):
        res = client.post("/api/v1/auth/login", json={
            "phone_number": TEST_REVIEWER_PHONE,
            "password": "IncorrectPassword999"
        })
        assert res.status_code == 401
        assert "Incorrect phone number or password" in res.json()["detail"]

    # 4. Unknown phone number -> rejected (HTTP 401)
    def test_04_unknown_reviewer_phone_rejected(self):
        res = client.post("/api/v1/auth/login", json={
            "phone_number": "9000000000",
            "password": TEST_REVIEWER_PW
        })
        assert res.status_code == 401
        assert "Incorrect phone number or password" in res.json()["detail"]

    # 5. Missing phone number -> rejected (HTTP 422)
    def test_05_missing_phone_rejected(self):
        res = client.post("/api/v1/auth/login", json={
            "password": TEST_REVIEWER_PW
        })
        assert res.status_code == 422

    # 6. Missing password -> rejected (HTTP 422)
    def test_06_missing_password_rejected(self):
        res = client.post("/api/v1/auth/login", json={
            "phone_number": TEST_REVIEWER_PHONE
        })
        assert res.status_code == 422

    # 7. Malformed credentials payload -> rejected (HTTP 422)
    def test_07_malformed_credentials_rejected(self):
        res = client.post("/api/v1/auth/login", json={
            "phone_number": ["invalid_type"],
            "password": 12345
        })
        assert res.status_code == 422

    # 8. Successful login produces valid JWT that authenticates API requests
    def test_08_jwt_authenticates_dashboard_api(self):
        res_login = client.post("/api/v1/auth/login", json={
            "phone_number": TEST_REVIEWER_PHONE,
            "password": TEST_REVIEWER_PW
        })
        assert res_login.status_code == 200
        jwt_token = res_login.json()["access_token"]

        # Call authenticated assistant chat endpoint
        with patch.object(settings, "ENVIRONMENT", "production"), \
             patch.object(settings, "DEMO_MODE", False):
            res_api = client.post(
                "/api/v1/assistant/chat",
                headers={"Authorization": f"Bearer {jwt_token}"},
                json={"message": "What is the recommended fertilizer for potato?", "language_code": "en"}
            )
            assert res_api.status_code == 200
            data_api = res_api.json()
            assert data_api["status"] == "success"

    # 9. No JWT without valid credentials -> HTTP 401 in production
    def test_09_unauthorized_dashboard_api_returns_401(self):
        with patch.object(settings, "ENVIRONMENT", "production"), \
             patch.object(settings, "DEMO_MODE", False):
            res = client.post(
                "/api/v1/assistant/chat",
                json={"message": "What is the recommended fertilizer?", "language_code": "en"}
            )
            assert res.status_code == 401

    # 10. Reviewer password is not returned by API
    def test_10_reviewer_password_never_returned_by_api(self):
        res_login = client.post("/api/v1/auth/login", json={
            "phone_number": TEST_REVIEWER_PHONE,
            "password": TEST_REVIEWER_PW
        })
        assert res_login.status_code == 200
        raw_text = res_login.text
        assert TEST_REVIEWER_PW not in raw_text
        assert "password" not in res_login.json()
        assert "hashed_password" not in res_login.json()

    # 11. Password is not stored plaintext in database
    def test_11_password_stored_as_bcrypt_hash(self):
        import asyncio

        async def _check_db():
            async with AsyncSessionLocal() as session:
                res = await session.execute(
                    select(User).where(User.phone_number.in_([TEST_REVIEWER_PHONE, f"+91{TEST_REVIEWER_PHONE}"]))
                )
                user = res.scalars().first()
                assert user is not None
                assert user.hashed_password != TEST_REVIEWER_PW
                assert user.hashed_password.startswith("$2b$") or user.hashed_password.startswith("$2a$")
                assert verify_password(TEST_REVIEWER_PW, user.hashed_password) is True

        asyncio.run(_check_db())

    # 12. Production still rejects 1234
    def test_12_production_rejects_1234(self):
        with patch.object(settings, "ENVIRONMENT", "production"), \
             patch.object(settings, "ALLOW_EVALUATOR_OTP", False):
            # Test A: without prior session
            res_no_session = client.post("/api/v1/auth/verify-otp", json={
                "phone_number": TEST_REVIEWER_PHONE,
                "otp": "1234"
            })
            assert res_no_session.status_code == 400

            # Test B: with active session, attempt 1234 bypass
            client.post("/api/v1/auth/send-otp", json={"phone_number": TEST_REVIEWER_PHONE})
            res = client.post("/api/v1/auth/verify-otp", json={
                "phone_number": TEST_REVIEWER_PHONE,
                "otp": "1234"
            })
            assert res.status_code == 400
            assert "Invalid verification code" in res.json()["detail"]

    # 13. Evaluator OTP remains disabled in production
    def test_13_evaluator_otp_disabled_in_production(self):
        prod_phone = "9988776650"
        with patch.object(settings, "ENVIRONMENT", "production"), \
             patch.object(settings, "ALLOW_EVALUATOR_OTP", False):
            res_send = client.post("/api/v1/auth/send-otp", json={
                "phone_number": prod_phone
            })
            assert res_send.status_code == 200
            data_send = res_send.json()
            assert data_send["auth_mode"] == "production"
            assert data_send["delivery_channel"] == "none"
            assert "otp" not in data_send
            assert "otp_code" not in data_send

    # 14. Reviewer account provisioning is idempotent
    def test_14_provisioning_is_idempotent(self):
        import asyncio

        async def _test_idem():
            async with AsyncSessionLocal() as session:
                with patch.dict(os.environ, {
                    "REVIEWER_PHONE": TEST_REVIEWER_PHONE,
                    "REVIEWER_PASSWORD": TEST_REVIEWER_PW
                }):
                    # Running again must return False (already exists) without error
                    result = await ensure_reviewer_account(session)
                    assert result is False

        asyncio.run(_test_idem())

    # 15. Reviewer farm, crop, area, and soil are genuinely DB-backed
    def test_15_reviewer_digital_twin_db_backed(self):
        res = client.post("/api/v1/auth/login", json={
            "phone_number": TEST_REVIEWER_PHONE,
            "password": TEST_REVIEWER_PW
        })
        assert res.status_code == 200
        data = res.json()
        assert data["farm_id"] == f"farm_reviewer_{TEST_REVIEWER_PHONE}"
        assert data["crop_name"] == "Potato"
        assert data["area_acres"] == 3.0
        assert data["soil_type"] == "red_sandy_loam"

    # 16. Normal farmer receives own farm, crop, area, and soil from database
    def test_16_normal_farmer_receives_own_data(self):
        import asyncio
        from decimal import Decimal
        from app.models.farmer import FarmerProfile
        from app.models.farm import Farm
        from app.models.crop import FarmCrop

        normal_phone = "9112233445"
        normal_pw = "CustomFarmerPass1"

        async def _seed_custom_farmer():
            async with AsyncSessionLocal() as session:
                res_u = await session.execute(select(User).where(User.phone_number == normal_phone))
                u = res_u.scalars().first()
                if not u:
                    u = User(id="custom_farmer_u1", phone_number=normal_phone, hashed_password=get_password_hash(normal_pw))
                    session.add(u)
                    await session.flush()
                    prof = FarmerProfile(id="prof_custom_u1", user_id=u.id, name="Srinivas Rao", state="Telangana", district="Khammam")
                    session.add(prof)
                    await session.flush()
                    farm = Farm(id="farm_custom_cotton_1", farmer_id=prof.id, farm_name="Khammam Cotton Farm", total_area_acres=Decimal("7.5"), soil_type="black_cotton")
                    session.add(farm)
                    await session.flush()
                    crop = FarmCrop(id="crop_custom_cotton_1", farm_id=farm.id, crop_name="Cotton", variety="Bt-Cotton", area_acres=Decimal("7.5"))
                    session.add(crop)
                    await session.commit()

        asyncio.run(_seed_custom_farmer())

        res = client.post("/api/v1/auth/login", json={
            "phone_number": normal_phone,
            "password": normal_pw
        })
        assert res.status_code == 200
        data = res.json()
        assert data["farm_id"] == "farm_custom_cotton_1"
        assert data["crop_name"] == "Cotton"
        assert data["area_acres"] == 7.5
        assert data["soil_type"] == "black_cotton"

    # 17. Un-onboarded user receives null/unconfigured farm context
    def test_17_un_onboarded_user_receives_null_farm_context(self):
        import asyncio
        unonboarded_phone = "9223344556"
        unonboarded_pw = "UnonboardedPass1"

        async def _seed_unonboarded_user():
            async with AsyncSessionLocal() as session:
                res_u = await session.execute(select(User).where(User.phone_number == unonboarded_phone))
                u = res_u.scalars().first()
                if not u:
                    u = User(id="unonboarded_u1", phone_number=unonboarded_phone, hashed_password=get_password_hash(unonboarded_pw))
                    session.add(u)
                    await session.flush()
                    from app.models.farmer import FarmerProfile
                    prof = FarmerProfile(id="prof_unonboarded_1", user_id=u.id, name="New Farmer", preferred_language="en")
                    session.add(prof)
                    await session.commit()

        asyncio.run(_seed_unonboarded_user())

        res = client.post("/api/v1/auth/login", json={
            "phone_number": unonboarded_phone,
            "password": unonboarded_pw
        })
        assert res.status_code == 200
        data = res.json()
        # Must strictly be null/None — never fabricated defaults
        assert data["farm_id"] is None
        assert data["crop_name"] is None
        assert data["area_acres"] is None
        assert data["soil_type"] is None
        assert data["is_new_user"] is True

    # 18. Un-onboarded user never receives Potato, 3.0, or red_sandy_loam
    def test_18_un_onboarded_user_never_gets_fabricated_defaults(self):
        unonboarded_phone = "9223344556"
        unonboarded_pw = "UnonboardedPass1"

        res = client.post("/api/v1/auth/login", json={
            "phone_number": unonboarded_phone,
            "password": unonboarded_pw
        })
        assert res.status_code == 200
        data = res.json()
        assert data["crop_name"] != "Potato"
        assert data["area_acres"] != 3.0
        assert data["soil_type"] != "red_sandy_loam"

    # 19. Farm isolation remains strictly enforced across accounts
    def test_19_farm_isolation_strictly_enforced(self):
        # Normal farmer cannot get reviewer farm
        res_normal = client.post("/api/v1/auth/login", json={
            "phone_number": "9112233445",
            "password": "CustomFarmerPass1"
        })
        assert res_normal.status_code == 200
        data_normal = res_normal.json()
        assert data_normal["farm_id"] != f"farm_reviewer_{TEST_REVIEWER_PHONE}"
        assert data_normal["crop_name"] != "Potato"

        # Reviewer cannot get normal farmer farm
        res_rev = client.post("/api/v1/auth/login", json={
            "phone_number": TEST_REVIEWER_PHONE,
            "password": TEST_REVIEWER_PW
        })
        assert res_rev.status_code == 200
        data_rev = res_rev.json()
        assert data_rev["farm_id"] != "farm_custom_cotton_1"
        assert data_rev["crop_name"] != "Cotton"

    # 20. Reviewer Demo Login succeeds without hardcoded client password
    def test_20_reviewer_demo_login_success(self):
        res = client.post("/api/v1/auth/login", json={"is_demo": True})
        assert res.status_code == 200, f"Demo login failed: {res.text}"
        data = res.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"
        assert data["name"] == "Reviewer Evaluator"
        assert data["crop_name"] == "Potato"
        assert data["farm_id"] is not None

    # 21. Reviewer Demo JWT authenticates /api/v1/auth/me
    def test_21_reviewer_demo_authenticates_me(self):
        res_login = client.post("/api/v1/auth/login", json={"is_demo": True})
        assert res_login.status_code == 200
        token = res_login.json()["access_token"]

        res_me = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert res_me.status_code == 200
        me_data = res_me.json()
        assert me_data["farmer_profile"]["name"] == "Reviewer Evaluator"
        assert me_data["farm"]["crop_name"] == "Potato"
        assert me_data["farm"]["soil_type"] == "red_sandy_loam"
        assert me_data["onboarding_required"] is False

    # 22. Reviewer Demo Session can be refreshed via /api/v1/auth/refresh
    def test_22_reviewer_demo_session_refresh(self):
        res_login = client.post("/api/v1/auth/login", json={"is_demo": True})
        assert res_login.status_code == 200
        refresh_tok = res_login.json()["refresh_token"]
        assert refresh_tok is not None

        res_ref = client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_tok})
        assert res_ref.status_code == 200
        ref_data = res_ref.json()
        assert "access_token" in ref_data
        assert "refresh_token" in ref_data

    # 23. Logout revokes the reviewer demo session
    def test_23_reviewer_demo_logout_revocation(self):
        res_login = client.post("/api/v1/auth/login", json={"is_demo": True})
        assert res_login.status_code == 200
        access_tok = res_login.json()["access_token"]
        refresh_tok = res_login.json()["refresh_token"]

        # Logout with bearer token
        res_logout = client.post(
            "/api/v1/auth/logout",
            headers={"Authorization": f"Bearer {access_tok}"},
            json={"refresh_token": refresh_tok}
        )
        assert res_logout.status_code == 200
        assert res_logout.json()["success"] is True

        # Subsequent refresh with revoked token must fail with 401
        res_ref_fail = client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_tok})
        assert res_ref_fail.status_code == 401

    # 24. Missing credentials without is_demo=True still rejected with 422
    def test_24_missing_credentials_without_demo_rejected(self):
        res = client.post("/api/v1/auth/login", json={})
        assert res.status_code == 422

    # 25. Farmer OTP routes remain fail-closed when SMS transport unconfigured
    def test_25_farmer_otp_routes_remain_fail_closed_in_prod(self):
        with patch.object(settings, "ENVIRONMENT", "production"), \
             patch.object(settings, "SMS_PROVIDER", "console"):
            res = client.post("/api/v1/auth/signup/request-otp", json={"phone_number": "9911991199"})
            assert res.status_code == 502

