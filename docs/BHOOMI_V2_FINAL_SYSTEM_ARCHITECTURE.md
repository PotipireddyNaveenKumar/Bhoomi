# BHOOMI V2 — FINAL SYSTEM ARCHITECTURE SPECIFICATION
**Voice-First Personal AI Farm Manager & Agricultural Decision Intelligence Platform**

---

## 1. Executive Architectural Summary

BHOOMI V2 is an integrated, voice-first agricultural decision intelligence platform designed specifically for Indian smallholder farmers. The system operates on a foundational paradigm: **Deterministic Agronomic Rules, Physical Constraints, and Mathematical Rigor form the authoritative core**, while Large Language Models (LLMs) and Multimodal Voice Systems function exclusively as natural language translation and synthesis interfaces.

### Core Architectural Loop:
```
       ┌───────────────┐
       │     ASK       │  (Multilingual Voice / Text: Sarvam AI + Saaras/Bulbul)
       └───────┬───────┘
               ↓
       ┌───────────────┐
       │   REMEMBER    │  (FarmMemoryV2: 4-Tier Provenance + Longitudinal Adherence)
       └───────┬───────┘
               ↓
       ┌───────────────┐
       │     PLAN      │  (TaskIntelligenceEngine: 7-Day Adaptive Schedule + Timezones)
       └───────┬───────┘
               ↓
       ┌───────────────┐
       │    MONITOR    │  (FarmStateEngine + ChangeDetector + IoT Sensors)
       └───────┬───────┘
               ↓
       ┌───────────────┐
       │    PREDICT    │  (ML Models: Yield, Price, MobileNetV3 Disease Vision)
       └───────┬───────┘
               ↓
       ┌───────────────┐
       │    COMPARE    │  (Crop Comparison & Mandi Net Realization Engine)
       └───────┬───────┘
               ↓
       ┌───────────────┐
       │    DECIDE     │  (FarmDecisionEngine: Deterministic Conflict Resolution + Risk)
       └───────┬───────┘
               ↓
       ┌───────────────┐
       │    REMIND     │  (ProactiveAlertEngine: Quiet Hours + Urgency Tiers)
       └───────┬───────┘
               ↓
       ┌───────────────┐
       │     ADAPT     │  (Feedback Loop: Weather Surges, Farmer Actions, Delays)
       └───────────────┘
```

---

## 2. High-Level System Architecture

```
                                  FARMER
                                    │
                        ┌───────────┴───────────┐
                        │                       │
                     VOICE                    TEXT
                 (Microphone)              (Chat UI)
                        │                       │
                        └───────────┬───────────┘
                                    ↓
                         INTENT NORMALIZATION
                    (Canonical VoiceIntent + 6 Langs)
                                    ↓
                           BHOOMI ORCHESTRATOR
                       (Multi-turn State Machine)
                                    ↓
                            CONTEXT ASSEMBLY
                        (Farm Digital Twin + State)
                                    ↓
             ┌──────────────────────┼──────────────────────┐
             ↓                      ↓                      ↓
      LONGITUDINAL MEMORY     TRUSTED RAG          LIVE TELEMETRY
       (FarmMemoryV2)       (ICAR / SAU / KVK)    (OpenWeather / Data.gov)
             │                      │                      │
             └──────────────────────┼──────────────────────┘
                                    ↓
                         DECISION INTELLIGENCE
                                    ↓
             ┌──────────────────────┼──────────────────────┐
             ↓                      ↓                      ↓
       ML PREDICTORS          COMPUTER VISION        RULES ENGINES
      (Yield / Price)       (Quality Gate + OOD)   (Agronomic Durations)
             │                      │                      │
             └──────────────────────┼──────────────────────┘
                                    ↓
                              SAFETY ENGINE
                    (Banned Chemical Block + Rice Barrier)
                                    ↓
                          DECISION / TASK PLAN
                      (Deterministic Canonical FarmTasks)
                                    ↓
                        PROACTIVE ALERT & REMIND
                      (Deduplication + Quiet Hours)
                                    ↓
                          LONGITUDINAL FEEDBACK
                        (Adherence + Outcome Audit)
```

---

## 3. Subsystem Breakdown

### 3.1. Farm Digital Twin (`DigitalTwinContext` & `FarmStateEngine`)
- **Farmer Profile**: Canonical IDs, preferred language (`en`, `te`, `hi`, `ta`, `kn`, `ml`), contact preferences, voice configuration.
- **Physical Farm Boundary**: Farm ID, GPS coordinates, state, district, sub-district, village, soil classification (black, red, alluvial, sandy loam), soil nutrient test records (N-P-K, pH, EC, organic carbon), water source (borewell, canal, drip, rainfed).
- **Active Crop Entity**: Crop species, cultivar/variety, sowing/transplanting timestamp, calibrated stage, historical pest pressure.
- **Zero-Fabrication Guarantee**: Missing parameters remain explicitly `None` or `UNKNOWN`.

