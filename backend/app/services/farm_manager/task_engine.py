import uuid
import hashlib
from datetime import date, datetime, timedelta, timezone
from typing import Dict, Any, List, Optional, Tuple

from app.schemas.decision import DecisionPriority, ConfidenceLevel
from app.schemas.task import (
    FarmTask,
    TaskType,
    TaskStatus,
    CropLifecycleState
)
from app.services.farm_manager.state_engine import FarmState
from app.services.crop.lifecycle_service import CropLifecycleService
from app.services.farm_manager.irrigation_decision import IrrigationDecisionService
from app.services.farm_manager.harvest_decision import HarvestDecisionEngine
from app.services.safety.safety_engine import SafetyEngine
from app.services.memory.farm_memory_v2 import FarmMemoryV2


class TaskIntelligenceEngine:
    """
    Agricultural Task Intelligence Engine.
    Generates, deduplicates, prioritizes, and dynamically replans canonical FarmTasks.
    Integrates with:
      - CropLifecycleService (deterministic biological stages)
      - IrrigationDecisionService (soil-water dynamics)
      - WeatherDecisionEngine / live weather (precipitation postponement)
      - CropHealthTimeline & Vision (inspection-first follow-up)
      - HarvestDecisionEngine (maturity-driven harvest & market prep)
      - SafetyEngine (banned chemical filtering & offline restrictions)
      - FarmMemoryV2 (episodic & longitudinal task lifecycle tracking)
    """

    # In-memory store for active tasks indexed by farm_id
    _tasks_by_farm: Dict[str, List[FarmTask]] = {}

    @classmethod
    def _generate_task_dedup_hash(cls, farm_id: str, crop: str, task_type: TaskType, trigger: str, due_window: str) -> str:
        raw = f"{farm_id}_{crop.lower()}_{task_type.value}_{trigger.lower()}_{due_window}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]

    @classmethod
    def get_tasks_for_farm(cls, farm_id: str) -> List[FarmTask]:
        return cls._tasks_by_farm.get(farm_id, [])

    @classmethod
    def clear_tasks_for_farm(cls, farm_id: str):
        if farm_id in cls._tasks_by_farm:
            cls._tasks_by_farm[farm_id] = []

    @classmethod
    def generate_tasks_for_farm(
        cls,
        state: FarmState,
        lifecycle: Optional[CropLifecycleState] = None,
        trace_id: Optional[str] = None
    ) -> List[FarmTask]:
        """
        Deterministically generates contextual FarmTasks from farm state, crop stage,
        weather, irrigation, crop health, and harvest readiness.
        """
        active_trace = trace_id or f"trace_{uuid.uuid4().hex[:12]}"
        crop = state.active_crop or "Chilli"
        farm_id = getattr(state, "farm_id", "farm_1")
        farmer_id = state.farmer_id

        # 1. Resolve crop lifecycle
        if not lifecycle:
            lifecycle = CropLifecycleService.calculate_lifecycle_state(
                crop=crop,
                sowing_date=getattr(state, "sowing_date", None),
                variety=getattr(state, "variety", None)
            )

        current_stage = lifecycle.current_stage.lower()
        freshness_map = {
            k: getattr(v, "freshness_status", "CURRENT")
            for k, v in (state.data_freshness or {}).items()
        }
        weather_freshness = freshness_map.get("weather", "CURRENT")

        today_dt = datetime.now(timezone.utc)
        today_str = today_dt.date().isoformat()
        tomorrow_str = (today_dt.date() + timedelta(days=1)).isoformat()

        new_tasks: List[FarmTask] = []

        # -------------------------------------------------------------
        # 1. CROP STAGE BASED TASKS
        # -------------------------------------------------------------
        guidance = CropLifecycleService.get_stage_guidance(crop, current_stage)

        if current_stage == "flowering":
            # Nutrient & pollinator task
            if crop.lower() in ["rice", "paddy"]:
                spray_title = f"[RESEARCH ONLY] {crop.capitalize()} Panicle Initiation Monitoring & Research Scouting"
                spray_desc = "Record panicle emergence and flag leaf health for agronomic research dataset. Barred from farmer chemical prescription."
                spray_task_type = TaskType.CROP_HEALTH_SCOUTING
                spray_safety = "RESEARCH_ONLY"
            else:
                spray_title = f"{crop.capitalize()} Flowering Foliar Support: Micronutrient & Flower Retention Spray"
                spray_desc = "Apply 19:19:19 + Boron foliar spray to prevent blossom drop. RESTRICTION: Spray ONLY in late evening after 5:30 PM to safeguard pollinating bees."
                spray_task_type = TaskType.FERTILIZATION
                spray_safety = "VERIFIED_SAFE"
            
            # Weather check for spray
            rain_prob = state.weather_summary.get("rain_probability") or 0
            is_rain_high = rain_prob >= 50

            task_status = TaskStatus.POSTPONED if is_rain_high else TaskStatus.DUE
            postpone_reason = "Rain probability is high (>= 50%). Spraying will wash away foliar nutrients." if is_rain_high else None

            spray_task = FarmTask(
                task_id=f"task_{farm_id}_foliar_flowering_{today_str}",
                farm_id=farm_id,
                crop=crop,
                task_type=spray_task_type,
                title=spray_title,
                description=spray_desc,
                priority=DecisionPriority.HIGH,
                status=task_status,
                due_at=today_str,
                expires_at=(today_dt.date() + timedelta(days=3)).isoformat(),
                crop_stage=current_stage,
                stage_dependency=current_stage,
                weather_dependency={"max_rain_probability": 40, "avoid_hours": "09:00-17:30"},
                trigger="crop_stage_flowering",
                reason=f"{crop.capitalize()} is in critical flowering stage requiring boron and potassium for fruit set.",
                evidence=f"Crop age: {lifecycle.days_after_sowing or state.days_after_sowing} DAS. IIHR recommended practice.",
                source_references=[guidance.get("source", "ICAR Package of Practices")],
                safety_status=spray_safety,
                postponed_at=today_str if is_rain_high else None,
                postponement_reason=postpone_reason,
                old_due_time=today_str if is_rain_high else None,
                new_due_time=tomorrow_str if is_rain_high else None,
                trace_id=active_trace,
                weather_freshness=weather_freshness
            )
            new_tasks.append(spray_task)

            # Weekly inspection task for flowering
            scout_task = FarmTask(
                task_id=f"task_{farm_id}_scout_flowering_{today_str}",
                farm_id=farm_id,
                crop=crop,
                task_type=TaskType.FIELD_INSPECTION,
                title=f"Inspect {crop.capitalize()} Terminal Leaves & Flowers",
                description="Check lower canopy and flowers on 10 plants per acre for thrips, mites, or blossom rot.",
                priority=DecisionPriority.MEDIUM,
                status=TaskStatus.DUE,
                due_at=today_str,
                crop_stage=current_stage,
                stage_dependency=current_stage,
                trigger="biweekly_flowering_scouting",
                reason="Flowering stage is highly susceptible to flower thrips and fungal blossom rot.",
                evidence="Regular IPM protocol for Solanaceous crops.",
                source_references=["ANGRAU IPM Guidelines"],
                safety_status="VERIFIED_SAFE",
                trace_id=active_trace,
                weather_freshness=weather_freshness
            )
            new_tasks.append(scout_task)

        elif current_stage == "vegetative":
            veg_task = FarmTask(
                task_id=f"task_{farm_id}_veg_weeding_{today_str}",
                farm_id=farm_id,
                crop=crop,
                task_type=TaskType.WEED_MANAGEMENT,
                title=f"Intercultural Weeding & Soil Aeration",
                description=f"Conduct manual hoeing or intercultural weeding between {crop} rows before canopy closes.",
                priority=DecisionPriority.MEDIUM,
                status=TaskStatus.PLANNED,
                due_at=tomorrow_str,
                crop_stage=current_stage,
                trigger="crop_stage_vegetative",
                reason="Weeds compete aggressively for soil nitrogen and moisture during active vegetative expansion.",
                evidence=f"Vegetative stage (DAS {lifecycle.days_after_sowing or state.days_after_sowing}).",
                source_references=["ICAR Package of Practices"],
                safety_status="VERIFIED_SAFE",
                trace_id=active_trace,
                weather_freshness=weather_freshness
            )
            new_tasks.append(veg_task)

        elif current_stage in ["fruit_development", "maturity"]:
            fruit_task = FarmTask(
                task_id=f"task_{farm_id}_fruit_inspection_{today_str}",
                farm_id=farm_id,
                crop=crop,
                task_type=TaskType.DISEASE_MONITORING,
                title=f"Inspect Fruit Canopy for Borer & Rot",
                description=f"Scout developing {crop} pods/fruits for anthracnose spots or fruit borer entry holes.",
                priority=DecisionPriority.HIGH,
                status=TaskStatus.DUE,
                due_at=today_str,
                crop_stage=current_stage,
                trigger="crop_stage_fruit_development",
                reason="Fruit damage causes direct market value discount and yield loss.",
                evidence="Fruit enlargement stage requires prophylactic monitoring.",
                source_references=["ICAR-IIHR Plant Pathology Guidelines"],
                safety_status="VERIFIED_SAFE",
                trace_id=active_trace,
                weather_freshness=weather_freshness
            )
            new_tasks.append(fruit_task)

        # -------------------------------------------------------------
        # 2. IRRIGATION DECISION ENGINE INTEGRATION
        # -------------------------------------------------------------
        rain_prob = state.weather_summary.get("rain_probability") or 0
        rain_mm = state.weather_summary.get("rainfall_mm") or 0.0
        soil_moisture = state.soil_moisture_percentage

        irrig_decision = IrrigationDecisionService.evaluate(
            soil_moisture_percent=soil_moisture,
            soil_type=state.soil_type or "black",
            crop_stage=current_stage,
            rain_probability=rain_prob,
            expected_rain_mm=rain_mm,
            water_source_available=True
        )

        if irrig_decision.action == "WAIT":
            irrig_task = FarmTask(
                task_id=f"task_{farm_id}_irrigation_{today_str}",
                farm_id=farm_id,
                crop=crop,
                task_type=TaskType.IRRIGATION,
                title="Postpone Irrigation: Rainfall Expected",
                description=f"Rainfall forecast is {rain_prob}% (~{rain_mm}mm). Delay watering to save pump electricity and prevent root rot.",
                priority=DecisionPriority.MEDIUM,
                status=TaskStatus.POSTPONED,
                due_at=today_str,
                crop_stage=current_stage,
                weather_dependency={"rain_probability": rain_prob, "expected_rain_mm": rain_mm},
                trigger="weather_precipitation_forecast",
                reason=irrig_decision.justification,
                evidence=f"Precipitation probability: {rain_prob}%, expected rain: {rain_mm}mm.",
                source_references=["IMD Forecast + IrrigationDecisionService"],
                safety_status="VERIFIED_SAFE",
                postponed_at=today_str,
                postponement_reason=f"Rain expected ({rain_prob}% probability). Re-evaluate in 48 hours.",
                old_due_time=today_str,
                new_due_time=(today_dt.date() + timedelta(days=2)).isoformat(),
                trace_id=active_trace,
                weather_freshness=weather_freshness
            )
            new_tasks.append(irrig_task)
        elif irrig_decision.action == "IRRIGATE":
            irrig_task = FarmTask(
                task_id=f"task_{farm_id}_irrigation_{today_str}",
                farm_id=farm_id,
                crop=crop,
                task_type=TaskType.IRRIGATION,
                title="Irrigate Field: Early Morning Session",
                description=f"Run irrigation for {irrig_decision.recommended_duration_hours} hours ({irrig_decision.water_volume_liters_per_acre:,.0f} L/acre).",
                priority=DecisionPriority.HIGH,
                status=TaskStatus.DUE,
                due_at=today_str,
                crop_stage=current_stage,
                weather_dependency={"max_rain_probability": 30},
                trigger="low_soil_moisture",
                reason=irrig_decision.justification,
                evidence=f"Soil moisture is {soil_moisture:.1f}% vs threshold 45.0% for {current_stage}.",
                source_references=["IrrigationDecisionService"],
                safety_status="VERIFIED_SAFE",
                trace_id=active_trace,
                weather_freshness=weather_freshness
            )
            new_tasks.append(irrig_task)

        # -------------------------------------------------------------
        # 3. CROP HEALTH & DIAGNOSTIC TASKS (INSPECTION-FIRST)
        # -------------------------------------------------------------
        observations = getattr(state, "active_crop_health_observations", [])
        if not observations and getattr(state, "observed_symptoms", None):
            observations = [{"symptom": state.observed_symptoms, "confidence": 0.50, "confirmed": False}]

        for obs in observations:
            obs_conf = obs.get("confidence", 0.50)
            is_confirmed = obs.get("confirmed", False)
            symptom_name = obs.get("symptom") or obs.get("disease") or "Suspected Leaf Anomaly"

            # Check Rice RESEARCH_ONLY guard
            if crop.lower() in ["rice", "paddy"]:
                rice_scout = FarmTask(
                    task_id=f"task_{farm_id}_rice_research_{today_str}",
                    farm_id=farm_id,
                    crop=crop,
                    task_type=TaskType.CROP_HEALTH_SCOUTING,
                    title=f"[RESEARCH ONLY] Record Rice Field Symptoms: {symptom_name}",
                    description="Rice vision and disease models are currently locked to RESEARCH_ONLY mode. Do not execute or prescribe chemical treatments to farmers.",
                    priority=DecisionPriority.INFORMATIONAL,
                    status=TaskStatus.PLANNED,
                    due_at=today_str,
                    crop_stage=current_stage,
                    trigger="rice_research_workflow",
                    reason="Rice models are in research stage and pending field validation. No farmer-facing chemical prescription allowed.",
                    evidence="BHOOMI Phase 5 Governance Policy.",
                    source_references=["BHOOMI Research Governance"],
                    safety_status="RESEARCH_ONLY",
                    trace_id=active_trace,
                    weather_freshness=weather_freshness
                )
                new_tasks.append(rice_scout)
                continue

            # Diagnostic confidence check:
            # If diagnostic confidence is LOW/uncertain, ALWAYS prefer inspection/confirm over chemical spray!
            if obs_conf < 0.80 or not is_confirmed:
                inspection_task_id = f"task_{farm_id}_inspect_symptom_{today_str}"
                inspect_task = FarmTask(
                    task_id=inspection_task_id,
                    farm_id=farm_id,
                    crop=crop,
                    task_type=TaskType.FIELD_INSPECTION,
                    title=f"Field Inspection: Verify {symptom_name}",
                    description="Diagnostic confidence is uncertain. Physically inspect 10 affected plants to verify symptoms before deciding on chemical intervention.",
                    priority=DecisionPriority.HIGH,
                    status=TaskStatus.DUE,
                    due_at=today_str,
                    crop_stage=current_stage,
                    trigger="uncertain_vision_observation",
                    reason="Low diagnostic confidence requires physical scouting confirmation to prevent inappropriate pesticide use.",
                    evidence=f"Preliminary detection confidence: {obs_conf:.2f} (below 0.80 threshold).",
                    source_references=["BHOOMI Responsible AI Protocol & ICAR Scouting SOP"],
                    safety_status="VERIFIED_SAFE",
                    trace_id=active_trace,
                    weather_freshness=weather_freshness
                )
                new_tasks.append(inspect_task)

                treatment_task = FarmTask(
                    task_id=f"task_{farm_id}_treatment_followup_{today_str}",
                    farm_id=farm_id,
                    crop=crop,
                    task_type=TaskType.SPRAYING,
                    title=f"Targeted Treatment Decision for {symptom_name}",
                    description="Execute cultural or organic control (e.g., neem oil 5ml/L or bio-agent) ONLY after field inspection confirms the active pathogen.",
                    priority=DecisionPriority.MEDIUM,
                    status=TaskStatus.PLANNED,
                    due_at=tomorrow_str,
                    crop_stage=current_stage,
                    dependencies=[inspection_task_id],
                    trigger="dependent_on_field_inspection",
                    reason="Prerequisite field inspection must be completed before initiating chemical or biological spray.",
                    evidence="Requires physical validation by farmer.",
                    source_references=["SafetyEngine Precedence Rule"],
                    safety_status="VERIFIED_SAFE",
                    trace_id=active_trace,
                    weather_freshness=weather_freshness
                )
                new_tasks.append(treatment_task)

        # -------------------------------------------------------------
        # 4. HARVEST & MARKET PREPARATION TASKS
        # -------------------------------------------------------------
        das = lifecycle.days_after_sowing or getattr(state, "days_after_sowing", 75)
        harvest_win = HarvestDecisionEngine.evaluate_harvest(
            crop_name=crop,
            days_after_sowing=das,
            expected_maturity_days=140,
            total_acres=state.total_acres,
            yield_per_acre=10.0,
            rain_in_forecast_days=3 if rain_prob > 40 else 8
        )

        if harvest_win.maturity_percentage >= 85:
            harvest_task = FarmTask(
                task_id=f"task_{farm_id}_harvest_prep_{today_str}",
                farm_id=farm_id,
                crop=crop,
                task_type=TaskType.HARVEST_PREPARATION,
                title=f"Harvest Preparation: Clean Crates & Labor Booking",
                description=f"Crop maturity has reached {harvest_win.maturity_percentage}%. {harvest_win.recommended_logistics}",
                priority=DecisionPriority.HIGH,
                status=TaskStatus.DUE,
                due_at=today_str,
                crop_stage="maturity",
                trigger="crop_maturity_threshold",
                reason=harvest_win.advisory,
                evidence=f"Maturity index: {harvest_win.maturity_percentage}%. Optimal window: {harvest_win.optimal_window_start}.",
                source_references=["HarvestDecisionEngine"],
                safety_status="VERIFIED_SAFE",
                trace_id=active_trace,
                weather_freshness=weather_freshness
            )
            new_tasks.append(harvest_task)

            market_task = FarmTask(
                task_id=f"task_{farm_id}_market_check_{today_str}",
                farm_id=farm_id,
                crop=crop,
                task_type=TaskType.MARKET_CHECK,
                title="Mandi Price Check: Guntur APMC Arrival Volume",
                description=f"Current modal realization is ₹{state.market_modal_price_per_quintal:,.0f}/Q. Compare regional arrivals before dispatching produce.",
                priority=DecisionPriority.MEDIUM,
                status=TaskStatus.PLANNED,
                due_at=tomorrow_str,
                trigger="pre_harvest_market_intelligence",
                reason="Tracking arrival spikes prevents distress selling at depressed farm-gate prices.",
                evidence=f"Market modal price: ₹{state.market_modal_price_per_quintal}/Q.",
                source_references=["AGMARKNET Portal"],
                safety_status="VERIFIED_SAFE",
                trace_id=active_trace,
                weather_freshness=freshness_map.get("market", "CURRENT")
            )
            new_tasks.append(market_task)

        # -------------------------------------------------------------
        # 5. SAFETYENGINE VERIFICATION ON ALL TASKS
        # -------------------------------------------------------------
        verified_tasks: List[FarmTask] = []
        for t in new_tasks:
            eval_result = SafetyEngine.evaluate(f"{t.title} {t.description or ''} {t.reason}")
            if eval_result.blocked_reasons:
                t.safety_status = "BLOCKED_UNSAFE"
                t.status = TaskStatus.CANCELLED
                t.reason = f"SafetyEngine blocked prohibited chemical: {', '.join(eval_result.blocked_reasons)}"
            elif t.crop.lower() in ["rice", "paddy"] or t.safety_status == "RESEARCH_ONLY":
                t.safety_status = "RESEARCH_ONLY"
                if "[RESEARCH ONLY]" not in t.title:
                    t.title = f"[RESEARCH ONLY] {t.title}"
                if t.task_type == TaskType.SPRAYING:
                    t.task_type = TaskType.CROP_HEALTH_SCOUTING
            else:
                t.safety_status = "VERIFIED_SAFE"
            verified_tasks.append(t)

        # -------------------------------------------------------------
        # 6. DEDUPLICATION WITH EXISTING TASKS
        # -------------------------------------------------------------
        existing_tasks = cls.get_tasks_for_farm(farm_id)
        deduplicated = cls.deduplicate_tasks(verified_tasks, existing_tasks)

        # Ensure active trace_id, weather_freshness and rice protections on returned tasks
        for t in deduplicated:
            if trace_id:
                t.trace_id = trace_id
            if weather_freshness:
                t.weather_freshness = weather_freshness
            if t.crop.lower() in ["rice", "paddy"]:
                t.safety_status = "RESEARCH_ONLY"
                if "[RESEARCH ONLY]" not in t.title:
                    t.title = f"[RESEARCH ONLY] {t.title}"
                if t.task_type == TaskType.SPRAYING:
                    t.task_type = TaskType.CROP_HEALTH_SCOUTING

        # Update in-memory registry
        cls._tasks_by_farm[farm_id] = deduplicated

        # Record created event in FarmMemoryV2
        for t in deduplicated:
            if t not in existing_tasks:
                FarmMemoryV2.add_memory(
                    farmer_id=farmer_id,
                    category="EVENT",
                    key=f"task_created_{t.task_id}",
                    value={
                        "task_id": t.task_id,
                        "crop": t.crop,
                        "task_type": t.task_type.value,
                        "priority": t.priority.value,
                        "status": t.status.value,
                        "due_at": t.due_at
                    },
                    source="TaskIntelligenceEngine"
                )

        return deduplicated

    @classmethod
    def deduplicate_tasks(cls, new_tasks: List[FarmTask], existing_tasks: List[FarmTask]) -> List[FarmTask]:
        """
        Deduplicates tasks based on (farm_id, crop, task_type, trigger, due_window).
        Preserves existing task status (COMPLETED, POSTPONED, etc.) instead of overwriting.
        """
        result = list(existing_tasks)
        existing_signatures = {}

        for t in existing_tasks:
            if t.status in [TaskStatus.CANCELLED, TaskStatus.EXPIRED]:
                continue
            sig = (t.farm_id, t.crop.lower(), t.task_type.value, t.trigger.lower(), t.due_at[:10])
            existing_signatures[sig] = t

        for new_t in new_tasks:
            sig = (new_t.farm_id, new_t.crop.lower(), new_t.task_type.value, new_t.trigger.lower(), new_t.due_at[:10])
            if sig in existing_signatures:
                existing_t = existing_signatures[sig]
                # A completed task must never resurface as pending or postponed
                if existing_t.status == TaskStatus.COMPLETED:
                    continue
                # If underlying conditions materially changed, update existing
                if new_t.status == TaskStatus.POSTPONED and existing_t.status != TaskStatus.POSTPONED:
                    existing_t.status = TaskStatus.POSTPONED
                    existing_t.postponed_at = new_t.postponed_at
                    existing_t.postponement_reason = new_t.postponement_reason
                    existing_t.old_due_time = new_t.old_due_time
                    existing_t.new_due_time = new_t.new_due_time
                existing_t.trace_id = new_t.trace_id
                existing_t.weather_freshness = new_t.weather_freshness
                existing_t.safety_status = new_t.safety_status
                existing_t.crop_stage = new_t.crop_stage
                existing_t.trigger = new_t.trigger
                existing_t.reason = new_t.reason
                existing_t.evidence = new_t.evidence
                existing_t.source_references = new_t.source_references
                continue
            result.append(new_t)
            existing_signatures[sig] = new_t

        return result

    @classmethod
    def can_execute(cls, task: FarmTask, all_tasks: List[FarmTask]) -> Tuple[bool, Optional[str]]:
        """
        Evaluates prerequisite dependencies for a task.
        A task cannot become DUE, IN_PROGRESS, or COMPLETED if prerequisite tasks are not COMPLETED.
        """
        if not task.dependencies:
            return True, None

        task_lookup = {t.task_id: t for t in all_tasks}
        for dep_id in task.dependencies:
            dep_task = task_lookup.get(dep_id)
            if not dep_task:
                return False, f"Prerequisite task '{dep_id}' is missing."
            if dep_task.status != TaskStatus.COMPLETED:
                return False, f"Prerequisite task '{dep_task.title}' (ID: {dep_id}) is not yet completed (current status: {dep_task.status.value})."

        return True, None

    @classmethod
    def complete_task(
        cls,
        task_id: str,
        farmer_id: str,
        farm_id: str = "farm_1",
        completion_source: str = "farmer_dialogue"
    ) -> FarmTask:
        """
        Marks a task as COMPLETED, records timestamps and audit trail in FarmMemoryV2.
        Enforces lifecycle transition guards.
        """
        tasks = cls.get_tasks_for_farm(farm_id)
        target = next((t for t in tasks if t.task_id == task_id), None)
        if not target:
            for f_tasks in cls._tasks_by_farm.values():
                target = next((t for t in f_tasks if t.task_id == task_id), None)
                if target:
                    tasks = f_tasks
                    break
        if not target:
            raise ValueError(f"Task with ID {task_id} not found.")

        if target.status in [TaskStatus.CANCELLED, TaskStatus.EXPIRED]:
            raise ValueError(f"Cannot complete task {task_id} with status {target.status.value}.")

        can_run, reason = cls.can_execute(target, tasks)
        if not can_run:
            raise ValueError(f"Cannot complete task: {reason}")

        now_str = datetime.now(timezone.utc).isoformat()
        target.status = TaskStatus.COMPLETED
        target.completion_status = "SUCCESS"
        target.completed_at = now_str
        target.completion_source = completion_source

        # Store in FarmMemoryV2
        FarmMemoryV2.add_memory(
            farmer_id=farmer_id,
            category="EVENT",
            key=f"task_completed_{task_id}",
            value={
                "task_id": target.task_id,
                "title": target.title,
                "crop": target.crop,
                "completed_at": now_str,
                "completion_source": completion_source
            },
            source=completion_source
        )

        return target

    @classmethod
    def postpone_task(
        cls,
        task_id: str,
        farmer_id: str,
        reason: str,
        days_to_postpone: int = 2,
        farm_id: str = "farm_1",
        weather_freshness: str = "CURRENT"
    ) -> FarmTask:
        """
        Postpones a task with explicit reason and preserved historical due time.
        """
        tasks = cls.get_tasks_for_farm(farm_id)
        target = next((t for t in tasks if t.task_id == task_id), None)
        if not target:
            for f_tasks in cls._tasks_by_farm.values():
                target = next((t for t in f_tasks if t.task_id == task_id), None)
                if target:
                    tasks = f_tasks
                    break
        if not target:
            raise ValueError(f"Task with ID {task_id} not found.")

        if target.status in [TaskStatus.COMPLETED, TaskStatus.CANCELLED]:
            raise ValueError(f"Cannot postpone task {task_id} with status {target.status.value}.")

        now_str = datetime.now(timezone.utc).isoformat()
        target.old_due_time = target.due_at

        # Section 31: Relative postponement preserves existing task due-time, timezone offset, and rolls date
        handled = False
        if target.due_at:
            if "T" in target.due_at:
                try:
                    parsed_dt = datetime.fromisoformat(target.due_at)
                    new_due_dt = parsed_dt + timedelta(days=days_to_postpone)
                    target.new_due_time = new_due_dt.isoformat()
                    target.due_at = new_due_dt.isoformat()
                    handled = True
                except Exception:
                    pass
            else:
                try:
                    parsed_d = date.fromisoformat(target.due_at)
                    new_due_d = parsed_d + timedelta(days=days_to_postpone)
                    target.new_due_time = new_due_d.isoformat()
                    target.due_at = new_due_d.isoformat()
                    handled = True
                except Exception:
                    pass

        if not handled:
            base_date = datetime.now(timezone.utc).date()
            new_due_date = base_date + timedelta(days=days_to_postpone)
            target.new_due_time = new_due_date.isoformat()
            target.due_at = new_due_date.isoformat()

        target.status = TaskStatus.POSTPONED
        target.postponed_at = now_str
        target.postponement_reason = reason
        target.weather_freshness = weather_freshness

        FarmMemoryV2.add_memory(
            farmer_id=farmer_id,
            category="EVENT",
            key=f"task_postponed_{task_id}",
            value={
                "task_id": target.task_id,
                "title": target.title,
                "reason": reason,
                "old_due_time": target.old_due_time,
                "new_due_time": target.new_due_time,
                "weather_freshness": weather_freshness
            },
            source="farmer_dialogue"
        )

        return target

    @classmethod
    def skip_task(
        cls,
        task_id: str,
        farmer_id: str,
        reason: str = "Farmer opted to skip",
        farm_id: str = "farm_1"
    ) -> FarmTask:
        """
        Marks a task as SKIPPED.
        """
        tasks = cls.get_tasks_for_farm(farm_id)
        target = next((t for t in tasks if t.task_id == task_id), None)
        if not target:
            for f_tasks in cls._tasks_by_farm.values():
                target = next((t for t in f_tasks if t.task_id == task_id), None)
                if target:
                    tasks = f_tasks
                    break
        if not target:
            raise ValueError(f"Task with ID {task_id} not found.")

        if target.status in [TaskStatus.COMPLETED, TaskStatus.CANCELLED]:
            raise ValueError(f"Cannot skip task {task_id} with status {target.status.value}.")

        now_str = datetime.now(timezone.utc).isoformat()
        target.status = TaskStatus.SKIPPED
        target.postponement_reason = reason

        FarmMemoryV2.add_memory(
            farmer_id=farmer_id,
            category="EVENT",
            key=f"task_skipped_{task_id}",
            value={
                "task_id": target.task_id,
                "title": target.title,
                "reason": reason,
                "skipped_at": now_str
            },
            source="farmer_dialogue"
        )

        return target

    @classmethod
    def dynamic_replan(cls, state: FarmState, farm_id: str = "farm_1") -> List[FarmTask]:
        """
        Dynamically replans all tasks when weather, crop stage, or farm conditions change.
        E.g. If weather shifts to rain, irrigation and spraying tasks are automatically postponed.
        """
        existing_tasks = cls.get_tasks_for_farm(farm_id)
        rain_prob = state.weather_summary.get("rain_probability") or 0
        rain_mm = state.weather_summary.get("rainfall_mm") or 0.0

        for t in existing_tasks:
            if t.status in [TaskStatus.COMPLETED, TaskStatus.CANCELLED, TaskStatus.SKIPPED]:
                continue

            # 1. Weather shifted to rain
            if rain_prob >= 40 or rain_mm >= 12.0:
                if t.task_type == TaskType.IRRIGATION and t.status != TaskStatus.POSTPONED:
                    t.status = TaskStatus.POSTPONED
                    t.old_due_time = t.due_at
                    t.new_due_time = (datetime.now(timezone.utc).date() + timedelta(days=2)).isoformat()
                    t.postponed_at = datetime.now(timezone.utc).isoformat()
                    t.postponement_reason = f"Rain expected ({rain_prob}% chance, ~{rain_mm}mm). Irrigation postponed to save power."
                elif t.task_type in [TaskType.SPRAYING, TaskType.FERTILIZATION] and rain_prob >= 50 and t.status != TaskStatus.POSTPONED:
                    t.status = TaskStatus.POSTPONED
                    t.old_due_time = t.due_at
                    t.new_due_time = (datetime.now(timezone.utc).date() + timedelta(days=1)).isoformat()
                    t.postponed_at = datetime.now(timezone.utc).isoformat()
                    t.postponement_reason = f"High rain probability ({rain_prob}%). Spraying postponed to avoid wash-off."

            # 2. Dependency resolution: If prerequisites finished, transition from PLANNED to DUE
            if t.status == TaskStatus.PLANNED and t.dependencies:
                can_run, _ = cls.can_execute(t, existing_tasks)
                if can_run:
                    t.status = TaskStatus.DUE

        return existing_tasks
