import os
import pytest
import io
from decimal import Decimal
from PIL import Image
import pandas as pd

from app.data.validator import DatasetValidator
from app.data.profiler import DatasetProfiler
from app.services.crop.recommendation_service import CropRecommendationService, CropRecommendationInput
from app.services.yield_prediction.yield_service import YieldPredictionService, YieldPredictionInput
from app.services.crop.fertilizer_service import FertilizerRecommendationService, FertilizerInput
from app.services.crop.comparison_service import CropComparisonService
from app.services.vision.vision_service import VisionService
from app.services.vision.validator import VisionPredictionValidator
from app.services.rag.rag_service import AgriculturalRAGService, RAGQueryInput
from app.services.tasks.smart_reminder_engine import SmartReminderEngine
from app.agents.tool_registry import ToolRegistry

# 1. Dataset Validator Tests
def test_dataset_validator_crop_recommendation():
    df = pd.DataFrame([{
        "nitrogen": 90.0, "phosphorus": 42.0, "potassium": 43.0,
        "temperature": 25.0, "humidity": 80.0, "ph": 6.5, "rainfall": 200.0, "crop": "rice"
    }])
    val_res = DatasetValidator.validate_crop_recommendation(df)
    assert val_res.is_valid is True
    assert val_res.stats["crops_count"] == 1

def test_dataset_validator_impossible_negative_values():
    df_bad = pd.DataFrame([{
        "nitrogen": -10.0, "phosphorus": 42.0, "potassium": 43.0,
        "temperature": 25.0, "humidity": 80.0, "ph": 6.5, "rainfall": 200.0, "crop": "rice"
    }])
    val_res = DatasetValidator.validate_crop_recommendation(df_bad)
    assert val_res.is_valid is False
    assert any("negative" in i.message.lower() for i in val_res.issues)

# 2. Crop Recommendation ML Service Tests
def test_crop_recommendation_prediction():
    inp = CropRecommendationInput(
        nitrogen=90.0,
        phosphorus=42.0,
        potassium=43.0,
        temperature=24.5,
        humidity=82.0,
        ph=6.5,
        rainfall=202.0
    )
    out = CropRecommendationService.predict(inp, top_k=3)
    assert out.status == "success"
    assert len(out.recommended_crops) == 3
    assert out.recommended_crops[0].percentage > 0
    # Top recommendation under high rainfall and high N should be Rice
    assert out.recommended_crops[0].crop.lower() == "rice"

def test_crop_recommendation_soil_warnings():
    inp = CropRecommendationInput(
        nitrogen=30.0,
        phosphorus=20.0,
        potassium=20.0,
        temperature=28.0,
        humidity=60.0,
        ph=4.8,  # Acidic
        rainfall=300.0  # Low
    )
    out = CropRecommendationService.predict(inp, top_k=2)
    assert any("acidic" in w.lower() for w in out.warnings)
    assert any("low rainfall" in w.lower() for w in out.warnings)

# 3. Yield Prediction ML Regressor Tests
def test_yield_prediction_service():
    inp = YieldPredictionInput(
        crop_name="Chilli",
        state="Andhra Pradesh",
        season="Kharif",
        area_acres=3.0,
        annual_rainfall_mm=850.0
    )
    out = YieldPredictionService.predict(inp)
    assert out.status == "success"
    assert out.predicted_yield_quintals_per_acre > 0
    assert out.total_estimated_production_quintals == round(out.predicted_yield_quintals_per_acre * 3.0, 2)
    assert len(out.confidence_interval_quintals) == 2
    assert out.confidence_interval_quintals[0] < out.confidence_interval_quintals[1]

# 4. Fertilizer Recommendation & SafetyEngine Coupling Tests
def test_fertilizer_service_chilli_vegetative():
    inp = FertilizerInput(
        crop_name="Chilli",
        crop_stage="vegetative",
        soil_type="black",
        nitrogen=30.0,  # Deficient
        phosphorus=15.0, # Deficient
        potassium=35.0
    )
    out = FertilizerRecommendationService.recommend(inp)
    assert out.status == "success"
    assert "Urea" in out.recommended_fertilizer
    assert "Nitrogen" in out.nutrient_deficiency
    assert "ICAR" in out.evidence_source

def test_fertilizer_service_flowering_safety_warning():
    inp = FertilizerInput(
        crop_name="Chilli",
        crop_stage="flowering",
        soil_type="black",
        nitrogen=60.0,
        phosphorus=30.0,
        potassium=40.0
    )
    out = FertilizerRecommendationService.recommend(inp)
    assert out.status == "success"
    assert "19:19:19" in out.recommended_fertilizer or "Boron" in out.recommended_fertilizer