### 3.2. Deterministic Crop Lifecycle Service (`CropLifecycleService`)
- Eliminates LLM hallucination of crop growth stages.
- Supported Stages: `SOWING`, `GERMINATION`, `VEGETATIVE`, `FLOWERING`, `FRUIT_DEVELOPMENT`, `MATURITY`, `HARVESTED`, `UNKNOWN`.
- Progression is calculated strictly from validated cultivar thermal time (GDD - Growing Degree Days) and calendar duration tables from ICAR and State Agricultural Universities.
- If sowing date is missing, status is deterministically returned as `UNKNOWN` with `LOW_CONFIDENCE`.

### 3.3. Farm Task Intelligence Engine (`TaskIntelligenceEngine`)
- Canonical single source of truth for all operational farm tasks.
- **13 Task Types**: `IRRIGATION`, `FIELD_INSPECTION`, `CROP_HEALTH_SCOUTING`, `FERTILIZATION`, `SPRAYING`, `WEED_MANAGEMENT`, `PEST_MONITORING`, `DISEASE_MONITORING`, `HARVEST_PREPARATION`, `HARVEST`, `MARKET_CHECK`, `SOIL_CHECK`, `GENERAL_FARM_TASK`.
- **8 Strict Statuses**: `PLANNED`, `DUE`, `IN_PROGRESS`, `COMPLETED`, `POSTPONED`, `SKIPPED`, `EXPIRED`, `CANCELLED`.
- **Timezone Safety**: Timestamps are strictly timezone-aware (`Asia/Kolkata` / `+05:30`). Postponements preserve the original planned hour/minute.
- **Auditability**: Every mutation records completion source, timestamp, reason, and trace ID.

### 3.4. Voice & Multilingual Experience (`SarvamVoiceProvider` + `IntentNormalizationService`)
- Primary farmer control interface using Sarvam AI (`saaras:v3` Speech-to-Text and `bulbul:v3` Text-to-Speech).
- Supported Languages: English, Telugu, Hindi, Tamil, Kannada, Malayalam.
- Canonical Intent Normalization maps unstructured farmer speech into structured voice intents (`TASK_COMPLETE`, `TASK_POSTPONE`, `TASK_SKIP`, `TASK_TODAY`, `TASK_WEEK`, `TASK_PENDING`, `TASK_WHY`, `TASK_CONFIRM`, `TASK_CANCEL`, `FARM_CHANGES`).
- Confidence Guard: When intent recognition confidence is < 0.65, clarification is solicited rather than making hazardous guesses.

### 3.5. Multi-Turn Confirmation State Machine (`ConfirmationStateMachine`)
- Critical safety barrier for irreversible or consequential actions (skipping high-priority irrigation, cancelling agronomic tasks).
- Explains the potential agronomic risk (e.g., soil moisture deficit during flowering stage) and requires an explicit positive confirmation ("Yes", "I confirm") before task state mutation.
- LLM is strictly prohibited from mutating database or task state directly.

### 3.6. Weather & Irrigation Intelligence (`WeatherDecisionEngine` & `IrrigationDecisionEngine`)
- Integrates OpenWeatherMap with fallback to localized agro-climatic stations.
- Strict Freshness Tiers: `CURRENT` (< 1h), `CACHED` (< 6h), `STALE` (> 6h), `UNAVAILABLE`.
- Agronomic Rules:
  - Rain probability $\ge 40\%$ or precipitation $\ge 12\text{ mm}$ $\implies$ Auto-defer surface irrigation.
  - Rain probability $\ge 50\%$ or precipitation $\ge 15\text{ mm}$ $\implies$ Hold chemical foliar spraying.
  - Flowering stage $\implies$ Restrict spraying to dawn/dusk to safeguard bee pollinators.

### 3.7. Market Intelligence & Crop Comparison (`MarketDecisionEngine`)
- Real-time Agmarknet / Data.gov mandi price integration.
- Exact financial math using Python `Decimal` (never floating-point approximations).
- Net Realization Calculation:
  $$\text{Net Realization} = \text{Gross Mandi Price} - \text{Transport Cost} - \text{Mandi User Fees} - \text{Loading Deductions}$$
- Action Recommendations: `SELL_NOW`, `WAIT`, `COMPARE_MARKETS`, `MONITOR`, `INSUFFICIENT_DATA`.

### 3.8. Computer Vision & Plant Pathology Pipeline
- High-resolution plant disease diagnosis:
  $$\text{Input Image} \longrightarrow \text{Image Quality Gate} \longrightarrow \text{Crop Model Registry} \longrightarrow \text{MobileNetV3} \longrightarrow \text{Temperature Scaling} \longrightarrow \text{OOD Detection} \longrightarrow \text{Safety Perimeter}$$
- Supported Crops: Chilli (Leaf Curl, Anthracnose, Healthy) and Tomato (Early Blight, Late Blight, Healthy).
- Uncertainty Safeguard: When image resolution is degraded or confidence is below threshold, the system never fabricates a disease name or chemical prescription; it generates a `FIELD_INSPECTION` task instead.

