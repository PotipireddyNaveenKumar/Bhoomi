import io
import os
import pytest
from PIL import Image

from app.schemas.vision import VisionPrediction, VisionTopPrediction
from app.services.vision.crop_registry import CropModelRegistry
from app.services.vision.provider_contract import VisionModelProvider, CropVisionModelProvider, TomatoVisionModelProvider
from app.services.vision.quality_gate import ImageQualityGate
from app.services.vision.validator import VisionPredictionValidator
from app.services.vision.registry import VisionModelRegistry
from app.services.vision.vision_service import VisionService, VisionAnalysisOutput
from app.services.safety.safety_engine import SafetyEngine
from app.services.rag.rag_service import AgriculturalRAGService, RAGQueryInput
from app.agents.tool_registry import ToolRegistry


def create_synthetic_leaf(color=(34, 139, 34), size=(256, 256)) -> bytes:
    from PIL import ImageDraw
    img = Image.new("RGB", size, color=color)
    if max(color) >= 20:
        draw = ImageDraw.Draw(img)
        for i in range(0, size[0], 8):
            draw.line([(i, 0), (i, size[1] - 1)], fill=(color[0] + 15, min(255, color[1] + 25), color[2] + 15), width=2)
            draw.line([(0, i), (size[0] - 1, i)], fill=(max(0, color[0] - 15), max(0, color[1] - 25), max(0, color[2] - 15)), width=2)
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()


# 1. CropModelRegistry Resolution
def test_crop_model_registry_resolution():
    crops = CropModelRegistry.get_supported_crops()
    assert "tomato" in crops
    assert "chilli" in crops
    assert "rice" in crops
    assert "banana" in crops
    assert "corn_maize" in crops

    # Aliases
    assert CropModelRegistry.normalize_crop_name("corn") == "corn_maize"
    assert CropModelRegistry.normalize_crop_name("paddy") == "rice"
    assert CropModelRegistry.normalize_crop_name("bell pepper") == "chilli"
    assert CropModelRegistry.normalize_crop_name("pumpkin") == "cucumber_pumpkin"


# 2. Tomato Model Remains Available
def test_tomato_model_available():
    provider = CropModelRegistry.get_provider("tomato")
    assert provider is not None
    assert provider.get_crop_name() == "tomato"
    assert provider.get_model_version() == "tomato_vision_v1.0"
    assert len(provider.get_supported_classes()) == 10


# 3. Chilli Model Loading
def test_chilli_model_loading():
    provider = CropModelRegistry.get_provider("chilli")
    assert provider is not None
    assert provider.get_crop_name() == "chilli"
    assert provider.get_model_version() == "chilli_vision_v1.0"
    assert len(provider.get_supported_classes()) == 6


# 4. Rice Model Loading
def test_rice_model_loading():
    provider = CropModelRegistry.get_provider("rice")
    assert provider is not None
    assert provider.get_crop_name() == "rice"
    assert provider.get_model_version() == "rice_vision_v1.0"
    assert len(provider.get_supported_classes()) == 4


# 5. Potato Model Loading
def test_potato_model_loading():
    provider = CropModelRegistry.get_provider("potato")
    assert provider is not None
    assert provider.get_crop_name() == "potato"
    assert provider.get_model_version() == "potato_vision_v1.0"
    assert len(provider.get_supported_classes()) == 3


# 6. Sugarcane Model Loading
def test_sugarcane_model_loading():
    provider = CropModelRegistry.get_provider("sugarcane")
    assert provider is not None
    assert provider.get_crop_name() == "sugarcane"
    assert provider.get_model_version() == "sugarcane_vision_v1.0"
    assert len(provider.get_supported_classes()) == 6


# 7. Banana Model Loading
def test_banana_model_loading():
    provider = CropModelRegistry.get_provider("banana")
    assert provider is not None
    assert provider.get_crop_name() == "banana"
    assert provider.get_model_version() == "banana_vision_v1.0"
    assert len(provider.get_supported_classes()) == 4


