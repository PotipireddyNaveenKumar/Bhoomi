import logging
from typing import Dict, Any, List, Optional

from app.services.vision.provider_contract import (
    VisionModelProvider,
    CropVisionModelProvider,
    TomatoVisionModelProvider
)
from app.schemas.vision import VisionPrediction

logger = logging.getLogger(__name__)

CROP_ALIASES = {
    "tomato": "tomato",
    "tomatoes": "tomato",
    "chilli": "chilli",
    "chili": "chilli",
    "pepper": "chilli",
    "bell pepper": "chilli",
    "rice": "rice",
    "paddy": "rice",
    "potato": "potato",
    "potatoes": "potato",
    "sugarcane": "sugarcane",
    "banana": "banana",
    "corn": "corn_maize",
    "maize": "corn_maize",
    "corn_maize": "corn_maize",
    "guava": "guava",
    "cucumber": "cucumber_pumpkin",
    "pumpkin": "cucumber_pumpkin",
    "cucumber_pumpkin": "cucumber_pumpkin",
    "apple": "apple",
    "apples": "apple"
}

class CropModelRegistry:
    """
    Centralized Registry for all Deep-Learning Crop Pathology Vision Models.
    Ensures safe crop model routing, uniform metadata inspection, and
    structured fallback when unsupported crops are queried.
    """
    _providers: Dict[str, VisionModelProvider] = {}
    _initialized: bool = False

    @classmethod
    def _initialize(cls):
        if cls._initialized:
            return

        # 1. Reference Tomato Model
        try:
            cls._providers["tomato"] = TomatoVisionModelProvider()
        except Exception as e:
            logger.warning("TomatoVisionModelProvider initialization failed: %s", str(e))
            cls._providers["tomato"] = CropVisionModelProvider("tomato")

        # 2. Multi-Crop Vision Providers
        crops = [
            "chilli",
            "rice",
            "potato",
            "sugarcane",
            "banana",
            "corn_maize",
            "guava",
            "cucumber_pumpkin",
            "apple"
        ]

        for crop in crops:
            try:
                cls._providers[crop] = CropVisionModelProvider(crop)
            except Exception as e:
                logger.error("Failed to register CropVisionModelProvider for %s: %s", crop, str(e))

        cls._initialized = True

    @classmethod
    def normalize_crop_name(cls, raw_crop: Optional[str]) -> Optional[str]:
        if not raw_crop:
            return None
        cleaned = raw_crop.lower().strip().replace("-", "_").replace(" ", "_")
        return CROP_ALIASES.get(cleaned, CROP_ALIASES.get(raw_crop.lower().strip()))

    @classmethod
    def get_supported_crops(cls) -> List[str]:
        cls._initialize()
        return list(cls._providers.keys())

    @classmethod
    def get_provider(cls, crop_name: str) -> Optional[VisionModelProvider]:
        cls._initialize()
        canonical = cls.normalize_crop_name(crop_name)
        if canonical and canonical in cls._providers:
            return cls._providers[canonical]
        return None

    @classmethod
    def get_all_models_metadata(cls) -> Dict[str, Any]:
        cls._initialize()
        summary = {}
        for crop, provider in cls._providers.items():
            summary[crop] = {
                "crop": crop,
                "model_version": provider.get_model_version(),
                "supported_classes": provider.get_supported_classes(),
                "metadata": provider.get_metadata()
            }
        return summary

    @classmethod
    def predict(
        cls,
        image_bytes: bytes,
        crop_hint: Optional[str] = None,
        top_k: int = 3
    ) -> VisionPrediction:
        """
        Safe routing dispatcher:
        If crop_hint is provided, queries the dedicated crop vision model.
        If crop is unknown or unsupported, safely returns an unforced diagnosis advisory.
        """
        cls._initialize()
        canonical = cls.normalize_crop_name(crop_hint)

        if not canonical or canonical not in cls._providers:
            return VisionPrediction(
                crop=crop_hint or "Unknown",
                disease="UNSUPPORTED_CROP",
                common_name="Crop Not Specified / Unsupported",
                confidence=0.0,
                calibrated_confidence=0.0,
                model_version="none",
                top_predictions=[],
                quality_status="PASSED",
                uncertainty_status="UNRELIABLE",
                is_ood=True,
                inference_time_ms=0.0,
                quality_metrics={},
                is_reliable=False
            )

        provider = cls._providers[canonical]
        return provider.predict(image_bytes=image_bytes, top_k=top_k)

    @classmethod
    def identify_best_candidate(
        cls,
        image_bytes: bytes,
        top_k: int = 3
    ) -> Optional[tuple]:
        """
        Runs multi-crop vision evaluation across all 10 registered crop providers.
        Returns (crop_name, best_prediction) sorted by calibrated confidence.
        Enforces:
        - Confidence threshold: top candidate must have calibrated_confidence >= 0.60
        - Model disagreement handling: if runner-up candidate is within 0.10 margin and top < 0.82, rejects as ambiguous cross-crop conflict
        - Crop vs disease confidence separation
        """
        cls._initialize()
        candidates = []
        for c_name, provider in cls._providers.items():
            try:
                p = provider.predict(image_bytes=image_bytes, top_k=top_k)
                if p.quality_status != "FAILED" and p.is_reliable and not p.is_ood:
                    candidates.append((c_name, p))
            except Exception as e:
                logger.debug("Provider %s failed during candidate scan: %s", c_name, e)
                continue

        if not candidates:
            return None

        candidates.sort(key=lambda x: x[1].calibrated_confidence, reverse=True)
        top_crop, top_pred = candidates[0]

        # 1. Minimum confidence threshold for unhinted crop detection
        if top_pred.calibrated_confidence < 0.60:
            logger.info("Multi-crop candidate %s rejected: confidence %.2f below threshold", top_crop, top_pred.calibrated_confidence)
            return None

        # 2. Model disagreement and multi-model conflict handling
        second_conf = 0.0
        if len(candidates) > 1:
            second_crop, second_pred = candidates[1]
            second_conf = second_pred.calibrated_confidence
            margin = top_pred.calibrated_confidence - second_conf
            high_conf_count = sum(1 for c, p in candidates if p.calibrated_confidence >= 0.70)
            if margin < 0.10 and (top_pred.calibrated_confidence < 0.90 or high_conf_count >= 3):
                logger.info(
                    "Crop candidate rejected due to model disagreement / ambiguity: top=%s (%.2f), runner_up=%s (%.2f), margin=%.2f, high_conf_count=%d",
                    top_crop, top_pred.calibrated_confidence, second_crop, second_conf, margin, high_conf_count
                )
                return None

        # 3. Calculate distinct crop_confidence vs disease_confidence
        crop_conf = round(top_pred.calibrated_confidence * (1.0 - second_conf / 2.0), 4) if second_conf else round(top_pred.calibrated_confidence, 4)
        top_pred.crop_confidence = crop_conf
        top_pred.disease_confidence = round(top_pred.calibrated_confidence, 4)

        # 4. Reject candidate if separated crop_confidence is below threshold (< 0.65)
        if crop_conf < 0.65:
            logger.info("Multi-crop candidate %s rejected: crop_confidence %.2f below 0.65 threshold", top_crop, crop_conf)
            return None

        return (top_crop, top_pred)

