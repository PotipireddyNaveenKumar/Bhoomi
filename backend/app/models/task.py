import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Text, Date, DateTime, ForeignKey, JSON, Enum
import enum
from sqlalchemy.orm import relationship
from app.db.session import Base

class TaskType(str, enum.Enum):
    IRRIGATION = "irrigation"
    FERTILIZER = "fertilizer"
    PEST_MONITORING = "pest_monitoring"
    DISEASE_MONITORING = "disease_monitoring"
    CROP_INSPECTION = "crop_inspection"
    HARVESTING = "harvesting"
    MARKET_CHECK = "market_check"
    GENERAL = "general"

class TaskPriority(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"

class TaskStatus(str, enum.Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    POSTPONED = "postponed"
    CANCELLED = "cancelled"

class TaskSource(str, enum.Enum):
    AI_AGENT = "ai_agent"
    CROP_LIFECYCLE = "crop_lifecycle"
    USER = "user"

class FarmTask(Base):
    __tablename__ = "farm_tasks"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    farmer_id = Column(String(36), ForeignKey("farmer_profiles.id", ondelete="CASCADE"), nullable=False)
    farm_id = Column(String(36), ForeignKey("farms.id", ondelete="CASCADE"), nullable=False)
    crop_id = Column(String(36), ForeignKey("farm_crops.id", ondelete="SET NULL"), nullable=True)
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    task_type = Column(String(50), default=TaskType.GENERAL.value, nullable=False)
    priority = Column(String(20), default=TaskPriority.MEDIUM.value, nullable=False)
    status = Column(String(20), default=TaskStatus.PENDING.value, nullable=False)
    due_date = Column(Date, nullable=False)
    reason = Column(Text, nullable=True)
    conditions = Column(JSON, nullable=True)  # {"check_weather": "rain_probability < 40%", "min_soil_moisture": 20}
    source = Column(String(30), default=TaskSource.AI_AGENT.value, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    farmer = relationship("FarmerProfile", back_populates="tasks")
    farm = relationship("Farm", back_populates="tasks")
    crop = relationship("FarmCrop", back_populates="tasks")
