# Phase 4 Step 2: Real LLM Provider Activation & Tool Integration Architecture

**Platform**: BHOOMI V2 — Voice-First Personal AI Farm Manager & Agricultural Decision Intelligence Platform  
**Phase**: Phase 4 — Real-World Readiness & Generalization Audit  
**Step**: Step 2 — Real LLM Provider Activation & Tool Grounding  
**Status**: COMPLETE  
**Test Suite**: 48/48 tests passing (43 baseline tests + 5 real LLM integration tests)

---

## 1. Executive Summary

Phase 4 Step 2 activates production-grade real LLM providers (**OpenAI**, **Google Gemini**, and **Groq**) within BHOOMI V2's decision intelligence loop while strictly preserving the existing `MockLLMProvider` as the zero-cost, deterministic baseline for automated testing and CI/CD pipelines.

The integration establishes an uncompromising security and agronomic boundary:
- **Zero Frontend Secret Exposure**: API keys reside strictly on the backend (`settings` / `.env`), never sent to Flutter clients.
- **Zero Secret Logging**: Authentication headers are kept in private instances; API keys are never written to stdout, log files, or error tracebacks.
- **Strict Calculation Isolation**: The LLM is **forbidden** from performing arithmetic, hallucinating weather forecasts, inventing mandi prices, or making up crop yields. All quantitative reasoning is delegated to deterministic domain tools.
- **Mandatory Safety Engine Gate**: All LLM responses pass through `SafetyEngine.evaluate()` before delivery to the farmer, blocking banned pesticides (CIBRC regulations) and injecting pollinator precautions.

```
+-----------------------------------------------------------------------------------+
|                        BHOOMI AGENT ORCHESTRATION PIPELINE                         |
+-----------------------------------------------------------------------------------+
                                          |
                                          v
                              [1. Farmer Query / Voice]
                                          |
                                          v
                           [2. Digital Twin Context Match]
                                          |
                                          v
                             [3. Intent & Tool Selection]
                               (OpenAI / Gemini / Groq)
                                          |
                    +---------------------+---------------------+
                    |                                           |
           (No Tool Needed)                                (Tool Called)
                    |                                           |
                    |                         +-----------------+-----------------+
                    |                         | Deterministic Execution:          |
                    |                         | - ML Crop Recommendation          |
                    |                         | - ML Yield Prediction (XGBoost)   |
                    |                         | - FinancialService (Decimal math) |
                    |                         | - WeatherService (Govt/Agro API)  |
                    |                         | - MarketService (Agmarknet)       |
                    |                         +-----------------+-----------------+
                    |                                           |
                    |                         [4. Structured Tool Output Received]
                    |                                           |
                    |                         [5. Farmer Explanation Synthesis]
                    |                            (LLM grounded in tool data)
                    +---------------------+---------------------+
                                          |
                                          v
                            [6. SafetyEngine Evaluation]
                       (CIBRC Banned Chemicals, PHI, Pollinators)
                                          |
                                          v
                      [7. Structured Visual Cards + Farmer Voice]
                                          |
                                          v
                        [8. Recommendation Trace Recorded]
```

---

## 2. Configurable Provider Architecture

The active LLM provider is resolved dynamically at runtime through environment variables:

```bash
# Set in backend/.env or system environment:
LLM_PROVIDER=openai     # Options: "openai" | "gemini" | "groq" | "mock"

# Backend-only Secret Keys (Never sent to Flutter, never logged):
OPENAI_API_KEY=sk-proj-...
GEMINI_API_KEY=...
GROQ_API_KEY=gsk_...
```

### Provider Resolution Table

| `LLM_PROVIDER` | Active Provider Class | Default Model | API Endpoint | Fallback Behavior |
| :--- | :--- | :--- | :--- | :--- |
| `openai` | `OpenAIProvider` | `gpt-4o-mini` | `https://api.openai.com/v1/chat/completions` | Falls back to `MockLLMProvider` on missing key, 429 quota, or timeout |
| `gemini` | `GeminiProvider` | `gemini-1.5-flash` | `https://generativelanguage.googleapis.com/v1beta/openai` | Falls back to `MockLLMProvider` on missing key, 404, or timeout |
| `groq` | `OpenAIProvider` | `llama-3.3-70b-versatile` | `https://api.groq.com/openai/v1/chat/completions` | Falls back to `MockLLMProvider` on missing key or network error |
| `mock` *(default)* | `MockLLMProvider` | Deterministic Mock | In-Memory | Primary provider for CI/CD and offline tests |

---

## 3. Code Implementations

### 3.1 LLM Factory (`backend/app/services/llm/factory.py`)

Resolves the provider and guarantees zero crashes:

