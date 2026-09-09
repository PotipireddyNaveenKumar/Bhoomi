from typing import Optional, List
from decimal import Decimal
from datetime import date
from enum import Enum
from pydantic import BaseModel, Field, model_validator

class MarketFreshnessStatus(str, Enum):
    CURRENT = "CURRENT"
    CACHED = "CACHED"
    STALE = "STALE"
    UNAVAILABLE = "UNAVAILABLE"
    HISTORICAL = "HISTORICAL"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"

class MandiPrice(BaseModel):
    mandi_name: str
    district: str
    state: str
    commodity: str
    variety: Optional[str] = None
    grade: Optional[str] = None
    min_price_per_quintal: Optional[Decimal] = None
    max_price_per_quintal: Optional[Decimal] = None
    modal_price_per_quintal: Optional[Decimal] = None
    price_unit: str = "₹/quintal"
    currency: str = "INR"
    distance_km: Optional[Decimal] = None
    transport_cost_per_quintal: Optional[Decimal] = None
    selling_cost_per_quintal: Optional[Decimal] = None
    net_realization_per_quintal: Optional[Decimal] = None
    arrival_date: Optional[str] = None
    price_date: Optional[date] = None
    source: str = "AGMARKNET / data.gov.in"
    retrieved_at: Optional[str] = None
    freshness: str = MarketFreshnessStatus.CURRENT.value
    is_live: bool = False
    status: str = "VALID"  # VALID or INSUFFICIENT_DATA

    @property
    def transport_distance_km(self) -> Optional[Decimal]:
        return self.distance_km

    @property
    def selling_fee_per_quintal(self) -> Optional[Decimal]:
        return self.selling_cost_per_quintal

    @model_validator(mode="after")
    def compute_or_validate_net_realization(self) -> "MandiPrice":
        """
        Enforces strict economic calculation:
          net_realization_per_quintal = modal_price_per_quintal - transport_cost_per_quintal - selling_cost_per_quintal
        If any cost input is missing/null, net_realization MUST be null and status MUST be INSUFFICIENT_DATA.
        Neither transport cost nor selling fees may be silently assumed to be zero.
        """
        if (
            self.modal_price_per_quintal is None
            or self.transport_cost_per_quintal is None
            or self.selling_cost_per_quintal is None
        ):
            self.net_realization_per_quintal = None
            self.status = "INSUFFICIENT_DATA"
        else:
            computed = (
                self.modal_price_per_quintal
                - self.transport_cost_per_quintal
                - self.selling_cost_per_quintal
            )
            # If not explicitly provided, assign the exact computed Decimal
            if self.net_realization_per_quintal is None:
                self.net_realization_per_quintal = computed
            self.status = "VALID"
        return self

class MarketComparisonResponse(BaseModel):
    commodity: str
    variety: Optional[str] = None
    state: Optional[str] = None
    district: Optional[str] = None
    recommended_mandi: Optional[str] = None
    best_net_realization: Optional[Decimal] = None
    mandi_options: List[MandiPrice] = []
    recommendation_reason: str = ""
    source: str = "AGMARKNET / data.gov.in"
    freshness: str = MarketFreshnessStatus.CURRENT.value
    retrieved_at: Optional[str] = None
    is_live: bool = False
    market_decision: Optional[str] = "COMPARE MARKETS"
    decision_rationale: Optional[str] = None
