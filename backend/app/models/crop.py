import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Date, Numeric, DateTime, ForeignKey, Enum
import enum
from sqlalchemy.orm import relationship
from app.db.session import Base

class CropStage(str, enum.Enum):
    PLANNING = "planning"
    SOWING = "sowing"
    GERMINATION = "germination"
    VEGETATIVE = "vegetative"
    FLOWERING = "flowering"
    FRUIT_DEVELOPMENT = "fruit_development"
    MATURITY = "maturity"
    HARVESTED = "harvested"

class CropStatus(str, enum.Enum):
    PLANNED = "planned"
    ACTIVE = "active"
    COMPLETED = "completed"

class FarmCrop(Base):
    __tablename__ = "farm_crops"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    farm_id = Column(String(36), ForeignKey("farms.id", ondelete="CASCADE"), nullable=False)
    crop_name = Column(String(100), nullable=False)  # Chilli, Cotton, Rice, Maize, Groundnut, etc.
    variety = Column(String(100), nullable=True)     # Teja, Hybrid 334, etc.
    area_acres = Column(Numeric(10, 2), nullable=False)
    sowing_date = Column(Date, nullable=True)
    expected_harvest_date = Column(Date, nullable=True)
    current_stage = Column(String(50), default=CropStage.VEGETATIVE.value, nullable=False)
    status = Column(String(20), default=CropStatus.ACTIVE.value, nullable=False)
    cultivation_cost_spent = Column(Numeric(12, 2), default=0.0)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    farm = relationship("Farm", back_populates="crops")
    tasks = relationship("FarmTask", back_populates="crop", cascade="all, delete-orphan")
