import os
import joblib
import numpy as np
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

class CropRecommendationInput(BaseModel):
    nitrogen: float = Field(..., ge=0, le=300, example=90.0, description="Nitrogen content ratio in soil")
    phosphorus: float = Field(..., ge=0, le=250, example=42.0, description="Phosphorus content ratio in soil")
    potassium: float = Field(..., ge=0, le=300, example=43.0, description="Potassium content ratio in soil")
    temperature: float = Field(..., ge=0, le=55, example=24.5, description="Ambient temperature in °C")
    humidity: float = Field(..., ge=0, le=100, example=82.0, description="Relative humidity in %")
    ph: float = Field(..., ge=3.5, le=9.5, example=6.5, description="Soil pH value")
    rainfall: float = Field(..., ge=0, le=4000, example=202.0, description="Rainfall in mm")

class RecommendedCrop(BaseModel):
    crop: str
    confidence: float
    percentage: float
    suitability: str
    key_drivers: List[str]

class CropRecommendationOutput(BaseModel):
    status: str
    model_version: str
    model_name: str
    recommended_crops: List[RecommendedCrop]
    input_summary: Dict[str, float]
    advisory: str
    warnings: List[str]

class CropRecommendationService:
    _model = None
    _scaler = None
    _label_encoder = None
    _metadata = None

    @classmethod
    def _load_artifacts(cls):
        if cls._model is None:
            from app.core.config import settings
            candidate_dirs = [
                os.path.join(settings.MODELS_DIR, "crop_recommendation"),
                "models/crop_recommendation",
                "../models/crop_recommendation",
                os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "models", "crop_recommendation")),
            ]
            
            loaded = False
            for model_dir in candidate_dirs:
                model_path = os.path.join(model_dir, "crop_recommendation_model.joblib")
                scaler_path = os.path.join(model_dir, "crop_scaler.joblib")
                encoder_path = os.path.join(model_dir, "crop_label_encoder.joblib")

                if os.path.exists(model_path) and os.path.exists(scaler_path) and os.path.exists(encoder_path):
                    cls._model = joblib.load(model_path)
                    cls._scaler = joblib.load(scaler_path)
                    cls._label_encoder = joblib.load(encoder_path)
                    loaded = True
                    break

            if not loaded:
                raise RuntimeError("Crop recommendation model artifacts not found across candidate directories.")

    @classmethod
    def predict(cls, input_data: CropRecommendationInput, top_k: int = 3) -> CropRecommendationOutput:
        cls._load_artifacts()

        features = np.array([[
            input_data.nitrogen,
            input_data.phosphorus,
            input_data.potassium,
            input_data.temperature,
            input_data.humidity,
            input_data.ph,
            input_data.rainfall
        ]])

        features_scaled = cls._scaler.transform(features)
        probs = cls._model.predict_proba(features_scaled)[0]
        top_indices = np.argsort(probs)[::-1][:top_k]

        warnings: List[str] = []
        if input_data.ph < 5.5:
            warnings.append("Acidic Soil Alert: Soil pH is below 5.5; consider agricultural lime application for acid-sensitive crops.")
        elif input_data.ph > 8.0:
            warnings.append("Alkaline Soil Alert: Soil pH exceeds 8.0; consider gypsum or sulfur amendments.")

        if input_data.rainfall < 400:
            warnings.append("Low Rainfall Alert: Supplementary irrigation (borewell/drip) is essential under <400mm precipitation.")

        recommended_crops = []
        for idx in top_indices:
            crop_name = cls._label_encoder.classes_[idx].title()
            conf = float(probs[idx])
            pct = round(conf * 100, 1)

            # Driver explanation
            drivers = []
            if input_data.rainfall > 150:
                drivers.append("High moisture tolerance")
            if input_data.temperature > 25:
                drivers.append("Warm climate adaptation")
            if input_data.nitrogen > 80:
                drivers.append("High nitrogen nutrient response")
            if not drivers:
                drivers.append("Balanced soil-climate suitability")

            suitability = "Optimal" if pct >= 60 else "Favorable" if pct >= 25 else "Moderate"

            recommended_crops.append(RecommendedCrop(
                crop=crop_name,
                confidence=round(conf, 4),
                percentage=pct,
                suitability=suitability,
                key_drivers=drivers
            ))

        primary_crop = recommended_crops[0].crop if recommended_crops else "Unknown"
        advisory = (
            f"Based on your soil nutrient levels (N:{input_data.nitrogen:.0f}, P:{input_data.phosphorus:.0f}, K:{input_data.potassium:.0f}), "
            f"pH of {input_data.ph:.1f}, and {input_data.rainfall:.0f}mm rainfall profile, **{primary_crop}** is the most suitable crop with "
            f"{recommended_crops[0].percentage}% agronomic confidence."
        )

        return CropRecommendationOutput(
            status="success",
            model_version="v2.0-production",
            model_name="RandomForestClassifier",
            recommended_crops=recommended_crops,
            input_summary={
                "N": input_data.nitrogen,
                "P": input_data.phosphorus,
                "K": input_data.potassium,
                "temperature": input_data.temperature,
                "humidity": input_data.humidity,
                "ph": input_data.ph,
                "rainfall": input_data.rainfall
            },
            advisory=advisory,
            warnings=warnings
        )
