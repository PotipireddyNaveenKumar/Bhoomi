import os
import joblib
import pandas as pd
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from app.services.safety.safety_engine import SafetyEngine

class FertilizerInput(BaseModel):
    crop_name: str = Field(..., example="Chilli", description="Crop being cultivated")
    crop_stage: str = Field(default="vegetative", example="vegetative", description="Current stage: vegetative, flowering, fruit_development")
    soil_type: str = Field(default="black", example="black", description="Soil type: black, red, alluvial, sandy, clay, loamy")
    nitrogen: float = Field(..., ge=0, example=40.0, description="Available Nitrogen in soil (kg/ha index)")
    phosphorus: float = Field(..., ge=0, example=20.0, description="Available Phosphorus in soil (kg/ha index)")
    potassium: float = Field(..., ge=0, example=30.0, description="Available Potassium in soil (kg/ha index)")
    temperature: float = Field(default=28.0, ge=0, le=55)
    humidity: float = Field(default=70.0, ge=0, le=100)
    moisture: float = Field(default=45.0, ge=0, le=100)

class FertilizerRecommendationOutput(BaseModel):
    status: str
    crop: str
    crop_stage: str
    nutrient_deficiency: str
    recommended_fertilizer: str
    recommended_dosage_per_acre: str
    application_method: str
    timing_guidance: str
    safety_advisory: str
    evidence_source: str
    confidence_level: str
    uncertainty_notes: Optional[str] = None
    follow_up_questions: List[str] = []

class FertilizerRecommendationService:
    # Authoritative ICAR / State Agricultural University (SAU) Package of Practices
    # Evidence-grounded dosage and nutrient tables
    AGRONOMIC_DOSAGE_TABLE = {
        "chilli": {
            "vegetative": {
                "fertilizer": "Urea + MOP (Muriate of Potash)",
                "dosage_per_acre": "25 kg Urea (46% N) + 15 kg MOP (60% K2O)",
                "method": "Side placement 5-7 cm away from the plant stem followed by light irrigation",
                "timing": "30-40 days after transplanting (First Top Dressing)",
                "source": "ICAR - Indian Institute of Horticultural Research (IIHR) Package of Practices"
            },
            "flowering": {
                "fertilizer": "19:19:19 (Water Soluble NPK) + Boron (20%)",
                "dosage_per_acre": "1.0 kg 19:19:19 + 250 g Boron in 200 L water",
                "method": "Foliar spray during clear sky morning hours (8 AM - 10 AM)",
                "timing": "At 10% flower emergence to prevent flower drop and improve fruit set",
                "source": "ANGRAU Chilli Agronomy Guidelines"
            },
            "fruit_development": {
                "fertilizer": "0:0:50 (Potassium Sulphate) + Calcium Nitrate",
                "dosage_per_acre": "1.5 kg 0:0:50 + 1.0 kg Calcium Nitrate in 200 L water",
                "method": "Foliar application or Fertigation drip line",
                "timing": "Fruit enlargement stage for pungent, thick-walled pod development",
                "source": "TNAU Agritech Portal"
            }
        },
        "rice": {
            "vegetative": {
                "fertilizer": "Urea + Zinc Sulphate (21%)",
                "dosage_per_acre": "30 kg Urea + 10 kg Zinc Sulphate (soil application)",
                "method": "Broadcast into saturated field with standing water < 2cm",
                "timing": "Active tillering stage (20-25 days after transplanting)",
                "source": "ICAR - National Rice Research Institute (NRRI)"
            },
            "flowering": {
                "fertilizer": "Muriate of Potash (MOP)",
                "dosage_per_acre": "15 kg MOP per acre",
                "method": "Top dressing before panicle initiation",
                "timing": "Panicle initiation stage",
                "source": "PJTSAU Rice Package of Practices"
            }
        },
        "cotton": {
            "vegetative": {
                "fertilizer": "Urea + DAP (Di-Ammonium Phosphate)",
                "dosage_per_acre": "35 kg Urea + 25 kg DAP",
                "method": "Ring placement around root zone",
                "timing": "Square formation stage (45-50 DAS)",
                "source": "ICAR - Central Institute for Cotton Research (CICR)"
            },
            "flowering": {
                "fertilizer": "13:0:45 (Potassium Nitrate) + Magnesium Sulphate",
                "dosage_per_acre": "1.5 kg 13:0:45 + 1.0 kg MgSO4 in 200 L water",
                "method": "Foliar spray to prevent square/boll drop",
                "timing": "Peak boll development stage",
                "source": "CICR Cotton Advisory"
            }
        }
    }

    @classmethod
    def recommend(cls, input_data: FertilizerInput) -> FertilizerRecommendationOutput:
        crop_key = input_data.crop_name.strip().lower()
        stage_key = input_data.crop_stage.strip().lower()

        # Identify major nutrient deficiency based on soil test
        deficiency = []
        if input_data.nitrogen < 50:
            deficiency.append("Nitrogen (N) Deficit")
        if input_data.phosphorus < 25:
            deficiency.append("Phosphorus (P) Deficit")
        if input_data.potassium < 40:
            deficiency.append("Potassium (K) Deficit")

        deficiency_str = ", ".join(deficiency) if deficiency else "Balanced Maintenance Nutrient"

        # Check knowledge base table
        crop_dict = cls.AGRONOMIC_DOSAGE_TABLE.get(crop_key)
        if not crop_dict:
            # Fallback for unlisted crops
            stage_info = {
                "fertilizer": "Balanced NPK (19-19-19) + Micronutrient Mixture",
                "dosage_per_acre": "2.0 kg per acre in 200 Litres of water",
                "method": "Foliar spray or soil drenching near root rhizosphere",
                "timing": "Early vegetative or active growing phase",
                "source": "State Department of Agriculture Standard Advisory"
            }
            uncertainty = f"Crop '{input_data.crop_name}' uses general agronomic baseline. Soil health card verification recommended."
            confidence = "Moderate"
        else:
            stage_info = crop_dict.get(stage_key, crop_dict["vegetative"])
            uncertainty = None
            confidence = "High (ICAR Verified)"

        # Run candidate advice through SafetyEngine
        candidate_text = f"Apply {stage_info['fertilizer']} at {stage_info['dosage_per_acre']}."
        safety_eval = SafetyEngine.evaluate(candidate_text, crop=input_data.crop_name, stage=input_data.crop_stage)

        safety_advisory = "Wear safety gloves and face mask during application. Apply with adequate soil moisture."
        if safety_eval.warnings:
            safety_advisory += " | " + " | ".join(safety_eval.warnings)

        follow_up = []
        if input_data.moisture < 20:
            follow_up.append("Soil moisture is very low (<20%). Irrigate field before applying chemical fertilizers to avoid root scorching.")

        return FertilizerRecommendationOutput(
            status="success",
            crop=input_data.crop_name.title(),
            crop_stage=input_data.crop_stage.title(),
            nutrient_deficiency=deficiency_str,
            recommended_fertilizer=stage_info["fertilizer"],
            recommended_dosage_per_acre=stage_info["dosage_per_acre"],
            application_method=stage_info["method"],
            timing_guidance=stage_info["timing"],
            safety_advisory=safety_advisory,
            evidence_source=stage_info["source"],
            confidence_level=confidence,
            uncertainty_notes=uncertainty,
            follow_up_questions=follow_up
        )
