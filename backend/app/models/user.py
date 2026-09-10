import uuid
from datetime import datetime
from sqlalchemy import Column, String, Boolean
from sqlalchemy.orm import relationship
from app.db.session import Base
from app.core.datetime_utils import NaiveUTCDateTime, utc_now_naive

class User(Base):
    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    phone_number = Column(String(20), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(NaiveUTCDateTime, default=utc_now_naive)
    updated_at = Column(NaiveUTCDateTime, default=utc_now_naive, onupdate=utc_now_naive)

    farmer_profile = relationship("FarmerProfile", back_populates="user", uselist=False, cascade="all, delete-orphan")
