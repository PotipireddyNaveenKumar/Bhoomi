# BHOOMI V2 — PHASE 6 STEP 3: FARMER VOICE INTERACTION & LONGITUDINAL FEEDBACK LOOP

**Document Version:** 1.0.0  
**Phase:** 6 — Step 3  
**Status:** IMPLEMENTED & VERIFIED (NOT_PRODUCTION_READY pending physical field validation)  
**Test Coverage:** 323/323 Passing Tests across Backend Test Suite (0 Regressions)

---

## 1. Executive Summary & Architecture Overview

BHOOMI V2 Phase 6 Step 3 transforms voice from a conversational presentation layer into a **deterministic, farmer-facing control interface** for agricultural task management, status synchronization, postponement, smart reminders, adherence calculation, and longitudinal feedback.

### Core Architectural Principle: Single Decision Pipeline
Voice and typing share the **exact same canonical business-logic path**. Voice is strictly an interface adapter—never a second decision engine.

```
                  ┌──────────────────────┐   ┌──────────────────────┐
                  │ Spoken Audio (Sarvam)│   │ Typed Input (Mobile) │
                  └──────────┬───────────┘   └──────────┬───────────┘
                             │                          │
                             ▼                          ▼
                  ┌─────────────────────────────────────────────────┐
                  │        IntentNormalizationService               │
                  │  - Language Script Detection (en/te/hi/ta/kn/ml)│
                  │  - Canonical VoiceIntent Model                  │
                  │  - Punctuation-Agnostic Entity Extraction       │
                  └──────────────────────┬──────────────────────────┘
                                         │
                                         ▼
                  ┌─────────────────────────────────────────────────┐
                  │          ConfirmationStateMachine               │
                  │  - Multi-Turn Disambiguation (e.g. Tomato/Chilli│
                  │  - Consequential Skip Safeguard (e.g. Irrigation)│
                  │  - State Tracking (Awaiting Confirmation/Delay) │
                  └──────────────────────┬──────────────────────────┘
                                         │
                                         ▼
                  ┌─────────────────────────────────────────────────┐
                  │           BhoomiAgentOrchestrator               │
                  │  - TaskIntelligenceEngine (State Mutation)      │
                  │  - SafetyEngine (Prohibited Chemical Intercept) │
                  │  - Rice RESEARCH_ONLY Policy Enforcement        │
                  │  - FarmStateEngine & Digital Twin               │
                  └──────────────┬──────────────────┬───────────────┘
                                 │                  │
                                 ▼                  ▼
                    ┌─────────────────┐    ┌─────────────────┐
                    │  FarmMemoryV2   │    │ TraceStore      │
                    │  (Provenance)   │    │ (Auditability)  │
                    └─────────────────┘    └─────────────────┘
                                 │                  │
                                 └─────────┬────────┘
                                           ▼
                  ┌─────────────────────────────────────────────────┐
                  │       Localized Voice Response (Sarvam TTS)     │
                  │       & Structured Visual Decision Cards        │
                  └─────────────────────────────────────────────────┘
```

---

## 2. Canonical Voice Intent Model

