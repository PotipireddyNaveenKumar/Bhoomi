import uuid
from sqlalchemy import Column, String, Text, DateTime, ForeignKey, JSON, Index
from sqlalchemy.orm import relationship
from app.db.session import Base
from app.core.datetime_utils import NaiveUTCDateTime, utc_now_naive


class FarmerNotification(Base):
    __tablename__ = "farmer_notifications"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    farmer_id = Column(String(36), ForeignKey("farmer_profiles.id", ondelete="CASCADE"), nullable=False, index=True)
    farm_id = Column(String(36), ForeignKey("farms.id", ondelete="CASCADE"), nullable=False, index=True)
    task_id = Column(String(36), ForeignKey("farm_tasks.id", ondelete="CASCADE"), nullable=False, index=True)
    event_id = Column(String(36), ForeignKey("farm_task_events.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    event_key = Column(String(120), nullable=False, index=True)
    notification_type = Column(String(50), nullable=False, index=True)
    title = Column(Text, nullable=False)
    message = Column(Text, nullable=False)
    locale = Column(String(10), default="en", nullable=False)
    priority = Column(String(20), default="MEDIUM", nullable=False)
    created_at = Column(NaiveUTCDateTime, default=utc_now_naive, nullable=False, index=True)
    read_at = Column(DateTime(timezone=True), nullable=True)
    acknowledged_at = Column(DateTime(timezone=True), nullable=True)
    meta_payload = Column(JSON, nullable=True)

    farmer = relationship("FarmerProfile")
    farm = relationship("Farm")
    task = relationship("FarmTask")
    event = relationship("FarmTaskEvent")

    __table_args__ = (
        Index("ix_farmer_notifications_farmer_created", "farmer_id", "created_at"),
        Index("ix_farmer_notifications_farmer_read", "farmer_id", "read_at"),
    )
