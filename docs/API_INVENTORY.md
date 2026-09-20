# BHOOMI V2 — Comprehensive API Architecture Inventory & Dependency Trace

**Generated for**: Master Stabilization Batch 2 — API Architecture Stabilization Audit  
**Repository**: [https://github.com/PotipireddyNaveenKumar/Bhoomi](https://github.com/PotipireddyNaveenKumar/Bhoomi)  
**Live Production**: [https://bhoomi-production-0e92.up.railway.app](https://bhoomi-production-0e92.up.railway.app)  
**Audit Scope**: Strict Read-Only Audit & Dependency Discovery (No Code or Route Deletions)  

---

## 1. Executive Summary & Taxonomy Distribution

Total registered endpoints audited: **96**

| Classification | Count | Definition |
|---|---|---|
| **CANONICAL** | 63 | Primary, production-active, maintained endpoint for feature domain. |
| **DUPLICATE** | 4 | Functionally redundant duplicate route or handler targeting same service/model. |
| **LEGACY** | 3 | Superseded by newer ML or modular architecture; retained for backwards compatibility. |
| **DEMO_ONLY** | 15 | Exclusively used for reviewer sandbox, simulated test telemetry, or demo state. |
| **INTERNAL** | 4 | System utility, RAG debug, condition evaluator, or internal helper endpoints. |
| **UNUSED** | 7 | No web, mobile, test, backend, or documentation references identified. |
| **UNKNOWN** | 0 | Unresolved dependency or ambiguous caller trace. |

---

## 2. Master API Inventory Table

| METHOD | PATH | ROUTER | SERVICE | FRONTEND USE | TEST USE | STATUS |
|---|---|---|---|---|---|---|
| `GET` | `/` | `main.py` | HealthService | Web (4) + Mobile (39) | Tests (40 files) | **CANONICAL** |
| `POST` | `/api/v1/assistant/chat` | `assistant.py` | BhoomiAgentOrchestrator, VisionService, RecommendationTraceStore | Web (1) + Mobile (2) | Tests (4 files) | **CANONICAL** |
| `POST` | `/api/v1/assistant/chat-upload` | `assistant.py` | BhoomiAgentOrchestrator, VisionService, RecommendationTraceStore | None | None | **UNUSED** |
| `POST` | `/api/v1/assistant/feedback` | `assistant.py` | BhoomiAgentOrchestrator, VisionService, RecommendationTraceStore | Web (app.js) | Tests (3 files) | **CANONICAL** |
| `GET` | `/api/v1/assistant/sessions` | `assistant.py` | BhoomiAgentOrchestrator, VisionService, RecommendationTraceStore | None | None | **UNUSED** |
| `GET` | `/api/v1/assistant/sessions/{session_id}` | `assistant.py` | BhoomiAgentOrchestrator, VisionService, RecommendationTraceStore | None | None | **UNUSED** |
| `POST` | `/api/v1/auth/login` | `auth.py` | AuthService, SMSTransport | Web (1) + Mobile (1) | Tests (5 files) | **CANONICAL** |
| `POST` | `/api/v1/auth/login/request-otp` | `auth.py` | AuthService, SMSTransport | Web (app.js) | Tests (1 files) | **CANONICAL** |
| `POST` | `/api/v1/auth/login/verify-otp` | `auth.py` | AuthService, SMSTransport | Web (app.js) | Tests (2 files) | **CANONICAL** |
| `POST` | `/api/v1/auth/logout` | `auth.py` | AuthService, SMSTransport | Web (app.js) | Tests (3 files) | **CANONICAL** |
| `GET` | `/api/v1/auth/me` | `auth.py` | AuthService, SMSTransport | Web (app.js) | Tests (3 files) | **CANONICAL** |
| `POST` | `/api/v1/auth/refresh` | `auth.py` | AuthService, SMSTransport | None | Tests (2 files) | **CANONICAL** |
| `POST` | `/api/v1/auth/register` | `auth.py` | AuthService, SMSTransport | Mobile (api_endpoints.dart) | None | **DEMO_ONLY** |
| `POST` | `/api/v1/auth/signup/request-otp` | `auth.py` | AuthService, SMSTransport | Web (app.js) | Tests (3 files) | **CANONICAL** |
| `POST` | `/api/v1/auth/signup/verify-otp` | `auth.py` | AuthService, SMSTransport | Web (app.js) | Tests (1 files) | **CANONICAL** |
| `POST` | `/api/v1/chat` | `chat.py` | BhoomiAgentOrchestrator | Web (1) + Mobile (3) | Tests (5 files) | **DUPLICATE** |
| `GET` | `/api/v1/chat/sessions` | `chat.py` | BhoomiAgentOrchestrator | Mobile (api_endpoints.dart) | None | **DUPLICATE** |
| `GET` | `/api/v1/chat/sessions/{session_id}` | `chat.py` | BhoomiAgentOrchestrator | None | None | **DUPLICATE** |
| `GET` | `/api/v1/crop/lifecycle` | `crop.py` | CropRecommendationService, CropLifecycleService | None | None | **UNUSED** |
| `POST` | `/api/v1/crop/recommend` | `crop.py` | CropRecommendationService, CropLifecycleService | None | None | **LEGACY** |
| `POST` | `/api/v1/decisions/evaluate` | `decision_routes.py` | DecisionTraceService, RecommendationTraceStore | None | Tests (1 files) | **CANONICAL** |
| `GET` | `/api/v1/demo/profile` | `demo.py` | DemoModeService | None | Tests (1 files) | **DEMO_ONLY** |
| `POST` | `/api/v1/demo/reset` | `demo.py` | DemoModeService | None | Tests (2 files) | **DEMO_ONLY** |
| `GET` | `/api/v1/demo/scenarios` | `demo.py` | DemoModeService | None | Tests (1 files) | **DEMO_ONLY** |
| `POST` | `/api/v1/demo/scenarios/{scenario_id}/execute` | `demo.py` | DemoModeService | None | Tests (1 files) | **DEMO_ONLY** |
| `POST` | `/api/v1/farm/compare-crops` | `farm_routes.py` | DigitalTwinService, CropComparisonService | Mobile (api_endpoints.dart) | None | **CANONICAL** |
| `GET` | `/api/v1/farm/crops` | `farm_routes.py` | DigitalTwinService, CropComparisonService | Mobile (api_endpoints.dart) | None | **CANONICAL** |
| `GET` | `/api/v1/farm/summary` | `farm_routes.py` | DigitalTwinService, CropComparisonService | Mobile (api_endpoints.dart) | None | **CANONICAL** |
| `GET` | `/api/v1/farm/tasks` | `farm_routes.py` | DigitalTwinService, CropComparisonService | None | None | **UNUSED** |
| `GET` | `/api/v1/farmer` | `farmer.py` | FarmerProfileService | Web (1) + Mobile (1) | None | **CANONICAL** |
| `PUT` | `/api/v1/farmer` | `farmer.py` | FarmerProfileService | Web (1) + Mobile (1) | None | **CANONICAL** |
| `GET` | `/api/v1/farms` | `farms.py` | FarmDigitalTwinService, SoilEstimateService | Web (1) + Mobile (1) | None | **CANONICAL** |
| `POST` | `/api/v1/farms` | `farms.py` | FarmDigitalTwinService, SoilEstimateService | Web (1) + Mobile (1) | None | **CANONICAL** |
| `GET` | `/api/v1/farms/soil-estimate` | `farms.py` | FarmDigitalTwinService, SoilEstimateService | Web (app.js) | None | **CANONICAL** |
| `GET` | `/api/v1/farms/{farm_id}` | `farms.py` | FarmDigitalTwinService, SoilEstimateService | Web (app.js) | None | **CANONICAL** |
| `POST` | `/api/v1/farms/{farm_id}/crops` | `farms.py` | FarmDigitalTwinService, SoilEstimateService | None | None | **UNUSED** |
| `POST` | `/api/v1/image/analyze` | `image.py` | VisionService | Mobile (api_endpoints.dart) | None | **LEGACY** |
| `GET` | `/api/v1/manager/alerts` | `farm_manager_routes.py` | FarmStateEngine, DailyFarmBriefingService, FarmChangeDetectionService | Mobile (api_endpoints.dart) | None | **CANONICAL** |
| `GET` | `/api/v1/manager/briefing/today` | `farm_manager_routes.py` | FarmStateEngine, DailyFarmBriefingService, FarmChangeDetectionService | Mobile (api_endpoints.dart) | None | **CANONICAL** |
| `GET` | `/api/v1/manager/briefing/week` | `farm_manager_routes.py` | FarmStateEngine, DailyFarmBriefingService, FarmChangeDetectionService | Mobile (api_endpoints.dart) | None | **CANONICAL** |
| `GET` | `/api/v1/manager/changes` | `farm_manager_routes.py` | FarmStateEngine, DailyFarmBriefingService, FarmChangeDetectionService | Mobile (api_endpoints.dart) | None | **CANONICAL** |
| `POST` | `/api/v1/manager/events` | `farm_manager_routes.py` | FarmStateEngine, DailyFarmBriefingService, FarmChangeDetectionService | Mobile (api_endpoints.dart) | None | **CANONICAL** |
| `POST` | `/api/v1/manager/feedback` | `farm_manager_routes.py` | FarmStateEngine, DailyFarmBriefingService, FarmChangeDetectionService | None | Tests (1 files) | **CANONICAL** |
| `GET` | `/api/v1/manager/plan` | `farm_manager_routes.py` | FarmStateEngine, DailyFarmBriefingService, FarmChangeDetectionService | Mobile (api_endpoints.dart) | None | **CANONICAL** |
| `GET` | `/api/v1/manager/state` | `farm_manager_routes.py` | FarmStateEngine, DailyFarmBriefingService, FarmChangeDetectionService | Mobile (api_endpoints.dart) | None | **CANONICAL** |
| `GET` | `/api/v1/manager/timeline` | `farm_manager_routes.py` | FarmStateEngine, DailyFarmBriefingService, FarmChangeDetectionService | Mobile (api_endpoints.dart) | None | **CANONICAL** |
| `GET` | `/api/v1/market` | `market.py` | MarketService | Mobile (api_endpoints.dart, chat_screen.dart, home_screen.dart, voice_assistant_screen.dart, app_router.dart, widget_test.dart) | Tests (2 files) | **CANONICAL** |
| `POST` | `/api/v1/ml/crop-recommendation` | `ml.py` | MLInferenceService | Mobile (api_endpoints.dart) | None | **CANONICAL** |
| `POST` | `/api/v1/ml/fertilizer-recommendation` | `ml.py` | MLInferenceService | Mobile (api_endpoints.dart) | None | **CANONICAL** |
| `POST` | `/api/v1/ml/yield-prediction` | `ml.py` | MLInferenceService | Mobile (api_endpoints.dart) | None | **CANONICAL** |
| `GET` | `/api/v1/pilot/acceptance` | `pilot.py` | PilotTelemetryService | None | Tests (1 files) | **DEMO_ONLY** |
| `GET` | `/api/v1/pilot/crops/{crop}` | `pilot.py` | PilotTelemetryService | None | Tests (1 files) | **DEMO_ONLY** |
| `GET` | `/api/v1/pilot/drift` | `pilot.py` | PilotTelemetryService | None | None | **DEMO_ONLY** |
| `POST` | `/api/v1/pilot/import` | `pilot.py` | PilotTelemetryService | None | None | **DEMO_ONLY** |
| `GET` | `/api/v1/pilot/metrics` | `pilot.py` | PilotTelemetryService | None | None | **DEMO_ONLY** |
| `GET` | `/api/v1/pilot/status` | `pilot.py` | PilotTelemetryService | None | Tests (1 files) | **DEMO_ONLY** |
| `GET` | `/api/v1/pilot/task-metrics` | `pilot.py` | PilotTelemetryService | None | None | **DEMO_ONLY** |
| `GET` | `/api/v1/pilot/voice-metrics` | `pilot.py` | PilotTelemetryService | None | None | **DEMO_ONLY** |
| `POST` | `/api/v1/profit/calculate` | `profit.py` | ProfitService | Web (1) + Mobile (1) | None | **CANONICAL** |
| `POST` | `/api/v1/rag/debug` | `rag_routes.py` | AgriculturalRAGService | None | None | **INTERNAL** |
| `POST` | `/api/v1/rag/search` | `rag_routes.py` | AgriculturalRAGService | Mobile (api_endpoints.dart) | None | **CANONICAL** |
| `POST` | `/api/v1/risk/assess` | `risk.py` | RiskAssessmentService | Mobile (api_endpoints.dart) | None | **CANONICAL** |
| `POST` | `/api/v1/simulation/run` | `simulation.py` | SimulationService | None | Tests (1 files) | **DUPLICATE** |
| `POST` | `/api/v1/simulation/what-if` | `simulation.py` | SimulationService | Web (1) + Mobile (2) | Tests (1 files) | **CANONICAL** |
| `GET` | `/api/v1/tasks` | `tasks.py` | TaskIntelligenceEngine | Mobile (api_endpoints.dart, app_router.dart, widget_test.dart) | Tests (3 files) | **CANONICAL** |
| `POST` | `/api/v1/tasks` | `tasks.py` | TaskIntelligenceEngine | Mobile (api_endpoints.dart, app_router.dart, widget_test.dart) | Tests (3 files) | **CANONICAL** |
| `GET` | `/api/v1/tasks/today` | `tasks.py` | TaskIntelligenceEngine | None | Tests (3 files) | **CANONICAL** |
| `GET` | `/api/v1/tasks/week` | `tasks.py` | TaskIntelligenceEngine | None | Tests (2 files) | **CANONICAL** |
| `PUT` | `/api/v1/tasks/{task_id}` | `tasks.py` | TaskIntelligenceEngine | Mobile (app_router.dart, widget_test.dart) | Tests (3 files) | **CANONICAL** |
| `POST` | `/api/v1/tasks/{task_id}/complete` | `tasks.py` | TaskIntelligenceEngine | None | Tests (1 files) | **CANONICAL** |
| `POST` | `/api/v1/tasks/{task_id}/evaluate-condition` | `tasks.py` | TaskIntelligenceEngine | None | None | **INTERNAL** |
| `POST` | `/api/v1/tasks/{task_id}/postpone` | `tasks.py` | TaskIntelligenceEngine | None | Tests (1 files) | **CANONICAL** |
| `POST` | `/api/v1/tasks/{task_id}/skip` | `tasks.py` | TaskIntelligenceEngine | None | Tests (1 files) | **CANONICAL** |
| `POST` | `/api/v1/vision/analyze` | `vision_routes.py` | VisionService, BhoomiPersonaEngine | Web (1) + Mobile (2) | Tests (1 files) | **CANONICAL** |
| `GET` | `/api/v1/vision/samples` | `vision_routes.py` | VisionService, BhoomiPersonaEngine | Web (app.js) | None | **DEMO_ONLY** |
| `POST` | `/api/v1/voice/interact` | `voice.py` | VoiceService, SarvamVoiceService, BhoomiAgentOrchestrator | Web (1) + Mobile (1) | Tests (3 files) | **CANONICAL** |
| `POST` | `/api/v1/voice/stt` | `voice.py` | VoiceService, SarvamVoiceService, BhoomiAgentOrchestrator | None | None | **INTERNAL** |
| `POST` | `/api/v1/voice/synthesize` | `voice.py` | VoiceService, SarvamVoiceService, BhoomiAgentOrchestrator | Web (1) + Mobile (2) | None | **CANONICAL** |
| `POST` | `/api/v1/voice/task-action` | `voice.py` | VoiceService, SarvamVoiceService, BhoomiAgentOrchestrator | Mobile (voice_assistant_screen.dart) | Tests (1 files) | **CANONICAL** |
| `POST` | `/api/v1/voice/transcribe` | `voice.py` | VoiceService, SarvamVoiceService, BhoomiAgentOrchestrator | Mobile (api_endpoints.dart) | None | **CANONICAL** |
| `POST` | `/api/v1/voice/tts` | `voice.py` | VoiceService, SarvamVoiceService, BhoomiAgentOrchestrator | Web (app.js) | Tests (1 files) | **INTERNAL** |
| `GET` | `/api/v1/weather` | `weather.py` | WeatherService | Mobile (api_endpoints.dart, chat_screen.dart, home_screen.dart, voice_assistant_screen.dart, app_router.dart) | Tests (3 files) | **CANONICAL** |
| `GET` | `/api/v1/weather/forecast` | `weather.py` | WeatherService | None | None | **UNUSED** |
| `POST` | `/api/v1/yield/predict` | `yield_routes.py` | YieldPredictionService | None | None | **LEGACY** |
| `GET` | `/app` | `main.py` | StaticFiles | Web (2) + Mobile (25) | None | **CANONICAL** |
| `GET` | `/finance` | `main.py` | StaticFiles | Web (app.js) | Tests (2 files) | **CANONICAL** |
| `GET` | `/health` | `main.py` | WeatherService, MarketService | None | None | **CANONICAL** |
| `GET` | `/home` | `main.py` | StaticFiles | Web (1) + Mobile (1) | Tests (1 files) | **CANONICAL** |
| `GET` | `/login` | `main.py` | StaticFiles | Web (1) + Mobile (1) | Tests (5 files) | **CANONICAL** |
| `GET` | `/manifest.json` | `main.py` | StaticFiles | Web (index.html) | None | **CANONICAL** |
| `GET` | `/onboarding` | `main.py` | StaticFiles | Web (1) + Mobile (1) | Tests (1 files) | **CANONICAL** |
| `GET` | `/reviewer-login` | `main.py` | StaticFiles | Web (app.js) | Tests (1 files) | **DEMO_ONLY** |
| `GET` | `/signup` | `main.py` | StaticFiles | Web (app.js) | Tests (4 files) | **CANONICAL** |
| `GET` | `/sw.js` | `main.py` | StaticFiles | Web (app.js) | None | **CANONICAL** |
| `GET` | `/verify-otp` | `main.py` | StaticFiles | Web (app.js) | Tests (4 files) | **CANONICAL** |
| `GET` | `/voice` | `main.py` | StaticFiles | Web (1) + Mobile (6) | Tests (5 files) | **CANONICAL** |

---

## 3. Deep Route Specifications & Dependency Trace

### `GET /`
- **Router File**: `backend/app/main.py` (`root`)
- **Service**: `HealthService`
- **Repository / Provider / Model**: `System/Settings`
- **Frontend Web Callers**: frontend/web/index.html, frontend/web/static/app.js, frontend/web/static/style.css, frontend/web/sw.js
- **Frontend Mobile (Flutter) Callers**: frontend/mobile/lib/core/constants/api_endpoints.dart, frontend/mobile/lib/core/constants/app_colors.dart, frontend/mobile/lib/core/networking/api_client.dart, frontend/mobile/lib/core/storage/secure_storage.dart, frontend/mobile/lib/core/theme/app_theme.dart, frontend/mobile/lib/core/utils/audio_player_stub.dart, frontend/mobile/lib/core/utils/audio_player_web.dart, frontend/mobile/lib/core/utils/file_picker_stub.dart, frontend/mobile/lib/core/utils/file_picker_web.dart, frontend/mobile/lib/features/auth/auth_screen.dart, frontend/mobile/lib/features/chat/chat_screen.dart, frontend/mobile/lib/features/command_center/farm_command_center_screen.dart, frontend/mobile/lib/features/farm/farm_profile_screen.dart, frontend/mobile/lib/features/home/home_screen.dart, frontend/mobile/lib/features/language/language_selection_screen.dart, frontend/mobile/lib/features/market/market_intelligence_screen.dart, frontend/mobile/lib/features/onboarding/onboarding_screen.dart, frontend/mobile/lib/features/profit/profit_simulator_screen.dart, frontend/mobile/lib/features/splash/splash_screen.dart, frontend/mobile/lib/features/tasks/tasks_screen.dart, frontend/mobile/lib/features/vision/edge_vision_provider.dart, frontend/mobile/lib/features/vision/leaf_scanner_screen.dart, frontend/mobile/lib/features/voice/voice_assistant_screen.dart, frontend/mobile/lib/features/weather/weather_screen.dart, frontend/mobile/lib/localization/app_localizations.dart, frontend/mobile/lib/main.dart, frontend/mobile/lib/routing/app_router.dart, frontend/mobile/lib/shared/cards/crop_recommendation_card.dart, frontend/mobile/lib/shared/cards/leaf_diagnosis_card.dart, frontend/mobile/lib/shared/cards/market_card.dart, frontend/mobile/lib/shared/cards/profit_card.dart, frontend/mobile/lib/shared/cards/risk_card.dart, frontend/mobile/lib/shared/cards/simulation_card.dart, frontend/mobile/lib/shared/cards/task_card.dart, frontend/mobile/lib/shared/cards/weather_card.dart, frontend/mobile/lib/shared/cards/yield_prediction_card.dart, frontend/mobile/lib/shared/widgets/voice_orb.dart, frontend/mobile/test/api_endpoints_test.dart, frontend/mobile/test/widget_test.dart
- **Backend Internal Callers**: backend/app/main.py
- **Test Callers**: backend/tests/test_agent_and_api.py, backend/tests/test_anti_hardcoding_and_vision_routing.py, backend/tests/test_assistant_feedback.py, backend/tests/test_auth_page_gating.py, backend/tests/test_browser_e2e_reviewer_journey.py, backend/tests/test_browser_weather_market_finance.py, backend/tests/test_datetime_timezone_regression.py, backend/tests/test_demo_scenarios.py, backend/tests/test_farm_finance_localization.py, backend/tests/test_financial_service.py, backend/tests/test_forensic_railway_fixes.py, backend/tests/test_phase29_final_verification.py, backend/tests/test_phase2_ml_and_intelligence.py, backend/tests/test_phase3_farm_manager.py, backend/tests/test_phase4_market.py, backend/tests/test_phase4_multi_crop_vision.py, backend/tests/test_phase4_real_llm.py, backend/tests/test_phase4_sarvam_voice.py, backend/tests/test_phase4_tomato_vision.py, backend/tests/test_phase4_weather.py, backend/tests/test_phase5_field_ingestion.py, backend/tests/test_phase5_field_pilot_readiness.py, backend/tests/test_phase5_field_validation.py, backend/tests/test_phase6_decision_intelligence.py, backend/tests/test_phase6_pilot_audit.py, backend/tests/test_phase6_task_engine.py, backend/tests/test_phase6_voice_interaction.py, backend/tests/test_production_auth_system.py, backend/tests/test_production_config_hardening.py, backend/tests/test_provider_fallback_safety.py, backend/tests/test_rag_production_upgrade.py, backend/tests/test_rag_redesign.py, backend/tests/test_real_sms_delivery.py, backend/tests/test_reviewer_password_auth.py, backend/tests/test_simulation_equivalence.py, backend/tests/test_simulation_service.py, backend/tests/test_task_authorization.py, backend/tests/test_voice_assistant_localization.py, backend/tests/test_voice_authentication_regression.py, backend/tests/test_weather_market_finance_correctness.py
- **Doc References**: README.md, data/benchmarks/300_scenarios.json, data/benchmarks/benchmark_execution_evidence.json, data/evaluation/evaluation_results_300.json, data/evaluation/public_smoke_test_evidence.json, data/evaluation/reviewer_questions/chat_questions.json, data/evaluation/reviewer_questions/image_questions.json, data/field_validation/README.md, data/field_validation/reports/field_validation_report.md, data/field_validation/schema/field_validation_schema.json, data/metadata/crop_recommendation_v1.json, data/metadata/fertilizer_recommendation_v1.json, data/organized/vision/other_crop_diseases/d10/README.md, data/rag/verified_knowledge.json, docs/API_INVENTORY.md, docs/BHOOMI_V2_FINAL_DEMO_GUIDE.md, docs/BHOOMI_V2_FINAL_SUBMISSION_STATUS.md, docs/BHOOMI_V2_FINAL_SYSTEM_ARCHITECTURE.md, docs/DATA_LEAKAGE_REPORT.md, docs/FARM_PLANNER.md, docs/ML_MODEL_REPORT.md, docs/PHASE_2_ARCHITECTURE.md, docs/PHASE_2_BASELINE.md, docs/PHASE_2_VERIFICATION_REPORT.md, docs/PHASE_3_ARCHITECTURE.md, docs/PHASE_3_BASELINE.md, docs/PHASE_3_VERIFICATION_REPORT.md, docs/PHASE_4_BASELINE.md, docs/PHASE_4_ML_VALIDATION_REPORT.md, docs/PHASE_4_MULTI_CROP_VISION.md, docs/PHASE_4_MULTI_CROP_VISION_DATA_AUDIT.md, docs/PHASE_4_REAL_LLM.md, docs/PHASE_4_REAL_MARKET.md, docs/PHASE_4_REAL_WEATHER.md, docs/PHASE_4_SARVAM_VOICE.md, docs/PHASE_4_TOMATO_VISION_DATA_AUDIT.md, docs/PHASE_4_TOMATO_VISION_MODEL.md, docs/PHASE_5_EDGE_AI_REPORT.md, docs/PHASE_5_FIELD_IMAGE_COLLECTION_GUIDE.md, docs/PHASE_5_FIELD_VALIDATION_PROTOCOL.md, docs/PHASE_5_FIELD_VALIDATION_REPORT.md, docs/PHASE_6_STEP_1_DECISION_INTELLIGENCE.md, docs/PHASE_6_STEP_2_CROP_LIFECYCLE_TASK_ENGINE.md, docs/PHASE_6_STEP_3_FARMER_VOICE_LONGITUDINAL_FEEDBACK.md, docs/PHASE_6_STEP_4_FIELD_PILOT_AUDIT_PIPELINE.md, docs/PROACTIVE_INTELLIGENCE.md, docs/RAG_ARCHITECTURE.md, docs/REVIEWER_READINESS_REPORT.md, docs/VISION_MODEL_REPORT.md, docs/api.md, docs/api_inventory.json, docs/architecture.md, docs/dataset_audit_report.md, docs/model_cards/crop_recommendation.md, docs/model_cards/yield_prediction.md, docs/roadmap.md, docs/safety.md, docs/voice.md
- **Reviewer / Demo Usage**: `No`
- **Production Verified**: `LIVE VERIFIED`
- **Behavior Overlap**: `None`
- **Classification**: **`CANONICAL`**

### `POST /api/v1/assistant/chat`
- **Router File**: `backend/app/api/v1/assistant.py` (`chat_with_assistant`)
- **Service**: `BhoomiAgentOrchestrator, VisionService, RecommendationTraceStore`
- **Repository / Provider / Model**: `ChatRepository, FarmMemoryV2, ModelMonitoringService`
- **Frontend Web Callers**: frontend/web/static/app.js
- **Frontend Mobile (Flutter) Callers**: frontend/mobile/lib/core/constants/api_endpoints.dart, frontend/mobile/test/api_endpoints_test.dart
- **Backend Internal Callers**: None
- **Test Callers**: backend/tests/test_datetime_timezone_regression.py, backend/tests/test_forensic_railway_fixes.py, backend/tests/test_reviewer_password_auth.py, backend/tests/test_voice_authentication_regression.py
- **Doc References**: data/evaluation/public_smoke_test_evidence.json, docs/API_INVENTORY.md, docs/api_inventory.json
- **Reviewer / Demo Usage**: `Yes`
- **Production Verified**: `LIVE VERIFIED`
- **Behavior Overlap**: `POST /api/v1/chat (Overlapping conversational agent orchestration)`
- **Classification**: **`CANONICAL`**

### `POST /api/v1/assistant/chat-upload`
- **Router File**: `backend/app/api/v1/assistant.py` (`chat_with_image_upload`)
- **Service**: `BhoomiAgentOrchestrator, VisionService, RecommendationTraceStore`
- **Repository / Provider / Model**: `ChatRepository, FarmMemoryV2, ModelMonitoringService`
- **Frontend Web Callers**: None
- **Frontend Mobile (Flutter) Callers**: None
- **Backend Internal Callers**: None
- **Test Callers**: None
- **Doc References**: docs/API_INVENTORY.md, docs/api_inventory.json
- **Reviewer / Demo Usage**: `No`
- **Production Verified**: `LIVE VERIFIED`
- **Behavior Overlap**: `None`
- **Classification**: **`UNUSED`**

### `POST /api/v1/assistant/feedback`
- **Router File**: `backend/app/api/v1/assistant.py` (`submit_assistant_feedback`)
- **Service**: `BhoomiAgentOrchestrator, VisionService, RecommendationTraceStore`
- **Repository / Provider / Model**: `ChatRepository, FarmMemoryV2, ModelMonitoringService`
- **Frontend Web Callers**: frontend/web/static/app.js
- **Frontend Mobile (Flutter) Callers**: None
- **Backend Internal Callers**: None
- **Test Callers**: backend/tests/test_assistant_feedback.py, backend/tests/test_datetime_timezone_regression.py, backend/tests/test_forensic_railway_fixes.py
- **Doc References**: data/evaluation/public_smoke_test_evidence.json, docs/API_INVENTORY.md, docs/REVIEWER_READINESS_REPORT.md, docs/api_inventory.json
- **Reviewer / Demo Usage**: `No`
- **Production Verified**: `LIVE VERIFIED`
- **Behavior Overlap**: `None`
- **Classification**: **`CANONICAL`**

### `GET /api/v1/assistant/sessions`
- **Router File**: `backend/app/api/v1/assistant.py` (`list_chat_sessions`)
- **Service**: `BhoomiAgentOrchestrator, VisionService, RecommendationTraceStore`
- **Repository / Provider / Model**: `ChatRepository, FarmMemoryV2, ModelMonitoringService`
- **Frontend Web Callers**: None
- **Frontend Mobile (Flutter) Callers**: None
- **Backend Internal Callers**: None
- **Test Callers**: None
- **Doc References**: docs/API_INVENTORY.md, docs/api_inventory.json
- **Reviewer / Demo Usage**: `No`
- **Production Verified**: `LIVE VERIFIED`
- **Behavior Overlap**: `GET /api/v1/chat/sessions (Both query ChatRepository farmer sessions)`
- **Classification**: **`UNUSED`**

### `GET /api/v1/assistant/sessions/{session_id}`
- **Router File**: `backend/app/api/v1/assistant.py` (`get_session_history`)
- **Service**: `BhoomiAgentOrchestrator, VisionService, RecommendationTraceStore`
- **Repository / Provider / Model**: `ChatRepository, FarmMemoryV2, ModelMonitoringService`
- **Frontend Web Callers**: None
- **Frontend Mobile (Flutter) Callers**: None
- **Backend Internal Callers**: None
- **Test Callers**: None
- **Doc References**: docs/API_INVENTORY.md, docs/api_inventory.json
- **Reviewer / Demo Usage**: `No`
- **Production Verified**: `LIVE VERIFIED`
- **Behavior Overlap**: `GET /api/v1/chat/sessions/{session_id} (Both query ChatRepository session by id)`
- **Classification**: **`UNUSED`**

### `POST /api/v1/auth/login`
- **Router File**: `backend/app/api/v1/auth.py` (`login`)
- **Service**: `AuthService, SMSTransport`
- **Repository / Provider / Model**: `AuthSession, User, FarmerProfile, ReviewerAccount`
- **Frontend Web Callers**: frontend/web/static/app.js
- **Frontend Mobile (Flutter) Callers**: frontend/mobile/lib/core/constants/api_endpoints.dart
- **Backend Internal Callers**: backend/app/api/deps.py
- **Test Callers**: backend/tests/test_auth_page_gating.py, backend/tests/test_phase6_task_engine.py, backend/tests/test_production_auth_system.py, backend/tests/test_reviewer_password_auth.py, backend/tests/test_task_authorization.py
- **Doc References**: docs/API_INVENTORY.md, docs/PHASE_2_BASELINE.md, docs/api.md, docs/api_inventory.json
- **Reviewer / Demo Usage**: `Yes`
- **Production Verified**: `LIVE VERIFIED`
- **Behavior Overlap**: `None`
- **Classification**: **`CANONICAL`**

### `POST /api/v1/auth/login/request-otp`
- **Router File**: `backend/app/api/v1/auth.py` (`login_request_otp`)
- **Service**: `AuthService, SMSTransport`
- **Repository / Provider / Model**: `AuthSession, User, FarmerProfile, ReviewerAccount`
- **Frontend Web Callers**: frontend/web/static/app.js
- **Frontend Mobile (Flutter) Callers**: None
- **Backend Internal Callers**: None
- **Test Callers**: backend/tests/test_production_auth_system.py
- **Doc References**: docs/API_INVENTORY.md, docs/api_inventory.json
- **Reviewer / Demo Usage**: `No`
- **Production Verified**: `LIVE VERIFIED`
- **Behavior Overlap**: `None`
- **Classification**: **`CANONICAL`**

### `POST /api/v1/auth/login/verify-otp`
- **Router File**: `backend/app/api/v1/auth.py` (`login_verify_otp`)
- **Service**: `AuthService, SMSTransport`
- **Repository / Provider / Model**: `AuthSession, User, FarmerProfile, ReviewerAccount`
- **Frontend Web Callers**: frontend/web/static/app.js
- **Frontend Mobile (Flutter) Callers**: None
- **Backend Internal Callers**: None
- **Test Callers**: backend/tests/test_production_auth_system.py, backend/tests/test_reviewer_password_auth.py
- **Doc References**: docs/API_INVENTORY.md, docs/api_inventory.json
- **Reviewer / Demo Usage**: `Yes`
- **Production Verified**: `LIVE VERIFIED`
- **Behavior Overlap**: `None`
- **Classification**: **`CANONICAL`**

### `POST /api/v1/auth/logout`
- **Router File**: `backend/app/api/v1/auth.py` (`logout`)
- **Service**: `AuthService, SMSTransport`
- **Repository / Provider / Model**: `AuthSession, User, FarmerProfile, ReviewerAccount`
- **Frontend Web Callers**: frontend/web/static/app.js
- **Frontend Mobile (Flutter) Callers**: None
- **Backend Internal Callers**: None
- **Test Callers**: backend/tests/test_auth_page_gating.py, backend/tests/test_production_auth_system.py, backend/tests/test_reviewer_password_auth.py
- **Doc References**: docs/API_INVENTORY.md, docs/api_inventory.json
- **Reviewer / Demo Usage**: `Yes`
- **Production Verified**: `LIVE VERIFIED`
- **Behavior Overlap**: `None`
- **Classification**: **`CANONICAL`**

### `GET /api/v1/auth/me`
- **Router File**: `backend/app/api/v1/auth.py` (`get_current_user_profile`)
- **Service**: `AuthService, SMSTransport`
- **Repository / Provider / Model**: `AuthSession, User, FarmerProfile, ReviewerAccount`
- **Frontend Web Callers**: frontend/web/static/app.js
- **Frontend Mobile (Flutter) Callers**: None
- **Backend Internal Callers**: None
- **Test Callers**: backend/tests/test_auth_page_gating.py, backend/tests/test_production_auth_system.py, backend/tests/test_reviewer_password_auth.py
- **Doc References**: docs/API_INVENTORY.md, docs/api_inventory.json
- **Reviewer / Demo Usage**: `Yes`
- **Production Verified**: `LIVE VERIFIED`
- **Behavior Overlap**: `None`
- **Classification**: **`CANONICAL`**

### `POST /api/v1/auth/refresh`
- **Router File**: `backend/app/api/v1/auth.py` (`refresh_access_token`)
- **Service**: `AuthService, SMSTransport`
- **Repository / Provider / Model**: `AuthSession, User, FarmerProfile, ReviewerAccount`
- **Frontend Web Callers**: None
- **Frontend Mobile (Flutter) Callers**: None
- **Backend Internal Callers**: None
- **Test Callers**: backend/tests/test_production_auth_system.py, backend/tests/test_reviewer_password_auth.py
- **Doc References**: docs/API_INVENTORY.md, docs/api_inventory.json
- **Reviewer / Demo Usage**: `Yes`
- **Production Verified**: `LIVE VERIFIED`
- **Behavior Overlap**: `None`
- **Classification**: **`CANONICAL`**

### `POST /api/v1/auth/register`
- **Router File**: `backend/app/api/v1/auth.py` (`register`)
- **Service**: `AuthService, SMSTransport`
- **Repository / Provider / Model**: `AuthSession, User, FarmerProfile, ReviewerAccount`
- **Frontend Web Callers**: None
- **Frontend Mobile (Flutter) Callers**: frontend/mobile/lib/core/constants/api_endpoints.dart
- **Backend Internal Callers**: None
- **Test Callers**: None
- **Doc References**: docs/API_INVENTORY.md, docs/PHASE_2_BASELINE.md, docs/api.md, docs/api_inventory.json
- **Reviewer / Demo Usage**: `Yes`
- **Production Verified**: `LIVE VERIFIED`
- **Behavior Overlap**: `None`
- **Classification**: **`DEMO_ONLY`**

### `POST /api/v1/auth/signup/request-otp`
- **Router File**: `backend/app/api/v1/auth.py` (`signup_request_otp`)
- **Service**: `AuthService, SMSTransport`
- **Repository / Provider / Model**: `AuthSession, User, FarmerProfile, ReviewerAccount`
- **Frontend Web Callers**: frontend/web/static/app.js
- **Frontend Mobile (Flutter) Callers**: None
- **Backend Internal Callers**: None
- **Test Callers**: backend/tests/test_production_auth_system.py, backend/tests/test_real_sms_delivery.py, backend/tests/test_reviewer_password_auth.py
- **Doc References**: docs/API_INVENTORY.md, docs/api_inventory.json
- **Reviewer / Demo Usage**: `Yes`
- **Production Verified**: `LIVE VERIFIED`
- **Behavior Overlap**: `None`
- **Classification**: **`CANONICAL`**

### `POST /api/v1/auth/signup/verify-otp`
- **Router File**: `backend/app/api/v1/auth.py` (`signup_verify_otp`)
- **Service**: `AuthService, SMSTransport`
- **Repository / Provider / Model**: `AuthSession, User, FarmerProfile, ReviewerAccount`
- **Frontend Web Callers**: frontend/web/static/app.js
- **Frontend Mobile (Flutter) Callers**: None
- **Backend Internal Callers**: None
- **Test Callers**: backend/tests/test_production_auth_system.py
- **Doc References**: docs/API_INVENTORY.md, docs/api_inventory.json
- **Reviewer / Demo Usage**: `No`
- **Production Verified**: `LIVE VERIFIED`
- **Behavior Overlap**: `None`
- **Classification**: **`CANONICAL`**

### `POST /api/v1/chat`
- **Router File**: `backend/app/api/v1/chat.py` (`send_message`)
- **Service**: `BhoomiAgentOrchestrator`
- **Repository / Provider / Model**: `ChatRepository`
- **Frontend Web Callers**: frontend/web/static/app.js
- **Frontend Mobile (Flutter) Callers**: frontend/mobile/lib/core/constants/api_endpoints.dart, frontend/mobile/lib/routing/app_router.dart, frontend/mobile/test/api_endpoints_test.dart
- **Backend Internal Callers**: backend/app/api/v1/assistant.py, backend/app/services/llm/gemini_provider.py, backend/app/services/llm/openai_provider.py
- **Test Callers**: backend/tests/test_datetime_timezone_regression.py, backend/tests/test_forensic_railway_fixes.py, backend/tests/test_reviewer_password_auth.py, backend/tests/test_voice_authentication_regression.py, test_live_http_api.py
- **Doc References**: data/evaluation/public_smoke_test_evidence.json, docs/API_INVENTORY.md, docs/PHASE_2_BASELINE.md, docs/PHASE_4_REAL_LLM.md, docs/api.md, docs/api_inventory.json
- **Reviewer / Demo Usage**: `Yes`
- **Production Verified**: `LIVE VERIFIED`
- **Behavior Overlap**: `POST /api/v1/assistant/chat (Overlapping conversational agent orchestration; /assistant/chat has multimodal, session, & audio support)`
- **Classification**: **`DUPLICATE`**

### `GET /api/v1/chat/sessions`
- **Router File**: `backend/app/api/v1/chat.py` (`list_sessions`)
- **Service**: `BhoomiAgentOrchestrator`
- **Repository / Provider / Model**: `ChatRepository`
- **Frontend Web Callers**: None
- **Frontend Mobile (Flutter) Callers**: frontend/mobile/lib/core/constants/api_endpoints.dart
- **Backend Internal Callers**: None
- **Test Callers**: None
- **Doc References**: docs/API_INVENTORY.md, docs/PHASE_2_BASELINE.md, docs/api_inventory.json
- **Reviewer / Demo Usage**: `No`
- **Production Verified**: `LIVE VERIFIED`
- **Behavior Overlap**: `GET /api/v1/assistant/sessions (Both query ChatRepository farmer sessions)`
- **Classification**: **`DUPLICATE`**

### `GET /api/v1/chat/sessions/{session_id}`
- **Router File**: `backend/app/api/v1/chat.py` (`get_session`)
- **Service**: `BhoomiAgentOrchestrator`
- **Repository / Provider / Model**: `ChatRepository`
- **Frontend Web Callers**: None
- **Frontend Mobile (Flutter) Callers**: None
- **Backend Internal Callers**: None
- **Test Callers**: None
- **Doc References**: docs/API_INVENTORY.md, docs/api_inventory.json
- **Reviewer / Demo Usage**: `No`
- **Production Verified**: `LIVE VERIFIED`
- **Behavior Overlap**: `GET /api/v1/assistant/sessions/{session_id} (Both query ChatRepository session by id)`
- **Classification**: **`DUPLICATE`**

### `GET /api/v1/crop/lifecycle`
- **Router File**: `backend/app/api/v1/crop.py` (`get_lifecycle`)
- **Service**: `CropRecommendationService, CropLifecycleService`
- **Repository / Provider / Model**: `AgronomicKnowledgeBase`
- **Frontend Web Callers**: None
- **Frontend Mobile (Flutter) Callers**: None
- **Backend Internal Callers**: None
- **Test Callers**: None
- **Doc References**: docs/API_INVENTORY.md, docs/PHASE_2_BASELINE.md, docs/api_inventory.json
- **Reviewer / Demo Usage**: `No`
- **Production Verified**: `LIVE VERIFIED`
- **Behavior Overlap**: `None`
- **Classification**: **`UNUSED`**

### `POST /api/v1/crop/recommend`
- **Router File**: `backend/app/api/v1/crop.py` (`recommend_crop`)
- **Service**: `CropRecommendationService, CropLifecycleService`
- **Repository / Provider / Model**: `AgronomicKnowledgeBase`
- **Frontend Web Callers**: None
- **Frontend Mobile (Flutter) Callers**: None
- **Backend Internal Callers**: None
- **Test Callers**: None
- **Doc References**: docs/API_INVENTORY.md, docs/PHASE_2_BASELINE.md, docs/api_inventory.json
- **Reviewer / Demo Usage**: `No`
- **Production Verified**: `LIVE VERIFIED`
- **Behavior Overlap**: `POST /api/v1/ml/crop-recommendation (Legacy rule/heuristic crop recommender superseded by Phase 2 Random Forest ML model)`
- **Classification**: **`LEGACY`**

### `POST /api/v1/decisions/evaluate`
- **Router File**: `backend/app/api/v1/decision_routes.py` (`evaluate_farm_decisions`)
- **Service**: `DecisionTraceService, RecommendationTraceStore`
- **Repository / Provider / Model**: `SHAPExplainerService, TraceStore`
- **Frontend Web Callers**: None
- **Frontend Mobile (Flutter) Callers**: None
- **Backend Internal Callers**: None
- **Test Callers**: backend/tests/test_phase6_decision_intelligence.py
- **Doc References**: docs/API_INVENTORY.md, docs/PHASE_6_STEP_1_DECISION_INTELLIGENCE.md, docs/api_inventory.json
- **Reviewer / Demo Usage**: `No`
- **Production Verified**: `LIVE VERIFIED`
- **Behavior Overlap**: `None`
- **Classification**: **`CANONICAL`**

### `GET /api/v1/demo/profile`
- **Router File**: `backend/app/api/v1/demo.py` (`get_demo_profile`)
- **Service**: `DemoModeService`
- **Repository / Provider / Model**: `CanonicalDemoStore, DemoTaskStore`
- **Frontend Web Callers**: None
- **Frontend Mobile (Flutter) Callers**: None
- **Backend Internal Callers**: None
- **Test Callers**: backend/tests/test_demo_scenarios.py
- **Doc References**: docs/API_INVENTORY.md, docs/api_inventory.json
- **Reviewer / Demo Usage**: `Yes`
- **Production Verified**: `LIVE VERIFIED`
- **Behavior Overlap**: `None`
- **Classification**: **`DEMO_ONLY`**

### `POST /api/v1/demo/reset`
- **Router File**: `backend/app/api/v1/demo.py` (`reset_demo_state`)
- **Service**: `DemoModeService`
- **Repository / Provider / Model**: `CanonicalDemoStore, DemoTaskStore`
- **Frontend Web Callers**: None
- **Frontend Mobile (Flutter) Callers**: None
- **Backend Internal Callers**: None
- **Test Callers**: backend/tests/test_demo_scenarios.py, test_live_http_api.py
- **Doc References**: docs/API_INVENTORY.md, docs/api_inventory.json
- **Reviewer / Demo Usage**: `Yes`
- **Production Verified**: `LIVE VERIFIED`
- **Behavior Overlap**: `None`
- **Classification**: **`DEMO_ONLY`**

### `GET /api/v1/demo/scenarios`
- **Router File**: `backend/app/api/v1/demo.py` (`list_demo_scenarios`)
- **Service**: `DemoModeService`
- **Repository / Provider / Model**: `CanonicalDemoStore, DemoTaskStore`
- **Frontend Web Callers**: None
- **Frontend Mobile (Flutter) Callers**: None
- **Backend Internal Callers**: None
- **Test Callers**: backend/tests/test_demo_scenarios.py
- **Doc References**: docs/API_INVENTORY.md, docs/api_inventory.json
- **Reviewer / Demo Usage**: `Yes`
- **Production Verified**: `LIVE VERIFIED`
- **Behavior Overlap**: `None`
- **Classification**: **`DEMO_ONLY`**

### `POST /api/v1/demo/scenarios/{scenario_id}/execute`
- **Router File**: `backend/app/api/v1/demo.py` (`execute_demo_scenario`)
- **Service**: `DemoModeService`
- **Repository / Provider / Model**: `CanonicalDemoStore, DemoTaskStore`
- **Frontend Web Callers**: None
- **Frontend Mobile (Flutter) Callers**: None
- **Backend Internal Callers**: None
- **Test Callers**: backend/tests/test_demo_scenarios.py
- **Doc References**: docs/API_INVENTORY.md, docs/api_inventory.json
- **Reviewer / Demo Usage**: `Yes`
- **Production Verified**: `LIVE VERIFIED`
- **Behavior Overlap**: `None`
- **Classification**: **`DEMO_ONLY`**

### `POST /api/v1/farm/compare-crops`
- **Router File**: `backend/app/api/v1/farm_routes.py` (`compare_crops`)
- **Service**: `DigitalTwinService, CropComparisonService`
- **Repository / Provider / Model**: `FarmRepository, Farm, Crop`
- **Frontend Web Callers**: None
- **Frontend Mobile (Flutter) Callers**: frontend/mobile/lib/core/constants/api_endpoints.dart
- **Backend Internal Callers**: None
- **Test Callers**: None
- **Doc References**: docs/API_INVENTORY.md, docs/api_inventory.json
- **Reviewer / Demo Usage**: `No`
- **Production Verified**: `LIVE VERIFIED`
- **Behavior Overlap**: `None`
- **Classification**: **`CANONICAL`**

### `GET /api/v1/farm/crops`
- **Router File**: `backend/app/api/v1/farm_routes.py` (`get_farm_crops`)
- **Service**: `DigitalTwinService, CropComparisonService`
- **Repository / Provider / Model**: `FarmRepository, Farm, Crop`
- **Frontend Web Callers**: None
- **Frontend Mobile (Flutter) Callers**: frontend/mobile/lib/core/constants/api_endpoints.dart
- **Backend Internal Callers**: None
- **Test Callers**: None
- **Doc References**: docs/API_INVENTORY.md, docs/api_inventory.json
- **Reviewer / Demo Usage**: `No`
- **Production Verified**: `LIVE VERIFIED`
- **Behavior Overlap**: `GET /api/v1/farms (Overlaps farm digital twin crop retrieval in /farms)`
- **Classification**: **`CANONICAL`**

### `GET /api/v1/farm/summary`
- **Router File**: `backend/app/api/v1/farm_routes.py` (`get_farm_summary`)
- **Service**: `DigitalTwinService, CropComparisonService`
- **Repository / Provider / Model**: `FarmRepository, Farm, Crop`
- **Frontend Web Callers**: None
- **Frontend Mobile (Flutter) Callers**: frontend/mobile/lib/core/constants/api_endpoints.dart
- **Backend Internal Callers**: None
- **Test Callers**: None
- **Doc References**: docs/API_INVENTORY.md, docs/api_inventory.json
- **Reviewer / Demo Usage**: `No`
- **Production Verified**: `LIVE VERIFIED`
- **Behavior Overlap**: `GET /api/v1/farms/{farm_id} & /api/v1/manager/state (Digital twin aggregation overlaps manager state)`
- **Classification**: **`CANONICAL`**

### `GET /api/v1/farm/tasks`
- **Router File**: `backend/app/api/v1/farm_routes.py` (`get_farm_tasks`)
- **Service**: `DigitalTwinService, CropComparisonService`
- **Repository / Provider / Model**: `FarmRepository, Farm, Crop`
- **Frontend Web Callers**: None
- **Frontend Mobile (Flutter) Callers**: None
- **Backend Internal Callers**: None
- **Test Callers**: None
- **Doc References**: docs/API_INVENTORY.md, docs/api_inventory.json
- **Reviewer / Demo Usage**: `No`
- **Production Verified**: `LIVE VERIFIED`
- **Behavior Overlap**: `GET /api/v1/tasks/today & /api/v1/tasks/week (Overlaps canonical task endpoints)`
- **Classification**: **`UNUSED`**

### `GET /api/v1/farmer`
- **Router File**: `backend/app/api/v1/farmer.py` (`get_profile`)
- **Service**: `FarmerProfileService`
- **Repository / Provider / Model**: `FarmerProfile`
- **Frontend Web Callers**: frontend/web/static/app.js
- **Frontend Mobile (Flutter) Callers**: frontend/mobile/lib/core/constants/api_endpoints.dart
- **Backend Internal Callers**: None
- **Test Callers**: None
- **Doc References**: docs/API_INVENTORY.md, docs/PHASE_2_BASELINE.md, docs/api.md, docs/api_inventory.json
- **Reviewer / Demo Usage**: `No`
- **Production Verified**: `LIVE VERIFIED`
- **Behavior Overlap**: `None`
- **Classification**: **`CANONICAL`**

### `PUT /api/v1/farmer`
- **Router File**: `backend/app/api/v1/farmer.py` (`update_profile`)
- **Service**: `FarmerProfileService`
- **Repository / Provider / Model**: `FarmerProfile`
- **Frontend Web Callers**: frontend/web/static/app.js
- **Frontend Mobile (Flutter) Callers**: frontend/mobile/lib/core/constants/api_endpoints.dart
- **Backend Internal Callers**: None
- **Test Callers**: None
- **Doc References**: docs/API_INVENTORY.md, docs/PHASE_2_BASELINE.md, docs/api.md, docs/api_inventory.json
- **Reviewer / Demo Usage**: `No`
- **Production Verified**: `LIVE VERIFIED`
- **Behavior Overlap**: `None`
- **Classification**: **`CANONICAL`**

### `GET /api/v1/farms`
- **Router File**: `backend/app/api/v1/farms.py` (`list_farms`)
- **Service**: `FarmDigitalTwinService, SoilEstimateService`
- **Repository / Provider / Model**: `FarmRepository, Farm, Crop, SoilService (ICAR-NBSS&LUP)`
- **Frontend Web Callers**: frontend/web/static/app.js
- **Frontend Mobile (Flutter) Callers**: frontend/mobile/lib/core/constants/api_endpoints.dart
- **Backend Internal Callers**: backend/app/services/vision/field_validation/acceptance_gate.py
- **Test Callers**: None
- **Doc References**: data/evaluation/public_smoke_test_evidence.json, docs/API_INVENTORY.md, docs/PHASE_2_BASELINE.md, docs/api.md, docs/api_inventory.json
- **Reviewer / Demo Usage**: `No`
- **Production Verified**: `LIVE VERIFIED`
- **Behavior Overlap**: `None`
- **Classification**: **`CANONICAL`**

### `POST /api/v1/farms`
- **Router File**: `backend/app/api/v1/farms.py` (`create_farm`)
- **Service**: `FarmDigitalTwinService, SoilEstimateService`
- **Repository / Provider / Model**: `FarmRepository, Farm, Crop, SoilService (ICAR-NBSS&LUP)`
- **Frontend Web Callers**: frontend/web/static/app.js
- **Frontend Mobile (Flutter) Callers**: frontend/mobile/lib/core/constants/api_endpoints.dart
- **Backend Internal Callers**: backend/app/services/vision/field_validation/acceptance_gate.py
- **Test Callers**: None
- **Doc References**: data/evaluation/public_smoke_test_evidence.json, docs/API_INVENTORY.md, docs/PHASE_2_BASELINE.md, docs/api.md, docs/api_inventory.json
- **Reviewer / Demo Usage**: `No`
- **Production Verified**: `LIVE VERIFIED`
- **Behavior Overlap**: `None`
- **Classification**: **`CANONICAL`**

### `GET /api/v1/farms/soil-estimate`
- **Router File**: `backend/app/api/v1/farms.py` (`get_location_soil_estimate`)
- **Service**: `FarmDigitalTwinService, SoilEstimateService`
- **Repository / Provider / Model**: `FarmRepository, Farm, Crop, SoilService (ICAR-NBSS&LUP)`
- **Frontend Web Callers**: frontend/web/static/app.js
- **Frontend Mobile (Flutter) Callers**: None
- **Backend Internal Callers**: None
- **Test Callers**: None
- **Doc References**: docs/API_INVENTORY.md, docs/api_inventory.json
- **Reviewer / Demo Usage**: `No`
- **Production Verified**: `LIVE VERIFIED`
- **Behavior Overlap**: `None`
- **Classification**: **`CANONICAL`**

### `GET /api/v1/farms/{farm_id}`
- **Router File**: `backend/app/api/v1/farms.py` (`get_farm`)
- **Service**: `FarmDigitalTwinService, SoilEstimateService`
- **Repository / Provider / Model**: `FarmRepository, Farm, Crop, SoilService (ICAR-NBSS&LUP)`
- **Frontend Web Callers**: frontend/web/static/app.js
- **Frontend Mobile (Flutter) Callers**: None
- **Backend Internal Callers**: None
- **Test Callers**: None
- **Doc References**: docs/API_INVENTORY.md, docs/api_inventory.json
- **Reviewer / Demo Usage**: `No`
- **Production Verified**: `LIVE VERIFIED`
- **Behavior Overlap**: `None`
- **Classification**: **`CANONICAL`**

### `POST /api/v1/farms/{farm_id}/crops`
- **Router File**: `backend/app/api/v1/farms.py` (`add_crop_to_farm`)
- **Service**: `FarmDigitalTwinService, SoilEstimateService`
- **Repository / Provider / Model**: `FarmRepository, Farm, Crop, SoilService (ICAR-NBSS&LUP)`
- **Frontend Web Callers**: None
- **Frontend Mobile (Flutter) Callers**: None
- **Backend Internal Callers**: None
- **Test Callers**: None
- **Doc References**: docs/API_INVENTORY.md, docs/api_inventory.json
- **Reviewer / Demo Usage**: `No`
- **Production Verified**: `LIVE VERIFIED`
- **Behavior Overlap**: `None`
- **Classification**: **`UNUSED`**

### `POST /api/v1/image/analyze`
- **Router File**: `backend/app/api/v1/image.py` (`analyze_crop_image`)
- **Service**: `VisionService`
- **Repository / Provider / Model**: `PlantPathologyCNN, TorchVision`
- **Frontend Web Callers**: None
- **Frontend Mobile (Flutter) Callers**: frontend/mobile/lib/core/constants/api_endpoints.dart
- **Backend Internal Callers**: None
- **Test Callers**: None
- **Doc References**: docs/API_INVENTORY.md, docs/PHASE_2_BASELINE.md, docs/api.md, docs/api_inventory.json
- **Reviewer / Demo Usage**: `No`
- **Production Verified**: `LIVE VERIFIED`
- **Behavior Overlap**: `POST /api/v1/vision/analyze (Legacy single-endpoint image analysis superseded by canonical modular vision pipeline /vision/analyze)`
- **Classification**: **`LEGACY`**

### `GET /api/v1/manager/alerts`
- **Router File**: `backend/app/api/v1/farm_manager_routes.py` (`get_proactive_alerts`)
- **Service**: `FarmStateEngine, DailyFarmBriefingService, FarmChangeDetectionService`
- **Repository / Provider / Model**: `ProactiveAlertEngine, FarmTimelineService, SeasonalPlannerService`
- **Frontend Web Callers**: None
- **Frontend Mobile (Flutter) Callers**: frontend/mobile/lib/core/constants/api_endpoints.dart
- **Backend Internal Callers**: None
- **Test Callers**: None
- **Doc References**: docs/API_INVENTORY.md, docs/api_inventory.json
- **Reviewer / Demo Usage**: `No`
- **Production Verified**: `LIVE VERIFIED`
- **Behavior Overlap**: `None`
- **Classification**: **`CANONICAL`**

### `GET /api/v1/manager/briefing/today`
- **Router File**: `backend/app/api/v1/farm_manager_routes.py` (`get_today_briefing`)
- **Service**: `FarmStateEngine, DailyFarmBriefingService, FarmChangeDetectionService`
- **Repository / Provider / Model**: `ProactiveAlertEngine, FarmTimelineService, SeasonalPlannerService`
- **Frontend Web Callers**: None
- **Frontend Mobile (Flutter) Callers**: frontend/mobile/lib/core/constants/api_endpoints.dart
- **Backend Internal Callers**: None
- **Test Callers**: None
- **Doc References**: docs/API_INVENTORY.md, docs/api_inventory.json
- **Reviewer / Demo Usage**: `No`
- **Production Verified**: `LIVE VERIFIED`
- **Behavior Overlap**: `None`
- **Classification**: **`CANONICAL`**

### `GET /api/v1/manager/briefing/week`
- **Router File**: `backend/app/api/v1/farm_manager_routes.py` (`get_week_briefing`)
- **Service**: `FarmStateEngine, DailyFarmBriefingService, FarmChangeDetectionService`
- **Repository / Provider / Model**: `ProactiveAlertEngine, FarmTimelineService, SeasonalPlannerService`
- **Frontend Web Callers**: None
- **Frontend Mobile (Flutter) Callers**: frontend/mobile/lib/core/constants/api_endpoints.dart
- **Backend Internal Callers**: None
- **Test Callers**: None
- **Doc References**: docs/API_INVENTORY.md, docs/api_inventory.json
- **Reviewer / Demo Usage**: `No`
- **Production Verified**: `LIVE VERIFIED`
- **Behavior Overlap**: `None`
- **Classification**: **`CANONICAL`**

### `GET /api/v1/manager/changes`
- **Router File**: `backend/app/api/v1/farm_manager_routes.py` (`get_farm_changes`)
- **Service**: `FarmStateEngine, DailyFarmBriefingService, FarmChangeDetectionService`
- **Repository / Provider / Model**: `ProactiveAlertEngine, FarmTimelineService, SeasonalPlannerService`
- **Frontend Web Callers**: None
- **Frontend Mobile (Flutter) Callers**: frontend/mobile/lib/core/constants/api_endpoints.dart
- **Backend Internal Callers**: None
- **Test Callers**: None
- **Doc References**: docs/API_INVENTORY.md, docs/api_inventory.json
- **Reviewer / Demo Usage**: `No`
- **Production Verified**: `LIVE VERIFIED`
- **Behavior Overlap**: `None`
- **Classification**: **`CANONICAL`**

### `POST /api/v1/manager/events`
- **Router File**: `backend/app/api/v1/farm_manager_routes.py` (`record_farm_event`)
- **Service**: `FarmStateEngine, DailyFarmBriefingService, FarmChangeDetectionService`
- **Repository / Provider / Model**: `ProactiveAlertEngine, FarmTimelineService, SeasonalPlannerService`
- **Frontend Web Callers**: None
- **Frontend Mobile (Flutter) Callers**: frontend/mobile/lib/core/constants/api_endpoints.dart
- **Backend Internal Callers**: None
- **Test Callers**: None
- **Doc References**: docs/API_INVENTORY.md, docs/api_inventory.json
- **Reviewer / Demo Usage**: `No`
- **Production Verified**: `LIVE VERIFIED`
- **Behavior Overlap**: `None`
- **Classification**: **`CANONICAL`**

### `POST /api/v1/manager/feedback`
- **Router File**: `backend/app/api/v1/farm_manager_routes.py` (`submit_recommendation_feedback`)
- **Service**: `FarmStateEngine, DailyFarmBriefingService, FarmChangeDetectionService`
- **Repository / Provider / Model**: `ProactiveAlertEngine, FarmTimelineService, SeasonalPlannerService`
- **Frontend Web Callers**: None
- **Frontend Mobile (Flutter) Callers**: None
- **Backend Internal Callers**: None
- **Test Callers**: backend/tests/test_assistant_feedback.py
- **Doc References**: docs/API_INVENTORY.md, docs/api_inventory.json
- **Reviewer / Demo Usage**: `No`
- **Production Verified**: `LIVE VERIFIED`
- **Behavior Overlap**: `None`
- **Classification**: **`CANONICAL`**

### `GET /api/v1/manager/plan`
- **Router File**: `backend/app/api/v1/farm_manager_routes.py` (`get_current_farm_plan`)
- **Service**: `FarmStateEngine, DailyFarmBriefingService, FarmChangeDetectionService`
- **Repository / Provider / Model**: `ProactiveAlertEngine, FarmTimelineService, SeasonalPlannerService`
- **Frontend Web Callers**: None
- **Frontend Mobile (Flutter) Callers**: frontend/mobile/lib/core/constants/api_endpoints.dart
- **Backend Internal Callers**: None
- **Test Callers**: None
- **Doc References**: docs/API_INVENTORY.md, docs/api_inventory.json
- **Reviewer / Demo Usage**: `No`
- **Production Verified**: `LIVE VERIFIED`
- **Behavior Overlap**: `None`
- **Classification**: **`CANONICAL`**

### `GET /api/v1/manager/state`
- **Router File**: `backend/app/api/v1/farm_manager_routes.py` (`get_farm_state`)
- **Service**: `FarmStateEngine, DailyFarmBriefingService, FarmChangeDetectionService`
- **Repository / Provider / Model**: `ProactiveAlertEngine, FarmTimelineService, SeasonalPlannerService`
- **Frontend Web Callers**: None
- **Frontend Mobile (Flutter) Callers**: frontend/mobile/lib/core/constants/api_endpoints.dart
- **Backend Internal Callers**: None
- **Test Callers**: None
- **Doc References**: docs/API_INVENTORY.md, docs/api_inventory.json
- **Reviewer / Demo Usage**: `No`
- **Production Verified**: `LIVE VERIFIED`
- **Behavior Overlap**: `None`
- **Classification**: **`CANONICAL`**

### `GET /api/v1/manager/timeline`
- **Router File**: `backend/app/api/v1/farm_manager_routes.py` (`get_crop_health_timeline`)
- **Service**: `FarmStateEngine, DailyFarmBriefingService, FarmChangeDetectionService`
- **Repository / Provider / Model**: `ProactiveAlertEngine, FarmTimelineService, SeasonalPlannerService`
- **Frontend Web Callers**: None
- **Frontend Mobile (Flutter) Callers**: frontend/mobile/lib/core/constants/api_endpoints.dart
- **Backend Internal Callers**: None
- **Test Callers**: None
- **Doc References**: docs/API_INVENTORY.md, docs/api_inventory.json
- **Reviewer / Demo Usage**: `No`
- **Production Verified**: `LIVE VERIFIED`
- **Behavior Overlap**: `None`
- **Classification**: **`CANONICAL`**

### `GET /api/v1/market`
- **Router File**: `backend/app/api/v1/market.py` (`get_market_analysis`)
- **Service**: `MarketService`
- **Repository / Provider / Model**: `AgmarknetProvider, DataGovInProvider`
- **Frontend Web Callers**: None
- **Frontend Mobile (Flutter) Callers**: frontend/mobile/lib/core/constants/api_endpoints.dart, frontend/mobile/lib/features/chat/chat_screen.dart, frontend/mobile/lib/features/home/home_screen.dart, frontend/mobile/lib/features/voice/voice_assistant_screen.dart, frontend/mobile/lib/routing/app_router.dart, frontend/mobile/test/widget_test.dart
- **Backend Internal Callers**: backend/app/services/conversation/dialogue_manager.py
- **Test Callers**: scratch_test_endpoints.py, test_live_http_api.py
- **Doc References**: data/evaluation/public_smoke_test_evidence.json, docs/API_INVENTORY.md, docs/PHASE_2_BASELINE.md, docs/PHASE_4_REAL_MARKET.md, docs/PHASE_6_STEP_2_CROP_LIFECYCLE_TASK_ENGINE.md, docs/api.md, docs/api_inventory.json
- **Reviewer / Demo Usage**: `No`
- **Production Verified**: `LIVE VERIFIED`
- **Behavior Overlap**: `None`
- **Classification**: **`CANONICAL`**

### `POST /api/v1/ml/crop-recommendation`
- **Router File**: `backend/app/api/v1/ml.py` (`recommend_crop`)
- **Service**: `MLInferenceService`
- **Repository / Provider / Model**: `RandomForestCropModel (Macro-F1: 0.9955), XGBoostYieldModel (R2: 0.9574), CIBRC SafetyEngine`
- **Frontend Web Callers**: None
- **Frontend Mobile (Flutter) Callers**: frontend/mobile/lib/core/constants/api_endpoints.dart
- **Backend Internal Callers**: None
- **Test Callers**: None
- **Doc References**: docs/API_INVENTORY.md, docs/PHASE_3_BASELINE.md, docs/api_inventory.json
- **Reviewer / Demo Usage**: `No`
- **Production Verified**: `LIVE VERIFIED`
- **Behavior Overlap**: `POST /api/v1/crop/recommend (Canonical Phase 2 ML model supersedes legacy /crop/recommend)`
- **Classification**: **`CANONICAL`**

### `POST /api/v1/ml/fertilizer-recommendation`
- **Router File**: `backend/app/api/v1/ml.py` (`recommend_fertilizer`)
- **Service**: `MLInferenceService`
- **Repository / Provider / Model**: `RandomForestCropModel (Macro-F1: 0.9955), XGBoostYieldModel (R2: 0.9574), CIBRC SafetyEngine`
- **Frontend Web Callers**: None
- **Frontend Mobile (Flutter) Callers**: frontend/mobile/lib/core/constants/api_endpoints.dart
- **Backend Internal Callers**: None
- **Test Callers**: None
- **Doc References**: docs/API_INVENTORY.md, docs/PHASE_3_BASELINE.md, docs/api_inventory.json
- **Reviewer / Demo Usage**: `No`
- **Production Verified**: `LIVE VERIFIED`
- **Behavior Overlap**: `None`
- **Classification**: **`CANONICAL`**

### `POST /api/v1/ml/yield-prediction`
- **Router File**: `backend/app/api/v1/ml.py` (`predict_yield`)
- **Service**: `MLInferenceService`
- **Repository / Provider / Model**: `RandomForestCropModel (Macro-F1: 0.9955), XGBoostYieldModel (R2: 0.9574), CIBRC SafetyEngine`
- **Frontend Web Callers**: None
- **Frontend Mobile (Flutter) Callers**: frontend/mobile/lib/core/constants/api_endpoints.dart
- **Backend Internal Callers**: None
- **Test Callers**: None
- **Doc References**: docs/API_INVENTORY.md, docs/PHASE_3_BASELINE.md, docs/api_inventory.json
- **Reviewer / Demo Usage**: `No`
- **Production Verified**: `LIVE VERIFIED`
- **Behavior Overlap**: `POST /api/v1/yield/predict (Canonical Phase 2 ML model supersedes legacy /yield/predict)`
- **Classification**: **`CANONICAL`**

### `GET /api/v1/pilot/acceptance`
- **Router File**: `backend/app/api/v1/pilot.py` (`get_pilot_acceptance_gate`)
- **Service**: `PilotTelemetryService`
- **Repository / Provider / Model**: `FieldValidationStore, TelemetryStore`
- **Frontend Web Callers**: None
- **Frontend Mobile (Flutter) Callers**: None
- **Backend Internal Callers**: None
- **Test Callers**: backend/tests/test_phase6_pilot_audit.py
- **Doc References**: docs/API_INVENTORY.md, docs/PHASE_6_STEP_4_FIELD_PILOT_AUDIT_PIPELINE.md, docs/api_inventory.json
- **Reviewer / Demo Usage**: `Yes`
- **Production Verified**: `LIVE VERIFIED`
- **Behavior Overlap**: `None`
- **Classification**: **`DEMO_ONLY`**

### `GET /api/v1/pilot/crops/{crop}`
- **Router File**: `backend/app/api/v1/pilot.py` (`get_crop_pilot_status`)
- **Service**: `PilotTelemetryService`
- **Repository / Provider / Model**: `FieldValidationStore, TelemetryStore`
- **Frontend Web Callers**: None
- **Frontend Mobile (Flutter) Callers**: None
- **Backend Internal Callers**: None
- **Test Callers**: backend/tests/test_phase6_pilot_audit.py
- **Doc References**: docs/API_INVENTORY.md, docs/PHASE_6_STEP_4_FIELD_PILOT_AUDIT_PIPELINE.md, docs/api_inventory.json
- **Reviewer / Demo Usage**: `Yes`
- **Production Verified**: `LIVE VERIFIED`
- **Behavior Overlap**: `None`
- **Classification**: **`DEMO_ONLY`**

### `GET /api/v1/pilot/drift`
- **Router File**: `backend/app/api/v1/pilot.py` (`get_pilot_drift_report`)
- **Service**: `PilotTelemetryService`
- **Repository / Provider / Model**: `FieldValidationStore, TelemetryStore`
- **Frontend Web Callers**: None
- **Frontend Mobile (Flutter) Callers**: None
- **Backend Internal Callers**: None
- **Test Callers**: None
- **Doc References**: docs/API_INVENTORY.md, docs/PHASE_6_STEP_4_FIELD_PILOT_AUDIT_PIPELINE.md, docs/api_inventory.json
- **Reviewer / Demo Usage**: `Yes`
- **Production Verified**: `LIVE VERIFIED`
- **Behavior Overlap**: `None`
- **Classification**: **`DEMO_ONLY`**

### `POST /api/v1/pilot/import`
- **Router File**: `backend/app/api/v1/pilot.py` (`import_pilot_record`)
- **Service**: `PilotTelemetryService`
- **Repository / Provider / Model**: `FieldValidationStore, TelemetryStore`
- **Frontend Web Callers**: None
- **Frontend Mobile (Flutter) Callers**: None
- **Backend Internal Callers**: None
- **Test Callers**: None
- **Doc References**: docs/API_INVENTORY.md, docs/PHASE_6_STEP_4_FIELD_PILOT_AUDIT_PIPELINE.md, docs/api_inventory.json
- **Reviewer / Demo Usage**: `Yes`
- **Production Verified**: `LIVE VERIFIED`
- **Behavior Overlap**: `None`
- **Classification**: **`DEMO_ONLY`**

### `GET /api/v1/pilot/metrics`
- **Router File**: `backend/app/api/v1/pilot.py` (`get_pilot_vision_metrics`)
- **Service**: `PilotTelemetryService`
- **Repository / Provider / Model**: `FieldValidationStore, TelemetryStore`
- **Frontend Web Callers**: None
- **Frontend Mobile (Flutter) Callers**: None
- **Backend Internal Callers**: None
- **Test Callers**: None
- **Doc References**: docs/API_INVENTORY.md, docs/PHASE_6_STEP_4_FIELD_PILOT_AUDIT_PIPELINE.md, docs/api_inventory.json
- **Reviewer / Demo Usage**: `Yes`
- **Production Verified**: `LIVE VERIFIED`
- **Behavior Overlap**: `None`
- **Classification**: **`DEMO_ONLY`**

### `GET /api/v1/pilot/status`
- **Router File**: `backend/app/api/v1/pilot.py` (`get_pilot_status`)
- **Service**: `PilotTelemetryService`
- **Repository / Provider / Model**: `FieldValidationStore, TelemetryStore`
- **Frontend Web Callers**: None
- **Frontend Mobile (Flutter) Callers**: None
- **Backend Internal Callers**: None
- **Test Callers**: backend/tests/test_phase6_pilot_audit.py
- **Doc References**: docs/API_INVENTORY.md, docs/PHASE_6_STEP_4_FIELD_PILOT_AUDIT_PIPELINE.md, docs/api_inventory.json
- **Reviewer / Demo Usage**: `Yes`
- **Production Verified**: `LIVE VERIFIED`
- **Behavior Overlap**: `None`
- **Classification**: **`DEMO_ONLY`**

### `GET /api/v1/pilot/task-metrics`
- **Router File**: `backend/app/api/v1/pilot.py` (`get_pilot_task_metrics`)
- **Service**: `PilotTelemetryService`
- **Repository / Provider / Model**: `FieldValidationStore, TelemetryStore`
- **Frontend Web Callers**: None
- **Frontend Mobile (Flutter) Callers**: None
- **Backend Internal Callers**: None
- **Test Callers**: None
- **Doc References**: docs/API_INVENTORY.md, docs/PHASE_6_STEP_4_FIELD_PILOT_AUDIT_PIPELINE.md, docs/api_inventory.json
- **Reviewer / Demo Usage**: `Yes`
- **Production Verified**: `LIVE VERIFIED`
- **Behavior Overlap**: `None`
- **Classification**: **`DEMO_ONLY`**

### `GET /api/v1/pilot/voice-metrics`
- **Router File**: `backend/app/api/v1/pilot.py` (`get_pilot_voice_metrics`)
- **Service**: `PilotTelemetryService`
- **Repository / Provider / Model**: `FieldValidationStore, TelemetryStore`
- **Frontend Web Callers**: None
- **Frontend Mobile (Flutter) Callers**: None
- **Backend Internal Callers**: None
- **Test Callers**: None
- **Doc References**: docs/API_INVENTORY.md, docs/PHASE_6_STEP_4_FIELD_PILOT_AUDIT_PIPELINE.md, docs/api_inventory.json
- **Reviewer / Demo Usage**: `Yes`
- **Production Verified**: `LIVE VERIFIED`
- **Behavior Overlap**: `None`
- **Classification**: **`DEMO_ONLY`**

### `POST /api/v1/profit/calculate`
- **Router File**: `backend/app/api/v1/profit.py` (`calculate_profit`)
- **Service**: `ProfitService`
- **Repository / Provider / Model**: `DeterministicArithmetic (Decimal)`
- **Frontend Web Callers**: frontend/web/static/app.js
- **Frontend Mobile (Flutter) Callers**: frontend/mobile/lib/core/constants/api_endpoints.dart
- **Backend Internal Callers**: None
- **Test Callers**: None
- **Doc References**: data/evaluation/public_smoke_test_evidence.json, docs/API_INVENTORY.md, docs/PHASE_2_BASELINE.md, docs/api.md, docs/api_inventory.json
- **Reviewer / Demo Usage**: `No`
- **Production Verified**: `LIVE VERIFIED`
- **Behavior Overlap**: `None`
- **Classification**: **`CANONICAL`**

### `POST /api/v1/rag/debug`
- **Router File**: `backend/app/api/v1/rag_routes.py` (`debug_agricultural_evidence`)
- **Service**: `AgriculturalRAGService`
- **Repository / Provider / Model**: `VectorStore, TF-IDF/BM25 Retriever, ICAR & SAU Documents`
- **Frontend Web Callers**: None
- **Frontend Mobile (Flutter) Callers**: None
- **Backend Internal Callers**: None
- **Test Callers**: None
- **Doc References**: docs/API_INVENTORY.md, docs/api_inventory.json
- **Reviewer / Demo Usage**: `No`
- **Production Verified**: `LIVE VERIFIED`
- **Behavior Overlap**: `None`
- **Classification**: **`INTERNAL`**

### `POST /api/v1/rag/search`
- **Router File**: `backend/app/api/v1/rag_routes.py` (`search_agricultural_evidence`)
- **Service**: `AgriculturalRAGService`
- **Repository / Provider / Model**: `VectorStore, TF-IDF/BM25 Retriever, ICAR & SAU Documents`
- **Frontend Web Callers**: None
- **Frontend Mobile (Flutter) Callers**: frontend/mobile/lib/core/constants/api_endpoints.dart
- **Backend Internal Callers**: None
- **Test Callers**: None
- **Doc References**: docs/API_INVENTORY.md, docs/PHASE_3_BASELINE.md, docs/api_inventory.json
- **Reviewer / Demo Usage**: `No`
- **Production Verified**: `LIVE VERIFIED`
- **Behavior Overlap**: `None`
- **Classification**: **`CANONICAL`**

### `POST /api/v1/risk/assess`
- **Router File**: `backend/app/api/v1/risk.py` (`assess_risk`)
- **Service**: `RiskAssessmentService`
- **Repository / Provider / Model**: `MultidimensionalRiskEngine`
- **Frontend Web Callers**: None
- **Frontend Mobile (Flutter) Callers**: frontend/mobile/lib/core/constants/api_endpoints.dart
- **Backend Internal Callers**: None
- **Test Callers**: None
- **Doc References**: docs/API_INVENTORY.md, docs/PHASE_2_BASELINE.md, docs/api.md, docs/api_inventory.json
- **Reviewer / Demo Usage**: `No`
- **Production Verified**: `LIVE VERIFIED`
- **Behavior Overlap**: `None`
- **Classification**: **`CANONICAL`**

### `POST /api/v1/simulation/run`
- **Router File**: `backend/app/api/v1/simulation.py` (`run_simulation`)
- **Service**: `SimulationService`
- **Repository / Provider / Model**: `MultiLeverSimulationEngine, Decimal`
- **Frontend Web Callers**: None
- **Frontend Mobile (Flutter) Callers**: None
- **Backend Internal Callers**: None
- **Test Callers**: backend/tests/test_simulation_equivalence.py
- **Doc References**: docs/API_INVENTORY.md, docs/PHASE_2_BASELINE.md, docs/api.md, docs/api_inventory.json
- **Reviewer / Demo Usage**: `No`
- **Production Verified**: `LIVE VERIFIED`
- **Behavior Overlap**: `POST /api/v1/simulation/what-if (Exact duplicate handler & schema)`
- **Classification**: **`DUPLICATE`**

### `POST /api/v1/simulation/what-if`
- **Router File**: `backend/app/api/v1/simulation.py` (`run_simulation`)
- **Service**: `SimulationService`
- **Repository / Provider / Model**: `MultiLeverSimulationEngine, Decimal`
- **Frontend Web Callers**: frontend/web/static/app.js
- **Frontend Mobile (Flutter) Callers**: frontend/mobile/lib/core/constants/api_endpoints.dart, frontend/mobile/test/api_endpoints_test.dart
- **Backend Internal Callers**: None
- **Test Callers**: backend/tests/test_simulation_equivalence.py
- **Doc References**: data/evaluation/public_smoke_test_evidence.json, docs/API_INVENTORY.md, docs/api_inventory.json
- **Reviewer / Demo Usage**: `No`
- **Production Verified**: `LIVE VERIFIED`
- **Behavior Overlap**: `POST /api/v1/simulation/run (Exact duplicate handler & schema)`
- **Classification**: **`CANONICAL`**

### `GET /api/v1/tasks`
- **Router File**: `backend/app/api/v1/tasks.py` (`get_tasks`)
- **Service**: `TaskIntelligenceEngine`
- **Repository / Provider / Model**: `TaskRepository, FarmTask, FarmMemoryV2`
- **Frontend Web Callers**: None
- **Frontend Mobile (Flutter) Callers**: frontend/mobile/lib/core/constants/api_endpoints.dart, frontend/mobile/lib/routing/app_router.dart, frontend/mobile/test/widget_test.dart
- **Backend Internal Callers**: backend/app/api/v1/farm_routes.py
- **Test Callers**: backend/tests/test_phase6_task_engine.py, backend/tests/test_task_authorization.py, test_live_http_api.py
- **Doc References**: docs/API_INVENTORY.md, docs/PHASE_2_BASELINE.md, docs/PHASE_3_BASELINE.md, docs/PHASE_6_STEP_2_CROP_LIFECYCLE_TASK_ENGINE.md, docs/api.md, docs/api_inventory.json
- **Reviewer / Demo Usage**: `No`
- **Production Verified**: `LIVE VERIFIED`
- **Behavior Overlap**: `None`
- **Classification**: **`CANONICAL`**

### `POST /api/v1/tasks`
- **Router File**: `backend/app/api/v1/tasks.py` (`create_task`)
- **Service**: `TaskIntelligenceEngine`
- **Repository / Provider / Model**: `TaskRepository, FarmTask, FarmMemoryV2`
- **Frontend Web Callers**: None
- **Frontend Mobile (Flutter) Callers**: frontend/mobile/lib/core/constants/api_endpoints.dart, frontend/mobile/lib/routing/app_router.dart, frontend/mobile/test/widget_test.dart
- **Backend Internal Callers**: backend/app/api/v1/farm_routes.py
- **Test Callers**: backend/tests/test_phase6_task_engine.py, backend/tests/test_task_authorization.py, test_live_http_api.py
- **Doc References**: docs/API_INVENTORY.md, docs/PHASE_2_BASELINE.md, docs/PHASE_3_BASELINE.md, docs/PHASE_6_STEP_2_CROP_LIFECYCLE_TASK_ENGINE.md, docs/api.md, docs/api_inventory.json
- **Reviewer / Demo Usage**: `No`
- **Production Verified**: `LIVE VERIFIED`
- **Behavior Overlap**: `None`
- **Classification**: **`CANONICAL`**

### `GET /api/v1/tasks/today`
- **Router File**: `backend/app/api/v1/tasks.py` (`get_today_tasks`)
- **Service**: `TaskIntelligenceEngine`
- **Repository / Provider / Model**: `TaskRepository, FarmTask, FarmMemoryV2`
- **Frontend Web Callers**: None
- **Frontend Mobile (Flutter) Callers**: None
- **Backend Internal Callers**: None
- **Test Callers**: backend/tests/test_phase6_task_engine.py, backend/tests/test_task_authorization.py, test_live_http_api.py
- **Doc References**: docs/API_INVENTORY.md, docs/PHASE_6_STEP_2_CROP_LIFECYCLE_TASK_ENGINE.md, docs/api_inventory.json
- **Reviewer / Demo Usage**: `No`
- **Production Verified**: `LIVE VERIFIED`
- **Behavior Overlap**: `None`
- **Classification**: **`CANONICAL`**

### `GET /api/v1/tasks/week`
- **Router File**: `backend/app/api/v1/tasks.py` (`get_week_tasks`)
- **Service**: `TaskIntelligenceEngine`
- **Repository / Provider / Model**: `TaskRepository, FarmTask, FarmMemoryV2`
- **Frontend Web Callers**: None
- **Frontend Mobile (Flutter) Callers**: None
- **Backend Internal Callers**: None
- **Test Callers**: backend/tests/test_phase6_task_engine.py, backend/tests/test_task_authorization.py
- **Doc References**: docs/API_INVENTORY.md, docs/PHASE_6_STEP_2_CROP_LIFECYCLE_TASK_ENGINE.md, docs/api_inventory.json
- **Reviewer / Demo Usage**: `No`
- **Production Verified**: `LIVE VERIFIED`
- **Behavior Overlap**: `None`
- **Classification**: **`CANONICAL`**

### `PUT /api/v1/tasks/{task_id}`
- **Router File**: `backend/app/api/v1/tasks.py` (`update_task`)
- **Service**: `TaskIntelligenceEngine`
- **Repository / Provider / Model**: `TaskRepository, FarmTask, FarmMemoryV2`
- **Frontend Web Callers**: None
- **Frontend Mobile (Flutter) Callers**: frontend/mobile/lib/routing/app_router.dart, frontend/mobile/test/widget_test.dart
- **Backend Internal Callers**: None
- **Test Callers**: backend/tests/test_phase6_task_engine.py, backend/tests/test_task_authorization.py, test_live_http_api.py
- **Doc References**: docs/API_INVENTORY.md, docs/PHASE_3_BASELINE.md, docs/PHASE_6_STEP_2_CROP_LIFECYCLE_TASK_ENGINE.md, docs/api_inventory.json
- **Reviewer / Demo Usage**: `No`
- **Production Verified**: `LIVE VERIFIED`
- **Behavior Overlap**: `None`
- **Classification**: **`CANONICAL`**

### `POST /api/v1/tasks/{task_id}/complete`
- **Router File**: `backend/app/api/v1/tasks.py` (`complete_farm_task`)
- **Service**: `TaskIntelligenceEngine`
- **Repository / Provider / Model**: `TaskRepository, FarmTask, FarmMemoryV2`
- **Frontend Web Callers**: None
- **Frontend Mobile (Flutter) Callers**: None
- **Backend Internal Callers**: None
- **Test Callers**: backend/tests/test_task_authorization.py
- **Doc References**: docs/API_INVENTORY.md, docs/PHASE_6_STEP_2_CROP_LIFECYCLE_TASK_ENGINE.md, docs/api_inventory.json
- **Reviewer / Demo Usage**: `No`
- **Production Verified**: `LIVE VERIFIED`
- **Behavior Overlap**: `None`
- **Classification**: **`CANONICAL`**

### `POST /api/v1/tasks/{task_id}/evaluate-condition`
- **Router File**: `backend/app/api/v1/tasks.py` (`evaluate_smart_reminder`)
- **Service**: `TaskIntelligenceEngine`
- **Repository / Provider / Model**: `TaskRepository, FarmTask, FarmMemoryV2`
- **Frontend Web Callers**: None
- **Frontend Mobile (Flutter) Callers**: None
- **Backend Internal Callers**: None
- **Test Callers**: None
- **Doc References**: docs/API_INVENTORY.md, docs/api_inventory.json
- **Reviewer / Demo Usage**: `No`
- **Production Verified**: `LIVE VERIFIED`
- **Behavior Overlap**: `None`
- **Classification**: **`INTERNAL`**

### `POST /api/v1/tasks/{task_id}/postpone`
- **Router File**: `backend/app/api/v1/tasks.py` (`postpone_farm_task`)
- **Service**: `TaskIntelligenceEngine`
- **Repository / Provider / Model**: `TaskRepository, FarmTask, FarmMemoryV2`
- **Frontend Web Callers**: None
- **Frontend Mobile (Flutter) Callers**: None
- **Backend Internal Callers**: None
- **Test Callers**: backend/tests/test_task_authorization.py
- **Doc References**: docs/API_INVENTORY.md, docs/PHASE_6_STEP_2_CROP_LIFECYCLE_TASK_ENGINE.md, docs/api_inventory.json
- **Reviewer / Demo Usage**: `No`
- **Production Verified**: `LIVE VERIFIED`
- **Behavior Overlap**: `None`
- **Classification**: **`CANONICAL`**

### `POST /api/v1/tasks/{task_id}/skip`
- **Router File**: `backend/app/api/v1/tasks.py` (`skip_farm_task`)
- **Service**: `TaskIntelligenceEngine`
- **Repository / Provider / Model**: `TaskRepository, FarmTask, FarmMemoryV2`
- **Frontend Web Callers**: None
- **Frontend Mobile (Flutter) Callers**: None
- **Backend Internal Callers**: None
- **Test Callers**: backend/tests/test_task_authorization.py
- **Doc References**: docs/API_INVENTORY.md, docs/PHASE_6_STEP_2_CROP_LIFECYCLE_TASK_ENGINE.md, docs/api_inventory.json
- **Reviewer / Demo Usage**: `No`
- **Production Verified**: `LIVE VERIFIED`
- **Behavior Overlap**: `None`
- **Classification**: **`CANONICAL`**

### `POST /api/v1/vision/analyze`
- **Router File**: `backend/app/api/v1/vision_routes.py` (`analyze_crop_image`)
- **Service**: `VisionService, BhoomiPersonaEngine`
- **Repository / Provider / Model**: `PlantPathologyCNN (ResNet/MobileNet), GradCAMService, Sarvam Bulbul TTS`
- **Frontend Web Callers**: frontend/web/static/app.js
- **Frontend Mobile (Flutter) Callers**: frontend/mobile/lib/core/constants/api_endpoints.dart, frontend/mobile/lib/features/vision/edge_vision_provider.dart
- **Backend Internal Callers**: None
- **Test Callers**: scratch_test_endpoints.py
- **Doc References**: data/evaluation/public_smoke_test_evidence.json, docs/API_INVENTORY.md, docs/PHASE_3_BASELINE.md, docs/api_inventory.json
- **Reviewer / Demo Usage**: `No`
- **Production Verified**: `LIVE VERIFIED`
- **Behavior Overlap**: `POST /api/v1/image/analyze (Canonical modular vision pipeline with Grad-CAM, OOD rejection, & audio)`
- **Classification**: **`CANONICAL`**

### `GET /api/v1/vision/samples`
- **Router File**: `backend/app/api/v1/vision_routes.py` (`get_sample_leaves`)
- **Service**: `VisionService, BhoomiPersonaEngine`
- **Repository / Provider / Model**: `PlantPathologyCNN (ResNet/MobileNet), GradCAMService, Sarvam Bulbul TTS`
- **Frontend Web Callers**: frontend/web/static/app.js
- **Frontend Mobile (Flutter) Callers**: None
- **Backend Internal Callers**: None
- **Test Callers**: None
- **Doc References**: docs/API_INVENTORY.md, docs/api_inventory.json
- **Reviewer / Demo Usage**: `Yes`
- **Production Verified**: `LIVE VERIFIED`
- **Behavior Overlap**: `None`
- **Classification**: **`DEMO_ONLY`**

### `POST /api/v1/voice/interact`
- **Router File**: `backend/app/api/v1/voice.py` (`voice_interact`)
- **Service**: `VoiceService, SarvamVoiceService, BhoomiAgentOrchestrator`
- **Repository / Provider / Model**: `IntentNormalizationService, ConfirmationStateMachine, TaskIntelligenceEngine`
- **Frontend Web Callers**: frontend/web/static/app.js
- **Frontend Mobile (Flutter) Callers**: frontend/mobile/lib/core/constants/api_endpoints.dart
- **Backend Internal Callers**: None
- **Test Callers**: backend/tests/test_datetime_timezone_regression.py, backend/tests/test_forensic_railway_fixes.py, backend/tests/test_voice_authentication_regression.py
- **Doc References**: data/evaluation/public_smoke_test_evidence.json, docs/API_INVENTORY.md, docs/PHASE_2_BASELINE.md, docs/PHASE_4_SARVAM_VOICE.md, docs/api.md, docs/api_inventory.json
- **Reviewer / Demo Usage**: `No`
- **Production Verified**: `LIVE VERIFIED`
- **Behavior Overlap**: `None`
- **Classification**: **`CANONICAL`**

### `POST /api/v1/voice/stt`
- **Router File**: `backend/app/api/v1/voice.py` (`web_stt`)
- **Service**: `VoiceService, SarvamVoiceService, BhoomiAgentOrchestrator`
- **Repository / Provider / Model**: `IntentNormalizationService, ConfirmationStateMachine, TaskIntelligenceEngine`
- **Frontend Web Callers**: None
- **Frontend Mobile (Flutter) Callers**: None
- **Backend Internal Callers**: None
- **Test Callers**: None
- **Doc References**: docs/API_INVENTORY.md, docs/api_inventory.json
- **Reviewer / Demo Usage**: `No`
- **Production Verified**: `LIVE VERIFIED`
- **Behavior Overlap**: `None`
- **Classification**: **`INTERNAL`**

### `POST /api/v1/voice/synthesize`
- **Router File**: `backend/app/api/v1/voice.py` (`synthesize_speech`)
- **Service**: `VoiceService, SarvamVoiceService, BhoomiAgentOrchestrator`
- **Repository / Provider / Model**: `IntentNormalizationService, ConfirmationStateMachine, TaskIntelligenceEngine`
- **Frontend Web Callers**: frontend/web/static/app.js
- **Frontend Mobile (Flutter) Callers**: frontend/mobile/lib/core/constants/api_endpoints.dart, frontend/mobile/lib/features/voice/voice_assistant_screen.dart
- **Backend Internal Callers**: None
- **Test Callers**: None
- **Doc References**: docs/API_INVENTORY.md, docs/PHASE_2_BASELINE.md, docs/api.md, docs/api_inventory.json
- **Reviewer / Demo Usage**: `No`
- **Production Verified**: `LIVE VERIFIED`
- **Behavior Overlap**: `None`
- **Classification**: **`CANONICAL`**

### `POST /api/v1/voice/task-action`
- **Router File**: `backend/app/api/v1/voice.py` (`voice_task_action`)
- **Service**: `VoiceService, SarvamVoiceService, BhoomiAgentOrchestrator`
- **Repository / Provider / Model**: `IntentNormalizationService, ConfirmationStateMachine, TaskIntelligenceEngine`
- **Frontend Web Callers**: None
- **Frontend Mobile (Flutter) Callers**: frontend/mobile/lib/features/voice/voice_assistant_screen.dart
- **Backend Internal Callers**: None
- **Test Callers**: backend/tests/test_phase6_voice_interaction.py
- **Doc References**: docs/API_INVENTORY.md, docs/PHASE_6_STEP_3_FARMER_VOICE_LONGITUDINAL_FEEDBACK.md, docs/api_inventory.json
- **Reviewer / Demo Usage**: `No`
- **Production Verified**: `LIVE VERIFIED`
- **Behavior Overlap**: `None`
- **Classification**: **`CANONICAL`**

### `POST /api/v1/voice/transcribe`
- **Router File**: `backend/app/api/v1/voice.py` (`transcribe_audio`)
- **Service**: `VoiceService, SarvamVoiceService, BhoomiAgentOrchestrator`
- **Repository / Provider / Model**: `IntentNormalizationService, ConfirmationStateMachine, TaskIntelligenceEngine`
- **Frontend Web Callers**: None
- **Frontend Mobile (Flutter) Callers**: frontend/mobile/lib/core/constants/api_endpoints.dart
- **Backend Internal Callers**: None
- **Test Callers**: None
- **Doc References**: docs/API_INVENTORY.md, docs/PHASE_2_BASELINE.md, docs/api.md, docs/api_inventory.json
- **Reviewer / Demo Usage**: `No`
- **Production Verified**: `LIVE VERIFIED`
- **Behavior Overlap**: `None`
- **Classification**: **`CANONICAL`**

### `POST /api/v1/voice/tts`
- **Router File**: `backend/app/api/v1/voice.py` (`web_tts`)
- **Service**: `VoiceService, SarvamVoiceService, BhoomiAgentOrchestrator`
- **Repository / Provider / Model**: `IntentNormalizationService, ConfirmationStateMachine, TaskIntelligenceEngine`
- **Frontend Web Callers**: frontend/web/static/app.js
- **Frontend Mobile (Flutter) Callers**: None
- **Backend Internal Callers**: None
- **Test Callers**: backend/tests/test_voice_authentication_regression.py
- **Doc References**: docs/API_INVENTORY.md, docs/api_inventory.json
- **Reviewer / Demo Usage**: `No`
- **Production Verified**: `LIVE VERIFIED`
- **Behavior Overlap**: `None`
- **Classification**: **`INTERNAL`**

### `GET /api/v1/weather`
- **Router File**: `backend/app/api/v1/weather.py` (`get_weather`)
- **Service**: `WeatherService`
- **Repository / Provider / Model**: `OpenWeatherMapProvider, IMDProvider`
- **Frontend Web Callers**: None
- **Frontend Mobile (Flutter) Callers**: frontend/mobile/lib/core/constants/api_endpoints.dart, frontend/mobile/lib/features/chat/chat_screen.dart, frontend/mobile/lib/features/home/home_screen.dart, frontend/mobile/lib/features/voice/voice_assistant_screen.dart, frontend/mobile/lib/routing/app_router.dart
- **Backend Internal Callers**: backend/app/services/conversation/dialogue_manager.py, backend/app/services/weather/real_provider.py
- **Test Callers**: scratch_test_endpoints.py, scratch_test_providers.py, test_live_http_api.py
- **Doc References**: data/evaluation/public_smoke_test_evidence.json, docs/API_INVENTORY.md, docs/PHASE_2_BASELINE.md, docs/PHASE_4_REAL_WEATHER.md, docs/api.md, docs/api_inventory.json
- **Reviewer / Demo Usage**: `No`
- **Production Verified**: `LIVE VERIFIED`
- **Behavior Overlap**: `None`
- **Classification**: **`CANONICAL`**

### `GET /api/v1/weather/forecast`
- **Router File**: `backend/app/api/v1/weather.py` (`get_weather_forecast`)
- **Service**: `WeatherService`
- **Repository / Provider / Model**: `OpenWeatherMapProvider, IMDProvider`
- **Frontend Web Callers**: None
- **Frontend Mobile (Flutter) Callers**: None
- **Backend Internal Callers**: None
- **Test Callers**: None
- **Doc References**: data/evaluation/public_smoke_test_evidence.json, docs/API_INVENTORY.md, docs/api_inventory.json
- **Reviewer / Demo Usage**: `No`
- **Production Verified**: `LIVE VERIFIED`
- **Behavior Overlap**: `None`
- **Classification**: **`UNUSED`**

### `POST /api/v1/yield/predict`
- **Router File**: `backend/app/api/v1/yield_routes.py` (`predict_yield`)
- **Service**: `YieldPredictionService`
- **Repository / Provider / Model**: `AgronomicYieldModel`
- **Frontend Web Callers**: None
- **Frontend Mobile (Flutter) Callers**: None
- **Backend Internal Callers**: None
- **Test Callers**: None
- **Doc References**: docs/API_INVENTORY.md, docs/PHASE_2_BASELINE.md, docs/api_inventory.json
- **Reviewer / Demo Usage**: `No`
- **Production Verified**: `LIVE VERIFIED`
- **Behavior Overlap**: `POST /api/v1/ml/yield-prediction (Legacy yield predict endpoint superseded by Phase 2 XGBoost ML model)`
- **Classification**: **`LEGACY`**

### `GET /app`
- **Router File**: `backend/app/main.py` (`app_portal`)
- **Service**: `StaticFiles`
- **Repository / Provider / Model**: `Web Frontend (index.html)`
- **Frontend Web Callers**: frontend/web/index.html, frontend/web/static/app.js
- **Frontend Mobile (Flutter) Callers**: frontend/mobile/lib/core/theme/app_theme.dart, frontend/mobile/lib/features/auth/auth_screen.dart, frontend/mobile/lib/features/chat/chat_screen.dart, frontend/mobile/lib/features/farm/farm_profile_screen.dart, frontend/mobile/lib/features/home/home_screen.dart, frontend/mobile/lib/features/language/language_selection_screen.dart, frontend/mobile/lib/features/market/market_intelligence_screen.dart, frontend/mobile/lib/features/onboarding/onboarding_screen.dart, frontend/mobile/lib/features/profit/profit_simulator_screen.dart, frontend/mobile/lib/features/splash/splash_screen.dart, frontend/mobile/lib/features/tasks/tasks_screen.dart, frontend/mobile/lib/features/vision/leaf_scanner_screen.dart, frontend/mobile/lib/features/voice/voice_assistant_screen.dart, frontend/mobile/lib/features/weather/weather_screen.dart, frontend/mobile/lib/main.dart, frontend/mobile/lib/shared/cards/crop_recommendation_card.dart, frontend/mobile/lib/shared/cards/leaf_diagnosis_card.dart, frontend/mobile/lib/shared/cards/market_card.dart, frontend/mobile/lib/shared/cards/profit_card.dart, frontend/mobile/lib/shared/cards/risk_card.dart, frontend/mobile/lib/shared/cards/simulation_card.dart, frontend/mobile/lib/shared/cards/task_card.dart, frontend/mobile/lib/shared/cards/weather_card.dart, frontend/mobile/lib/shared/cards/yield_prediction_card.dart, frontend/mobile/lib/shared/widgets/voice_orb.dart
- **Backend Internal Callers**: backend/app/main.py
- **Test Callers**: None
- **Doc References**: README.md, data/benchmarks/300_scenarios.json, data/evaluation/reviewer_questions/image_questions.json, data/rag/verified_knowledge.json, docs/API_INVENTORY.md, docs/PHASE_2_BASELINE.md, docs/PHASE_2_VERIFICATION_REPORT.md, docs/PHASE_3_BASELINE.md, docs/PHASE_4_BASELINE.md, docs/PHASE_4_REAL_LLM.md, docs/PHASE_4_REAL_MARKET.md, docs/PHASE_4_REAL_WEATHER.md, docs/PHASE_4_SARVAM_VOICE.md, docs/PHASE_6_STEP_1_DECISION_INTELLIGENCE.md, docs/PHASE_6_STEP_2_CROP_LIFECYCLE_TASK_ENGINE.md, docs/PHASE_6_STEP_3_FARMER_VOICE_LONGITUDINAL_FEEDBACK.md, docs/PHASE_6_STEP_4_FIELD_PILOT_AUDIT_PIPELINE.md, docs/api_inventory.json
- **Reviewer / Demo Usage**: `No`
- **Production Verified**: `LIVE VERIFIED`
- **Behavior Overlap**: `None`
- **Classification**: **`CANONICAL`**

### `GET /finance`
- **Router File**: `backend/app/main.py` (`app_portal`)
- **Service**: `StaticFiles`
- **Repository / Provider / Model**: `Web Frontend (index.html)`
- **Frontend Web Callers**: frontend/web/static/app.js
- **Frontend Mobile (Flutter) Callers**: None
- **Backend Internal Callers**: backend/app/main.py
- **Test Callers**: backend/tests/test_auth_page_gating.py, backend/tests/test_browser_weather_market_finance.py
- **Doc References**: docs/API_INVENTORY.md, docs/PHASE_2_BASELINE.md, docs/PHASE_3_BASELINE.md, docs/api_inventory.json
- **Reviewer / Demo Usage**: `No`
- **Production Verified**: `LIVE VERIFIED`
- **Behavior Overlap**: `None`
- **Classification**: **`CANONICAL`**

### `GET /health`
- **Router File**: `backend/app/main.py` (`health`)
- **Service**: `WeatherService, MarketService`
- **Repository / Provider / Model**: `System/Providers`
- **Frontend Web Callers**: None
- **Frontend Mobile (Flutter) Callers**: None
- **Backend Internal Callers**: backend/app/main.py
- **Test Callers**: None
- **Doc References**: data/benchmarks/300_scenarios.json, data/evaluation/reviewer_questions/image_questions.json, docs/API_INVENTORY.md, docs/api_inventory.json
- **Reviewer / Demo Usage**: `No`
- **Production Verified**: `LIVE VERIFIED`
- **Behavior Overlap**: `None`
- **Classification**: **`CANONICAL`**

### `GET /home`
- **Router File**: `backend/app/main.py` (`app_portal`)
- **Service**: `StaticFiles`
- **Repository / Provider / Model**: `Web Frontend (index.html)`
- **Frontend Web Callers**: frontend/web/static/app.js
- **Frontend Mobile (Flutter) Callers**: frontend/mobile/lib/routing/app_router.dart
- **Backend Internal Callers**: backend/app/main.py
- **Test Callers**: backend/tests/test_auth_page_gating.py
- **Doc References**: docs/API_INVENTORY.md, docs/BHOOMI_V2_FINAL_DEMO_GUIDE.md, docs/api_inventory.json
- **Reviewer / Demo Usage**: `No`
- **Production Verified**: `LIVE VERIFIED`
- **Behavior Overlap**: `None`
- **Classification**: **`CANONICAL`**

### `GET /login`
- **Router File**: `backend/app/main.py` (`app_portal`)
- **Service**: `StaticFiles`
- **Repository / Provider / Model**: `Web Frontend (index.html)`
- **Frontend Web Callers**: frontend/web/static/app.js
- **Frontend Mobile (Flutter) Callers**: frontend/mobile/lib/core/constants/api_endpoints.dart
- **Backend Internal Callers**: backend/app/main.py
- **Test Callers**: backend/tests/test_auth_page_gating.py, backend/tests/test_phase6_task_engine.py, backend/tests/test_production_auth_system.py, backend/tests/test_reviewer_password_auth.py, backend/tests/test_task_authorization.py
- **Doc References**: docs/API_INVENTORY.md, docs/PHASE_2_BASELINE.md, docs/api.md, docs/api_inventory.json
- **Reviewer / Demo Usage**: `No`
- **Production Verified**: `LIVE VERIFIED`
- **Behavior Overlap**: `None`
- **Classification**: **`CANONICAL`**

### `GET /manifest.json`
- **Router File**: `backend/app/main.py` (`manifest`)
- **Service**: `StaticFiles`
- **Repository / Provider / Model**: `PWA Web App Manifest`
- **Frontend Web Callers**: frontend/web/index.html
- **Frontend Mobile (Flutter) Callers**: None
- **Backend Internal Callers**: backend/app/main.py
- **Test Callers**: None
- **Doc References**: docs/API_INVENTORY.md, docs/api_inventory.json
- **Reviewer / Demo Usage**: `No`
- **Production Verified**: `LIVE VERIFIED`
- **Behavior Overlap**: `None`
- **Classification**: **`CANONICAL`**

### `GET /onboarding`
- **Router File**: `backend/app/main.py` (`app_portal`)
- **Service**: `StaticFiles`
- **Repository / Provider / Model**: `Web Frontend (index.html)`
- **Frontend Web Callers**: frontend/web/static/app.js
- **Frontend Mobile (Flutter) Callers**: frontend/mobile/lib/routing/app_router.dart
- **Backend Internal Callers**: backend/app/main.py
- **Test Callers**: backend/tests/test_auth_page_gating.py
- **Doc References**: docs/API_INVENTORY.md, docs/api_inventory.json
- **Reviewer / Demo Usage**: `No`
- **Production Verified**: `LIVE VERIFIED`
- **Behavior Overlap**: `None`
- **Classification**: **`CANONICAL`**

### `GET /reviewer-login`
- **Router File**: `backend/app/main.py` (`app_portal`)
- **Service**: `StaticFiles`
- **Repository / Provider / Model**: `Web Frontend (index.html)`
- **Frontend Web Callers**: frontend/web/static/app.js
- **Frontend Mobile (Flutter) Callers**: None
- **Backend Internal Callers**: backend/app/main.py
- **Test Callers**: backend/tests/test_auth_page_gating.py
- **Doc References**: docs/API_INVENTORY.md, docs/api_inventory.json
- **Reviewer / Demo Usage**: `Yes`
- **Production Verified**: `LIVE VERIFIED`
- **Behavior Overlap**: `None`
- **Classification**: **`DEMO_ONLY`**

### `GET /signup`
- **Router File**: `backend/app/main.py` (`app_portal`)
- **Service**: `StaticFiles`
- **Repository / Provider / Model**: `Web Frontend (index.html)`
- **Frontend Web Callers**: frontend/web/static/app.js
- **Frontend Mobile (Flutter) Callers**: None
- **Backend Internal Callers**: backend/app/main.py
- **Test Callers**: backend/tests/test_auth_page_gating.py, backend/tests/test_production_auth_system.py, backend/tests/test_real_sms_delivery.py, backend/tests/test_reviewer_password_auth.py
- **Doc References**: docs/API_INVENTORY.md, docs/api_inventory.json
- **Reviewer / Demo Usage**: `No`
- **Production Verified**: `LIVE VERIFIED`
- **Behavior Overlap**: `None`
- **Classification**: **`CANONICAL`**

### `GET /sw.js`
- **Router File**: `backend/app/main.py` (`service_worker`)
- **Service**: `StaticFiles`
- **Repository / Provider / Model**: `Service Worker script`
- **Frontend Web Callers**: frontend/web/static/app.js
- **Frontend Mobile (Flutter) Callers**: None
- **Backend Internal Callers**: backend/app/main.py
- **Test Callers**: None
- **Doc References**: docs/API_INVENTORY.md, docs/api_inventory.json
- **Reviewer / Demo Usage**: `No`
- **Production Verified**: `LIVE VERIFIED`
- **Behavior Overlap**: `None`
- **Classification**: **`CANONICAL`**

### `GET /verify-otp`
- **Router File**: `backend/app/main.py` (`app_portal`)
- **Service**: `StaticFiles`
- **Repository / Provider / Model**: `Web Frontend (index.html)`
- **Frontend Web Callers**: frontend/web/static/app.js
- **Frontend Mobile (Flutter) Callers**: None
- **Backend Internal Callers**: backend/app/main.py
- **Test Callers**: backend/tests/test_auth_page_gating.py, backend/tests/test_forensic_railway_fixes.py, backend/tests/test_production_auth_system.py, backend/tests/test_reviewer_password_auth.py
- **Doc References**: data/evaluation/public_smoke_test_evidence.json, docs/API_INVENTORY.md, docs/REVIEWER_READINESS_REPORT.md, docs/api_inventory.json
- **Reviewer / Demo Usage**: `No`
- **Production Verified**: `LIVE VERIFIED`
- **Behavior Overlap**: `None`
- **Classification**: **`CANONICAL`**

### `GET /voice`
- **Router File**: `backend/app/main.py` (`app_portal`)
- **Service**: `StaticFiles`
- **Repository / Provider / Model**: `Web Frontend (index.html)`
- **Frontend Web Callers**: frontend/web/static/app.js
- **Frontend Mobile (Flutter) Callers**: frontend/mobile/lib/core/constants/api_endpoints.dart, frontend/mobile/lib/features/chat/chat_screen.dart, frontend/mobile/lib/features/home/home_screen.dart, frontend/mobile/lib/features/voice/voice_assistant_screen.dart, frontend/mobile/lib/routing/app_router.dart, frontend/mobile/test/widget_test.dart
- **Backend Internal Callers**: backend/app/main.py
- **Test Callers**: backend/tests/test_auth_page_gating.py, backend/tests/test_datetime_timezone_regression.py, backend/tests/test_forensic_railway_fixes.py, backend/tests/test_phase6_voice_interaction.py, backend/tests/test_voice_authentication_regression.py
- **Doc References**: data/evaluation/public_smoke_test_evidence.json, docs/API_INVENTORY.md, docs/PHASE_2_BASELINE.md, docs/PHASE_4_SARVAM_VOICE.md, docs/PHASE_6_STEP_3_FARMER_VOICE_LONGITUDINAL_FEEDBACK.md, docs/PHASE_6_STEP_4_FIELD_PILOT_AUDIT_PIPELINE.md, docs/api.md, docs/api_inventory.json
- **Reviewer / Demo Usage**: `No`
- **Production Verified**: `LIVE VERIFIED`
- **Behavior Overlap**: `None`
- **Classification**: **`CANONICAL`**
