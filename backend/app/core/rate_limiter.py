import time
from typing import Dict, List, Optional
from fastapi import HTTPException, status
from app.core.logging import logger

class InMemoryRateLimiter:
    """
    Sliding-window and cooldown rate limiter for authentication endpoints.
    Protects against SMS flooding, verification brute force, and credential stuffing.
    """
    def __init__(self):
        # phone -> timestamp of last OTP request
        self._last_request_time: Dict[str, float] = {}
        # phone -> list of request timestamps within the window
        self._phone_request_history: Dict[str, List[float]] = {}
        # ip -> list of request timestamps within the window
        self._ip_request_history: Dict[str, List[float]] = {}
        # phone -> list of failed verification timestamps
        self._verify_failures: Dict[str, List[float]] = {}

    def check_otp_request_limits(
        self,
        phone: str,
        ip_address: Optional[str] = None,
        cooldown_seconds: float = 30.0,
        max_phone_requests: int = 5,
        phone_window_seconds: float = 900.0,  # 15 minutes
        max_ip_requests: int = 20,
        ip_window_seconds: float = 900.0,
    ) -> None:
        """
        Enforces:
        1. Resend cooldown (default 30 seconds)
        2. Per-phone request limit (max 5 requests per 15 minutes)
        3. Per-IP request limit (max 20 requests per 15 minutes)
        """
        now = time.time()

        # 1. Cooldown check
        last_time = self._last_request_time.get(phone)
        if last_time and (now - last_time < cooldown_seconds):
            remaining = int(cooldown_seconds - (now - last_time)) + 1
            logger.warning(f"OTP request cooldown active for masked phone. Try again in {remaining}s.")
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Please wait {remaining} seconds before requesting another verification code."
            )

        # 2. Per-phone sliding window
        history = [t for t in self._phone_request_history.get(phone, []) if now - t < phone_window_seconds]
        if len(history) >= max_phone_requests:
            logger.warning(f"OTP request limit exceeded for phone window.")
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many verification code requests. Please wait 15 minutes before trying again."
            )

        # 3. Per-IP sliding window
        if ip_address:
            ip_history = [t for t in self._ip_request_history.get(ip_address, []) if now - t < ip_window_seconds]
            if len(ip_history) >= max_ip_requests:
                logger.warning(f"OTP request limit exceeded for IP address window.")
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Too many verification requests from this network. Please wait before trying again."
                )

    def record_otp_request(self, phone: str, ip_address: Optional[str] = None) -> None:
        """Records a successful OTP request for rate-limit tracking."""
        now = time.time()
        self._last_request_time[phone] = now

        # Update phone history
        history = [t for t in self._phone_request_history.get(phone, []) if now - t < 900.0]
        history.append(now)
        self._phone_request_history[phone] = history

        # Update IP history
        if ip_address:
            ip_history = [t for t in self._ip_request_history.get(ip_address, []) if now - t < 900.0]
            ip_history.append(now)
            self._ip_request_history[ip_address] = ip_history

    def record_verification_failure(self, phone: str, max_failures: int = 10, window_seconds: float = 900.0) -> None:
        """Tracks repeated verification failures across challenges to block brute-force attacks."""
        now = time.time()
        failures = [t for t in self._verify_failures.get(phone, []) if now - t < window_seconds]
        failures.append(now)
        self._verify_failures[phone] = failures

        if len(failures) >= max_failures:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many failed verification attempts. Please wait 15 minutes before requesting a new code."
            )

    def reset_for_test(self) -> None:
        """Clears all tracking structures for test isolation."""
        self._last_request_time.clear()
        self._phone_request_history.clear()
        self._ip_request_history.clear()
        self._verify_failures.clear()


# Global singleton instance
auth_rate_limiter = InMemoryRateLimiter()
