from typing import Optional
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
    commodity: Optional[str] = Query(default=None),
    state: Optional[str] = Query(default=None),
    district: Optional[str] = Query(default=None),
    farmer: FarmerProfile = Depends(get_current_farmer_profile),
):
    from fastapi import HTTPException, status
    target_crop = commodity or getattr(farmer, "crop", None)
    if not target_crop:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Commodity name must be provided via query parameter or configured in farmer profile."
        )

    dist = district or getattr(farmer, "district", None)
    if not dist:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="District must be provided via query parameter or configured in farmer profile."
        )

    st = state or getattr(farmer, "state", None) or (
        "Telangana" if dist.lower() in ("warangal", "khammam", "hyderabad", "karimnagar", "nizamabad") else "Andhra Pradesh"
    )

    res = await MarketService.get_mandi_prices(commodity=target_crop, state=st, district=dist)
    try:
        if res.best_net_realization is not None:
            decision_out = MarketDecisionEngine.evaluate(
                crop_name=target_crop,
                current_modal_price=res.best_net_realization,
                mandi_options=res.mandi_options,
                freshness=res.freshness
            )
            res.market_decision = decision_out.decision
            res.decision_rationale = decision_out.rationale
        else:
            res.market_decision = "UNAVAILABLE"
            res.decision_rationale = "Live mandi rates currently unavailable from official price feeds. Verify quotes with local APMC market committee."
    except Exception:
        pass
    return res
