from typing import Dict, Any, Optional
from pydantic import BaseModel, Field
from app.schemas.voice_intent import TaskFeedback, FeedbackOutcome
from app.services.memory.farm_memory_v2 import FarmMemoryV2, ProvenanceType
from app.services.farm_manager.recommendation_trace import RecommendationTraceStore
from app.services.farm_manager.task_engine import TaskIntelligenceEngine


class AdherenceMetrics(BaseModel):
    farmer_id: str
    tasks_created: int = 0
    tasks_completed: int = 0
    tasks_postponed: int = 0
    tasks_skipped: int = 0
    overdue_tasks: int = 0
    adherence_rate: float = 0.0  # 0.0 to 1.0
    adherence_level: str = "INSUFFICIENT_DATA"  # HIGH (>=0.8), MODERATE (0.5-0.79), LOW (<0.5), INSUFFICIENT_DATA


class PersonalizationProfile(BaseModel):
    reminder_lead_hours: int = 4
    explanation_verbosity: str = "BALANCED"  # CONCISE, BALANCED, DETAILED
    nudge_frequency: str = "STANDARD"       # REDUCED, STANDARD, FREQUENT
    needs_water_availability_check: bool = False
    guidance_message: Optional[str] = None


class TaskAdherenceService:
    """
    Longitudinal Farm Task Adherence and Personalization Service.
    Calculates deterministic adherence from FarmMemoryV2 events.
    Personalizes reminder timing and explanation depth.
    GUARANTEE: Behavioral adherence NEVER overrides SafetyEngine or agronomic decision engines.
    """

    @classmethod
    def calculate_adherence(cls, farmer_id: str, farm_id: str = "farm_1") -> AdherenceMetrics:
        """
        Deterministically calculates task completion adherence.
        Safe against zero-denominator without generating fake 100% rates.
        """
        memories = FarmMemoryV2.get_memories_by_category(farmer_id, "EVENT")
        
        created_count = sum(1 for m in memories if m.key.startswith("task_created_"))
        completed_count = sum(1 for m in memories if m.key.startswith("task_completed_"))
        postponed_count = sum(1 for m in memories if m.key.startswith("task_postponed_"))
        skipped_count = sum(1 for m in memories if m.key.startswith("task_skipped_"))

        # Inspect current tasks for overdue items
        current_tasks = TaskIntelligenceEngine.get_tasks_for_farm(farm_id)
        overdue_count = sum(1 for t in current_tasks if t.is_overdue)

        # Eligible tasks = tasks that were either completed, skipped, or are currently overdue
        eligible = completed_count + skipped_count + overdue_count

        if eligible == 0:
            rate = 0.0
            level = "INSUFFICIENT_DATA"
        else:
            rate = round(completed_count / eligible, 2)
            if rate >= 0.80:
                level = "HIGH"
            elif rate >= 0.50:
                level = "MODERATE"
            else:
                level = "LOW"

        return AdherenceMetrics(
            farmer_id=farmer_id,
            tasks_created=created_count,
            tasks_completed=completed_count,
            tasks_postponed=postponed_count,
            tasks_skipped=skipped_count,
            overdue_tasks=overdue_count,
            adherence_rate=rate,
            adherence_level=level
        )

    @classmethod
    def get_personalization_profile(cls, farmer_id: str, farm_id: str = "farm_1") -> PersonalizationProfile:
        """
        Computes interaction personalization based on longitudinal task compliance.
        Only modifies presentation / timing; NEVER overrides agronomic decisions.
        """
        adherence = cls.calculate_adherence(farmer_id, farm_id)

        if adherence.adherence_level == "HIGH":
            # Highly compliant farmer: concise prompts, standard reminders
            return PersonalizationProfile(
                reminder_lead_hours=2,
                explanation_verbosity="CONCISE",
                nudge_frequency="STANDARD"
            )
        elif adherence.adherence_level == "LOW":
            # Low compliance or frequent postponements: explain risks in greater detail, advance reminder
            profile = PersonalizationProfile(
                reminder_lead_hours=6,
                explanation_verbosity="DETAILED",
                nudge_frequency="FREQUENT"
            )
            if adherence.tasks_postponed >= 2:
                profile.needs_water_availability_check = True
                profile.guidance_message = "Frequent postponement detected. Consider checking irrigation pump electrical supply or labor availability."
            return profile
        else:
            return PersonalizationProfile(
                reminder_lead_hours=4,
                explanation_verbosity="BALANCED",
                nudge_frequency="STANDARD"
            )

    @classmethod
    def record_feedback(cls, feedback: TaskFeedback) -> TaskFeedback:
        """
        Records farmer-reported feedback in FarmMemoryV2 and RecommendationTraceStore.
        Strictly tagged as FARMER_REPORTED_OUTCOME (never confused with VERIFIED_OUTCOME).
        """
        FarmMemoryV2.add_memory(
            farmer_id=feedback.farmer_id,
            category="FEEDBACK",
            key=f"task_feedback_{feedback.task_id}",
            value={
                "task_id": feedback.task_id,
                "rating": feedback.rating,
                "outcome": feedback.outcome.value,
                "comment": feedback.comment,
                "source": feedback.source,
                "created_at": feedback.created_at,
                "trace_id": feedback.trace_id
            },
            source=feedback.source,
            provenance=ProvenanceType.FARMER_REPORTED_OUTCOME
        )

        # Update trace store if active trace exists
        if feedback.trace_id:
            RecommendationTraceStore.update_feedback(
                recommendation_id=feedback.trace_id,
                farmer_action="COMPLETED",
                feedback_rating=feedback.outcome.value,
                feedback_notes=feedback.comment
            )

        return feedback
