# BHOOMI V2 — Phase 3 Architecture: Autonomous Personal AI Farm Manager

## 1. System Vision
Phase 3 establishes BHOOMI as a proactive, autonomous **Personal AI Farm Manager**.
The platform operates on a continuous feedback loop:
$$\text{OBSERVE} \longrightarrow \text{UNDERSTAND} \longrightarrow \text{PREDICT} \longrightarrow \text{DECIDE} \longrightarrow \text{ACT} \longrightarrow \text{REMEMBER} \longrightarrow \text{ADAPT}$$

---

## 2. Integrated System Diagram

```mermaid
graph TD
    FarmerVoice[Farmer Voice / Flutter App] --> VoiceGateway[Unified Voice Interact API]
    VoiceGateway --> Orchestrator[BHOOMI Agent Orchestrator]

    subgraph Farm Intelligence Layer
        Orchestrator --> StateEngine[FarmStateEngine]
        StateEngine --> EventStore[FarmEventStore & Processor]
        StateEngine --> DecisionEngine[FarmDecisionEngine]
        DecisionEngine --> BriefingService[DailyFarmBriefingService]
        DecisionEngine --> ChangeDetector[FarmChangeDetectionService]
        DecisionEngine --> ProactiveAlerts[ProactiveAlertEngine]
        DecisionEngine --> WeatherDecision[WeatherDecisionEngine]
        DecisionEngine --> MarketDecision[MarketDecisionEngine]
        DecisionEngine --> IrrigationDecision[IrrigationDecisionService]
        DecisionEngine --> HarvestDecision[HarvestDecisionEngine]
        DecisionEngine --> HealthTimeline[CropHealthTimeline]
        DecisionEngine --> PersonalPlanner[PersonalCropPlanner]
        DecisionEngine --> FarmPlanMgr[Adaptive FarmPlan & Contingency]
    end

    subgraph Memory & Observability
        Orchestrator --> MemoryV2[FarmMemory 2.0]
        Orchestrator --> TraceStore[RecommendationTraceStore]
        Orchestrator --> ModelMonitor[ModelMonitoringService]
    end

    Orchestrator --> SafetyEngine[SafetyEngine Guardrails]
    SafetyEngine --> Response[Multilingual Spoken Audio + Command Center Visual Cards]
```

---

## 3. Core Operating Tenets
1. **Mathematical Determinism**: Financial ROI, net realization, yield totals, and what-if shifts are calculated in verified Python Decimal math.
2. **Authoritative Agronomy**: All pest, disease, and fertilizer recommendations are grounded in ICAR/SAU research and validated by SafetyEngine.
3. **Auditability & Explainability**: Every recommendation logs input parameters, tools executed, model versions, and safety checks into `RecommendationTraceStore`.
4. **Data Freshness**: Real-time status (`CURRENT`, `CACHED`, `STALE`) is explicitly displayed for weather and market data.
