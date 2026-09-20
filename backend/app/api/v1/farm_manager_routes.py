from fastapi import APIRouter, Depends, HTTPException, status
from typing import Dict, Any, List, Optional
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.api.deps import get_current_farmer_profile
from app.models.farmer import FarmerProfile

from app.services.farm_manager.state_engine import FarmStateEngine, FarmState
from app.services.farm_manager.daily_briefing import DailyFarmBriefingService, DailyBriefing, WeeklyBriefing
from app.services.farm_manager.change_detector import FarmChangeDetectionService, FarmChangeReport
from app.services.farm_manager.proactive_alerts import ProactiveAlertEngine, ProactiveAlert, FarmerThresholds
from app.services.farm_manager.event_system import FarmEvent, FarmEventProcessor, EventProcessingResult
from app.services.farm_manager.crop_health_timeline import CropHealthTimeline, TimelineStatus, FoliarObservation
from app.services.farm_manager.recommendation_trace import RecommendationTraceStore, RecommendationRecord
from app.services.farm_manager.farm_plan import FarmPlanManager, FarmPlan

router = APIRouter(prefix="/manager", tags=["Personal AI Farm Manager"])

@router.get("/state", response_model=FarmState)
async def get_farm_state(
    farmer: FarmerProfile = Depends(get_current_farmer_profile),
    db: AsyncSession = Depends(get_db)
):
    """
    Constructs the canonical real-time FarmState for decision intelligence.
    Identity strictly derived from authenticated JWT session.
    """
    try:
        return await FarmStateEngine.get_current_state(farmer_id=farmer.id, db=db)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

@router.get("/briefing/today", response_model=DailyBriefing)
async def get_today_briefing(
    farmer: FarmerProfile = Depends(get_current_farmer_profile),
    db: AsyncSession = Depends(get_db)
):
    """
    Answers: "What should I do today?"
    Strictly isolated to authenticated farmer profile.
    """
    state = await FarmStateEngine.get_current_state(farmer_id=farmer.id, db=db)
    return DailyFarmBriefingService.generate_today_briefing(state)

@router.get("/briefing/week", response_model=WeeklyBriefing)
async def get_week_briefing(
    farmer: FarmerProfile = Depends(get_current_farmer_profile),
    db: AsyncSession = Depends(get_db)
):
    """
    Answers: "What should I do this week?"
    Strictly isolated to authenticated farmer profile.
    """
    state = await FarmStateEngine.get_current_state(farmer_id=farmer.id, db=db)
    return DailyFarmBriefingService.generate_week_briefing(state)

@router.get("/changes", response_model=FarmChangeReport)
async def get_farm_changes(
    farmer: FarmerProfile = Depends(get_current_farmer_profile),
    db: AsyncSession = Depends(get_db)
):
    """
    "What changed?" Engine.
    Detects differences in weather, market, crop stage, and farm tasks since yesterday.
    """
    state = await FarmStateEngine.get_current_state(farmer_id=farmer.id, db=db)
    return FarmChangeDetectionService.detect_changes(state)

@router.get("/alerts", response_model=List[ProactiveAlert])
async def get_proactive_alerts(
    farmer: FarmerProfile = Depends(get_current_farmer_profile),
    db: AsyncSession = Depends(get_db)
):
    """
    Fetches proactive evidence-grounded alerts strictly for authenticated farmer.
    """
    state = await FarmStateEngine.get_current_state(farmer_id=farmer.id, db=db)
    return ProactiveAlertEngine.evaluate_alerts(state)

@router.post("/events", response_model=EventProcessingResult)
async def record_farm_event(
    event: FarmEvent,
    farmer: FarmerProfile = Depends(get_current_farmer_profile)
):
    """
    Records a farm event and evaluates reactive task adjustments.
    Enforces strict tenant boundary: farmer cannot manipulate another farmer's state.
    """
    if event.farmer_id and event.farmer_id != farmer.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access forbidden: You cannot record events for another farmer."
        )
    event.farmer_id = farmer.id
    return FarmEventProcessor.process_event(event)

@router.get("/timeline", response_model=TimelineStatus)
async def get_crop_health_timeline(
    crop_name: str = "Chilli",
    farmer: FarmerProfile = Depends(get_current_farmer_profile)
):
    """
    Tracks serial crop health observations over time for authenticated farmer.
    """
    return CropHealthTimeline.evaluate_trajectory(farmer_id=farmer.id, crop_name=crop_name)

@router.get("/plan", response_model=Optional[FarmPlan])
async def get_current_farm_plan(
    farmer: FarmerProfile = Depends(get_current_farmer_profile),
    db: AsyncSession = Depends(get_db)
):
    """
    Gets the adaptive Farm Plan and active contingency playbooks for authenticated farmer.
    """
    from app.repositories.farm_repo import FarmRepository
    farm_repo = FarmRepository(db)
    farms = await farm_repo.get_farms_by_farmer(farmer.id)
    target_farm_id = farms[0].id if farms else "farm_1"
    plan = FarmPlanManager.get_plan(farmer.id)
    if not plan:
        plan = FarmPlanManager.create_or_update_plan(farmer_id=farmer.id, farm_id=target_farm_id)
    return plan

class FeedbackRequest(BaseModel):
    recommendation_id: str
    action_taken: str  # ACCEPTED, MODIFIED, REJECTED
    feedback_rating: str  # USEFUL, PARTIAL, NOT_USEFUL
    notes: Optional[str] = None

@router.post("/feedback")
async def submit_recommendation_feedback(
    feedback: FeedbackRequest,
    farmer: FarmerProfile = Depends(get_current_farmer_profile),
    db: AsyncSession = Depends(get_db)
):
    """
    Submits farmer feedback on AI recommendation to close the evaluation loop.
    Strictly requires authenticated farmer session.
    """
    updated = await RecommendationTraceStore.update_feedback_async(
        recommendation_id=feedback.recommendation_id,
        farmer_action=feedback.action_taken,
        feedback_rating=feedback.feedback_rating,
        feedback_notes=feedback.notes,
        db=db
    )
    return {"status": "success", "updated_record": updated.model_dump() if updated else None}

