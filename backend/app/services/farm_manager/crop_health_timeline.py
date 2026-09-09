from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

class FoliarObservation(BaseModel):
    observation_id: str
    farmer_id: str
    crop_name: str
    condition_detected: str
    is_healthy: bool
    confidence: float
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    applied_treatment: Optional[str] = None
    notes: Optional[str] = None

class TimelineStatus(BaseModel):
    crop_name: str
    total_observations: int
    health_trajectory: str  # IMPROVING, STABLE, WORSENING, UNCERTAIN
    latest_condition: str
    latest_confidence: float
    summary_advisory: str
    observations: List[FoliarObservation]

class CropHealthTimeline:
    """
    Crop Health Timeline.
    Tracks sequential leaf/plant observations over time to monitor disease regression,
    stability, or recovery post-treatment.
    """
    _records: Dict[str, List[FoliarObservation]] = {}

    @classmethod
    def record_observation(cls, observation: FoliarObservation) -> FoliarObservation:
        key = f"{observation.farmer_id}_{observation.crop_name.lower()}"
        if key not in cls._records:
            cls._records[key] = []
        cls._records[key].append(observation)
        return observation

    @classmethod
    def evaluate_trajectory(cls, farmer_id: str, crop_name: str = "Chilli") -> TimelineStatus:
        key = f"{farmer_id}_{crop_name.lower()}"
        obs_list = cls._records.get(key, [])

        if not obs_list:
            return TimelineStatus(
                crop_name=crop_name,
                total_observations=0,
                health_trajectory="UNCERTAIN",
                latest_condition="No observations recorded yet",
                latest_confidence=0.0,
                summary_advisory="Take your first plant photo using the leaf scanner to start the health timeline.",
                observations=[]
            )

        # Sort chronologically
        sorted_obs = sorted(obs_list, key=lambda x: x.timestamp)
        latest = sorted_obs[-1]

        if len(sorted_obs) == 1:
            trajectory = "STABLE"
            adv = f"Baseline established: {latest.condition_detected} ({latest.confidence * 100:.1f}% confidence). Take a follow-up photo in 5-7 days."
        else:
            prev = sorted_obs[-2]
            if not prev.is_healthy and latest.is_healthy:
                trajectory = "IMPROVING"
                adv = "Excellent progress: Foliar canopy shows robust recovery with healthy green vegetative growth."
            elif not prev.is_healthy and not latest.is_healthy and latest.condition_detected == prev.condition_detected:
                trajectory = "STABLE"
                adv = f"Condition persists as {latest.condition_detected}. Continue prescribed IPM protocol; check for new leaf flushes."
            elif prev.is_healthy and not latest.is_healthy:
                trajectory = "WORSENING"
                adv = f"New infection detected: {latest.condition_detected}. Immediate intervention recommended."
            else:
                trajectory = "STABLE"
                adv = "Foliage condition remains consistent."

        return TimelineStatus(
            crop_name=crop_name,
            total_observations=len(sorted_obs),
            health_trajectory=trajectory,
            latest_condition=latest.condition_detected,
            latest_confidence=latest.confidence,
            summary_advisory=adv,
            observations=sorted_obs
        )
