import uuid
from datetime import datetime
from sqlalchemy import Column, String, Text, Float, ForeignKey, Enum
import enum
from sqlalchemy.orm import relationship
from app.db.session import Base
from app.core.datetime_utils import NaiveUTCDateTime, utc_now_naive

class MemoryCategory(str, enum.Enum):
    FARM_ATTRIBUTE = "farm_attribute"       # e.g., soil=black soil, area=3 acres
    FARMER_PREFERENCE = "farmer_preference" # e.g., prefers organic, pest tolerance
    HISTORICAL_EVENT = "historical_event"   # e.g., last year chilli wilt issue
    DECISION_RECORD = "decision_record"     # e.g., decided to sell at Guntur mandi

class FarmerMemory(Base):
    __tablename__ = "farmer_memory"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    farmer_id = Column(String(36), ForeignKey("farmer_profiles.id", ondelete="CASCADE"), nullable=False)
    key = Column(String(100), nullable=False)      # e.g. "soil_type", "total_area", "pest_history"
    value = Column(Text, nullable=False)           # e.g. "black soil", "3 acres", "leaf curl reported in July"
    category = Column(String(50), default=MemoryCategory.FARM_ATTRIBUTE.value, nullable=False)
    confidence = Column(Float, default=1.0)
    source_session_id = Column(String(36), ForeignKey("chat_sessions.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(NaiveUTCDateTime, default=utc_now_naive)
    updated_at = Column(NaiveUTCDateTime, default=utc_now_naive, onupdate=utc_now_naive)

    farmer = relationship("FarmerProfile", back_populates="memories")
