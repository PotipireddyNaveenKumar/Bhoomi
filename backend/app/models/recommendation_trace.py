import uuid
from datetime import datetime
from typing import Dict, Any, List, Optional, TYPE_CHECKING
from sqlalchemy import String, Text, Float, ForeignKey, JSON, Index, Column
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.session import Base
from app.core.datetime_utils import NaiveUTCDateTime, utc_now_naive

if TYPE_CHECKING:
    from app.models.farmer import FarmerProfile


class RecommendationTrace(Base):
    __tablename__ = "recommendation_traces"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    decision_id: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    recommendation_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    farmer_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("farmer_profiles.id", ondelete="CASCADE"),
        index=True,
        nullable=False
    )
    farm_id: Mapped[Optional[str]] = mapped_column(String(64), index=True, nullable=True)
    decision_type: Mapped[Optional[str]] = mapped_column(String(100), index=True, nullable=True)
    intent: Mapped[Optional[str]] = mapped_column(String(100), index=True, nullable=True)

    created_at: Mapped[datetime] = mapped_column(NaiveUTCDateTime, default=utc_now_naive, index=True, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        NaiveUTCDateTime,
        default=utc_now_naive,
        onupdate=utc_now_naive,
        nullable=False
    )

    # Context and Provenance
    input_context: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    data_freshness: Mapped[Dict[str, str]] = mapped_column(JSON, default=dict, nullable=False)
    tools_used: Mapped[List[str]] = mapped_column(JSON, default=list, nullable=False)
    model_versions: Mapped[Dict[str, str]] = mapped_column(JSON, default=dict, nullable=False)
    rag_sources: Mapped[List[str]] = mapped_column(JSON, default=list, nullable=False)
    weather_source: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    market_source: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    calculations: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    safety_checks: Mapped[List[str]] = mapped_column(JSON, default=list, nullable=False)

    # Core Recommendation Details
    recommendation_text: Mapped[str] = mapped_column(Text, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    assumptions: Mapped[List[str]] = mapped_column(JSON, default=list, nullable=False)
    rationale: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    evidence: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    xai_info: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)

    # Lifecycle and Feedback
    farmer_action: Mapped[str] = mapped_column(String(50), default="PENDING", index=True, nullable=False)
    outcome: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    feedback_rating: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    feedback_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Metadata & Localization
    locale: Mapped[str] = mapped_column(String(20), default="en", nullable=False)
    metadata_json: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)

    farmer: Mapped["FarmerProfile"] = relationship("FarmerProfile", back_populates="recommendation_traces")

    __table_args__ = (
        Index("ix_rec_traces_farmer_created", "farmer_id", "created_at"),
        Index("ix_rec_traces_farm_created", "farm_id", "created_at"),
        Index("ix_rec_traces_farmer_type", "farmer_id", "decision_type"),
    )
