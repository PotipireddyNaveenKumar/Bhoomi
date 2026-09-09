# BHOOMI V2 — Phase 4 Baseline Audit & System Inventory

## Executive Summary
This document serves as the comprehensive, authoritative audit of the BHOOMI V2 codebase prior to commencing Phase 4.
All 43 unit and integration tests across Phase 1, Phase 2, and Phase 3 are passing (100%), and the system provides an end-to-end decision intelligence platform for Indian farmers.

---

## 1. Current Backend Architecture
The backend is constructed using **Python 3.11** and **FastAPI**, structured into clean layered domains:
- **API Routers (`backend/app/api/v1/`)**:
  - `auth.py`: JWT authentication, token refresh, password hashing.
  - `farmer.py`, `farms.py`: Farmer onboarding, geo-coordinates, acreage, soil types.
  - `crop.py`, `yield_routes.py`: Crop registry, growth stages, yield predictions.
  - `profit.py`, `simulation.py`, `risk.py`: Deterministic financial calculations, what-if simulations, 7-factor risk scoring.
  - `tasks.py`: Stage-specific operational task management.
  - `ml.py`: Crop recommendation (RandomForest), yield prediction (XGBoost), fertilizer planning.
  - `vision_routes.py`: Multimodal plant pathology and foliar leaf analysis.
  - `rag_routes.py`: Agricultural knowledge base search with authoritative citations.
  - `farm_routes.py`: Farm summary, digital twin, and multi-crop comparison.
  - `farm_manager_routes.py`: Personal Farm Manager endpoints (state, today/week briefings, changes diff, proactive alerts, events, timeline, plan, feedback).
- **Service Layer (`backend/app/services/`)**:
  - Domain isolation: `crop/`, `farm_manager/`, `finance/`, `llm/`, `market/`, `memory/`, `monitoring/`, `rag/`, `risk/`, `safety/`, `simulation/`, `tasks/`, `vision/`, `weather/`.
- **Agents & Orchestration (`backend/app/agents/`)**:
  - `BhoomiAgentOrchestrator`: Multi-turn manager turn handler, missing info detector, tool router, safety enforcement, and recommendation trace logger.
  - `ToolRegistry`: 17 registered domain tools.

---

## 2. Current Flutter Architecture
The mobile application is built in **Flutter (Dart)** under `frontend/mobile/lib/`:
- **Features (`lib/features/`)**:
  - `command_center/`: `FarmCommandCenterScreen` with 4 tabbed sections (Today, My Crop, What Changed, Financials) and central voice orb.
  - `vision/`: `LeafScannerScreen` supporting camera capture, gallery upload, image quality check, and diagnosis card rendering.
  - `home/`: Main farmer dashboard.
  - `voice/`: `VoiceAssistantScreen` with state-aware VoiceOrb (idle, listening, processing, speaking).
  - `market/`: `MarketIntelligenceScreen` showing mandi rates, transport costs, and net realization.
  - `profit/`: `ProfitSimulatorScreen` with interactive cost and price sensitivity sliders.
  - `tasks/`, `farm/`, `language/`, `auth/`, `onboarding/`, `splash/`.
- **Shared Cards (`lib/shared/cards/`)**:
  - `CropRecommendationCard`, `YieldPredictionCard`, `LeafDiagnosisCard`, `MarketCard`, `ProfitCard`, `RiskCard`, `SimulationCard`, `TaskCard`, `WeatherCard`.
- **Routing & Localization**:
  - `AppRouter` managing 13 named routes.
  - Localization support across 6 Indian languages (`en`, `te`, `hi`, `ta`, `kn`, `ml`).

---

## 3. Current Database Schema
The database uses **SQLAlchemy 2.0 (Async + Sync)** supporting both local SQLite and production PostgreSQL:
- **Engines Configured**:
  - Development / CI: `sqlite+aiosqlite:///./bhoomi.db`
  - Production (`.env.example`): `postgresql+asyncpg://postgres:postgres@localhost:5432/bhoomi_v2` (with PgVector support for vector embeddings)
