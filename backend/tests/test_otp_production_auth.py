"""
BHOOMI - Comprehensive Production OTP Authentication Test Suite
Verifies all 12 Phase 5 test criteria:
1. Valid legitimate OTP -> SUCCESS
2. Wrong OTP -> 400 auth error with remaining attempts
3. Expired OTP -> 400 rejected
4. Reused OTP -> rejected (single-use semantics)
5. Missing OTP -> 400 rejected
6. Malformed OTP -> 400 rejected
7. Rate limit -> enforced (both send rate limit and verify attempt limits)
8. Production cannot accept hardcoded 1234 unless 1234 was legitimately generated
9. Production does not expose OTP in API response
10. Successful verification produces valid JWT/session
11. Unauthorized dashboard API access remains blocked without JWT
12. Existing evaluator/development tests remain isolated from production behavior
"""

import time
import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient

from app.main import app
from app.core.config import settings
from app.api.v1.auth import _OTP_STORE

client = TestClient(app)


class TestOtpProductionAuthentication:
    """Suite covering all 12 test cases for production OTP security."""

    def setup_method(self):
        """Clean OTP store before each test."""
        _OTP_STORE.clear()

    # -------------------------------------------------------------------------
    # Case 1: Valid legitimate OTP -> SUCCESS
    # -------------------------------------------------------------------------
    def test_case_01_valid_legitimate_otp_success(self):
        phone = "9876543210"
        # In dev mode, send-otp returns legitimate generated OTP
        res_send = client.post("/api/v1/auth/send-otp", json={"phone_number": phone})
        assert res_send.status_code == 200
        data_send = res_send.json()
        legit_otp = data_send["otp"]
        assert len(legit_otp) == 4

        # Verify with that exact code
        res_verify = client.post("/api/v1/auth/verify-otp", json={
            "phone_number": phone,
            "otp": legit_otp,
            "name": "Test Farmer"
        })
        assert res_verify.status_code == 200
        data_verify = res_verify.json()
        assert "access_token" in data_verify
        assert data_verify["access_token"] is not None

    # -------------------------------------------------------------------------
    # Case 2: Wrong OTP -> 400 with remaining attempts count
    # -------------------------------------------------------------------------
    def test_case_02_wrong_otp_rejected(self):
        phone = "9876543211"
        res_send = client.post("/api/v1/auth/send-otp", json={"phone_number": phone})
        assert res_send.status_code == 200
        legit_otp = res_send.json()["otp"]
        wrong_otp = "0001" if legit_otp != "0001" else "0002"

        # In production mode, master bypasses are disabled
        with patch.object(settings, "ENVIRONMENT", "production"), \
             patch.object(settings, "ALLOW_EVALUATOR_OTP", False):
            res_verify = client.post("/api/v1/auth/verify-otp", json={
                "phone_number": phone,
                "otp": wrong_otp
            })
            assert res_verify.status_code == 400
            assert "Invalid verification code" in res_verify.json()["detail"]
            assert "4 attempt(s) remaining" in res_verify.json()["detail"]

    # -------------------------------------------------------------------------
    # Case 3: Expired OTP -> rejected
    # -------------------------------------------------------------------------
    def test_case_03_expired_otp_rejected(self):
        phone = "9876543212"
        res_send = client.post("/api/v1/auth/send-otp", json={"phone_number": phone})
        assert res_send.status_code == 200
        legit_otp = res_send.json()["otp"]

        # Manually expire the OTP in store
        _OTP_STORE[phone]["expires_at"] = time.time() - 10.0

        res_verify = client.post("/api/v1/auth/verify-otp", json={
            "phone_number": phone,
            "otp": legit_otp
        })
        assert res_verify.status_code == 400
        assert "expired" in res_verify.json()["detail"].lower()
        # Ensure it was purged
        assert phone not in _OTP_STORE

    # -------------------------------------------------------------------------
    # Case 4: Reused OTP -> rejected (one-time semantics)
    # -------------------------------------------------------------------------
    def test_case_04_reused_otp_rejected(self):
        phone = "9876543213"
        res_send = client.post("/api/v1/auth/send-otp", json={"phone_number": phone})
        assert res_send.status_code == 200
        legit_otp = res_send.json()["otp"]

        # First verification succeeds
        res_verify_1 = client.post("/api/v1/auth/verify-otp", json={
            "phone_number": phone,
            "otp": legit_otp
        })
        assert res_verify_1.status_code == 200

        # Immediate reuse of same OTP must fail because it was consumed
        res_verify_2 = client.post("/api/v1/auth/verify-otp", json={
            "phone_number": phone,
            "otp": legit_otp
        })
        assert res_verify_2.status_code == 400
        assert "No active verification session" in res_verify_2.json()["detail"]

    # -------------------------------------------------------------------------
    # Case 5: Missing OTP -> rejected
    # -------------------------------------------------------------------------
    def test_case_05_missing_otp_rejected(self):
        phone = "9876543214"
        client.post("/api/v1/auth/send-otp", json={"phone_number": phone})

        # Send empty string OTP
        res_verify = client.post("/api/v1/auth/verify-otp", json={
            "phone_number": phone,
            "otp": ""
        })
        assert res_verify.status_code == 400
        assert "cannot be empty" in res_verify.json()["detail"].lower()

    # -------------------------------------------------------------------------
    # Case 6: Malformed OTP -> rejected
    # -------------------------------------------------------------------------
    def test_case_06_malformed_otp_rejected(self):
        phone = "9876543215"
        client.post("/api/v1/auth/send-otp", json={"phone_number": phone})

        # Test non-digit
        res_bad_alpha = client.post("/api/v1/auth/verify-otp", json={
            "phone_number": phone,
            "otp": "abcd"
        })
        assert res_bad_alpha.status_code == 400
        assert "4 numeric digits" in res_bad_alpha.json()["detail"]

        # Test wrong length (3 digits)
        res_bad_short = client.post("/api/v1/auth/verify-otp", json={
            "phone_number": phone,
            "otp": "123"
        })
        assert res_bad_short.status_code == 400
        assert "4 numeric digits" in res_bad_short.json()["detail"]

    # -------------------------------------------------------------------------
    # Case 7: Rate limit -> enforced (send cooldown & max attempts)
    # -------------------------------------------------------------------------
    def test_case_07_rate_limit_enforced(self):
        phone = "9876543216"
        # First send succeeds
        res_send_1 = client.post("/api/v1/auth/send-otp", json={"phone_number": phone})
        assert res_send_1.status_code == 200

        # Rapid second send (< 10 seconds) fails with 429
        res_send_2 = client.post("/api/v1/auth/send-otp", json={"phone_number": phone})
        assert res_send_2.status_code == 429
        assert "wait before requesting" in res_send_2.json()["detail"].lower()

        # Test verification attempts lockout (5 failed attempts)
        with patch.object(settings, "ENVIRONMENT", "production"), \
             patch.object(settings, "ALLOW_EVALUATOR_OTP", False):
            for i in range(1, 5):
                res = client.post("/api/v1/auth/verify-otp", json={"phone_number": phone, "otp": "9998"})
                assert res.status_code == 400
                assert f"{5 - i} attempt(s) remaining" in res.json()["detail"]

            # 5th failed attempt should lock out and purge OTP
            res_5 = client.post("/api/v1/auth/verify-otp", json={"phone_number": phone, "otp": "9998"})
            assert res_5.status_code == 400
            assert "Maximum verification attempts exceeded" in res_5.json()["detail"]
            assert phone not in _OTP_STORE

    # -------------------------------------------------------------------------
    # Case 8: Production cannot accept hardcoded 1234 unless 1234 was generated
    # -------------------------------------------------------------------------
    def test_case_08_production_cannot_accept_hardcoded_1234(self):
        phone = "9876543217"
        # In production mode:
        with patch.object(settings, "ENVIRONMENT", "production"), \
             patch.object(settings, "ALLOW_EVALUATOR_OTP", False):
            # Artificially set generated code to 7891
            _OTP_STORE[phone] = {
                "code": "7891",
                "expires_at": time.time() + 600,
                "attempts": 0,
                "max_attempts": 5
            }
            res_verify = client.post("/api/v1/auth/verify-otp", json={
                "phone_number": phone,
                "otp": "1234"
            })
            assert res_verify.status_code == 400
            assert "Invalid verification code" in res_verify.json()["detail"]

    # -------------------------------------------------------------------------
    # Case 9: Production does not expose OTP in API response
    # -------------------------------------------------------------------------
    def test_case_09_production_does_not_expose_otp_in_response(self):
        phone = "9876543218"
        with patch.object(settings, "ENVIRONMENT", "production"), \
             patch.object(settings, "ALLOW_EVALUATOR_OTP", False):
            res_send = client.post("/api/v1/auth/send-otp", json={"phone_number": phone})
            assert res_send.status_code == 200
            data = res_send.json()
            assert "otp" not in data
            assert "otp_code" not in data
            assert "demo_otp" not in data
            assert data["auth_mode"] == "production"
            # Does not claim SMS was sent if no gateway configured
            assert data["delivery_channel"] == "none"

    # -------------------------------------------------------------------------
    # Case 10: Successful verification produces valid JWT/session
    # -------------------------------------------------------------------------
    def test_case_10_successful_verification_produces_valid_jwt(self):
        phone = "9876543219"
        res_send = client.post("/api/v1/auth/send-otp", json={"phone_number": phone})
        legit_otp = res_send.json()["otp"]

        res_verify = client.post("/api/v1/auth/verify-otp", json={
            "phone_number": phone,
            "otp": legit_otp,
            "name": "Naveen",
            "state": "Telangana",
            "district": "Warangal"
        })
        assert res_verify.status_code == 200
        token = res_verify.json()["access_token"]
        assert token
        assert len(token) > 20

        # Validate token against protected endpoint
        res_chat = client.post(
            "/api/v1/assistant/chat",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "message": "Hello Bhoomi",
                "session_id": "test_session_jwt_10",
                "farm_id": res_verify.json()["farm_id"],
                "language_code": "en"
            }
        )
        assert res_chat.status_code == 200

    # -------------------------------------------------------------------------
    # Case 11: Unauthorized dashboard API access remains blocked
    # -------------------------------------------------------------------------
    def test_case_11_unauthorized_access_blocked_without_jwt(self):
        # In production with DEMO_MODE=False, protected routes reject unauthenticated requests
        with patch.object(settings, "ENVIRONMENT", "production"), \
             patch.object(settings, "DEMO_MODE", False):
            res = client.post(
                "/api/v1/assistant/chat",
                json={
                    "message": "Hello Bhoomi",
                    "session_id": "unauth_session",
                    "language_code": "en"
                }
            )
            assert res.status_code == 401

    # -------------------------------------------------------------------------
    # Case 12: Existing evaluator/development mode isolated from production
    # -------------------------------------------------------------------------
    def test_case_12_evaluator_mode_isolated_from_production(self):
        phone = "9876543220"
        # In non-production with ALLOW_EVALUATOR_OTP=True:
        with patch.object(settings, "ENVIRONMENT", "development"), \
             patch.object(settings, "ALLOW_EVALUATOR_OTP", True):
            res_send = client.post("/api/v1/auth/send-otp", json={"phone_number": phone})
            assert res_send.status_code == 200
            data = res_send.json()
            assert data["auth_mode"] == "evaluator"
            assert "otp" in data
            assert len(data["otp"]) == 4

            # Master reviewer code 1234 is accepted only in this non-production mode
            res_verify = client.post("/api/v1/auth/verify-otp", json={
                "phone_number": phone,
                "otp": "1234"
            })
            assert res_verify.status_code == 200
            assert "access_token" in res_verify.json()