```python
def get_llm_provider(provider_name: Optional[str] = None) -> LLMProvider:
    name = (provider_name or os.environ.get("LLM_PROVIDER") or settings.LLM_PROVIDER).lower().strip()
    
    if name == "openai":
        api_key = os.environ.get("OPENAI_API_KEY") or settings.OPENAI_API_KEY
        if api_key and not api_key.startswith("your_"):
            return OpenAIProvider(api_key=api_key, model="gpt-4o-mini", provider_name="openai")
        return MockLLMProvider()

    elif name == "gemini":
        api_key = os.environ.get("GEMINI_API_KEY") or settings.GEMINI_API_KEY
        if api_key and not api_key.startswith("your_"):
            return GeminiProvider(api_key=api_key, model="gemini-1.5-flash")
        return MockLLMProvider()

    elif name == "groq":
        api_key = os.environ.get("GROQ_API_KEY") or settings.GROQ_API_KEY
        if api_key and not api_key.startswith("your_"):
            return OpenAIProvider(
                api_key=api_key,
                base_url="https://api.groq.com/openai/v1",
                model="llama-3.3-70b-versatile",
                provider_name="groq"
            )
        return MockLLMProvider()

    else:
        return MockLLMProvider()
```

### 3.2 Real LLM Provider (`backend/app/services/llm/openai_provider.py`)

Converts BHOOMI's `ToolRegistry` schema into standard OpenAI / Groq function calling specifications, parses structured JSON tool arguments, and encapsulates network timeouts and exceptions:

```python
class OpenAIProvider(LLMProvider):
    def _format_tools(self, tools: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        return [{
            "type": "function",
            "function": {
                "name": t["name"],
                "description": t["description"],
                "parameters": t.get("parameters", {"type": "object", "properties": {}})
            }
        } for t in tools]
```

### 3.3 Complete 5-Step Tool Synthesis in Orchestrator (`backend/app/agents/orchestrator.py`)

When tools are identified by the LLM:
1. **Understand farmer intent**: LLM receives farmer query alongside farm Digital Twin context (crop, acre, soil, village).
2. **Select tools**: LLM picks tools from `ToolRegistry` (e.g., `calculate_profit`, `recommend_crops`, `predict_crop_yield`).
3. **Pass structured arguments**: Exact numerical parameters passed as JSON (e.g. `production_quintals: 30, price: 12000, cost: 70000`).
4. **Execute deterministically**: `ToolRegistry.execute_tool` runs local Python domain service; creates visual cards.
5. **Feed tool results to LLM**: Real LLM synthesizes natural, reassuring farmer advisory in the farmer's preferred language using **only** the deterministic tool outputs.
6. **SafetyEngine verification**: Inspects the final text for banned agrochemicals and issues safety warnings before returning to farmer.

---

## 4. Verification and Non-Negotiable Guardrails

### 4.1 Agronomic Guardrail Enforcement

| Rule | Implementation Mechanism | Enforced By |
| :--- | :--- | :--- |
| **No LLM Financial Math** | Financial calculations use Python `Decimal` arithmetic exclusively in `FinancialService.calculate_profit`. | `ToolRegistry` + `FinancialService` |
| **No Hallucinated Weather** | Weather conditions and precipitation forecasts are fetched from deterministic APIs. | `WeatherService` |
| **No Hallucinated Mandi Prices** | Prices are queried from authenticated Agmarknet data feeds. | `MarketService` |
| **No Hallucinated ML Predictions** | Crop suitability and yields are calculated by serialized Scikit-Learn / XGBoost models. | `CropRecommendationService`, `YieldPredictionService` |
| **No Unsafe Chemical Recommendations** | Any mention of banned substances (e.g., Monocrotophos, Endosulfan, Paraquat) is blocked immediately. | `SafetyEngine.evaluate()` |

### 4.2 Automated Test Suite Results

```bash
$ python -m pytest backend/tests -v
======================= 48 passed, 60 warnings in 4.21s =======================
```

- **Phase 1 Baseline**: 13/13 tests PASSED
- **Phase 2 Baseline**: 14/14 tests PASSED
- **Phase 3 Baseline**: 16/16 tests PASSED
- **Phase 4 Real LLM Suite**: 5/5 tests PASSED (`backend/tests/test_phase4_real_llm.py`)
  1. `test_llm_factory_resolution`: Confirms dynamic resolution for `openai`, `gemini`, `groq`, and `mock`.
  2. `test_real_llm_tool_schema_formatting`: Verifies JSON Schema compliance for function definitions.
  3. `test_real_llm_graceful_fallback_on_network_error`: Verifies zero crash policy on network/auth failure.
  4. `test_orchestrator_five_step_tool_loop`: Verifies full 5-step intent -> tool -> execution -> card -> trace pipeline.
  5. `test_safety_engine_blocks_unsafe_chemicals_in_orchestrator`: Confirms CIBRC banned chemical override.

**Total**: **48 / 48 PASSING (100%)**
