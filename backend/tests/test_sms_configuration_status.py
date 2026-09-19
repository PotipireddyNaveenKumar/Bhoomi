from unittest.mock import patch

import pytest

from app.core.config import settings
from app.db.session import AsyncSessionLocal
from app.services.auth.otp_service import OTPService
from app.services.sms.sms_provider import is_production_sms_configured


def test_fast2sms_requires_explicit_message_id_and_sender():
    with (
        patch.object(settings, "SMS_PROVIDER", "fast2sms"),
        patch.object(settings, "FAST2SMS_API_KEY", "test-key"),
        patch.object(settings, "FAST2SMS_SENDER_ID", "BHOOMI"),
        patch.object(settings, "FAST2SMS_MESSAGE_ID", None),
        patch.object(settings, "SMS_TEMPLATE_ID", "telecom-template-id"),
    ):
        assert is_production_sms_configured() is False


@pytest.mark.asyncio
async def test_missing_production_sms_configuration_does_not_activate_challenge():
    with (
        patch.object(settings, "ENVIRONMENT", "production"),
        patch.object(settings, "SMS_PROVIDER", "console"),
    ):
        async with AsyncSessionLocal() as db:
            success, message, challenge = await OTPService.request_otp_challenge(
                db=db,
                phone_number="9876543210",
                purpose="SIGNUP",
            )

    assert success is False
    assert challenge is None
    assert message == "SMS delivery is not configured. Please contact BHOOMI support."