- **Core Entities & Tables**:
  - `users`: User identity, phone, hashed password, role (`farmer`, `admin`).
  - `farmers`: Profile, preferred language, state, district, village, geo-coordinates.
  - `farms`: Farm entity, total acreage, soil type (black, red, alluvial, sandy, clay, loamy), irrigation source.
  - `crops`: Active cultivated crops, variety, sowing date, current stage, expected harvest.
  - `chat_sessions`, `chat_messages`: Multi-turn conversational history.
  - `farm_memories`: Key-value episodic and procedural memory with confidence scores.
  - `farm_tasks`: Operational activities with priority, deadlines, and conditional triggers.
  - `predictions`: Logged ML inferences for yield and crop recommendation.

---

## 4. Current ML Models
Trained, serialized, and benchmarked models in `models/`:
- **Crop Recommendation Engine (`models/crop_recommendation/`)**:
  - **Algorithm**: `RandomForestClassifier` (100 estimators).
  - **Performance**: 0.9955 Macro-F1, 0.9955 Test Accuracy across 22 crops.
  - **Artifacts**: `crop_recommendation_model.joblib`, `crop_scaler.joblib`, `crop_label_encoder.joblib`, `metadata.json`.
- **Yield Prediction Regressor (`models/yield_prediction/`)**:
  - **Algorithm**: `XGBoostRegressor`.
  - **Performance**: 0.9574 $R^2$, 0.8192 t/ha MAE.
  - **Feature Hygiene**: Target leakage strictly eliminated (post-harvest `production` excluded).
  - **Artifacts**: `yield_prediction_pipeline.joblib`, `metadata.json`.
- **Fertilizer Planning Pipeline (`models/fertilizer_recommendation/`)**:
  - Multi-class soil deficit classifier paired with ICAR/SAU package-of-practices guidelines.

---

## 5. Current Vision Models & Plant Pathology
- **ImageQualityGate (`backend/app/services/vision/quality_gate.py`)**:
  - Evaluates minimum resolution ($224\times 224$), illumination ($30 \le B \le 245$), aspect ratio ($\le 4.5:1$), and edge gradient variance (blur).
- **VisionModelRegistry (`backend/app/services/vision/registry.py`)**:
  - Multi-crop pathology taxonomy covering 10 crops: Chilli (ChiLCV, Cercospora), Rice (BLB, Blast), Tomato (ToLCV, Early Blight), Potato, Sugarcane, Banana, Guava, Corn/Maize, Cucurbits, Apple.
- **VisionPredictionValidator (`backend/app/services/vision/validator.py`)**:
  - Out-of-Distribution (OOD) anomaly and confidence gate flagging uncertain scans.
- **CropHealthTimeline (`backend/app/services/farm_manager/crop_health_timeline.py`)**:
  - Tracks serial scans over time, classifying health trajectories into `IMPROVING`, `STABLE`, or `WORSENING`.

---

## 6. Current RAG System
- **AgriculturalRAGService (`backend/app/services/rag/rag_service.py`)**:
  - Grounded semantic search engine with `InMemoryVectorStore` and `CitationBuilder`.
  - Indexed official publications from ICAR, ANGRAU, NRRI, CICR, and IIHR.
  - Mandatory evidence requirement for high-risk chemical and pest management recommendations.

---

## 7. Current FarmStateEngine
- **`FarmStateEngine` (`backend/app/services/farm_manager/state_engine.py`)**:
  - Aggregates 12 distinct sources into a canonical `FarmState` object:
    - Farmer profile & acreage
    - Soil type & borewell irrigation
    - Crop lifecycle stage & Days After Sowing (DAS)
    - IMD weather forecast
    - APMC mandi modal price & Net Realization
    - XGBoost yield prediction (Q/acre & total production)
    - Deterministic Decimal gross revenue, cost, and net profit
    - 7-factor risk score
    - Pending operational tasks
    - Real-time data freshness flags (`CURRENT`, `CACHED`, `STALE`)

---

## 8. Current FarmDecisionEngine
- **`FarmDecisionEngine` (`backend/app/services/farm_manager/decision_engine.py`)**:
  - Converts `FarmState` into prioritized `DecisionPlan`.
  - Every decision item contains: `priority`, `action`, `category`, `reason`, `urgency`, `deadline`, `expected_benefit`, `risk_if_ignored`, `confidence`, `evidence`, and `required_farmer_confirmation`.
