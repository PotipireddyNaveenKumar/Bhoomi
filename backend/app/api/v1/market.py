from decimal import Decimal
from fastapi import APIRouter, Depends, Query
from app.api.deps import get_current_farmer_profile
from app.models.farmer import FarmerProfile
from app.services.market.market_service import MarketService
from app.services.farm_manager.market_decision import MarketDecisionEngine
from app.schemas.market import MarketComparisonResponse

router = APIRouter(prefix="/market", tags=["Market Mandi Intelligence"])

@router.get("", response_model=MarketComparisonResponse)
async def get_market_analysis(
    commodity: str = Query(default="Chilli"),
    state: str = Query(default="Andhra Pradesh"),
    district: str = Query(default="Guntur"),
    farmer: FarmerProfile = Depends(get_current_farmer_profile),
):
    dist = district or getattr(farmer, "district", None) or "Guntur"
    st = state or getattr(farmer, "state", None) or "Andhra Pradesh"
    res = await MarketService.get_mandi_prices(commodity=commodity, state=st, district=dist)
    try:
        decision_out = MarketDecisionEngine.evaluate(
            crop_name=commodity,
            current_modal_price=res.best_net_realization or Decimal("12200.00"),
            mandi_options=res.mandi_options,
            freshness=res.freshness
        )
        res.market_decision = decision_out.decision
        res.decision_rationale = decision_out.rationale
    except Exception:
        pass
    return res
