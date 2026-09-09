# BHOOMI V2 — Phase 6 Step 1: Production Farm Decision Intelligence Hardening

## 1. Architecture Overview

Phase 6 Step 1 establishes a deterministic, explainable, evidence-grounded Decision Intelligence layer for BHOOMI V2.
The system is architected around a strict principle:
> **Deterministic agronomic engines calculate the decision; the LLM merely translates and explains.**

```
                                      FarmState
                                          ↓
                                 Freshness Validation
                     (CURRENT, CACHED, STALE, UNAVAILABLE, HISTORICAL)
                                          ↓
                                 FarmRiskAggregator
                  (WEATHER, WATER, CROP_HEALTH, MARKET, YIELD, FINANCIAL, TASK, DATA_QUALITY)
                                          ↓
                       Domain-Specific Specialized Engines
                   ├── IrrigationDecisionService (Kc & Soil Tension)
                   ├── WeatherDecisionEngine (IMD Provider Truth)
                   ├── MarketDecisionEngine (Net Realization = Modal - Freight - Cess)
                   └── CropHealthTimeline & IPM
                                          ↓
                              DecisionConflictResolver
                   (Harvest vs Rain vs Market, Spray vs Rain, Bloom Safety)
                                          ↓
                                    SafetyEngine
                     (CIBRC Banned Chemicals, PPE, Pollinator Guards)
                                          ↓
                                    DecisionPlan
                              (Canonical FarmDecisions)
                                          ↓
                             RecommendationTraceStore
                         (Full Provenance & Audit Trail)
                                          ↓
                     Farmer Explanation & Voice Delivery (Sarvam)
```

---

## 2. Canonical Farm Decision Contract