- **`DailyFarmBriefingService`**:
  - Generates Today's Briefing and Weekly Agricultural Schedule.
- **Specialized Decision Engines**:
  - `WeatherDecisionEngine`: Translates rain probabilities $\ge 40\%$ into irrigation holds and spray postponement.
  - `MarketDecisionEngine`: Evaluates net realization against farmer thresholds to issue `SELL NOW`, `WAIT`, `COMPARE MARKETS`, or `MONITOR`.
  - `IrrigationDecisionEngine`: Calculates soil moisture deficits and watering durations.
  - `HarvestDecisionEngine`: Determines physiological maturity % and harvest window logistics.

---

## 9. Current FarmMemory
- **`FarmMemoryV2` (`backend/app/services/memory/farm_memory_v2.py`)**:
  - Categorizes 8 longitudinal memory types:
    1. Farmer Preferences (target crops, risk tolerance)
    2. Farm Facts (soil characteristics, borewell yield)
    3. Historical Decisions (sowing decisions, chemical choices)
    4. Crop History (past rotational yields)
    5. Farm Events (unseasonal rain, pest outbreaks)
    6. Previous Recommendations (BHOOMI suggested actions)
    7. Farmer Feedback (accepted, modified, rejected)
    8. Actual Outcomes (harvest yield, realized mandi prices, net profit)

---

## 10. Current AgentOrchestrator
- **`BhoomiAgentOrchestrator` (`backend/app/agents/orchestrator.py`)**:
  - Implements multi-turn reasoning:
    $$\text{Farmer Input} \longrightarrow \text{Context Retrieval} \longrightarrow \text{Missing Info Gate} \longrightarrow \text{Tool Selection} \longrightarrow \text{Tool Execution} \longrightarrow \text{SafetyEngine} \longrightarrow \text{Trace Recording} \longrightarrow \text{Output}$$
  - Connects to 17 tools in `ToolRegistry`.
  - Records every recommendation into `RecommendationTraceStore` for complete auditability.

---

## 11. Current External API Providers
- **Voice Provider**:
  - `SarvamVoiceProvider`: Implements Sarvam AI STT (`saaras:v2`) and TTS (`bulbul:v1`) for Indian languages (`te`, `hi`, `en`, `ta`, `kn`, `ml`).
  - `MockVoiceProvider`: Offline mock fallback for test execution.
- **LLM Provider**:
  - `OpenAIProvider`: Configured for GPT-4o / GPT-4o-mini via `OPENAI_API_KEY`.
  - `GeminiProvider`: Configured for Gemini 1.5 Pro / Flash via `GEMINI_API_KEY`.
  - `GroqProvider`: Configured for Llama-3-70b via `GROQ_API_KEY`.
  - `MockLLMProvider`: Deterministic keyword-and-tool matcher for zero-cost offline CI/CD.
- **Weather Provider**:
  - `OpenWeatherMapProvider`: Hourly and 5-day precipitation forecasts via `WEATHER_API_KEY`.
  - `MockWeatherProvider`: Synthesizes IMD-compliant meteorological bulletins.
- **Market Mandi Provider**:
  - `DataGovMarketProvider`: AGMARKNET real-time daily mandi modal arrival prices via `DATA_GOV_API_KEY`.
  - `MockMarketProvider`: Simulates APMC arrival prices and transport deduction math.
- **Vector Database**:
  - `ChromaDB`: Embedded vector persistence in `./data/chroma`.
- **Cache & Message Broker**:
  - `Redis`: Configured at `redis://localhost:6379/0` (with fallback to in-memory).

---

