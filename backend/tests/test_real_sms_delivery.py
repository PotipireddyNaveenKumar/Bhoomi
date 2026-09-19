"""
BHOOMI — Task 1.2: Real SMS Delivery Integration Test Suite
Verifies all 14 criteria:
1. Production HTTP provider configured and resolved
2. Missing API key rejected / returns False in production
3. Missing API URL rejected / returns False
4. Invalid provider response body rejected / returns False
5. HTTP 4xx handled safely (returns False, logs masked phone)
6. HTTP 5xx handled safely (returns False, logs masked phone)
7. Gateway timeout handled safely without blind duplicate retries
8. Successful provider acceptance confirms delivery and returns True
9. Provider failure does not activate OTP challenge (zero ghost OTP)
10. OTP never appears in API response
11. OTP never appears in application logs
12. API key never appears in application logs
13. Console provider cannot silently activate in production
14. Mock provider cannot silently activate in production
"""

import re
import pytest
import httpx
from unittest.mock import patch, AsyncMock, MagicMock
from fastapi.testclient import TestClient
from sqlalchemy.future import select

from app.main import app
from app.core.config import settings
from app.db.session import AsyncSessionLocal
from app.models.otp_challenge import OTPChallenge
from app.services.sms.sms_provider import (
    HttpSMSProvider,
    ConsoleSMSProvider,
    MockSMSProvider,
    get_sms_provider,
    _mock_provider_instance
)
from app.services.auth.otp_service import OTPService

client = TestClient(app)