All queries are mapped into `VoiceIntent` objects via [intent_service.py](file:///C:/Users/SURESH/SIH/backend/app/services/voice/intent_service.py):

| Intent Type | Example Utterance | Parsed Entities |
|---|---|---|
| `TASK_COMPLETE` | "I finished watering." / "నీరు పెట్టడం పూర్తి చేశాను." / "सिंचाई पूरी कर ली।" | `target_task_type: IRRIGATION` |
| `TASK_POSTPONE` | "Postpone watering by two days." / "రెండు రోజులు వాయిదా వేయి." | `requested_delay_days: 2` |
| `TASK_SKIP` | "Skip today's irrigation." / "ఈ రోజు తడి దాటవేయి." | `confirmation_required: True` |
| `TASK_TODAY` | "What should I do today?" / "ఈరోజు నేను ఏమి చేయాలి?" | Daily briefing triggers |
| `TASK_WEEK` | "What should I do this week?" / "ఈ వారం పనులు ఏంటి?" | 7-day schedule triggers |
| `TASK_PENDING` | "What is pending?" / "బాకీ పనులు ఏమిటి?" | Overdue & pending queries |
| `TASK_WHY` | "Why should I water?" / "ఎందుకు తడి పెట్టాలి?" | Task evidence & triggers |
| `TASK_CONFIRM` | "Yes." / "అవును." / "हाँ।" / "ஆம்." | Confirmation affirmation |
| `TASK_CANCEL_ACTION` | "No, cancel that." / "వద్దు, రద్దు చెయ్యి." | Action abort |
| `FARM_CHANGES` | "What changed on my farm?" / "మార్పులు ఏమిటి?" | Delta state detection |
| `UNKNOWN` | Low confidence / unintelligible audio | Clarification required |

---

## 3. Deterministic Task Operations

### 3.1 Task Completion
1. Resolves active tasks for the farmer via `TaskIntelligenceEngine`.
2. Validates prerequisite dependencies (`can_execute`). If a prerequisite (e.g. physical scouting) is incomplete, the system refuses to complete the dependent action and explains the constraint.
3. Mutates `FarmTask.status = COMPLETED`, records `completed_at` ISO timestamp and `completion_source = "VOICE"` or `"TYPING"`.
4. Records structured event in `FarmMemoryV2` with `provenance = FARMER_ACTION`.
5. Records immutable audit record in `RecommendationTraceStore`.

### 3.2 Task Postponement
1. Farmer says: *"Postpone watering by two days."*
2. Entity extraction parses `requested_delay_days = 2`.
3. **Deterministic Backend Computation:** The LLM NEVER invents timestamps. Backend calculates:
   $$\text{new\_due\_time} = \text{datetime.now().date()} + \text{timedelta(days=2)}$$
4. Preserves `old_due_time`, sets `new_due_time`, records `postponement_reason`, updates `postponed_at`.

### 3.3 Consequential Skip & Multi-Turn Confirmation State Machine
When a farmer asks to skip a high-consequence task (e.g., Irrigation during a moisture deficit, or High/Critical priority spraying):
1. **Interceptor:** The system refuses to silently skip.
2. **Confirmation Request:** `ConfirmationStateMachine` transitions to `AWAITING_CONFIRMATION` with a 5-minute TTL.
   - Example Prompt: *"Skipping 'Chilli Drip Irrigation' may affect crop yield as soil moisture is low. Do you still want to skip it?"*
3. **Multi-Turn Resolution:**
   - Farmer says **"Yes"**: Marked as `SKIPPED`, logs audit event in `FarmMemoryV2` and `RecommendationTraceStore`.
   - Farmer says **"No"**: Operation aborted (`CANCELLED`), task remains `DUE`.
   - Timeout (5 min): Confirmation expires harmlessly, state resets to `NO_CONFIRMATION`.

### 3.4 Ambiguous Task Disambiguation (No Blind Guessing)
If multiple active tasks match a voice instruction (e.g. Chilli Drip Irrigation and Tomato Furrow Irrigation):
1. System refuses to guess or pick randomly.
2. `ConfirmationStateMachine` enters `AWAITING_TASK_SELECTION` and presents matching candidate crops.
3. Farmer clarifies: *"Tomato field."*
4. Disambiguated task is executed. Other crops remain untouched.

---

## 4. Multilingual Parity (6 Languages)

The exact same canonical business logic processes voice and typed requests across:
1. **English (`en`)**
2. **Telugu (`te`)**
3. **Hindi (`hi`)**
4. **Tamil (`ta`)**
5. **Kannada (`kn`)**
6. **Malayalam (`ml`)**

Language-specific logic is strictly isolated to:
- Sarvam STT transcription
- Script-based language detection
- Keyword/regex intent & entity extraction
- Localized confirmation responses
- Sarvam TTS synthesis

---

## 5. Proactive Nudge & Reminder Engine

Built into [proactive_alerts.py](file:///C:/Users/SURESH/SIH/backend/app/services/farm_manager/proactive_alerts.py):
- **Contact Preferences:** `FarmerContactPreferences` allows configuring quiet hours (`quiet_hours_start`, `quiet_hours_end`), notification caps (`max_daily_reminders`), and reminder toggles (`reminders_enabled`).
- **Quiet Hours Enforcement:** Nudges are silenced between 22:00 and 06:00 (or custom configured windows).
- **Deduplication:** Hash-based deduplication (`_compute_hash("REMINDER", trigger, signature)`) prevents repeated notifications for the same unchanged condition.
- **Reminder Types:**
  - `Overdue Task`: Severity WARNING, requires acknowledgement.
  - `Due Today Task`: Severity INFO.
  - `Postponed Task`: Severity INFO.

---

## 6. Longitudinal Adherence & Personalization

Managed deterministically by [task_adherence.py](file:///C:/Users/SURESH/SIH/backend/app/services/farm_manager/task_adherence.py):

### 6.1 Adherence Rate Formula
$$\text{adherence\_rate} = \frac{\text{tasks\_completed}}{\text{tasks\_completed} + \text{tasks\_skipped} + \text{overdue\_tasks}}$$

- **Zero-Denominator Safety:** If eligible tasks $= 0$, adherence is `0.0` with level `INSUFFICIENT_DATA` (never fabricated as 100%).
- **Levels:**
  - $\ge 0.80$: `HIGH`
  - $0.50 - 0.79$: `MODERATE`
  - $< 0.50$: `LOW`
  - $0.00$ (no history): `INSUFFICIENT_DATA`

### 6.2 Personalization Rules & Non-Override Boundary
Longitudinal behavior personalizes:
- Reminder lead time (e.g. 6 hours for low compliance vs 2 hours for high compliance).
- Explanation verbosity (`DETAILED`, `BALANCED`, `CONCISE`).
- Nudge frequency (`FREQUENT`, `STANDARD`, `REDUCED`).
- Chronic postponement detection: $\ge 2$ postponements triggers `needs_water_availability_check = True` and prompts inquiry into pump electricity or labor constraints.

> [!IMPORTANT]
> **Agronomic Non-Override Guarantee:** Behavioral adherence NEVER overrides `SafetyEngine`, `WeatherDecisionEngine`, `IrrigationDecisionEngine`, or regulatory dosage constraints.

---

## 7. Provenance & Farmer Feedback

`FarmMemoryV2` enforces strict categorization of past outcomes:
1. `SYSTEM_RECOMMENDATION` — Algorithmic outputs.
2. `FARMER_ACTION` — Logged farmer executions (e.g. task completed or postponed).
3. `FARMER_REPORTED_OUTCOME` — Farmer's subjective feedback (e.g. "Drip saved 3 hours").
4. `VERIFIED_OUTCOME` — Ground-truth physical verification by field agronomist.

Subjective farmer feedback is stored with `FARMER_REPORTED_OUTCOME` and linked to its recommendation trace ID. It is NEVER conflated with verified agronomic truth.

---

## 8. Safety Boundaries & Rice Protection

1. **Un-bypassable SafetyEngine:**
   - Every query is evaluated for banned substances (e.g., *Monocrotophos*, *Endosulfan*, *Paraquat*).
   - Prohibited chemicals are blocked at the perimeter before tool execution or task creation.
2. **Rice Research-Only Protocol:**
   - Rice models remain strictly `RESEARCH_ONLY`.
   - Any voice or text inquiry requesting chemical spray prescriptions on Rice returns an explicit research-only limitation card and message.

---

## 9. API Specifications

### `POST /api/v1/voice/task-action`

**Request Payload:**
```json
{
  "audio": "base64_audio_string...",
  "text": "I finished watering.",
  "language": "en",
  "farmer_id": "farmer_demo_1",
  "conversation_id": "session_api_demo"
}
```

**Response Payload:**
```json
{
  "intent": "TASK_COMPLETE",
  "task_id": "task_irrig_1",
  "action": "TASK_COMPLETE",
  "status": "SUCCESS",
  "requires_confirmation": false,
  "response_text": "Task 'Chilli Drip Irrigation' has been marked as COMPLETED.",
  "language": "en",
  "trace_id": "trace_voice_9f14ab28"
}
```

---

## 10. Test Verification Results

The complete test suite was executed across the entire repository:

```
============================= test session starts =============================
platform win32 -- Python 3.11.0, pytest-9.1.1, pluggy-1.6.0
rootdir: C:\Users\SURESH\SIH
configfile: pyproject.toml
collected 323 items

backend\tests\test_agent_and_api.py ...                                  [  0%]
backend\tests\test_financial_service.py ...                              [  1%]
backend\tests\test_image_gate.py ...                                     [  2%]
backend\tests\test_phase2_ml_and_intelligence.py ..............          [  7%]
backend\tests\test_phase3_farm_manager.py ................               [ 12%]
backend\tests\test_phase4_market.py ...................................  [ 22%]
backend\tests\test_phase4_multi_crop_vision.py ......................... [ 30%]
..                                                                       [ 31%]
backend\tests\test_phase4_real_llm.py .....                              [ 32%]
backend\tests\test_phase4_sarvam_voice.py ..............                 [ 37%]
backend\tests\test_phase4_tomato_vision.py ....................          [ 43%]
backend\tests\test_phase4_weather.py ............................        [ 52%]
backend\tests\test_phase5_edge_ai.py ....................                [ 58%]
backend\tests\test_phase5_field_ingestion.py .................           [ 63%]
backend\tests\test_phase5_field_pilot_readiness.py ....................  [ 69%]
backend\tests\test_phase5_field_validation.py ................           [ 74%]
backend\tests\test_phase6_decision_intelligence.py ..................... [ 81%]
.......                                                                  [ 83%]
backend\tests\test_phase6_task_engine.py ..........................      [ 91%]
backend\tests\test_phase6_voice_interaction.py ........................  [ 98%]
backend\tests\test_safety_engine.py ..                                   [ 99%]
backend\tests\test_simulation_service.py ..                              [100%]

============================ 323 passed in 39.11s =============================
```

- **Previous Test Count:** 299
- **New Tests Added:** 24
- **Total Tests:** 323
- **Passed:** 323
- **Failed:** 0
- **Regression Count:** 0

---

## 11. Known Limitations & Production Readiness

> [!CAUTION]
> **Production Status: `NOT_PRODUCTION_READY`**  
> While all 323 automated unit and integration tests pass cleanly, BHOOMI V2 remains strictly `NOT_PRODUCTION_READY` pending physical field pilot data collection and agronomic expert review:
> 1. Real farmer voice recordings under field tractor noise, wind distortion, and dialectal variations.
> 2. Real-world multi-day farm task completion compliance logs.
> 3. Field crop observation verification against physical field trials.
