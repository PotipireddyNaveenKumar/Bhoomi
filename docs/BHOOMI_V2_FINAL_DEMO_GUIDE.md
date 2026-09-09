# BHOOMI V2 — FINAL DEMONSTRATION GUIDE & PRESENTATION SCRIPT
**Step-by-Step Live Demonstration Protocol for Judges & Agronomic Evaluators**

---

## 0. Demo Overview & Operational Context

| Dimension | Specification |
|:---|:---|
| **Demo Profile** | `DEMO_PROFILE / SIMULATED` (Clearly Labeled) |
| **Model Farmer** | Ramesh Kumar (`demo_farmer_1`) |
| **Model Farm** | Guntur Model Farm (`farm_demo_1`), Tenali, Andhra Pradesh |
| **Acreage & Soil** | 3.0 Acres, Deep Black Soil (Vertisol) |
| **Active Crop** | Tomato (*Solanum lycopersicum*, Teja Hybrid) |
| **Growth Stage** | Flowering Stage (Days 45–65 after transplanting) |
| **Voice Provider** | Sarvam AI (`saaras:v3` STT / `bulbul:v3` TTS) |
| **Readiness** | `CONTROLLED_PILOT_READY`, `NOT_PRODUCTION_READY` |

---

## 1. Step-by-Step 20-Step Live Demonstration Protocol

### Step 1: Launch Mobile App & Splash Screen
- **Action**: Launch the Flutter application on emulator or physical mobile device.
- **Visual**: Dark emerald brand screen appears with green pulsating leaf logo, app title `BHOOMI: Personal AI Farm Manager`, and automatic authentication check.
- **Narrative**: *"Welcome to BHOOMI V2, a voice-first Personal AI Farm Manager built from the ground up for Indian smallholder farmers."*

### Step 2: Language Selection & Multilingual Foundation
- **Action**: Open Language Selector (`/language`).
- **Visual**: Displays 6 major Indian agricultural languages: Telugu (తెలుగు), Hindi (हिन्दी), Tamil (தமிழ்), Kannada (ಕನ್ನಡ), Malayalam (മലയാളം), and English.
- **Select**: Telugu or English.
- **Narrative**: *"BHOOMI provides full functional parity across all supported Indian languages. The exact same business logic, agronomic safety perimeters, and decision rules operate uniformly regardless of dialect."*

### Step 3: Farmer Digital Twin Profile Inspection
- **Action**: Tap Profile icon on top right to open Farm Profile (`/farm-profile`).
- **Visual**: Shows verified farm digital twin: Ramesh Kumar, Guntur Model Farm, 3.0 Acres Black Soil, Borewell Drip Irrigation, Tomato (Teja Hybrid) in flowering stage.
- **Narrative**: *"BHOOMI maintains an active Digital Twin of the farm. Notice that missing parameters remain explicitly unassigned rather than fabricated. Everything the system knows is grounded in verifiable farm parameters."*

### Step 4: Farm Command Center ("What Should I Do Now?")
- **Action**: Return to Home Screen (`/home` or `/command-center`).
- **Visual**: Clean, readable dashboard answering the single most pressing question of an Indian farmer: *'What should I do now?'* Displays central glowing voice orb, Today's Priority Tasks, Weather Advisory, and Mandi Benchmark.
- **Narrative**: *"Instead of overwhelming the farmer with complex charts, BHOOMI highlights today's high-priority operational decisions."*

### Step 5: Ask "What should I do today?" (Scenario 1)
- **Action**: Tap the central Voice Orb and speak (or type in Chat):
  - *English*: `"What should I do today?"`
  - *Telugu*: `"ఈరోజు నేను ఏమి చేయాలి?"`
  - *Hindi*: `"आज मुझे क्या करना चाहिए?"`
- **Visual**: Voice orb transitions `IDLE -> LISTENING -> PROCESSING -> RESPONDING`. Displays Daily Briefing Card highlighting Tomato flowering stage and today's priority: **Morning Drip Irrigation**.
- **Voice Response**: Sarvam TTS speaks a concise audio announcement tailored to the farmer.

### Step 6: Query Weather-Aware Irrigation Decision (Scenario 6)
- **Action**: Ask:
  - *English*: `"Should I irrigate today?"`
  - *Telugu*: `"ఈరోజు నీరు పెట్టాలా?"`
- **Visual**: BHOOMI executes `IrrigationDecisionEngine`, combining current soil tension (-45 kPa), high evapotranspiration demand during flowering, and upcoming rain forecast.
- **Response**: Recommends completing planned drip irrigation before afternoon, deferring surface flooding if rain probability exceeds 40%.

### Step 7: Voice Task Completion (Scenario 2)
- **Action**: Tap Voice Orb and state:
  - *English*: `"I finished watering."`
  - *Telugu*: `"నీరు పెట్టడం పూర్తయింది."`
- **Visual**: Task Intelligence Engine immediately maps the voice intent to `task_irrig_demo` (Morning Drip Irrigation), transitions status from `DUE` to `COMPLETED`, records timestamp, and speaks confirmation.
- **Audit**: Logged with provenance `FARMER_ACTION` in `FarmMemoryV2`.

### Step 8: Timezone-Aware Task Postponement (Scenario 3)
- **Action**: Tap Voice Orb and state:
  - *English*: `"Postpone spraying by two days."`
  - *Telugu*: `"మందు పిచికారీని రెండు రోజులు వాయిదా వేయి."`
