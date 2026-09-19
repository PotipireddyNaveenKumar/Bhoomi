import secrets
import hmac
import hashlib
from datetime import datetime, timedelta
from typing import Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import update

from app.core.config import settings
from app.core.datetime_utils import utc_now_naive
from app.core.logging import logger
from app.core.phone_utils import normalize_indian_phone, mask_phone_number
from app.core.rate_limiter import auth_rate_limiter
from app.models.otp_challenge import OTPChallenge
from app.services.sms.sms_provider import BaseSMSProvider, get_sms_provider

OTP_LIFETIME_SECONDS = 600  # 10 minutes
OTP_RESEND_COOLDOWN_SECONDS = 30  # 30 seconds
MAX_VERIFICATION_ATTEMPTS = 5

class OTPService:
    """
    BHOOMI Authoritative OTP Engine.
    
    Generates 6-digit cryptographically secure OTPs.
    Computes and stores HMAC-SHA256 hashes (never plaintext).
    Enforces 10-minute expiry, max 5 attempts, 30s resend cooldown, single-use,
    and strict provider failure safety (challenge is only activated if SMS transport succeeds).
    """

    @staticmethod
    def generate_6digit_otp() -> str:
        """Generates a secure, unbiased 6-digit numeric OTP (100000 - 999999)."""
        return f"{secrets.randbelow(900000) + 100000}"

    @staticmethod
    def compute_otp_hash(otp: str) -> str:
        """Computes server-side HMAC-SHA256 of the OTP using SECRET_KEY."""
        key = (settings.SECRET_KEY or "bhoomi_v2_fallback_otp_hmac_secret_key").encode("utf-8")
        return hmac.new(key, otp.strip().encode("utf-8"), hashlib.sha256).hexdigest()

    @staticmethod
    def verify_otp_hash(plain_otp: str, stored_hash: str) -> bool:
        """Constant-time verification of submitted OTP against stored HMAC hash."""
        expected = OTPService.compute_otp_hash(plain_otp)
        return hmac.compare_digest(expected, stored_hash)

    @classmethod
    async def request_otp_challenge(
        cls,
        db: AsyncSession,
        phone_number: str,
        purpose: str,  # SIGNUP | LOGIN
        ip_address: Optional[str] = None,
        sms_provider: Optional[BaseSMSProvider] = None,
    ) -> Tuple[bool, str, Optional[OTPChallenge]]:
        """
        Executes the OTP request pipeline:
        1. Normalizes phone.
        2. Enforces cooldown and frequency rate limits.
        3. Generates 6-digit OTP.
        4. Transports via SMS provider.
        5. If delivery fails -> DOES NOT activate challenge, returns error.
        6. If delivery succeeds -> Invalidates prior active challenges, commits new challenge.
        """
        try:
            norm_phone = normalize_indian_phone(phone_number)
        except ValueError as e:
            return False, str(e), None

        # Enforce rate limits
        auth_rate_limiter.check_otp_request_limits(
            phone=norm_phone,
            ip_address=ip_address,
            cooldown_seconds=OTP_RESEND_COOLDOWN_SECONDS
        )

        now = utc_now_naive()
        otp = cls.generate_6digit_otp()
        otp_hash = cls.compute_otp_hash(otp)
        message = (
            f"Your BHOOMI verification code is {otp}. "
            f"It is valid for 10 minutes. Do not share this code with anyone."
        )

        # Attempt delivery through SMS transport
        provider = sms_provider or get_sms_provider()
        delivered = await provider.send_sms(norm_phone, message)

        if not delivered:
            masked = mask_phone_number(norm_phone)
            logger.error(f"SMS transport failed for {masked}. Aborting OTP challenge creation.")
            return False, "SMS delivery failed. Please check the phone number or try again later.", None

        # Delivery succeeded -> Invalidate existing active challenges for this phone & purpose
        await db.execute(
            update(OTPChallenge)
            .where(
                OTPChallenge.phone_number == norm_phone,
                OTPChallenge.purpose == purpose,
                OTPChallenge.used_at.is_(None),
                OTPChallenge.expires_at > now
            )
            .values(expires_at=now)
        )

        # Create and commit new challenge
        challenge = OTPChallenge(
            phone_number=norm_phone,
            purpose=purpose,
            otp_hash=otp_hash,
            expires_at=now + timedelta(seconds=OTP_LIFETIME_SECONDS),
            attempts=0,
            max_attempts=MAX_VERIFICATION_ATTEMPTS,
            resend_available_at=now + timedelta(seconds=OTP_RESEND_COOLDOWN_SECONDS),
            created_at=now,
            used_at=None
        )
        db.add(challenge)
        await db.commit()
        await db.refresh(challenge)

        # Record rate-limiter timestamp
        auth_rate_limiter.record_otp_request(phone=norm_phone, ip_address=ip_address)

        masked = mask_phone_number(norm_phone)
        logger.info(f"Successfully activated {purpose} OTP challenge for {masked} (id={challenge.id}).")
        return True, "Verification code sent.", challenge

    @classmethod
    async def verify_otp_challenge(
        cls,
        db: AsyncSession,
        phone_number: str,
        purpose: str,
        otp: str,
    ) -> Tuple[bool, str, Optional[OTPChallenge]]:
        """
        Verifies a submitted OTP against the active challenge:
        1. Normalizes phone.
        2. Finds the latest active unexpired challenge for this purpose.
        3. Enforces single-use (`used_at is None`) and attempt limits (`attempts < max_attempts`).
        4. Validates HMAC hash.
        5. Updates attempt count or marks challenge `used_at`.
        """
        try:
            norm_phone = normalize_indian_phone(phone_number)
        except ValueError as e:
            return False, str(e), None

        clean_otp = (otp or "").strip()
        if not clean_otp or len(clean_otp) != 6 or not clean_otp.isdigit():
            return False, "Invalid verification code format. Code must be 6 numeric digits.", None

        now = utc_now_naive()

        # Query latest challenge for this phone and purpose
        res = await db.execute(
            select(OTPChallenge)
            .where(
                OTPChallenge.phone_number == norm_phone,
                OTPChallenge.purpose == purpose
            )
            .order_by(OTPChallenge.created_at.desc())
        )
        challenges = list(res.scalars().all())

        if not challenges:
            return False, "No active verification code found for this mobile number. Please request a new code.", None

        # Find the active challenge
        challenge = challenges[0]

        # Check if already used (single-use semantics)
        if challenge.used_at is not None:
            return False, "This verification code has already been used. Please request a new code.", None

        # Check if expired
        if challenge.expires_at <= now:
            return False, "Verification code has expired. Please request a new code.", None

        # Check attempt limit
        if challenge.attempts >= challenge.max_attempts:
            return False, "Maximum verification attempts exceeded. Please request a new code.", None

        # Increment attempt count
        challenge.attempts += 1

        # Check hash
        is_valid = cls.verify_otp_hash(clean_otp, challenge.otp_hash)

        if not is_valid:
            auth_rate_limiter.record_verification_failure(norm_phone)
            await db.commit()
            remaining = challenge.max_attempts - challenge.attempts
            if remaining > 0:
                msg = f"Invalid verification code. {remaining} attempt{'s' if remaining != 1 else ''} remaining."
            else:
                msg = "Maximum verification attempts exceeded. Please request a new code."
            return False, msg, None

        # Success: Mark single-use consumption
        challenge.used_at = now
        await db.commit()
        await db.refresh(challenge)

        masked = mask_phone_number(norm_phone)
        logger.info(f"Successfully verified {purpose} OTP challenge for {masked} (challenge_id={challenge.id}).")
        return True, "Verification successful.", challenge
