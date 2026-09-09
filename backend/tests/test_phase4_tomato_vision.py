import os
import io
import json
import pytest
from PIL import Image

from app.schemas.vision import VisionPrediction, VisionTopPrediction
from app.services.vision.tomato_model import (
    TomatoVisionModel,
    PLANTVILLAGE_TO_REGISTRY_KEY,
    PLANTVILLAGE_COMMON_NAMES
)
from app.services.vision.quality_gate import ImageQualityGate
from app.services.vision.validator import VisionPredictionValidator
from app.services.vision.registry import VisionModelRegistry
from app.services.vision.vision_service import VisionService, VisionAnalysisOutput
from app.services.safety.safety_engine import SafetyEngine
from app.services.rag.rag_service import AgriculturalRAGService, RAGQueryInput
from app.agents.tool_registry import ToolRegistry


def create_synthetic_leaf_bytes(color=(34, 139, 34), size=(256, 256), format="JPEG") -> bytes:
    """Helper to generate a clean synthetic leaf image with texture in memory."""
    from PIL import ImageDraw
    img = Image.new("RGB", size, color=color)
    if max(color) >= 20:
        draw = ImageDraw.Draw(img)
        for i in range(0, size[0], 8):
            draw.line([(i, 0), (i, size[1] - 1)], fill=(color[0] + 15, min(255, color[1] + 25), color[2] + 15), width=2)
            draw.line([(0, i), (size[0] - 1, i)], fill=(max(0, color[0] - 15), max(0, color[1] - 25), max(0, color[2] - 15)), width=2)
    buf = io.BytesIO()
    img.save(buf, format=format)
    return buf.getvalue()


# 1. Model Loading
def test_model_loading():
    model_service = TomatoVisionModel.get_instance()
    assert model_service is not None
    assert model_service.is_loaded is True
    assert model_service.model is not None


# 2. Label Mapping
def test_label_mapping():
    model_service = TomatoVisionModel.get_instance()
    assert len(model_service.labels) == 10
    assert 0 in model_service.labels
    for idx, name in model_service.labels.items():
        assert name.startswith("Tomato___")
        assert name in PLANTVILLAGE_TO_REGISTRY_KEY


# 3. Preprocessing Pipeline
def test_preprocessing_pipeline():
    model_service = TomatoVisionModel.get_instance()
    assert model_service.transform is not None

    raw_bytes = create_synthetic_leaf_bytes()
    img = Image.open(io.BytesIO(raw_bytes)).convert("RGB")
    tensor = model_service.transform(img)

    assert tensor.shape == (3, 224, 224)
    # Check normalization range
    assert tensor.mean().item() != 0.0


# 4. Valid Tomato Image Inference
def test_valid_tomato_inference():
    model_service = TomatoVisionModel.get_instance()
    leaf_bytes = create_synthetic_leaf_bytes(color=(40, 160, 40))

    pred: VisionPrediction = model_service.predict(leaf_bytes, top_k=3)
    assert pred.crop == "tomato"
    assert pred.disease in model_service.labels.values()
    assert pred.quality_status == "PASSED"
    assert pred.inference_time_ms > 0.0


# 5. Top-K Predictions
def test_top_k_predictions():
    model_service = TomatoVisionModel.get_instance()
    leaf_bytes = create_synthetic_leaf_bytes()

    pred: VisionPrediction = model_service.predict(leaf_bytes, top_k=5)
    assert len(pred.top_predictions) == 5
    # Confidences must be strictly decreasing
    confidences = [p.calibrated_confidence for p in pred.top_predictions]
    assert confidences == sorted(confidences, reverse=True)


# 6. Confidence Output & Calibration
def test_confidence_output_and_calibration():
    model_service = TomatoVisionModel.get_instance()
    assert model_service.temperature > 0.0

    leaf_bytes = create_synthetic_leaf_bytes()
    pred: VisionPrediction = model_service.predict(leaf_bytes)
    assert 0.0 <= pred.confidence <= 1.0
    assert 0.0 <= pred.calibrated_confidence <= 1.0


# 7. Low Confidence Handling
def test_low_confidence_handling():
    # An ambiguous noise/gray image
    gray_bytes = create_synthetic_leaf_bytes(color=(128, 128, 128))
    model_service = TomatoVisionModel.get_instance()
    pred: VisionPrediction = model_service.predict(gray_bytes)

    # Uncertainty validator should appropriately categorize
    assert pred.uncertainty_status in ["LOW", "MODERATE", "UNRELIABLE"]


# 8. Non-Tomato / OOD Handling
def test_non_tomato_ood_rejection():
    # If confidence is below threshold, validator flags OOD
    ood_res = VisionPredictionValidator.evaluate(
        top_confidence=0.35,
        crop_detected="tomato",
        disease_predicted="early_blight"
    )
    assert ood_res.is_in_distribution is False
    assert ood_res.uncertainty_level == "UNRELIABLE"
    assert "Out-Of-Distribution" in ood_res.warning


# 9. Corrupted Image Rejection
def test_corrupted_image_rejection():
    corrupted_bytes = b"NOT_A_VALID_IMAGE_BYTE_PAYLOAD_12345"
    gate_res = ImageQualityGate.validate(corrupted_bytes)
    assert gate_res.is_valid is False
    assert "Failed to decode" in gate_res.reason

    model_service = TomatoVisionModel.get_instance()
    pred = model_service.predict(corrupted_bytes)
    assert pred.quality_status == "FAILED"
    assert pred.is_reliable is False


# 10. Invalid MIME / Empty Image
def test_empty_or_invalid_mime():
    empty_bytes = b""
    gate_res = ImageQualityGate.validate(empty_bytes)
    assert gate_res.is_valid is False
    assert "Empty image" in gate_res.reason


