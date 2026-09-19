import uuid
from sqlalchemy import Column, String, ForeignKey
from sqlalchemy.orm import relationship
from app.db.session import Base
from app.core.datetime_utils import NaiveUTCDateTime, utc_now_naive

class AuthSession(Base):
    __tablename__ = "auth_sessions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    refresh_token_hash = Column(String(255), nullable=False, index=True)
    created_at = Column(NaiveUTCDateTime, default=utc_now_naive, nullable=False)
    expires_at = Column(NaiveUTCDateTime, nullable=False)
    revoked_at = Column(NaiveUTCDateTime, nullable=True)
    last_used_at = Column(NaiveUTCDateTime, nullable=True)
    device_info = Column(String(255), nullable=True)
    ip_address = Column(String(50), nullable=True)

    user = relationship("User", back_populates="sessions")

    @property
    def is_valid(self) -> bool:
        """Returns True if the session has not been revoked and has not expired."""
        now = utc_now_naive()
        return self.revoked_at is None and self.expires_at > now