Defined in [`backend/app/schemas/decision.py`](file:///c:/Users/SURESH/SIH/backend/app/schemas/decision.py), every consequential recommendation conforms to the canonical `FarmDecision` contract:

| Field | Type | Description |
| :--- | :--- | :--- |
| `decision_id` | `str` | Unique identifier (e.g. `dec_irr_rain_delay`) |
| `farmer_id` | `str` | Farmer ID |
| `farm_id` | `str` | Farm / plot ID |
| `created_at` | `str` (ISO-8601) | Timestamp of generation |
| `decision_type` | `DecisionType` | `IRRIGATION`, `SPRAYING`, `FERTILIZATION`, `CROP_HEALTH`, `HARVEST`, `MARKET_SELL`, `MARKET_WAIT`, `CROP_PLANNING`, `WEATHER_RESPONSE`, `RISK`, `TASK`, `GENERAL_FARM_ACTION` |
| `priority` | `DecisionPriority` | `CRITICAL`, `HIGH`, `MEDIUM`, `LOW`, `INFORMATIONAL` |
| `status` | `DecisionStatus` | `PROPOSED`, `ACCEPTED`, `REJECTED`, `SUPERSEDED`, `EXECUTED` |
| `title` | `str` | Action-oriented heading |
| `summary` | `str` | High-level summary |
| `recommended_action` | `str` | Exact operational action for farmer |
| `reason` | `str` | Agronomic justification |
| `evidence` | `str` | Grounding reference (e.g., IMD advisory, ICAR protocol) |
| `confidence` | `ConfidenceLevel` | `HIGH`, `MEDIUM`, `LOW`, `INSUFFICIENT_DATA` |
| `confidence_score` | `float` (0.0–1.0) | Deterministic confidence score |
| `uncertainty` | `str` | `LOW`, `MODERATE`, `HIGH` |
| `deadline` | `str` | Action window deadline |
| `valid_until` | `str` | Expiration window |
| `data_freshness` | `Dict[str, str]` | Telemetry freshness map |
| `risks` | `List[str]` | Downside risks if ignored |
| `constraints` | `List[str]` | Operational constraints (e.g. evening spraying only) |
| `alternative_actions` | `List[str]` | Fallback actions |
| `required_information`| `List[str]` | Unmet prerequisite data |
| `source_tools` | `List[str]` | Engines participating in recommendation |
| `model_versions` | `Dict[str, str]` | AI / ML model versions used |
| `safety_status` | `str` | `VERIFIED_SAFE` or `BLOCKED` |
| `trace_id` | `str` | Cross-reference link to `RecommendationTraceStore` |

---

## 3. Priority System

Priority is calculated deterministically based on agronomic risk and deadline urgency:
- **`CRITICAL`**: Active spreading pathogens, emergency harvest prior to cyclone/storm, chemical poisoning hazard.
- **`HIGH`**: Severe moisture stress during flowering/fruit development, rain-induced spray postponement, target mandi price breached.
- **`MEDIUM`**: Routine scheduled irrigation, regular foliar nutrition, preventive field scouting.
- **`LOW`**: General intercultural weeding, drainage outlet clearing during dry spells.
- **`INFORMATIONAL`**: Weather reports, market trend updates.

---

## 4. Data Freshness Model

Every decision tracks external telemetry freshness across:
- `CURRENT`: Freshly fetched live telemetry ($< 1$ hour old).
- `CACHED`: Valid cached telemetry within TTL ($< 6$ hours).
- `STALE`: Telemetry exceeding freshness window ($> 6$ hours); triggers confidence penalty.
- `HISTORICAL`: Past seasonal snapshot; cannot be used as live market price.
- `UNAVAILABLE`: Telemetry connection down; triggers `INSUFFICIENT_DATA` and requests farmer ground check.

---

## 5. Conflict Resolution (`DecisionConflictResolver`)

When multiple domain engines produce conflicting signals, `DecisionConflictResolver` applies deterministic precedence:
1. **Spraying vs Rain**: If rain probability $\ge 50\%$ or rainfall $\ge 10\text{mm}$, spraying is put on **`HOLD`** to prevent active ingredient wash-off and chemical runoff pollution.
2. **Irrigation vs Rain**: If rain probability $\ge 40\%$, irrigation is **`DELAYED`** by 48 hours to prevent waterlogging and root hypoxia in heavy Vertisol soils.
3. **Harvest vs Rain vs Market Wait**: If a crop is mature and heavy rain ($\ge 50\%$) is forecasted, but market says `WAIT`, harvest is elevated to **`CRITICAL`** to prevent catastrophic field mold and fruit cracking. Produce is harvested and moved to covered storage.
4. **Bloom vs Daytime Spray**: If crop is in `flowering`, foliar chemical applications are restricted to evening hours after 5:30 PM to protect honeybee pollinators.

---

## 6. Risk Aggregation (`FarmRiskAggregator`)

Monitors and evaluates 8 distinct risk dimensions:
1. **`WEATHER`**: Rainfall storms, unseasonal hail, heat waves.
2. **`WATER`**: Root-zone moisture deficit vs waterlogging.
3. **`CROP_HEALTH`**: Sucking pests, foliar blights, viral complexes.
4. **`MARKET`**: Mandi price softening below cost of cultivation.
5. **`YIELD`**: Anthesis disruption and flower drop.
6. **`FINANCIAL`**: Net realization uncertainty due to unquoted freight.
7. **`TASK`**: Labor shortage and intercultural delay.
8. **`DATA_QUALITY`**: Telemetry outage or stale sensors.

---

## 7. Missing Information Detection (`MissingInformationDetector`)

Formulates concise, non-intrusive questions targeting only the minimum missing parameter:
- Asking for crop stage if fertilization is queried.
- Asking for soil type or rain cover if irrigation is queried.
- Asking for transport distance if mandi selling is queried.
- Does NOT ask for farmer names, bank details, or unnecessary personal history.

---

## 8. Alert Lifecycle & Deduplication (`ProactiveAlertEngine`)

Alerts transition through a 6-stage lifecycle:
$$\text{CREATED} \longrightarrow \text{DELIVERED} \longrightarrow \text{ACKNOWLEDGED} \longrightarrow \text{DISMISSED} \longrightarrow \text{RESOLVED}$$
*(or $\text{EXPIRED}$ if time window closes).*
- **Deduplication**: Alerts are tagged with a 16-hex `dedup_hash`. Acknowledged alerts are suppressed from re-alerting the farmer unless the underlying metric shifts significantly.

---

## 9. Recommendation Provenance & Feedback (`RecommendationTraceStore`)

Every recommendation records full provenance:
- Exact inputs, timestamps, source tools, calculations, and safety checks.
- Structured farmer feedback: `HELPFUL`, `NOT_HELPFUL`, `FOLLOWED`, `NOT_FOLLOWED`, `SUCCESSFUL`, `UNSUCCESSFUL`, `CORRECT`, `INCORRECT`.
- Stored exclusively for offline clinical evaluation; never used for uncontrolled automated retraining.

---

## 10. Safety Boundaries & LLM Constraints

1. **SafetyEngine Precedence**: No recommendation bypasses CIBRC screening. Banned chemicals (e.g. Monocrotophos) are unconditionally blocked.
2. **Offline Safety Contract**: Offline edge mode suppresses synthetic pesticide recommendations.
3. **LLM Restrictions**:
   - The LLM **cannot** invent weather forecasts or market spot prices.
   - The LLM **cannot** perform authoritative financial arithmetic (handled by `FinancialService` and `SimulationService` using Python `Decimal`).
   - The LLM **cannot** diagnose Rice (Rice remains `RESEARCH_ONLY`).
   - The LLM **cannot** override deterministic safety gates.

---

## 11. Decision API Contract

- **Endpoint**: `POST /api/v1/decisions/evaluate`
- **Request**:
  ```json
  {
    "farmer_id": "farmer_demo_1",
    "farm_id": "farm_1",
    "intent": "irrigation",
    "user_question": "Should I irrigate today?"
  }
  ```
- **Response**: Returns `DecisionEvaluationResponse` containing complete `DecisionPlan`, active `FarmDecision`s, resolved conflicts, and active risks.

---

## 12. Verification & Test Coverage

- **Suite**: `backend/tests/test_phase6_decision_intelligence.py` (28 dedicated tests).
- **Total Passing Tests**: **273/273 tests (100%)**.