# 11. Oversized Image Handling
def test_oversized_image_handling():
    # 16 MB payload
    huge_bytes = b"0" * (16 * 1024 * 1024)
    gate_res = ImageQualityGate.validate(huge_bytes)
    assert gate_res.is_valid is False
    assert "exceeds maximum allowed" in gate_res.reason


# 12. ImageQualityGate Blur & Underexposure
def test_quality_gate_darkness_blur():
    # Dark black image
    dark_bytes = create_synthetic_leaf_bytes(color=(5, 5, 5))
    gate_res = ImageQualityGate.validate(dark_bytes)
    assert gate_res.is_valid is False
    assert "too dark" in gate_res.reason.lower()


# 13. VisionPredictionValidator Integration
def test_vision_prediction_validator_integration():
    high_conf = VisionPredictionValidator.evaluate(0.92, "tomato", "early_blight")
    assert high_conf.is_in_distribution is True
    assert high_conf.uncertainty_level == "LOW"

    mod_conf = VisionPredictionValidator.evaluate(0.65, "tomato", "early_blight")
    assert mod_conf.is_in_distribution is True
    assert mod_conf.uncertainty_level == "MODERATE"


# 14. Agricultural RAG Integration
def test_rag_integration_for_tomato_disease():
    res = AgriculturalRAGService.search(
        RAGQueryInput(query="How to manage tomato early blight and target spot?", crop="tomato")
    )
    assert res.evidence_found is True
    assert len(res.citations) > 0
    passage_text = " ".join(res.evidence_passages).lower()
    assert "tomato" in passage_text or "blight" in passage_text


# 15. SafetyEngine Integration (Pesticide Guardrails)
def test_safety_engine_tomato_verification():
    # CIBRC compliant treatment
    safe_eval = SafetyEngine.evaluate(
        recommendation_text="Prune lower leaves and spray Mancozeb 75% WP @ 2.5g/L with PPE.",
        crop="tomato",
        stage="vegetative"
    )
    assert safe_eval.is_safe is True

    # Banned or hazardous chemical
    unsafe_eval = SafetyEngine.evaluate(
        recommendation_text="Spray Monocrotophos 36% SL on blooming tomatoes.",
        crop="tomato",
        stage="flowering"
    )
    assert unsafe_eval.is_safe is False
    assert len(unsafe_eval.blocked_reasons) > 0 or len(unsafe_eval.warnings) > 0


# 16. Agent / ToolRegistry Integration
@pytest.mark.asyncio
async def test_agent_tool_registry_diagnose_plant_disease():
    # Verify tool is registered in definitions
    tool_defs = ToolRegistry.get_tool_definitions()
    tool_names = [t["name"] for t in tool_defs]
    assert "diagnose_plant_disease" in tool_names

    # Execute tool with empty image (should reject via quality gate)
    res = await ToolRegistry.execute_tool("diagnose_plant_disease", {"crop_name": "tomato"})
    assert res["card_type"] == "leaf_diagnosis_card"
    assert res["data"]["success"] is False
    assert res["data"]["requires_retake"] is True


# 17. Multilingual Response Path
def test_multilingual_disease_neutrality():
    # Internal disease keys are language-neutral
    for k, v in PLANTVILLAGE_TO_REGISTRY_KEY.items():
        assert isinstance(k, str)
        assert isinstance(v, str)
        # Verify disease exists in registry
        info = VisionModelRegistry.get_disease_info("tomato", v)
        assert info is not None


# 18. Model Version Propagation
def test_model_version_propagation():
    model_service = TomatoVisionModel.get_instance()
    leaf_bytes = create_synthetic_leaf_bytes()
    pred = model_service.predict(leaf_bytes)
    assert pred.model_version == "tomato_vision_v1.0"


# 19. Full VisionService End-to-End Tomato Path
@pytest.mark.asyncio
async def test_full_vision_service_tomato_path():
    # Test with real tomato leaf if available
    sample_dir = "data/organized/vision/tomato_diseases/d1/tomato_dataset/train/Tomato___Early_blight"
    if os.path.exists(sample_dir) and os.listdir(sample_dir):
        sample_img_path = os.path.join(sample_dir, os.listdir(sample_dir)[0])
        with open(sample_img_path, "rb") as f:
            leaf_bytes = f.read()
        output: VisionAnalysisOutput = await VisionService.analyze_leaf_image(leaf_bytes, crop_hint="tomato")
        assert output.crop_identified == "Tomato"
        assert output.disease_detected.startswith("tomato_")
        assert output.confidence > 0.50
        assert output.ipm_recommendation != "None"
        assert output.chemical_treatment != "None"
    else:
        # Fallback to synthetic leaf
        leaf_bytes = create_synthetic_leaf_bytes(color=(34, 139, 34))
        output = await VisionService.analyze_leaf_image(leaf_bytes, crop_hint="tomato")
        assert output.crop_identified == "Tomato"
        assert output.uncertainty_level in ["LOW", "MODERATE", "UNRELIABLE"]


# 20. Deterministic Inference Schema
def test_deterministic_inference_schema():
    leaf_bytes = create_synthetic_leaf_bytes()
    model_service = TomatoVisionModel.get_instance()
    pred = model_service.predict(leaf_bytes)

    dumped = pred.model_dump()
    assert "crop" in dumped
    assert "disease" in dumped
    assert "confidence" in dumped
    assert "calibrated_confidence" in dumped
    assert "model_version" in dumped
    assert "top_predictions" in dumped
    assert "is_reliable" in dumped
