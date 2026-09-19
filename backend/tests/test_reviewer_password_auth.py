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