## 12. Current Test Suite
The automated test suite in `backend/tests/` contains **43 tests passing 100%** in 4.42s:
1. `test_agent_and_api.py` (3 tests): Missing info detection, mock voice transcription and synthesis.
2. `test_financial_service.py` (3 tests): Exact Decimal arithmetic, multi-acre scaling, profit/loss scenarios.
3. `test_image_gate.py` (3 tests): Resolution, aspect ratio, dark illumination rejection.
4. `test_safety_engine.py` (2 tests): Monocrotophos banned chemical interception, flowering pollinator warnings.
5. `test_simulation_service.py` (2 tests): -20% price drop simulation, cost surge + yield shock simulation.
6. `test_phase2_ml_and_intelligence.py` (14 tests): Dataset validation, ML crop recommendation, yield prediction CI, fertilizer dosage, RAG retrieval, crop comparison, smart reminders, ToolRegistry.
7. `test_phase3_farm_manager.py` (16 tests): FarmStateEngine, FarmEventProcessor, FarmMemory 2.0, RecommendationTrace audit, DailyBriefing, ChangeDetection, ProactiveAlerts, Weather/Market/Irrigation/Harvest decision engines, CropHealthTimeline, PersonalCropPlanner, Adaptive FarmPlan, ModelMonitoring, and Orchestrator conversation.

---

## 13. Current Environment Configuration
Defined in `backend/app/core/config.py` and `.env.example`:
- `APP_NAME` ("BHOOMI V2"), `APP_ENV` (`development` | `production`), `DEBUG` (`True` | `False`).
- `HOST` (`0.0.0.0`), `PORT` (`8000`), `API_V1_STR` (`/api/v1`).
- `DATABASE_URL`: `sqlite+aiosqlite:///./bhoomi.db` (local dev) / `postgresql+asyncpg://postgres:postgres@localhost:5432/bhoomi_v2` (production).
- `DATABASE_SYNC_URL`: `sqlite:///./bhoomi.db` (local dev) / `postgresql://postgres:postgres@localhost:5432/bhoomi_v2` (production).
- `SECRET_KEY`, `ALGORITHM` (`HS256`), `ACCESS_TOKEN_EXPIRE_MINUTES` (`43200`).
- `REDIS_URL` (`redis://localhost:6379/0`).
- `VOICE_PROVIDER` (`sarvam` | `whisper` | `mock` | `bhashini`).
- `SARVAM_API_KEY`, `SARVAM_STT_MODEL` (`saaras:v2`), `SARVAM_TTS_MODEL` (`bulbul:v1`).
- `LLM_PROVIDER` (`openai` | `gemini` | `groq` | `mock`).
- `OPENAI_API_KEY`, `GEMINI_API_KEY`, `GROQ_API_KEY`.
- `VECTOR_DB_PROVIDER` (`chroma` | `qdrant` | `pgvector`), `CHROMA_PERSIST_DIR` (`./data/chroma`).
- `WEATHER_PROVIDER` (`openweathermap` | `mock`), `WEATHER_API_KEY`.
- `MARKET_PROVIDER` (`data_gov` | `mock`), `DATA_GOV_API_KEY`.
- `OBJECT_STORAGE_PROVIDER` (`local`), `STORAGE_LOCAL_DIR` (`./uploads`).

---

## 14. Current Mock / Demo Data
- **Demo Farmer**: Ramesh Kumar, Guntur District, Tenali Village, Andhra Pradesh.
- **Demo Farm**: 3.0 Acres, Vertisol Black Soil, Borewell Irrigation.
- **Active Demo Crop**: Chilli (Teja variety), Flowering Stage (45 Days After Sowing).
- **Default Meteorological Conditions**: 31.5°C, 78% humidity, 40% rain probability, 2.4mm rain.
- **Default Market Data**: Guntur APMC Mandi, ₹12,200/Q modal price, ₹80/Q transport cost $\rightarrow$ ₹12,120/Q Net Realization.

---

## 15. Current Production Gaps
1. **Live External Feeds**: Weather and Market providers currently default to `mock` when live API keys (`WEATHER_API_KEY`, `DATA_GOV_API_KEY`) are not supplied in `.env`.
2. **Database Engine**: Local SQLite used in development; PostgreSQL with PgVector required for enterprise production concurrency.
3. **Deep Learning Vision Deployment**: Vision inference currently runs heuristic feature and rule verification on PIL images; production deployment requires serving PyTorch / ONNX models trained on the organized 10-crop disease datasets.
4. **Offline Mobile Caching**: Flutter UI communicates over HTTP; mobile-side SQLite / Hive caching required for zero-connectivity field operations.
5. **Real-World Farmer Validation**: Validation against field soil health cards and local Krishi Vigyan Kendra (KVK) agronomic calendars.
