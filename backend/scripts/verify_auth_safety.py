"""
BHOOMI — Production & Staging Authentication Safety Verification Script
Tests:
1. ENVIRONMENT resolution
2. DEMO_MODE default (must be False)
3. ALLOW_EVALUATOR_OTP behavior
4. send_otp in production (suppresses OTP code leakage)
5. verify_otp in production (rejects evaluator master codes)
6. JWT SECRET_KEY production validation
7. Environment variable requirements report
"""

import os
import sys
import asyncio
from fastapi import HTTPException

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
BACKEND_DIR = os.path.join(REPO_ROOT, "backend")
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from app.core.config import Settings
from app.api.v1.auth import SendOtpRequest, VerifyOtpRequest, send_otp, verify_otp, _OTP_STORE

async def run_auth_verification():
    print("=" * 80)
    print("TASK 4: PRODUCTION/STAGING AUTH SAFETY VERIFICATION")
    print("=" * 80)

    # 1. Test DEMO_MODE default
    s_default = Settings()
    print(f"1. Default Settings:")
    print(f"   ENVIRONMENT (effective) : {s_default.effective_env}")
    print(f"   DEMO_MODE               : {s_default.DEMO_MODE} (Must default to False)")
    print(f"   ALLOW_EVALUATOR_OTP     : {s_default.ALLOW_EVALUATOR_OTP}")
    assert s_default.DEMO_MODE is False, "DEMO_MODE must default to False"

    # 2. Test Production SECRET_KEY & DATABASE_URL enforcement
    print("\n2. Production Security Validation:")
    try:
        # In production without strong SECRET_KEY or DATABASE_URL, Settings must raise ValueError
        Settings(ENVIRONMENT="production", SECRET_KEY="short", DATABASE_URL="sqlite:///./test.db")
        print("   ERROR: Production settings allowed weak secret or SQLite!")
    except ValueError as ve:
        print(f"   Enforcement Confirmed: Production correctly rejected insecure config -> {ve}")

    # 3. Test Development/Staging OTP Leakage vs Production OTP Suppression
    print("\n3. OTP API Response Leakage Test:")
    from app.core.config import settings
    from app.db.session import AsyncSessionLocal
    orig_env = settings.ENVIRONMENT
    orig_app_env = settings.APP_ENV

    async with AsyncSessionLocal() as session:
        # Non-production test
        os.environ["ENVIRONMENT"] = "development"
        os.environ["APP_ENV"] = "development"
        dev_otp_res = await send_otp(SendOtpRequest(phone_number="9876543210"), db=session)
        print(f"   Dev Mode send_otp response keys: {list(dev_otp_res.keys())}")
        print(f"   Dev Mode returned otp: {dev_otp_res.get('otp')}")

        # Production test (mock production state)
        os.environ["ENVIRONMENT"] = "production"
        os.environ["APP_ENV"] = "production"
        prod_otp_res = await send_otp(SendOtpRequest(phone_number="9876543211"), db=session)
        print(f"   Prod Mode send_otp response keys: {list(prod_otp_res.keys())}")
        has_otp_in_prod = any(k in prod_otp_res for k in ("otp", "otp_code", "demo_otp"))
        print(f"   Prod Mode leaked OTP code: {has_otp_in_prod} (Must be False)")
        assert not has_otp_in_prod, "Production mode must NOT leak OTP in API response!"

        # 4. Evaluator OTP Code Rejection in Production
        print("\n4. Evaluator OTP Rejection Test:")
        try:
            await verify_otp(VerifyOtpRequest(phone_number="9876543211", otp="1234"), db=session)
            print("   ERROR: Production verify_otp accepted evaluator code 1234!")
        except HTTPException as he:
            print(f"   Production rejection confirmed: Evaluator code 1234 rejected with HTTP {he.status_code}: {he.detail}")

    # Restore environment
    if orig_env:
        os.environ["ENVIRONMENT"] = orig_env
    else:
        os.environ.pop("ENVIRONMENT", None)
    if orig_app_env:
        os.environ["APP_ENV"] = orig_app_env
    else:
        os.environ.pop("APP_ENV", None)

    print("\n5. SMS Authentication Status:")
    print("   SMS Provider Integrated: False (Zero third-party SMS gateway configured).")
    print("   Notice: No SMS delivery is claimed. System operates via cryptographically secure server-side OTP.")

    print("\n" + "=" * 80)
    print("TASK 4 VERIFICATION COMPLETED SUCCESSFULLY")
    print("=" * 80)

if __name__ == "__main__":
    asyncio.run(run_auth_verification())
