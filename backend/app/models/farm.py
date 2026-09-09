import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Float, Numeric, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from app.db.session import Base

class Farm(Base):
    __tablename__ = "farms"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    farmer_id = Column(String(36), ForeignKey("farmer_profiles.id", ondelete="CASCADE"), nullable=False)
    farm_name = Column(String(100), default="My Farm", nullable=False)
    total_area_acres = Column(Numeric(10, 2), nullable=False)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    soil_type = Column(String(50), nullable=True)  # black, red, alluvial, sandy, clay, loamy
    irrigation_source = Column(String(50), nullable=True)  # borewell, canal, drip, sprinkler, rainfed
    soil_health_data = Column(JSON, nullable=True)  # {"N": 120, "P": 40, "K": 60, "pH": 6.8}
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    farmer = relationship("FarmerProfile", back_populates="farms")
    crops = relationship("FarmCrop", back_populates="farm", cascade="all, delete-orphan")
    tasks = relationship("FarmTask", back_populates="farm", cascade="all, delete-orphan")
