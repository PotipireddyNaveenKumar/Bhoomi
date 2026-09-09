from fastapi import APIRouter, HTTPException, status
from typing import Dict, Any, List

from app.schemas.decision import (
    DecisionEvaluationRequest,
    DecisionEvaluationResponse,
    DecisionPlan
)
from app.services.farm_manager.state_engine import FarmStateEngine
from app.services.farm_manager.decision_engine import FarmDecisionEngine
from app.services.farm_manager.risk_aggregator import FarmRiskAggregator
from app.services.farm_manager.missing_info_detector import MissingInformationDetector

router = APIRouter(prefix="/decisions", tags=["Decision Intelligence"])


@router.post("/evaluate", response_model=DecisionEvaluationResponse)
async def evaluate_farm_decisions(request: DecisionEvaluationRequest):
    """
    Canonical Decision Intelligence Evaluation Endpoint.
    Evaluates FarmState, assesses operational risks, resolves conflicts deterministically,
    and returns a fully traceable DecisionPlan.
    """
    try:
        state = await FarmStateEngine.get_current_state(farmer_id=request.farmer_id)
        plan = FarmDecisionEngine.generate_plan(state)
        risks = FarmRiskAggregator.evaluate_risks(state)
        missing_info = MissingInformationDetector.detect_missing(state=state, intent=request.intent)

        return DecisionEvaluationResponse(
            success=True,
            plan=plan,
            missing_information=missing_info,
            conflicts_resolved=[],
            active_risks=[r.model_dump() for r in risks]
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Decision evaluation failed: {str(e)}"
        )
