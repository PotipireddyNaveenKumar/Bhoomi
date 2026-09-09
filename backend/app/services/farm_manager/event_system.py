from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

class FarmEvent(BaseModel):
    event_id: str
    farmer_id: str
    farm_id: str
    event_type: str  # sowing_completed, irrigation_completed, fertilizer_applied, pesticide_applied, disease_detected, heavy_rainfall, rainfall_deficit, temperature_anomaly, market_price_change, harvest_approaching, task_completed, task_missed, farmer_decision, crop_stage_transition
    severity: str = "INFO"  # INFO, WARNING, CRITICAL
    payload: Dict[str, Any] = {}
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

class EventProcessingResult(BaseModel):
    event: FarmEvent
    state_modified: bool
    tasks_affected: List[str]
    notification_message: Optional[str] = None
    recommended_action: Optional[str] = None

class FarmEventStore:
    """
    In-memory / persistent event store tracking chronological farm events.
    """
    _events: List[FarmEvent] = []

    @classmethod
    def record_event(cls, event: FarmEvent) -> FarmEvent:
        cls._events.append(event)
        return event

    @classmethod
    def get_events_for_farmer(cls, farmer_id: str, limit: int = 50) -> List[FarmEvent]:
        events = [e for e in cls._events if e.farmer_id == farmer_id]
        return sorted(events, key=lambda x: x.timestamp, reverse=True)[:limit]

class FarmEventProcessor:
    """
    Evaluates incoming farm events against operational rules and current farm state.
    Triggers reactive task adjustments and proactive farmer notifications.
    """
    @classmethod
    def process_event(cls, event: FarmEvent) -> EventProcessingResult:
        FarmEventStore.record_event(event)

        state_modified = False
        tasks_affected = []
        notification = None
        action = None

        if event.event_type == "heavy_rainfall":
            state_modified = True
            tasks_affected.append("irrigation_task_102")
            notification = (
                f"🌧️ Weather Alert: Heavy precipitation expected ({event.payload.get('rainfall_mm', 30)}mm). "
                f"Scheduled surface irrigation has been postponed by 48 hours to protect root health."
            )
            action = "Inspect and open drainage ditches to prevent low-lying water stagnation."

        elif event.event_type == "disease_detected":
            state_modified = True
            disease = event.payload.get("disease_name", "Leaf Spot")
            tasks_affected.append(f"scout_task_{event.event_id}")
            notification = f"⚠️ Pathology Alert: Detected {disease}. Immediate foliar inspection and IPM bio-control recommended."
            action = f"Apply recommended {event.payload.get('ipm_treatment', 'Neem oil')} on affected plots."

        elif event.event_type == "market_price_change":
            price = event.payload.get("modal_price", 0.0)
            threshold = event.payload.get("threshold", 12000.0)
            if price >= threshold:
                state_modified = True
                notification = f"📈 Mandi Peak Alert: Modal price reached ₹{price:,.0f}/quintal, exceeding your target ₹{threshold:,.0f}."
                action = "Review harvesting schedule and arrange mandi transportation."

        elif event.event_type == "crop_stage_transition":
            new_stage = event.payload.get("new_stage", "flowering")
            state_modified = True
            notification = f"🌸 Crop Lifecycle Update: Crop transitioned into {new_stage.upper()} stage."
            if new_stage.lower() == "flowering":
                action = "Enforce pollinator safety: schedule spraying only during late evening hours."

        elif event.event_type == "farmer_decision":
            state_modified = True
            decision = event.payload.get("decision", "")
            notification = f"✅ Farm Decision Recorded: {decision}. Farm Plan and dynamic tasks updated."
            action = "Executing corresponding stage tasks in Farm Plan."

        return EventProcessingResult(
            event=event,
            state_modified=state_modified,
            tasks_affected=tasks_affected,
            notification_message=notification,
            recommended_action=action
        )
