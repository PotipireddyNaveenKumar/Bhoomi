from fastapi import APIRouter, Depends, HTTPException, status
from typing import Dict, Any, List, Optional
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db

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
async def get_farm_state(farmer_id: str = "farmer_demo_1", db: AsyncSession = Depends(get_db)):
    """
    Constructs the canonical real-time FarmState for decision intelligence.
    """
    try:
        return await FarmStateEngine.get_current_state(farmer_id=farmer_id, db=db)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

@router.get("/briefing/today", response_model=DailyBriefing)
async def get_today_briefing(farmer_id: str = "farmer_demo_1", db: AsyncSession = Depends(get_db)):
    """
    Answers: "What should I do today?"
    """
    state = await FarmStateEngine.get_current_state(farmer_id=farmer_id, db=db)
    return DailyFarmBriefingService.generate_today_briefing(state)

@router.get("/briefing/week", response_model=WeeklyBriefing)
async def get_week_briefing(farmer_id: str = "farmer_demo_1", db: AsyncSession = Depends(get_db)):
    """
    Answers: "What should I do this week?"
    """
    state = await FarmStateEngine.get_current_state(farmer_id=farmer_id, db=db)
    return DailyFarmBriefingService.generate_week_briefing(state)

@router.get("/changes", response_model=FarmChangeReport)
async def get_farm_changes(farmer_id: str = "farmer_demo_1", db: AsyncSession = Depends(get_db)):
    """
    "What changed?" Engine.
    Detects differences in weather, market, crop stage, and farm tasks since yesterday.
    """
    state = await FarmStateEngine.get_current_state(farmer_id=farmer_id, db=db)
    return FarmChangeDetectionService.detect_changes(state)

@router.get("/alerts", response_model=List[ProactiveAlert])
async def get_proactive_alerts(farmer_id: str = "farmer_demo_1", db: AsyncSession = Depends(get_db)):
    """
    Fetches proactive evidence-grounded alerts.
    """
    state = await FarmStateEngine.get_current_state(farmer_id=farmer_id, db=db)
    return ProactiveAlertEngine.evaluate_alerts(state)

@router.post("/events", response_model=EventProcessingResult)
async def record_farm_event(event: FarmEvent):
    """
    Records a farm event and evaluates reactive task adjustments.
    """
    return FarmEventProcessor.process_event(event)

@router.get("/timeline", response_model=TimelineStatus)
async def get_crop_health_timeline(farmer_id: str = "farmer_demo_1", crop_name: str = "Chilli"):
    """
    Tracks serial crop health observations over time.
    """
    return CropHealthTimeline.evaluate_trajectory(farmer_id=farmer_id, crop_name=crop_name)

@router.get("/plan", response_model=Optional[FarmPlan])
async def get_current_farm_plan(farmer_id: str = "farmer_demo_1"):
    """
    Gets the adaptive Farm Plan and active contingency playbooks.
    """
    plan = FarmPlanManager.get_plan(farmer_id)
    if not plan:
        plan = FarmPlanManager.create_or_update_plan(farmer_id=farmer_id, farm_id="farm_1")
    return plan

class FeedbackRequest(BaseModel):
    recommendation_id: str
    action_taken: str  # ACCEPTED, MODIFIED, REJECTED
    feedback_rating: str  # USEFUL, PARTIAL, NOT_USEFUL
    notes: Optional[str] = None

@router.post("/feedback")
async def submit_recommendation_feedback(feedback: FeedbackRequest):
    """
    Submits farmer feedback on AI recommendation to close the evaluation loop.
    """
    updated = RecommendationTraceStore.update_feedback(
        recommendation_id=feedback.recommendation_id,
        farmer_action=feedback.action_taken,
        feedback_rating=feedback.feedback_rating,
        feedback_notes=feedback.notes
    )
    return {"status": "success", "updated_record": updated.model_dump() if updated else None}
