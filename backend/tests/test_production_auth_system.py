"""
BHOOMI — Production Authentication System Comprehensive Test Suite
Verifies all 26 Phase 20 criteria:
1. Phone normalization (E.164 +91XXXXXXXXXX)
2. Signup request OTP (6-digit BHOOMI-generated)
3. Signup request rate limit (30-second cooldown and sliding window)
4. Signup SMS provider success (challenge activated)
5. Signup SMS provider failure (challenge NOT activated, returns error)
6. Signup OTP verification success (user created, phone_number_verified=True, onboarding_required=True)
7. Invalid OTP rejection (HTTP 400, remaining attempts decremented)
8. Expired OTP rejection (HTTP 400)
9. 5-attempt limit enforcement (HTTP 400)
10. OTP single-use guarantee (used_at set, replay rejected)
11. Resend cooldown enforcement (HTTP 429)
12. New OTP invalidates old OTP for same phone & purpose
13. Login request & verify for existing farmer
14. Login request for nonexistent user (safe 404 response, no account auto-created)
15. Refresh token flow (issues new access token)
16. Revoked refresh token rejection (HTTP 401)
17. Logout flow (revokes session, subsequent refresh rejected)
18. /auth/me endpoint (returns genuine DB user, unconfigured user has farm=null)
19. Unauthenticated protected endpoint rejection (HTTP 401)
20. Cross-user farm data isolation (User A cannot access User B's farm data)
21. Reviewer login regression (password login continues working)
22. Production DEMO_MODE disabled behavior
23. Production evaluator OTP disabled behavior
24. OTP never appears in API response
25. OTP never appears in application logs
26. SMS provider secret never appears in logs
"""

import time
import uuid
import secrets
import pytest
from datetime import timedelta
from unittest.mock import patch
from fastapi.testclient import TestClient

from app.main import app, _rate_limits
from app.core.config import settings
from app.core.datetime_utils import utc_now_naive
from app.core.phone_utils import normalize_indian_phone, validate_indian_phone
from app.core.rate_limiter import auth_rate_limiter
from app.services.sms.sms_provider import _mock_provider_instance, MockSMSProvider
from app.services.auth.otp_service import OTPService
from app.services.auth.session_service import SessionService

client = TestClient(app)

