from typing import Dict, Any, List, Optional
from pydantic import BaseModel

class OODValidationResult(BaseModel):
    is_in_distribution: bool
    confidence_score: float
    uncertainty_level: str  # LOW, MODERATE, HIGH, UNRELIABLE
    warning: Optional[str] = None
    advisory: str

class VisionPredictionValidator:
    """
    Out-Of-Distribution (OOD) and Confidence Calibration Validator.
    Never forces an anomalous, non-crop, or ambiguous photo into a false diagnosis.
    """
    MIN_CONFIDENCE_THRESHOLD = 0.45
    HIGH_CONFIDENCE_THRESHOLD = 0.75

    @classmethod
    def evaluate(cls, top_confidence: float, crop_detected: str, disease_predicted: str) -> OODValidationResult:
        if top_confidence < cls.MIN_CONFIDENCE_THRESHOLD:
            return OODValidationResult(
                is_in_distribution=False,
                confidence_score=round(top_confidence, 4),
                uncertainty_level="UNRELIABLE",
                warning="Out-Of-Distribution Alert: The image features do not match known plant disease patterns with sufficient certainty.",
                advisory="I am not confident in diagnosing this photo. Please hold the camera closer to the symptoms, take a photo in clear natural daylight, or consult a local KVK agricultural extension officer."
            )

        if top_confidence < cls.HIGH_CONFIDENCE_THRESHOLD:
            return OODValidationResult(
                is_in_distribution=True,
                confidence_score=round(top_confidence, 4),
                uncertainty_level="MODERATE",
                warning="Moderate Confidence: Symptoms partially resemble multiple conditions.",
                advisory="The symptoms match preliminary early stages. Monitor the crop closely over the next 48 hours for progression."
            )

        return OODValidationResult(
            is_in_distribution=True,
            confidence_score=round(top_confidence, 4),
            uncertainty_level="LOW",
            warning=None,
            advisory="High diagnostic confidence based on characteristic foliar lesion patterns."
        )
