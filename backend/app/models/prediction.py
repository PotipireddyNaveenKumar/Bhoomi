from typing import Optional, Dict, Any, TYPE_CHECKING
import uuid
from datetime import datetime
from sqlalchemy import String, Float, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.session import Base
from app.core.datetime_utils import NaiveUTCDateTime, utc_now_naive

if TYPE_CHECKING:
    from app.models.farmer import FarmerProfile

class PredictionHistory(Base):
    __tablename__ = "prediction_history"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    farmer_id: Mapped[str] = mapped_column(String(36), ForeignKey("farmer_profiles.id", ondelete="CASCADE"), nullable=False)
    prediction_type: Mapped[str] = mapped_column(String(50), nullable=False)  # yield, crop_recommendation, disease_diagnosis, profit, risk
    input_features: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False)
    output_result: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False)
    model_version: Mapped[str] = mapped_column(String(50), default="v1.0.0")
    confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(NaiveUTCDateTime, default=utc_now_naive)
