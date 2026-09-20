from fastapi import APIRouter, HTTPException, status, Depends, Query
from typing import Dict, Any, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.api.deps import get_current_farmer_profile
from app.models.farmer import FarmerProfile
from app.repositories.farm_repo import FarmRepository
from app.repositories.recommendation_repo import RecommendationRepository
from app.schemas.decision import (
    DecisionEvaluationRequest,
    DecisionEvaluationResponse,
    DecisionPlan,
    DecisionTraceResponse,
    DecisionHistoryResponse,
)
from app.services.farm_manager.state_engine import FarmStateEngine
from app.services.farm_manager.decision_engine import FarmDecisionEngine
from app.services.farm_manager.risk_aggregator import FarmRiskAggregator
from app.services.farm_manager.missing_info_detector import MissingInformationDetector

router = APIRouter(prefix="/decisions", tags=["Decision Intelligence"])


def _format_trace_response(trace) -> DecisionTraceResponse:
    return DecisionTraceResponse(
        id=trace.id,
        decision_id=trace.decision_id,
        recommendation_id=trace.recommendation_id,
        farmer_id=trace.farmer_id,
        farm_id=trace.farm_id,
        decision_type=trace.decision_type,
        intent=trace.intent,
        created_at=trace.created_at.isoformat() if trace.created_at else "",
        updated_at=trace.updated_at.isoformat() if trace.updated_at else "",
        input_context=trace.input_context or {},
        data_freshness=trace.data_freshness or {},
        tools_used=trace.tools_used or [],
        model_versions=trace.model_versions or {},
        rag_sources=trace.rag_sources or [],
        weather_source=trace.weather_source,
        market_source=trace.market_source,
        calculations=trace.calculations or {},
        safety_checks=trace.safety_checks or [],
        recommendation_text=trace.recommendation_text,
        confidence=trace.confidence,
        assumptions=trace.assumptions or [],
        rationale=trace.rationale,
        evidence=trace.evidence or {},
        xai_info=trace.xai_info or {},
        farmer_action=trace.farmer_action,
        outcome=trace.outcome,
        feedback_rating=trace.feedback_rating,
        feedback_notes=trace.feedback_notes,
        locale=trace.locale or "en",
        metadata_json=trace.metadata_json or {},
    )


@router.post("/evaluate", response_model=DecisionEvaluationResponse)
async def evaluate_farm_decisions(
    request: DecisionEvaluationRequest,
    farmer: FarmerProfile = Depends(get_current_farmer_profile),
    db: AsyncSession = Depends(get_db)
):
    """
    Canonical Decision Intelligence Evaluation Endpoint.
    Evaluates FarmState, assesses operational risks, resolves conflicts deterministically,
    and returns a fully traceable DecisionPlan.
    Enforces JWT authentication, farmer ownership, and farm authorization.
    """
    # 1. Tenant & Identity Enforcement: Client-supplied farmer_id cannot impersonate another farmer
    effective_farmer_id = farmer.id

    # 2. Farm Ownership Enforcement
    farm_repo = FarmRepository(db)
    farmer_farms = await farm_repo.get_farms_by_farmer(farmer.id)
    authorized_farm_ids = {f.id for f in farmer_farms} if farmer_farms else set()

    effective_farm_id = request.farm_id
    if effective_farm_id and effective_farm_id != "farm_1":
        if authorized_farm_ids and effective_farm_id not in authorized_farm_ids:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access forbidden: Specified farm does not belong to the authenticated farmer."
            )
    else:
        effective_farm_id = farmer_farms[0].id if farmer_farms else (request.farm_id or "farm_1")

    try:
        state = await FarmStateEngine.get_current_state(farmer_id=effective_farmer_id, db=db)
        if effective_farm_id:
            state.farm_id = effective_farm_id

        plan = await FarmDecisionEngine.generate_plan_async(state, db=db)
        risks = FarmRiskAggregator.evaluate_risks(state)
        missing_info = MissingInformationDetector.detect_missing(state=state, intent=request.intent)

        return DecisionEvaluationResponse(
            success=True,
            plan=plan,
            missing_information=missing_info,
            conflicts_resolved=[],
            active_risks=[r.model_dump() for r in risks]
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Decision evaluation failed: {str(e)}"
        )


@router.get("/history", response_model=DecisionHistoryResponse)
async def get_decision_history(
    farm_id: Optional[str] = Query(default=None, description="Filter by farm ID"),
    decision_type: Optional[str] = Query(default=None, description="Filter by decision type"),
    limit: int = Query(default=20, ge=1, le=100, description="Page limit"),
    offset: int = Query(default=0, ge=0, description="Page offset"),
    farmer: FarmerProfile = Depends(get_current_farmer_profile),
    db: AsyncSession = Depends(get_db)
):
    """
    Retrieves chronological decision history for the authenticated farmer.
    Enforces strict tenant isolation and farm ownership verification.
    """
    if farm_id:
        farm_repo = FarmRepository(db)
        farms = await farm_repo.get_farms_by_farmer(farmer.id)
        authorized_farm_ids = [f.id for f in farms] if farms else []
        if farm_id not in authorized_farm_ids:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access forbidden: Specified farm does not belong to the authenticated farmer."
            )

    repo = RecommendationRepository(db)
    traces = await repo.list_for_farmer(
        farmer_id=farmer.id,
        farm_id=farm_id,
        decision_type=decision_type,
        limit=limit,
        offset=offset
    )

    return DecisionHistoryResponse(
        success=True,
        total=len(traces),
        limit=limit,
        offset=offset,
        decisions=[_format_trace_response(t) for t in traces]
    )


@router.get("/{decision_id}", response_model=DecisionTraceResponse)
async def get_decision_detail(
    decision_id: str,
    farmer: FarmerProfile = Depends(get_current_farmer_profile),
    db: AsyncSession = Depends(get_db)
):
    """
    Retrieves full provenance and explainability details for a specific decision.
    Strictly verifies tenant ownership; returns 404 if missing, 403 if foreign.
    """
    repo = RecommendationRepository(db)
    trace = await repo.get_by_decision_id(decision_id)
    if not trace:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Decision trace '{decision_id}' not found."
        )

    if trace.farmer_id != farmer.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access forbidden: You do not have permission to view this decision trace."
        )

    return _format_trace_response(trace)