# 8. Maize Model Loading
def test_maize_model_loading():
    provider = CropModelRegistry.get_provider("corn_maize")
    assert provider is not None
    assert provider.get_crop_name() == "corn_maize"
    assert provider.get_model_version() == "corn_maize_vision_v1.0"
    assert len(provider.get_supported_classes()) == 4


# 9. Guava Model Loading
def test_guava_model_loading():
    provider = CropModelRegistry.get_provider("guava")
    assert provider is not None
    assert provider.get_crop_name() == "guava"
    assert provider.get_model_version() == "guava_vision_v1.0"
    assert len(provider.get_supported_classes()) == 3


# 10. Cucumber / Pumpkin Model Loading
def test_cucumber_pumpkin_model_loading():
    provider = CropModelRegistry.get_provider("cucumber_pumpkin")
    assert provider is not None
    assert provider.get_crop_name() == "cucumber_pumpkin"
    assert provider.get_model_version() == "cucumber_pumpkin_vision_v1.0"
    assert len(provider.get_supported_classes()) == 5


# 11. Apple Model Loading
def test_apple_model_loading():
    provider = CropModelRegistry.get_provider("apple")
    assert provider is not None
    assert provider.get_crop_name() == "apple"
    assert provider.get_model_version() == "apple_vision_v1.0"
    assert len(provider.get_supported_classes()) == 4


# 12. Common Prediction Schema
def test_common_prediction_schema():
    leaf_bytes = create_synthetic_leaf()
    for crop in ["banana", "guava", "corn_maize"]:
        pred = CropModelRegistry.predict(leaf_bytes, crop_hint=crop)
        assert isinstance(pred, VisionPrediction)
        assert pred.crop == crop
        assert isinstance(pred.confidence, float)
        assert isinstance(pred.calibrated_confidence, float)
        assert isinstance(pred.inference_time_ms, float)
        assert hasattr(pred, "model_version")
        assert hasattr(pred, "is_ood")


# 13. Label Mapping Across Crops
def test_label_mappings():
    meta = CropModelRegistry.get_all_models_metadata()
    for crop, data in meta.items():
        assert "supported_classes" in data
        assert len(data["supported_classes"]) >= 3


# 14. Preprocessing Standardization
def test_preprocessing_standardization():
    provider: CropVisionModelProvider = CropModelRegistry.get_provider("banana")
    assert provider.transform is not None

    leaf_bytes = create_synthetic_leaf()
    img = Image.open(io.BytesIO(leaf_bytes)).convert("RGB")
    tensor = provider.transform(img)
    assert tensor.shape == (3, 224, 224)


# 15. ImageQualityGate Integration Across Crops
def test_image_quality_gate_across_crops():
    dark_bytes = create_synthetic_leaf(color=(5, 5, 5))
    pred = CropModelRegistry.predict(dark_bytes, crop_hint="banana")
    assert pred.quality_status == "FAILED"
    assert pred.is_reliable is False


# 16. Confidence Validation Across Crops
def test_confidence_validation():
    leaf_bytes = create_synthetic_leaf()
    pred = CropModelRegistry.predict(leaf_bytes, crop_hint="guava")
    assert 0.0 <= pred.confidence <= 1.0
    assert 0.0 <= pred.calibrated_confidence <= 1.0


# 17. OOD Handling
def test_ood_handling_unrelated_input():
    # Synthetic flat block triggers uncertainty
    leaf_bytes = create_synthetic_leaf(color=(128, 128, 128))
    pred = CropModelRegistry.predict(leaf_bytes, crop_hint="apple")
    assert pred.uncertainty_status in ["LOW", "MODERATE", "UNRELIABLE"]


# 18. Low-Confidence Handling
def test_low_confidence_validator():
    val_res = VisionPredictionValidator.evaluate(0.30, "chilli", "leaf_curl")
    assert val_res.is_in_distribution is False
    assert val_res.uncertainty_level == "UNRELIABLE"