### 3.9. Final Safety Perimeter (`SafetyEngine` & Rice Protection Barrier)
- Non-bypassable rule engine operating downstream of all LLM and tool responses.
- **Banned Chemical Interception**: Automatically blocks hazardous and banned active ingredients (Monocrotophos, Paraquat, Chlorpyrifos, Endosulfan, etc.).
- **Rice Protection**: Rice remains permanently locked to `RESEARCH_ONLY`. Any farmer-facing chemical spraying prescription for rice is barred across all endpoints, voice channels, and frontend screens.
- Generates mandatory PPE advisories, pollinator safety alerts, and pre-harvest interval (PHI) warnings.

### 3.10. Longitudinal Farm Memory & Auditability (`FarmMemoryV2`)
- 4-Tier Strict Provenance Model:
  1. `SYSTEM_RECOMMENDATION`
  2. `FARMER_ACTION`
  3. `FARMER_REPORTED_OUTCOME`
  4. `VERIFIED_OUTCOME`
- Explicit Separation: Farmer-reported estimates are never converted into verified scientific facts without independent physical ground-truthing.
- Full traceability through `RecommendationTraceStore` linking farmer queries, tools executed, safety checks, and latencies.

### 3.11. Controlled Demonstration Mode (`DemoModeService`)
- Provides a pristine, repeatable demonstration environment for evaluation without reliance on flaky live internet connectivity.
- Model Farm: Guntur Model Farm (3.0 Acres Black Soil, Tomato at Flowering Stage, Farmer Ramesh Kumar).
- Explicit Labelling: All synthetic or mock data is labeled `DEMO_PROFILE / SIMULATED`.
- Reset Endpoint: Instantaneous state reset to pristine demonstration baseline.

---

## 4. Frontend Architecture (Flutter Mobile Application)

The Flutter mobile application (`bhoomi_mobile`) is architected for smallholder farmers with large readable typography, high-contrast visual cues, and voice-first ergonomics.

### Screen Inventory (18 Production-Grade Farmer Screens):
1. **Splash Screen**: Brand identity, automatic token check, animated navigation.
2. **Language Selection**: 6 Indian languages (English, Telugu, Hindi, Tamil, Kannada, Malayalam).
3. **Farmer Onboarding**: Name, phone, primary location, voice activation toggle.
4. **Farm Setup Screen**: Land area, soil classification, irrigation type, crop selection.
5. **Farm Command Center (Home)**: "What should I do now?" priority dashboard, central voice orb, today's tasks, live weather summary, mandi realization card.
6. **Voice Assistant Screen**: Central pulsating voice orb, dynamic state badge (`IDLE`, `LISTENING`, `PROCESSING`, `THINKING`, `RESPONDING`, `OFFLINE`), live transcript, visual advice cards, speech playback.
7. **Farmer Chat Interface**: Optional typing alternative with full parity to the voice pipeline.
8. **Crop Digital Twin Status**: Growth stage gauge, sowing-to-harvest progress bar, thermal time GDD tracker.
9. **Plant Pathology Camera**: Leaf capture, quality validation, diagnosis card, IPM advisories.
10. **Weather Intelligence Screen**: 5-day forecast, hourly rain probability, soil moisture advisory.
11. **Mandi Market Intelligence**: Price comparison across 3 closest mandis, net realization breakdown, distance-adjusted arbitrage.
12. **Farm Tasks & Smart Reminders**: Filterable task cards, complete, postpone, and skip controls with confirmation dialogs.
13. **Task Detail View**: Full agronomic rationale, weather dependencies, safety precautions, source literature citations.
14. **Farm History Timeline**: Chronological log of past sprays, irrigations, and harvests.
15. **What-If Farm Simulator**: Interactive sliders for market price shift, yield variance, rainfall deficit, and input cost fluctuations.
16. **Crop Comparison Matrix**: Side-by-side risk, water requirement, and profit potential analysis between competing crops.
17. **Proactive Alerts & Reminders**: Dedicated tray for weather surges, urgent scouting alerts, and market price spikes.
18. **Farmer Profile & Settings**: Farm configuration, language selector, quiet hours, offline cache controls.

---

## 5. Security, Infrastructure & Deployment

- **Authentication**: Stateless JWT with HS256 algorithm and bcrypt password hashing.
- **Authorization**: Row-level tenant isolation ensuring farmers can only access their own farms, tasks, and memory.
- **Sanitization**: API keys and secrets stored exclusively in gitignored `.env` files; `.env.example` contains only non-sensitive dummy placeholders.
- **Docker Compose Orchestration**: Production-grade multi-container topology (`backend`, `postgres:15-alpine`, `redis:7-alpine`) with healthchecks and persistent volumes.
- **Static Analysis Compliance**: 0 errors, 0 warnings on `flutter analyze`; clean syntax across all Python backend modules.
