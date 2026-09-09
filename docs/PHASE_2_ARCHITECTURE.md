# BHOOMI V2 — Phase 2 Architecture: Personal AI Farm Manager

## 1. System Vision
BHOOMI V2 transforms from an agricultural voice chatbot into an autonomous **Personal AI Farm Manager & Agricultural Decision Intelligence Platform**.
It continuously tracks:
- **Who the farmer is**: Profile, preferences, language (`te`, `hi`, `en`, `ta`, `kn`, `ml`), historical crops.
- **Where the farm is**: Coordinates, soil type, irrigation source, microclimate.
- **What crop is being grown**: Current crop, variety, sowing date, lifecycle stage.
- **Decision Intelligence Loop**:
  $$\text{ASK} \longrightarrow \text{REMEMBER} \longrightarrow \text{PLAN} \longrightarrow \text{MONITOR} \longrightarrow \text{PREDICT} \longrightarrow \text{COMPARE} \longrightarrow \text{DECIDE} \longrightarrow \text{REMIND} \longrightarrow \text{ADAPT}$$

---

## 2. Layered Architecture

```mermaid
graph TD
    VoiceUI[Flutter Mobile App / Sarvam Voice Orb] --> VoiceGateway[Unified Voice Interact API]
    VoiceGateway --> Orchestrator[BHOOMI Agent Orchestrator]
    
    subgraph Core Intelligence Engines
        Orchestrator --> MissingInfo[Missing Info Detector]
        Orchestrator --> DigitalTwin[Farm Digital Twin & Memory]
        Orchestrator --> CropML[Crop Recommendation ML (RF 0.995 F1)]
        Orchestrator --> YieldML[Yield Prediction ML (XGBoost 0.957 R²)]
        Orchestrator --> FertEngine[Fertilizer RAG & Dosage Engine]
        Orchestrator --> VisionService[Modular Plant Pathology CV Engine]
        Orchestrator --> RAGService[Agricultural RAG & Citation Engine]
        Orchestrator --> ComparisonEngine[Crop Comparison Engine]
        Orchestrator --> FinanceEngine[Deterministic Decimal Profit Engine]
        Orchestrator --> SimEngine[What-If Farm Simulator]
        Orchestrator --> RiskEngine[7-Dimension Farm Risk Engine]
        Orchestrator --> ReminderEngine[Dynamic Condition Smart Reminders]
        Orchestrator --> WeatherProvider[Weather Provider Abstraction]
        Orchestrator --> MarketProvider[Market Mandi Arbitrage Provider]
    end
    
    Orchestrator --> SafetyEngine[SafetyEngine Guardrails]
    SafetyEngine --> ResponseBuilder[Multilingual Text + Visual Cards + Sarvam Audio]
```

---

## 3. Strict Architectural Boundaries
- **Numerical Determinism**: Yield, profit, simulation, and risk values are computed by verified mathematical modules (`Decimal`), never fabricated by the LLM.
- **Evidence-Based Agronomy**: High-risk treatments and fertilizer dosages are grounded in ICAR/SAU publications via `AgriculturalRAGService` and validated by `SafetyEngine`.
- **Offline & Low Connectivity**: Cached advisory fallbacks, resilient quality gates, and transparent timestamps (`Last updated...`).