class TestRealSMSDelivery:

    def setup_method(self):
        self._orig_env = settings.ENVIRONMENT
        self._orig_app_env = settings.APP_ENV
        self._orig_sms_provider = settings.SMS_PROVIDER
        self._orig_gateway_url = settings.SMS_GATEWAY_URL
        self._orig_api_key = settings.SMS_API_KEY
        self._orig_auth_token = settings.SMS_AUTH_TOKEN
        self._orig_fast2sms_api_key = settings.FAST2SMS_API_KEY
        self._orig_fast2sms_sender_id = settings.FAST2SMS_SENDER_ID
        self._orig_fast2sms_message_id = settings.FAST2SMS_MESSAGE_ID
        self._orig_sms_template_id = settings.SMS_TEMPLATE_ID
        self._orig_fast2sms_gateway_url = settings.FAST2SMS_GATEWAY_URL
        self._orig_fast2sms_route = settings.FAST2SMS_ROUTE

    def teardown_method(self):
        settings.ENVIRONMENT = self._orig_env
        settings.APP_ENV = self._orig_app_env
        settings.SMS_PROVIDER = self._orig_sms_provider
        settings.SMS_GATEWAY_URL = self._orig_gateway_url
        settings.SMS_API_KEY = self._orig_api_key
        settings.SMS_AUTH_TOKEN = self._orig_auth_token
        settings.FAST2SMS_API_KEY = self._orig_fast2sms_api_key
        settings.FAST2SMS_SENDER_ID = self._orig_fast2sms_sender_id
        settings.FAST2SMS_MESSAGE_ID = self._orig_fast2sms_message_id
        settings.SMS_TEMPLATE_ID = self._orig_sms_template_id
        settings.FAST2SMS_GATEWAY_URL = self._orig_fast2sms_gateway_url
        settings.FAST2SMS_ROUTE = self._orig_fast2sms_route

    def test_01_production_http_provider_configured_and_resolved(self):
        """In production, get_sms_provider resolves to HttpSMSProvider."""
        settings.ENVIRONMENT = "production"
        settings.SMS_PROVIDER = "http"
        provider = get_sms_provider()
        assert isinstance(provider, HttpSMSProvider)

    @pytest.mark.asyncio
    async def test_02_missing_api_key_in_production_returns_false(self):
        """In production, HttpSMSProvider without credentials returns False and fails safely."""
        settings.ENVIRONMENT = "production"
        provider = HttpSMSProvider(
            endpoint_url="https://api.sms-gateway.example.com/v1/send",
            api_key=None,
            auth_token=None
        )
        delivered = await provider.send_sms("+919876543210", "Your BHOOMI OTP is 123456")
        assert delivered is False

    @pytest.mark.asyncio
    async def test_03_missing_api_url_returns_false(self):
        """HttpSMSProvider without SMS_GATEWAY_URL returns False."""
        provider = HttpSMSProvider(
            endpoint_url=None,
            api_key="valid_api_key_12345"
        )
        delivered = await provider.send_sms("+919876543210", "Your BHOOMI OTP is 123456")
        assert delivered is False

    @pytest.mark.asyncio
    async def test_04_invalid_provider_response_body_returns_false(self):
        """Gateway returning HTTP 200 with an error response body returns False."""
        provider = HttpSMSProvider(
            endpoint_url="https://api.sms-gateway.example.com/v1/send",
            api_key="valid_api_key_12345"
        )
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"return": False, "message": ["Invalid DLT template"]}

        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_resp
            delivered = await provider.send_sms("+919876543210", "Your BHOOMI OTP is 123456")
            assert delivered is False

    @pytest.mark.asyncio
    async def test_05_http_4xx_handled_safely(self):
        """Gateway returning HTTP 401 Unauthorized returns False."""
        provider = HttpSMSProvider(
            endpoint_url="https://api.sms-gateway.example.com/v1/send",
            api_key="expired_or_invalid_key"
        )
        mock_resp = MagicMock()
        mock_resp.status_code = 401

        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_resp
            delivered = await provider.send_sms("+919876543210", "Your BHOOMI OTP is 123456")
            assert delivered is False

    @pytest.mark.asyncio
    async def test_06_http_5xx_handled_safely(self):
        """Gateway returning HTTP 503 Service Unavailable returns False."""
        provider = HttpSMSProvider(
            endpoint_url="https://api.sms-gateway.example.com/v1/send",
            api_key="valid_key"
        )
        mock_resp = MagicMock()
        mock_resp.status_code = 503

        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_resp
            delivered = await provider.send_sms("+919876543210", "Your BHOOMI OTP is 123456")
            assert delivered is False

    @pytest.mark.asyncio
    async def test_07_gateway_timeout_handled_safely_no_duplicate_retries(self):
        """Gateway timeout returns False and does NOT blindly retry to avoid duplicate SMS."""
        provider = HttpSMSProvider(
            endpoint_url="https://api.sms-gateway.example.com/v1/send",
            api_key="valid_key",
            timeout=5.0
        )
        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.side_effect = httpx.TimeoutException("Read timed out")
            delivered = await provider.send_sms("+919876543210", "Your BHOOMI OTP is 123456")
            assert delivered is False
            # Ensure post was called exactly once — NO blind duplicate retries
            assert mock_post.call_count == 1

    @pytest.mark.asyncio
    async def test_08_successful_provider_acceptance_returns_true(self):
        """Gateway returning HTTP 200 with success body confirms delivery and returns True."""
        provider = HttpSMSProvider(
            endpoint_url="https://api.sms-gateway.example.com/v1/send",
            api_key="valid_key"
        )
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"return": True, "message": "Message sent successfully"}

        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_resp
            delivered = await provider.send_sms("+919876543210", "Your BHOOMI OTP is 123456")
            assert delivered is True

    @pytest.mark.asyncio
    async def test_09_provider_failure_does_not_activate_otp_challenge(self):
        """If SMS provider fails, OTP challenge is aborted: zero records created in database."""
        test_phone = "+919811223344"
        failing_provider = MockSMSProvider()
        failing_provider.simulate_failure(True)

        async with AsyncSessionLocal() as db:
            success, msg, challenge = await OTPService.request_otp_challenge(
                db=db,
                phone_number=test_phone,
                purpose="SIGNUP",
                sms_provider=failing_provider
            )
            assert success is False
            assert challenge is None
            assert "SMS delivery failed" in msg

            # Assert database has ZERO active challenges for this phone
            res = await db.execute(
                select(OTPChallenge).where(OTPChallenge.phone_number == test_phone)
            )
            challenges = list(res.scalars().all())
            assert len(challenges) == 0, "No challenge must be committed if SMS transport fails"

    def test_10_otp_never_appears_in_api_response(self):
        """Request OTP endpoints strictly return metadata and NEVER return the OTP value."""
        settings.SMS_PROVIDER = "mock"
        _mock_provider_instance.clear()

        phone = "9822334455"
        res = client.post("/api/v1/auth/signup/request-otp", json={"phone_number": phone})
        assert res.status_code == 200
        data = res.json()

        assert "otp" not in data
        assert "otp_code" not in data
        assert "code" not in data
        assert "demo_otp" not in data
        assert data.get("success") is True
        assert data.get("delivery_channel") == "sms"

    def test_11_otp_never_appears_in_application_logs(self, caplog):
        """OTP codes are never logged to console or application log stream."""
        settings.SMS_PROVIDER = "mock"
        _mock_provider_instance.clear()

        phone = "9833445566"
        caplog.clear()
        res = client.post("/api/v1/auth/signup/request-otp", json={"phone_number": phone})
        assert res.status_code == 200

        # Retrieve the generated OTP from mock provider
        assert len(_mock_provider_instance.sent_messages) == 1
        msg = _mock_provider_instance.sent_messages[0]["message"]
        match = re.search(r"\b\d{6}\b", msg)
        assert match is not None
        otp = match.group(0)

        # Ensure OTP does NOT appear in caplog
        for record in caplog.records:
            assert otp not in record.message, "Raw OTP code was found in application log!"

    def test_12_api_key_never_appears_in_application_logs(self, caplog):
        """Gateway API keys and authorization tokens are never leaked to logs."""
        secret_api_key = "super_secret_telco_token_xyz999"
        provider = HttpSMSProvider(
            endpoint_url="https://api.sms-gateway.example.com/v1/send",
            api_key=secret_api_key
        )

        caplog.clear()
        # Trigger an error scenario
        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_resp = MagicMock()
            mock_resp.status_code = 403
            mock_post.return_value = mock_resp
            import asyncio
            asyncio.run(provider.send_sms("+919876543210", "Your BHOOMI OTP is 123456"))

        for record in caplog.records:
            assert secret_api_key not in record.message, "Secret API key leaked in application logs!"

    def test_13_console_provider_cannot_silently_activate_in_production(self):
        """In production, setting or defaulting to console provider raises a RuntimeError."""
        settings.ENVIRONMENT = "production"
        settings.SMS_PROVIDER = "console"

        with pytest.raises(RuntimeError) as exc_info:
            get_sms_provider()

        assert "is not permitted in production" in str(exc_info.value)
        assert "console" in str(exc_info.value)

    def test_14_mock_provider_cannot_silently_activate_in_production(self):
        """In production, setting or resolving to mock provider raises a RuntimeError."""
        settings.ENVIRONMENT = "production"
        settings.SMS_PROVIDER = "mock"

        with pytest.raises(RuntimeError) as exc_info:
            get_sms_provider()

        assert "not permitted in production" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_15_fast2sms_dlt_contract_fields_and_otp_variable(self):
        """Fast2SMS DLT route uses exact payload fields and maps BHOOMI OTP to variables_values."""
        settings.SMS_PROVIDER = "fast2sms"
        settings.FAST2SMS_API_KEY = "test_fast2sms_key"
        settings.FAST2SMS_SENDER_ID = "BHOMEE"
        settings.FAST2SMS_MESSAGE_ID = "123456"

        provider = HttpSMSProvider()

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "return": True,
            "request_id": "req_abc123",
            "message": ["SMS sent successfully."]
        }

        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_resp
            delivered = await provider.send_sms("+919876543210", "Your BHOOMI verification code is 583214. It is valid for 10 minutes.")
            assert delivered is True

            # Inspect exact payload sent to Fast2SMS
            mock_post.assert_called_once()
            call_url = mock_post.call_args[0][0]
            call_kwargs = mock_post.call_args[1]

            assert call_url == "https://www.fast2sms.com/dev/bulkV2"
            assert call_kwargs["headers"]["authorization"] == "test_fast2sms_key"

            payload = call_kwargs["json"]
            assert payload["route"] == "dlt"
            assert payload["sender_id"] == "BHOMEE"
            assert payload["message"] == "123456"  # Fast2SMS Message ID
            assert payload["variables_values"] == "583214"  # Exact BHOOMI-generated OTP
            assert payload["numbers"] == "9876543210"

    @pytest.mark.asyncio
    async def test_16_fast2sms_production_requires_message_id(self):
        """In production, Fast2SMS rejects execution if FAST2SMS_MESSAGE_ID is missing."""
        settings.ENVIRONMENT = "production"
        settings.SMS_PROVIDER = "fast2sms"
        settings.FAST2SMS_API_KEY = "test_key"
        settings.FAST2SMS_MESSAGE_ID = None
        settings.SMS_TEMPLATE_ID = None

        provider = HttpSMSProvider()
        delivered = await provider.send_sms("+919876543210", "Your BHOOMI OTP is 583214")
        assert delivered is False

    def test_16b_fast2sms_does_not_use_generic_template_id_as_message_id(self):
        """A telecom Content Template ID is not a Fast2SMS Message ID."""
        settings.SMS_PROVIDER = "fast2sms"
        settings.FAST2SMS_MESSAGE_ID = None
        settings.SMS_TEMPLATE_ID = "telecom-content-template-id"

        provider = HttpSMSProvider()

        assert provider.message_id is None
        assert provider.template_id == "telecom-content-template-id"

    @pytest.mark.asyncio
    async def test_17_fast2sms_explicit_quick_route_override(self):
        """When FAST2SMS_ROUTE is explicitly set to 'q', it transmits via quick route."""
        settings.SMS_PROVIDER = "fast2sms"
        settings.FAST2SMS_API_KEY = "test_key"
        settings.FAST2SMS_ROUTE = "q"

        provider = HttpSMSProvider()

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"return": True, "message": ["SMS sent."]}

        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_resp
            delivered = await provider.send_sms("+919876543210", "Your BHOOMI OTP is 583214")
            assert delivered is True

            payload = mock_post.call_args[1]["json"]
            assert payload["route"] == "q"
            assert "Your BHOOMI OTP is 583214" in payload["message"]
            assert payload["numbers"] == "9876543210"
