import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.db.session import Base

class FarmerProfile(Base):
    __tablename__ = "farmer_profiles"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    name = Column(String(100), nullable=False)
    preferred_language = Column(String(10), default="en", nullable=False)  # en, te, hi, ta, kn, ml
    state = Column(String(100), nullable=True)
    district = Column(String(100), nullable=True)
    village = Column(String(100), nullable=True)
    experience_years = Column(Integer, default=0)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    user = relationship("User", back_populates="farmer_profile")
    farms = relationship("Farm", back_populates="farmer", cascade="all, delete-orphan")
    chat_sessions = relationship("ChatSession", back_populates="farmer", cascade="all, delete-orphan")
    memories = relationship("FarmerMemory", back_populates="farmer", cascade="all, delete-orphan")
    tasks = relationship("FarmTask", back_populates="farmer", cascade="all, delete-orphan")