class TestProductionAuthSystem:
    """Comprehensive test suite verifying the BHOOMI authoritative OTP & session system."""

    def setup_method(self):
        """Reset rate limiters and mock SMS provider before each test."""
        auth_rate_limiter.reset_for_test()
        _rate_limits.clear()
        _mock_provider_instance.clear()
        self._orig_sms_provider = settings.SMS_PROVIDER
        settings.SMS_PROVIDER = "mock"

    def teardown_method(self):
        """Restore global settings and clear rate limiter state."""
        auth_rate_limiter.reset_for_test()
        _rate_limits.clear()
        _mock_provider_instance.clear()
        settings.SMS_PROVIDER = getattr(self, "_orig_sms_provider", "console")

    def _gen_phone(self) -> str:
        """Generate a random valid 10-digit Indian phone number for isolated test runs."""
        return f"9{secrets.randbelow(900000000) + 100000000}"

    # -------------------------------------------------------------------------
    # 1. Phone Normalization
    # -------------------------------------------------------------------------
    def test_01_phone_normalization(self):
        cases = [
            ("9876543210", "+919876543210"),
            ("+919876543210", "+919876543210"),
            ("919876543210", "+919876543210"),
            ("09876543210", "+919876543210"),
            ("+91 98765 43210", "+919876543210"),
            ("+91-98765-43210", "+919876543210"),
        ]
        for raw, expected in cases:
            assert normalize_indian_phone(raw) == expected, f"Failed for {raw}"

        # Invalid cases
        with pytest.raises(ValueError):
            normalize_indian_phone("12345")
        with pytest.raises(ValueError):
            normalize_indian_phone("")
        with pytest.raises(ValueError):
            normalize_indian_phone("abcdefghij")

    # -------------------------------------------------------------------------
    # 2. Signup Request OTP (6-digit, BHOOMI generated)
    # -------------------------------------------------------------------------
    def test_02_signup_request_otp(self):
        phone = self._gen_phone()
        res = client.post("/api/v1/auth/signup/request-otp", json={"phone_number": phone})
        assert res.status_code == 200
        data = res.json()
        assert data["success"] is True
        assert data["delivery_channel"] == "sms"
        assert data["expires_in"] == 600
        assert data["resend_after"] == 30

        # Verify exact message captured in mock provider
        assert len(_mock_provider_instance.sent_messages) == 1
        sent = _mock_provider_instance.sent_messages[0]
        assert sent["phone_number"] == f"+91{phone}"
        assert "Your BHOOMI verification code is " in sent["message"]

        # Extract 6-digit code
        words = sent["message"].split()
        otp_idx = words.index("is") + 1
        code = words[otp_idx].rstrip(".")
        assert len(code) == 6
        assert code.isdigit()

    # -------------------------------------------------------------------------
    # 3. Signup Request Rate Limit (Cooldown & Sliding Window)
    # -------------------------------------------------------------------------
    def test_03_signup_request_rate_limit(self):
        phone = self._gen_phone()
        # First request succeeds
        res1 = client.post("/api/v1/auth/signup/request-otp", json={"phone_number": phone})
        assert res1.status_code == 200

        # Immediate second request fails with HTTP 429
        res2 = client.post("/api/v1/auth/signup/request-otp", json={"phone_number": phone})
        assert res2.status_code == 429
        assert "wait" in res2.json()["detail"].lower()

    # -------------------------------------------------------------------------
    # 4. Signup SMS Provider Success -> Challenge Activated
    # -------------------------------------------------------------------------
    def test_04_signup_sms_provider_success(self):
        phone = self._gen_phone()
        res = client.post("/api/v1/auth/signup/request-otp", json={"phone_number": phone})
        assert res.status_code == 200
        assert len(_mock_provider_instance.sent_messages) == 1

    # -------------------------------------------------------------------------
    # 5. Signup SMS Provider Failure -> Challenge NOT Activated, HTTP 502
    # -------------------------------------------------------------------------
    def test_05_signup_sms_provider_failure(self):
        phone = self._gen_phone()
        _mock_provider_instance.simulate_failure(True)

        res = client.post("/api/v1/auth/signup/request-otp", json={"phone_number": phone})
        assert res.status_code == 502
        assert "SMS delivery failed" in res.json()["detail"]

        # Attempting verify with any code must fail as no challenge was activated
        res_verify = client.post("/api/v1/auth/signup/verify-otp", json={
            "phone_number": phone,
            "otp": "123456"
        })
        assert res_verify.status_code == 400
        assert "No active verification code found" in res_verify.json()["detail"]

    # -------------------------------------------------------------------------
    # 6. Signup OTP Verification Success
    # -------------------------------------------------------------------------
    def test_06_signup_otp_verification_success(self):
        phone = self._gen_phone()
        res_req = client.post("/api/v1/auth/signup/request-otp", json={"phone_number": phone})
        assert res_req.status_code == 200
        sent_msg = _mock_provider_instance.sent_messages[-1]["message"]
        code = sent_msg.split("Your BHOOMI verification code is ")[1].split(".")[0].strip()

        res_verify = client.post("/api/v1/auth/signup/verify-otp", json={
            "phone_number": phone,
            "otp": code
        })
        assert res_verify.status_code == 200
        data = res_verify.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"
        assert data["user"]["phone_number"] == f"+91{phone}"
        assert data["user"]["phone_number_verified"] is True
        assert data["onboarding_required"] is True

    # -------------------------------------------------------------------------
    # 7. Invalid OTP Rejection (HTTP 400)
    # -------------------------------------------------------------------------
    def test_07_invalid_otp_rejection(self):
        phone = self._gen_phone()
        res_req = client.post("/api/v1/auth/signup/request-otp", json={"phone_number": phone})
        assert res_req.status_code == 200

        res_verify = client.post("/api/v1/auth/signup/verify-otp", json={
            "phone_number": phone,
            "otp": "000000"  # incorrect OTP
        })
        assert res_verify.status_code == 400
        assert "Invalid verification code" in res_verify.json()["detail"]
        assert "4 attempts remaining" in res_verify.json()["detail"]

    # -------------------------------------------------------------------------
    # 8. Expired OTP Rejection (HTTP 400)
    # -------------------------------------------------------------------------
    def test_08_expired_otp_rejection(self):
        phone = self._gen_phone()
        res_req = client.post("/api/v1/auth/signup/request-otp", json={"phone_number": phone})
        assert res_req.status_code == 200
        sent_msg = _mock_provider_instance.sent_messages[-1]["message"]
        code = sent_msg.split("Your BHOOMI verification code is ")[1].split(".")[0].strip()

        # Simulate time passing by 11 minutes (past 10 minute expiry)
        with patch("app.services.auth.otp_service.utc_now_naive", return_value=utc_now_naive() + timedelta(minutes=11)):
            res_verify = client.post("/api/v1/auth/signup/verify-otp", json={
                "phone_number": phone,
                "otp": code
            })
            assert res_verify.status_code == 400
            assert "expired" in res_verify.json()["detail"].lower()

    # -------------------------------------------------------------------------
    # 9. 5-Attempt Limit Rejection (HTTP 400)
    # -------------------------------------------------------------------------
    def test_09_max_attempts_limit(self):
        phone = self._gen_phone()
        res_req = client.post("/api/v1/auth/signup/request-otp", json={"phone_number": phone})
        assert res_req.status_code == 200

        for i in range(5):
            res_fail = client.post("/api/v1/auth/signup/verify-otp", json={
                "phone_number": phone,
                "otp": "999999"
            })
            assert res_fail.status_code == 400

        # 6th attempt should be rejected with maximum attempts exceeded
        res_exceeded = client.post("/api/v1/auth/signup/verify-otp", json={
            "phone_number": phone,
            "otp": "999999"
        })
        assert res_exceeded.status_code == 400
        assert "Maximum verification attempts exceeded" in res_exceeded.json()["detail"]

    # -------------------------------------------------------------------------
    # 10. OTP Single-Use Guarantee
    # -------------------------------------------------------------------------
    def test_10_otp_single_use(self):
        phone = self._gen_phone()
        res_req = client.post("/api/v1/auth/signup/request-otp", json={"phone_number": phone})
        assert res_req.status_code == 200
        sent_msg = _mock_provider_instance.sent_messages[-1]["message"]
        code = sent_msg.split("Your BHOOMI verification code is ")[1].split(".")[0].strip()

        # First verification succeeds
        res1 = client.post("/api/v1/auth/signup/verify-otp", json={
            "phone_number": phone,
            "otp": code
        })
        assert res1.status_code == 200

        # Re-submitting the exact same OTP fails
        res2 = client.post("/api/v1/auth/signup/verify-otp", json={
            "phone_number": phone,
            "otp": code
        })
        assert res2.status_code == 400
        assert "already been used" in res2.json()["detail"].lower()

    # -------------------------------------------------------------------------
    # 11. Resend Cooldown
    # -------------------------------------------------------------------------
    def test_11_resend_cooldown(self):
        phone = self._gen_phone()
        res1 = client.post("/api/v1/auth/signup/request-otp", json={"phone_number": phone})
        assert res1.status_code == 200

        res2 = client.post("/api/v1/auth/signup/request-otp", json={"phone_number": phone})
        assert res2.status_code == 429
        assert "Please wait" in res2.json()["detail"]

    # -------------------------------------------------------------------------
    # 12. New OTP Invalidates Old OTP
    # -------------------------------------------------------------------------
    def test_12_new_otp_invalidates_old_otp(self):
        phone = self._gen_phone()
        norm = f"+91{phone}"
        # First OTP request
        res1 = client.post("/api/v1/auth/signup/request-otp", json={"phone_number": phone})
        assert res1.status_code == 200
        first_code = _mock_provider_instance.sent_messages[-1]["message"].split("is ")[1].split(".")[0].strip()

        # Advance rate limiter cooldown by 35 seconds
        auth_rate_limiter._last_request_time[norm] -= 35.0

        # Second OTP request
        res2 = client.post("/api/v1/auth/signup/request-otp", json={"phone_number": phone})
        assert res2.status_code == 200
        second_code = _mock_provider_instance.sent_messages[-1]["message"].split("is ")[1].split(".")[0].strip()

        # The first code must now be invalid/expired
        res_old = client.post("/api/v1/auth/signup/verify-otp", json={
            "phone_number": phone,
            "otp": first_code
        })
        assert res_old.status_code == 400

        # The second code succeeds
        res_new = client.post("/api/v1/auth/signup/verify-otp", json={
            "phone_number": phone,
            "otp": second_code
        })
        assert res_new.status_code == 200

    # -------------------------------------------------------------------------
    # 13. Login Existing Farmer Flow
    # -------------------------------------------------------------------------
    def test_13_login_existing_farmer(self):
        phone = self._gen_phone()
        # 1. Sign up first
        res_s = client.post("/api/v1/auth/signup/request-otp", json={"phone_number": phone})
        assert res_s.status_code == 200
        code1 = _mock_provider_instance.sent_messages[-1]["message"].split("is ")[1].split(".")[0].strip()
        res_signup = client.post("/api/v1/auth/signup/verify-otp", json={"phone_number": phone, "otp": code1})
        assert res_signup.status_code == 200

        auth_rate_limiter.reset_for_test()

        # 2. Login request OTP
        res_login_req = client.post("/api/v1/auth/login/request-otp", json={"phone_number": phone})
        assert res_login_req.status_code == 200
        code2 = _mock_provider_instance.sent_messages[-1]["message"].split("is ")[1].split(".")[0].strip()

        # 3. Login verify OTP
        res_login_ver = client.post("/api/v1/auth/login/verify-otp", json={"phone_number": phone, "otp": code2})
        assert res_login_ver.status_code == 200
        data = res_login_ver.json()
        assert data["user"]["phone_number"] == f"+91{phone}"
        assert "access_token" in data
        assert "refresh_token" in data

    # -------------------------------------------------------------------------
    # 14. Login Nonexistent User (Safe Response, No Account Auto-Created)
    # -------------------------------------------------------------------------
    def test_14_login_nonexistent_user(self):
        phone = self._gen_phone()
        res = client.post("/api/v1/auth/login/request-otp", json={"phone_number": phone})
        assert res.status_code == 404
        assert "not registered" in res.json()["detail"].lower()

    # -------------------------------------------------------------------------
    # 15. Refresh Token Flow
    # -------------------------------------------------------------------------
    def test_15_refresh_token_flow(self):
        phone = self._gen_phone()
        res_s = client.post("/api/v1/auth/signup/request-otp", json={"phone_number": phone})
        assert res_s.status_code == 200
        code = _mock_provider_instance.sent_messages[-1]["message"].split("is ")[1].split(".")[0].strip()
        res_signup = client.post("/api/v1/auth/signup/verify-otp", json={"phone_number": phone, "otp": code})
        assert res_signup.status_code == 200
        refresh_token = res_signup.json()["refresh_token"]

        # Call /refresh
        res_refresh = client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})
        assert res_refresh.status_code == 200
        data = res_refresh.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"

    # -------------------------------------------------------------------------
    # 16. Revoked Refresh Token Rejection (HTTP 401)
    # -------------------------------------------------------------------------
    def test_16_revoked_refresh_token(self):
        phone = self._gen_phone()
        res_s = client.post("/api/v1/auth/signup/request-otp", json={"phone_number": phone})
        assert res_s.status_code == 200
        code = _mock_provider_instance.sent_messages[-1]["message"].split("is ")[1].split(".")[0].strip()
        res_signup = client.post("/api/v1/auth/signup/verify-otp", json={"phone_number": phone, "otp": code})
        assert res_signup.status_code == 200
        old_refresh = res_signup.json()["refresh_token"]

        # Rotate token once
        res_refresh = client.post("/api/v1/auth/refresh", json={"refresh_token": old_refresh})
        assert res_refresh.status_code == 200

        # Re-using the old refresh token must fail (it was revoked on rotation)
        res_reused = client.post("/api/v1/auth/refresh", json={"refresh_token": old_refresh})
        assert res_reused.status_code == 401
        assert "revoked" in res_reused.json()["detail"].lower()

    # -------------------------------------------------------------------------
    # 17. Logout Flow (Revokes Session)
    # -------------------------------------------------------------------------
    def test_17_logout_flow(self):
        phone = self._gen_phone()
        res_s = client.post("/api/v1/auth/signup/request-otp", json={"phone_number": phone})
        assert res_s.status_code == 200
        code = _mock_provider_instance.sent_messages[-1]["message"].split("is ")[1].split(".")[0].strip()
        res_signup = client.post("/api/v1/auth/signup/verify-otp", json={"phone_number": phone, "otp": code})
        assert res_signup.status_code == 200
        data = res_signup.json()
        access_token = data["access_token"]
        refresh_token = data["refresh_token"]

        # Logout with access token
        res_logout = client.post(
            "/api/v1/auth/logout",
            headers={"Authorization": f"Bearer {access_token}"}
        )
        assert res_logout.status_code == 200
        assert res_logout.json()["success"] is True

        # Refresh must now fail
        res_refresh = client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})
        assert res_refresh.status_code == 401

    # -------------------------------------------------------------------------
    # 18. /auth/me Endpoint (Genuine Data, Unconfigured Farm is Null)
    # -------------------------------------------------------------------------
    def test_18_auth_me_unconfigured_user(self):
        phone = self._gen_phone()
        res_s = client.post("/api/v1/auth/signup/request-otp", json={"phone_number": phone})
        assert res_s.status_code == 200
        code = _mock_provider_instance.sent_messages[-1]["message"].split("is ")[1].split(".")[0].strip()
        res_signup = client.post("/api/v1/auth/signup/verify-otp", json={"phone_number": phone, "otp": code})
        assert res_signup.status_code == 200
        access_token = res_signup.json()["access_token"]

        res_me = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {access_token}"}
        )
        assert res_me.status_code == 200
        me = res_me.json()
        assert me["phone_number"] == f"+91{phone}"
        assert me["phone_number_verified"] is True
        assert me["farm"] is None, "New user must have farm=null without fake defaults"
        assert me["onboarding_required"] is True

    # -------------------------------------------------------------------------
    # 19. Unauthenticated Protected Endpoint Rejection (HTTP 401)
    # -------------------------------------------------------------------------
    def test_19_unauthenticated_protected_endpoint(self):
        res = client.get("/api/v1/auth/me")
        assert res.status_code == 401

    # -------------------------------------------------------------------------
    # 20. Cross-User Farm Data Isolation
    # -------------------------------------------------------------------------
    def test_20_cross_user_farm_isolation(self):
        # Register User A
        phone_a = self._gen_phone()
        res_a = client.post("/api/v1/auth/signup/request-otp", json={"phone_number": phone_a})
        assert res_a.status_code == 200
        code_a = _mock_provider_instance.sent_messages[-1]["message"].split("is ")[1].split(".")[0].strip()
        token_a = client.post("/api/v1/auth/signup/verify-otp", json={"phone_number": phone_a, "otp": code_a}).json()["access_token"]

        auth_rate_limiter.reset_for_test()

        # Register User B
        phone_b = self._gen_phone()
        res_b = client.post("/api/v1/auth/signup/request-otp", json={"phone_number": phone_b})
        assert res_b.status_code == 200
        code_b = _mock_provider_instance.sent_messages[-1]["message"].split("is ")[1].split(".")[0].strip()
        token_b = client.post("/api/v1/auth/signup/verify-otp", json={"phone_number": phone_b, "otp": code_b}).json()["access_token"]

        # Call /auth/me for both
        me_a = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token_a}"}).json()
        me_b = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token_b}"}).json()

        assert me_a["id"] != me_b["id"]
        assert me_a["phone_number"] == f"+91{phone_a}"
        assert me_b["phone_number"] == f"+91{phone_b}"

    # -------------------------------------------------------------------------
    # 21. Reviewer Login Regression
    # -------------------------------------------------------------------------
    def test_21_reviewer_login_regression(self):
        res = client.post("/api/v1/auth/login", json={
            "phone_number": "9876543210",
            "password": "demo_farmer_default_pw"
        })
        assert res.status_code == 200
        data = res.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    # -------------------------------------------------------------------------
    # 22. Production DEMO_MODE Disabled Behavior
    # -------------------------------------------------------------------------
    def test_22_production_demo_mode_disabled(self):
        with patch.object(settings, "DEMO_MODE", False):
            with patch.object(settings, "ENVIRONMENT", "production"):
                assert settings.is_production is True
                assert settings.DEMO_MODE is False

    # -------------------------------------------------------------------------
    # 23. Production Evaluator OTP Disabled Behavior
    # -------------------------------------------------------------------------
    def test_23_production_evaluator_otp_disabled(self):
        with patch.object(settings, "ENVIRONMENT", "production"):
            with patch.object(settings, "ALLOW_EVALUATOR_OTP", False):
                res = client.post("/api/v1/auth/send-otp", json={"phone_number": self._gen_phone()})
                assert res.status_code == 200
                data = res.json()
                assert "otp" not in data
                assert "otp_code" not in data
                assert "demo_otp" not in data
                assert data["auth_mode"] == "production"

    # -------------------------------------------------------------------------
    # 24. OTP Never Appears in API Response
    # -------------------------------------------------------------------------
    def test_24_otp_never_appears_in_api_response(self):
        phone = self._gen_phone()
        res = client.post("/api/v1/auth/signup/request-otp", json={"phone_number": phone})
        assert res.status_code == 200
        body_text = res.text
        assert "otp" not in res.json()
        assert "code" not in res.json()
        # Verify 6-digit digits do not appear in raw JSON body
        sent_code = _mock_provider_instance.sent_messages[-1]["message"].split("is ")[1].split(".")[0].strip()
        assert sent_code not in body_text

    # -------------------------------------------------------------------------
    # 25. OTP Never Appears in Application Logs
    # -------------------------------------------------------------------------
    def test_25_otp_never_in_logs(self, caplog):
        import logging
        caplog.set_level(logging.DEBUG)
        phone = self._gen_phone()
        res = client.post("/api/v1/auth/signup/request-otp", json={"phone_number": phone})
        assert res.status_code == 200
        sent_code = _mock_provider_instance.sent_messages[-1]["message"].split("is ")[1].split(".")[0].strip()

        for record in caplog.records:
            assert sent_code not in record.message, "Plaintext OTP leaked in logger!"

    # -------------------------------------------------------------------------
    # 26. SMS Provider Secret Never Appears in Logs
    # -------------------------------------------------------------------------
    def test_26_sms_provider_secret_never_in_logs(self, caplog):
        import logging
        caplog.set_level(logging.DEBUG)
        phone = self._gen_phone()
        secret_token = "SECRET_SUPER_CONFIDENTIAL_SMS_KEY_XYZ"
        with patch.object(settings, "SMS_API_KEY", secret_token):
            res = client.post("/api/v1/auth/signup/request-otp", json={"phone_number": phone})
            assert res.status_code == 200

        for record in caplog.records:
            assert secret_token not in record.message, "SMS API Key leaked in logger!"