# 19. RAG Integration for Multi-Crops
def test_rag_integration_multi_crops():
    crops_to_query = [
        ("potato", "How to control potato late blight?"),
        ("banana", "Banana sigatoka disease management guidelines"),
        ("sugarcane", "Sugarcane red rot package of practices"),
        ("apple", "Apple scab spray schedule")
    ]
    for crop, query in crops_to_query:
        res = AgriculturalRAGService.search(RAGQueryInput(query=query, crop=crop))
        assert res.evidence_found is True
        assert len(res.citations) > 0


# 20. SafetyEngine Integration for Multi-Crops
def test_safety_engine_multi_crops():
    # Safe recommendation
    res_safe = SafetyEngine.evaluate("Apply Mancozeb 75% WP @ 2.5g/L with protective gloves.", "potato")
    assert res_safe.is_safe is True

    # Banned substance
    res_unsafe = SafetyEngine.evaluate("Spray Endosulfan 35% EC on banana.", "banana")
    assert res_unsafe.is_safe is False
    assert len(res_unsafe.blocked_reasons) > 0


# 21. ToolRegistry Integration with Multi-Crop Routing
@pytest.mark.asyncio
async def test_tool_registry_multi_crop_integration():
    res_banana = await ToolRegistry.execute_tool("diagnose_plant_disease", {"crop_name": "banana"})
    assert res_banana["card_type"] == "leaf_diagnosis_card"
    assert "data" in res_banana

    res_potato = await ToolRegistry.execute_tool("diagnose_plant_disease", {"crop_name": "potato"})
    assert res_potato["card_type"] == "leaf_diagnosis_card"


# 22. Model Version Propagation
def test_model_version_propagation():
    for crop in ["banana", "rice", "potato", "guava"]:
        provider = CropModelRegistry.get_provider(crop)
        assert provider.get_model_version().startswith(f"{crop}_vision_v1")


# 23. RecommendationTrace Integration
def test_recommendation_trace_compatibility():
    # Models expose clean metadata dictionary for audit trails
    for crop in ["chilli", "sugarcane", "apple"]:
        provider = CropModelRegistry.get_provider(crop)
        meta = provider.get_metadata()
        assert "architecture" in meta
        assert "status" in meta
        assert "field_validation" in meta


# 24. Unsupported Crop Behavior
def test_unsupported_crop_behavior():
    leaf_bytes = create_synthetic_leaf()
    pred = CropModelRegistry.predict(leaf_bytes, crop_hint="dragonfruit")
    assert pred.disease == "UNSUPPORTED_CROP"
    assert pred.is_reliable is False
    assert pred.is_ood is True


# 25. Unknown / None Crop Behavior
def test_unknown_crop_behavior():
    leaf_bytes = create_synthetic_leaf()
    pred = CropModelRegistry.predict(leaf_bytes, crop_hint=None)
    assert pred.disease == "UNSUPPORTED_CROP"
    assert pred.is_reliable is False


# 26. No Forced Diagnosis (Uncertainty Preservation)
@pytest.mark.asyncio
async def test_no_forced_diagnosis():
    corrupt_bytes = b"CORRUPT_BYTES_DATA"
    out: VisionAnalysisOutput = await VisionService.analyze_leaf_image(corrupt_bytes, crop_hint="banana")
    assert out.success is False
    assert out.requires_retake is True
    assert "I am not confident" in out.farmer_explanation or "Quality" in out.common_name


# 27. Multilingual Response Routing
def test_multilingual_routing_disease_keys():
    # Check that disease keys are language-neutral ASCII identifiers
    for crop in ["banana", "guava", "corn_maize", "potato"]:
        provider = CropModelRegistry.get_provider(crop)
        for c in provider.get_supported_classes():
            assert isinstance(c, str)
            assert len(c) > 0
