# BHOOMI V2 — Phase 3 Architecture Baseline

## 1. Executive Summary
This document establishes the verified baseline of BHOOMI V2 following the completion of Phase 1 and Phase 2.
All 27 automated tests pass 100%, and all existing interfaces, ML models, RAG vector stores, voice providers, and database structures are protected under backward-compatibility guarantees.

---

## 2. Protected Baseline Components

### A. Machine Learning Models & Artifacts
- **Crop Recommendation Engine** (`models/crop_recommendation/`):
  - Model: `RandomForestClassifier` (Macro-F1: 0.9955, Test Accuracy: 0.9955)
  - Features: `nitrogen`, `phosphorus`, `potassium`, `temperature`, `humidity`, `ph`, `rainfall`
  - Served via: `POST /api/v1/ml/crop-recommendation`
- **Yield Prediction Regressor** (`models/yield_prediction/`):
  - Model: `XGBoostRegressor` ($R^2$: 0.9574, MAE: 0.8192 tonnes/ha)
  - Features: `crop`, `season`, `state`, `area`, `annual_rainfall`, `fertilizer`, `pesticide`
  - Strict leakage isolation: `production` excluded from features
  - Served via: `POST /api/v1/ml/yield-prediction`
- **Fertilizer Recommendation Service** (`backend/app/services/crop/fertilizer_service.py`):
  - Couplings: Soil nutrient ratios $\rightarrow$ ICAR/SAU Package of Practices $\rightarrow$ SafetyEngine guard $\rightarrow$ Farmer advice.
  - Served via: `POST /api/v1/ml/fertilizer-recommendation`

### B. Computer Vision & Plant Pathology
- **Vision Model Registry** (`backend/app/services/vision/registry.py`):
  - Manages pathology across 10 crops: Chilli, Rice, Tomato, Potato, Sugarcane, Banana, Guava, Corn/Maize, Cucurbits, Apple.
- **Image Quality Gate** (`backend/app/services/vision/quality_gate.py`):
  - Checks minimum resolution ($224\times 224$), illumination ($30 \le B \le 245$), aspect ratio, and blur.
- **OOD Uncertainty Validator** (`backend/app/services/vision/validator.py`):
  - Rejects ambiguous patterns with supportive farmer guidance.
- Served via: `POST /api/v1/vision/analyze`

### C. Agricultural RAG & Grounded Evidence
- **Agricultural RAG Service** (`backend/app/services/rag/rag_service.py`):
  - Pre-loaded with ICAR, ANGRAU, NRRI, CICR, and IIHR research documentation.
  - Semantic vector store with citations and authority tracking.
  - Served via: `POST /api/v1/rag/search`

### D. Core Engines & Data Structures
- **Farm Digital Twin & Memory** (`backend/app/services/memory/digital_twin.py`)
- **Deterministic Financial Engine** (`backend/app/services/finance/profit_service.py`): Exact `Decimal` calculations.
- **What-If Simulation Service** (`backend/app/services/simulation/simulation_service.py`)
- **Multi-Factor Risk Engine** (`backend/app/services/risk/risk_service.py`)
- **Crop Comparison Service** (`backend/app/services/crop/comparison_service.py`)
- **Dynamic Smart Reminder Engine** (`backend/app/services/tasks/smart_reminder_engine.py`)
- **Safety Engine** (`backend/app/services/safety/safety_engine.py`): Banned chemical interception and pollinator warnings.
- **Tool Registry** (`backend/app/agents/tool_registry.py`): 13 registered domain tools.

### E. Mobile UI & Multilingual Voice
- Flutter mobile app localized in 6 Indian languages (`en`, `te`, `hi`, `ta`, `kn`, `ml`).
- `VoiceOrb` safe-state widget and dedicated cards (`WeatherCard`, `MarketCard`, `ProfitCard`, `CropRecommendationCard`, `YieldPredictionCard`, `LeafDiagnosisCard`).
- Interactive screens: `LeafScannerScreen`, `MarketIntelligenceScreen`, `ProfitSimulatorScreen`.

---

## 3. Verified Automated Test Suite (27/27 Passing 100%)
- `backend/tests/test_agent_and_api.py` (3 tests)
- `backend/tests/test_financial_service.py` (3 tests)
- `backend/tests/test_image_gate.py` (3 tests)
- `backend/tests/test_safety_engine.py` (2 tests)
- `backend/tests/test_simulation_service.py` (2 tests)
- `backend/tests/test_phase2_ml_and_intelligence.py` (14 tests)

---

## 4. Protected Rules for Phase 3
1. No breaking changes to existing endpoints or database models.
2. All Phase 3 services will be implemented modularly under `backend/app/services/farm_manager/`.
3. The central intelligence loop must be:
   $$\text{OBSERVE} \longrightarrow \text{UNDERSTAND} \longrightarrow \text{PREDICT} \longrightarrow \text{DECIDE} \longrightarrow \text{ACT} \longrightarrow \text{REMEMBER} \longrightarrow \text{ADAPT}$$