- **Visual**: System identifies `task_spray_demo` (Evening Foliar Spray), validates against future weather forecast, advances date by exactly 2 days while strictly preserving original planned hour `17:30:00+05:30`.
- **Narrative**: *"Notice timezone safety: BHOOMI does not corrupt timestamps to arbitrary server UTC midnights. The spray remains scheduled for the cool evening window to protect honeybees."*

### Step 9: Consequential Task Skip & Confirmation Flow (Scenario 4)
- **Action**: Tap Voice Orb and state:
  - *English*: `"Skip irrigation."`
- **Visual**: State machine intercepts the request. Because skipping irrigation during flowering carries severe yield risk (blossom drop), BHOOMI enters `AWAITING_CONFIRMATION` mode and asks:
  - *"Warning: Skipping irrigation when soil moisture is depleted may cause flower abortion. Are you sure you want to skip?"*
- **Action (Confirmation)**: State `"Yes, I confirm."`
- **Visual**: Task status transitions to `SKIPPED`. Full audit trail recorded.

### Step 10: Plant Pathology Camera & Quality Gate (Scenario 5)
- **Action**: Navigate to Leaf Scanner (`/leaf-scanner`). Tap **Capture Photo**.
- **Visual**: Image Quality Gate verifies lighting, focus, and leaf presence. MobileNetV3 model executes calibrated disease inference.
- **Low Confidence / OOD Demonstration**: If image is blurry or disease uncertain, BHOOMI explicitly declares: *"Unable to confidently diagnose leaf condition. Generating a field inspection scouting task rather than prescribing chemical pesticides."*

### Step 11: SafetyEngine Chemical Block Perimeter (Scenario 10)
- **Action**: Speak or type:
  - *English*: `"Spray monocrotophos."`
- **Visual**: Intercepted instantaneously by `SafetyEngine`. An orange-red **Safety Alert Card** appears:
  - *"SAFETY ALERT: Monocrotophos is a hazardous organophosphate insecticide strictly banned by Central Government regulations. Task creation blocked."*
- **Narrative**: *"No LLM hallucination or prompt injection can bypass the SafetyEngine perimeter."*

### Step 12: Rice RESEARCH_ONLY Protection Protocol (Scenario 11)
- **Action**: Speak or type:
  - *English*: `"What pesticide should I spray on rice?"`
- **Visual**: Triggers immediate Rice Research Barrier. Returns:
  - *"SAFETY WARNING: Rice disease detection and treatment protocols remain in RESEARCH_ONLY status. Farmer-facing chemical spraying advice is strictly barred pending multi-season agronomic field validation."*

### Step 13: Mandi Market Intelligence & Net Realization (Scenario 7)
- **Action**: Ask:
  - *English*: `"Should I sell now?"` or `"What is the market price?"`
- **Visual**: Opens Market Intelligence Screen. BHOOMI runs `MarketDecisionEngine`, comparing Guntur Benchmark Mandi with Khammam and Warangal mandis. Uses Python `Decimal` arithmetic to subtract transport fees and loading charges, displaying true **Net Realization**.

### Step 14: What-If Farm Financial Simulator
- **Action**: Navigate to Simulator (`/profit-simulator`).
- **Interactive**: Drag sliders for **Market Price Shift (-20%)** and **Rainfall Deficit (-25%)**.
- **Visual**: Instantly displays recalculated gross revenue, cost of cultivation, surplus margin, and recommended hedging actions.

### Step 15: Farm Change Detection ("What Changed on My Farm?") (Scenario 8)
- **Action**: Ask:
  - *English*: `"What changed on my farm?"`
- **Visual**: Returns **Farm Changes Card**:
  - Reports irrigation completed, foliar spray postponed to Sunday, and weather advisory updated.

### Step 16: Weekly Adaptive Farm Plan (Scenario 9)
- **Action**: Ask:
  - *English*: `"What should I do this week?"`
- **Visual**: Displays 7-Day Adaptive Calendar with weather-aware badges on every task.

### Step 17: Transparent Decision Traces & Audit Trail
- **Action**: Inspect Recommendation Trace store via API or log view.
- **Visual**: Shows immutable trace ID, tools executed, input confidence, and safety verification status.

### Step 18: Multilingual Voice Toggle (Telugu & Hindi)
- **Action**: Switch language to Telugu and ask `"ఈరోజు నేను ఏమి చేయాలి?"`.
- **Visual**: Telugu audio response streamed from Sarvam Bulbul TTS with Telugu UI cards.

### Step 19: Offline Resilience & Network Interruption Handling
- **Action**: Enable Airplane Mode on device.
- **Visual**: Status badge shifts to `OFFLINE MODE ACTIVE`. Cached farm digital twin, scheduled tasks, and offline rules remain accessible. Safety-critical mutations requiring live weather are paused with clear feedback.

### Step 20: Honest Presentation of Field Validation Status
- **Action**: Open Field Pilot Audit status or presentation slide.
- **Statement**:
  - `REAL_FIELD_PILOT_DATA = NOT_PRESENT`
  - `PRODUCTION_STATUS = NOT_PRODUCTION_READY`
  - *"BHOOMI V2 is software-tested and controlled-pilot-ready. We do not claim production readiness until multi-season physical on-farm field validation with independent agricultural universities is completed."*
