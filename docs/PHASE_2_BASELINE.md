# BHOOMI V2 — Phase 2 Architecture Baseline

## 1. Executive Summary
This baseline document records the complete working state of Phase 1 prior to Phase 2 extensions.
All existing APIs, database models, voice pipelines, deterministic financial calculations, What-If simulation engines, and the Flutter mobile interface are protected under backward compatibility guarantees.

---

## 2. Existing Phase 1 Architecture Components

### A. Backend Core & Configuration
- **Entrypoint**: [backend/app/main.py](file:///c:/Users/SURESH/SIH/backend/app/main.py)
- **Configuration**: [backend/app/core/config.py](file:///c:/Users/SURESH/SIH/backend/app/core/config.py)
  - Pydantic Settings supporting SQLite / PostgreSQL, Redis, and multi-provider credentials.
- **Security & JWT**: [backend/app/core/security.py](file:///c:/Users/SURESH/SIH/backend/app/core/security.py)
- **Logging & Exceptions**: [backend/app/core/logging.py](file:///c:/Users/SURESH/SIH/backend/app/core/logging.py), [backend/app/core/exceptions.py](file:///c:/Users/SURESH/SIH/backend/app/core/exceptions.py)

### B. Database Schema & Models (`backend/app/models/`)
- `User`: Authentication and phone number credentials.
- `FarmerProfile`: Farmer name, preferred language (`en`, `te`, `hi`, `ta`, `kn`, `ml`), location (State, District, Village).
- `Farm`: Total acreage, coordinates, soil type, irrigation source, soil health JSON.
- `FarmCrop`: Crop name, variety, area, sowing date, expected harvest, current stage, cultivation costs.
- `ChatSession` & `ChatMessage`: Conversational history, input mode (`voice`, `text`, `image`), visual cards payload.
- `FarmerMemory`: Persistent episodic and long-term farm memory facts.
- `FarmTask`: Scheduled farm actions with dynamic conditions.
- `PredictionHistory`: Audit trail for ML and model inferences.

### C. Existing Phase 1 APIs (`/api/v1`)
- `/auth/register` & `/auth/login`
- `/farmer` (GET, PUT)
- `/farms` (GET, POST), `/farms/{id}`, `/farms/{id}/crops`
- `/chat` (POST), `/chat/sessions` (GET)
- `/voice/transcribe`, `/voice/synthesize`, `/voice/interact`
- `/image/analyze`
- `/weather`
- `/market`
- `/crop/recommend`, `/crop/lifecycle`
- `/yield/predict`
- `/profit/calculate`
- `/simulation/run`
- `/risk/assess`
- `/tasks` (GET, POST, PUT), `/tasks/{id}/evaluate-condition`

### D. Verified Services & Protected Contracts
1. **FinancialService** ([backend/app/services/finance/profit_service.py](file:///c:/Users/SURESH/SIH/backend/app/services/finance/profit_service.py)):
   - Strict `Decimal` precision arithmetic.
   - Tested baseline: $10\text{ quintals} \times 12,000 - 70,000 = 50,000\text{ INR Net Profit}$.
2. **SimulationService** ([backend/app/services/simulation/simulation_service.py](file:///c:/Users/SURESH/SIH/backend/app/services/simulation/simulation_service.py)):
   - Deterministic What-If scenario shifts for price drops, yield shocks, rainfall deficit, and cost escalations.
3. **SafetyEngine** ([backend/app/services/safety/safety_engine.py](file:///c:/Users/SURESH/SIH/backend/app/services/safety/safety_engine.py)):
   - CIBRC banned chemical interception (Monocrotophos, Endosulfan, Paraquat).
   - Pollinator and PPE safety warnings during flowering stages.
4. **VoiceProvider & Sarvam Integration** ([backend/app/services/voice/](file:///c:/Users/SURESH/SIH/backend/app/services/voice/)):
   - `SarvamVoiceProvider` with backend key protection.
   - `MockVoiceProvider` for zero-dependency CI/CD.
5. **Agent Orchestrator** ([backend/app/agents/](file:///c:/Users/SURESH/SIH/backend/app/agents/)):
   - Multi-turn conversational flow with `MissingInformationDetector`.

---

## 3. Existing Test Baseline (13 Tests Passing 100%)
- `backend/tests/test_financial_service.py` (3 tests)
- `backend/tests/test_simulation_service.py` (2 tests)
- `backend/tests/test_safety_engine.py` (2 tests)
- `backend/tests/test_image_gate.py` (3 tests)
- `backend/tests/test_agent_and_api.py` (3 tests)

---

## 4. Protected Files (MUST NOT BE BROKEN)
- `backend/app/main.py` (v1 routes must remain accessible)
- `backend/app/db/session.py`, `backend/app/db/base.py`
- `backend/app/models/*` (all existing tables and relationships)
- `backend/app/services/finance/profit_service.py`
- `backend/app/services/simulation/simulation_service.py`
- `backend/app/services/safety/safety_engine.py`
- `frontend/mobile/lib/main.dart` & `frontend/mobile/lib/routing/app_router.dart`
- `frontend/mobile/lib/localization/*` (all 6 regional language JSONs)