# 5. Computer Vision Diagnosis & OOD Tests
@pytest.mark.asyncio
async def test_vision_leaf_analysis_healthy():
    sample_path = os.path.join(
        "data", "organized", "vision", "chilli_diseases",
        "Chilli Plant Diseases Dataset(Augmented)", "Chilli Plant Diseases Dataset",
        "train", "Chilli___healthy", "1.jpg"
    )
    if os.path.exists(sample_path):
        with open(sample_path, "rb") as f:
            buf_bytes = f.read()
    else:
        from PIL import ImageDraw
        img = Image.new("RGB", (300, 300), color=(50, 180, 50))
        draw = ImageDraw.Draw(img)
        for i in range(0, 300, 8):
            draw.line([(i, 0), (i, 299)], fill=(65, 205, 65), width=2)
            draw.line([(0, i), (299, i)], fill=(35, 155, 35), width=2)
        buf = io.BytesIO()
        img.save(buf, format="JPEG")
        buf_bytes = buf.getvalue()

    out = await VisionService.analyze_leaf_image(buf_bytes, crop_hint="Chilli")
    assert out.crop_identified == "Chilli"
    assert out.success is True
    if os.path.exists(sample_path):
        assert "healthy" in out.disease_detected.lower()
    else:
        assert out.disease_detected is not None

@pytest.mark.asyncio
async def test_vision_quality_gate_rejection():
    # Blurry / tiny image
    tiny = Image.new("RGB", (50, 50), color=(100, 100, 100))
    buf = io.BytesIO()
    tiny.save(buf, format="JPEG")

    out = await VisionService.analyze_leaf_image(buf.getvalue())
    assert out.success is False
    assert out.requires_retake is True

# 6. Agricultural RAG Tests
def test_agricultural_rag_search():
    query = RAGQueryInput(query="chilli leaf curl whitefly management", crop="chilli")
    res = AgriculturalRAGService.search(query)
    assert res.evidence_found is True
    assert len(res.evidence_passages) > 0
    assert len(res.citations) > 0
    assert any("ICAR" in c.authority for c in res.citations)

# 7. Crop Comparison Service Tests
def test_crop_comparison_service():
    res = CropComparisonService.compare_crops(
        crop_names=["chilli", "cotton", "maize"],
        area_acres=Decimal("3.0"),
        soil_type="black",
        location="Guntur"
    )
    assert len(res.comparison) == 3
    assert res.recommended_crop != ""
    assert res.comparison[0].gross_revenue_per_acre > 0
    assert res.comparison[0].net_profit_total == res.comparison[0].net_profit_per_acre * Decimal("3.0")

# 8. Smart Reminder Condition Engine Tests
def test_smart_reminder_rain_trigger():
    res = SmartReminderEngine.evaluate_task_condition(
        task_id="t1",
        title="Apply Urea Fertilizer to Chilli Field",
        condition_str="If rain expected, delay",
        weather_data={"rain_probability": 0.65, "rainfall_mm": 20.0}
    )
    assert res.is_triggered is True
    assert res.adjustment_action == "DELAY"
    assert "Hold Chemical" in res.adjusted_message

def test_smart_reminder_market_peak_trigger():
    res = SmartReminderEngine.evaluate_task_condition(
        task_id="t2",
        title="Check Mandi Prices",
        condition_str="Alert if price exceeds 12000",
        market_data={"modal_price": 12400.0}
    )
    assert res.is_triggered is True
    assert res.adjustment_action == "EXPEDITE"
    assert "Market Peak Alert" in res.adjusted_message

# 9. ToolRegistry Execution of Phase 2 Tools
@pytest.mark.asyncio
async def test_tool_registry_phase2_tools():
    # Test crop_recommendation tool
    card1 = await ToolRegistry.execute_tool("crop_recommendation", {
        "nitrogen": 90, "phosphorus": 42, "potassium": 43, "ph": 6.5, "rainfall": 200
    })
    assert card1["card_type"] == "crop_recommendation_card"

    # Test yield_prediction tool
    card2 = await ToolRegistry.execute_tool("yield_prediction", {
        "crop_name": "Chilli", "area_acres": 3.0
    })
    assert card2["card_type"] == "yield_prediction_card"

    # Test fertilizer_recommendation tool
    card3 = await ToolRegistry.execute_tool("fertilizer_recommendation", {
        "crop_name": "Chilli", "nitrogen": 40, "phosphorus": 20, "potassium": 30
    })
    assert card3["card_type"] == "fertilizer_card"

    # Test compare_crops tool
    card4 = await ToolRegistry.execute_tool("compare_crops", {
        "crops": ["chilli", "cotton"], "area_acres": 3.0
    })
    assert card4["card_type"] == "comparison_card"
