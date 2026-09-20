import uuid
import enum
from datetime import datetime
from sqlalchemy import Column, String, Text, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from app.db.session import Base
from app.core.datetime_utils import NaiveUTCDateTime, utc_now_naive


class TaskEventType(str, enum.Enum):
    TASK_DUE = "TASK_DUE"
    TASK_OVERDUE = "TASK_OVERDUE"
    TASK_EXPIRED = "TASK_EXPIRED"
    TASK_REMINDER = "TASK_REMINDER"


class TaskEventStatus(str, enum.Enum):
    PENDING = "PENDING"
    DELIVERED = "DELIVERED"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class FarmTaskEvent(Base):
    __tablename__ = "farm_task_events"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    task_id = Column(String(36), ForeignKey("farm_tasks.id", ondelete="CASCADE"), nullable=False, index=True)
    farmer_id = Column(String(36), ForeignKey("farmer_profiles.id", ondelete="CASCADE"), nullable=False, index=True)
    farm_id = Column(String(36), ForeignKey("farms.id", ondelete="CASCADE"), nullable=False, index=True)
    event_type = Column(String(50), nullable=False, index=True)
    event_key = Column(String(120), unique=True, nullable=False, index=True)
    created_at = Column(NaiveUTCDateTime, default=utc_now_naive, nullable=False)
    scheduled_for = Column(DateTime(timezone=True), nullable=True)
    delivered_at = Column(DateTime(timezone=True), nullable=True)
    acknowledged_at = Column(DateTime(timezone=True), nullable=True)
    payload = Column(JSON, nullable=True)
    status = Column(String(30), default=TaskEventStatus.PENDING.value, nullable=False, index=True)

    task = relationship("FarmTask", backref="lifecycle_events")
    farmer = relationship("FarmerProfile")
    farm = relationship("Farm")
