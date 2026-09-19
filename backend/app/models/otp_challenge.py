import uuid
from sqlalchemy import Column, String, Integer
from app.db.session import Base
from app.core.datetime_utils import NaiveUTCDateTime, utc_now_naive

class OTPChallenge(Base):
    __tablename__ = "otp_challenges"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    phone_number = Column(String(20), index=True, nullable=False)
    purpose = Column(String(20), default="SIGNUP", nullable=False)  # SIGNUP | LOGIN | PHONE_CHANGE
    otp_hash = Column(String(255), nullable=False)
    expires_at = Column(NaiveUTCDateTime, nullable=False)
    attempts = Column(Integer, default=0, nullable=False)
    max_attempts = Column(Integer, default=5, nullable=False)
    resend_available_at = Column(NaiveUTCDateTime, nullable=False)
    created_at = Column(NaiveUTCDateTime, default=utc_now_naive, nullable=False)
    used_at = Column(NaiveUTCDateTime, nullable=True)

    @property
    def is_active(self) -> bool:
        """Returns True if the challenge has not been used, not expired, and not exceeded attempts."""
        now = utc_now_naive()
        return (
            self.used_at is None
            and self.expires_at > now
            and self.attempts < self.max_attempts
        )
