"""
LLM Context Builder & Prompt Construction Service for BHOOMI Agricultural RAG 2.0.
Constructs a strictly partitioned context object distinguishing:
- User Question & Intent
- Retrieved RAG Evidence (with authority & confidence)
- Live Tool Results (Weather forecasts, Mandi prices)
- Farm Evidence (Digital Twin sensors, Soil moisture, Crop stage, Location)
- ML / Vision Predictions
- Secondary Task Context (Strictly secondary contextual notes, never primary answer)
- Deterministic Safety Constraints
"""
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from app.services.rag.reranker import RerankedChunk
from app.services.rag.query_understanding import QueryUnderstandingResult


class GroundedEvidenceItem(BaseModel):
    chunk_id: str
    document_id: str = "doc_0"
    document_title: str
    authority: str
    authority_tier: str
    content: str
    score: float
    source_url: Optional[str] = None
    section: Optional[str] = None
    retrieval_method: str = "hybrid"


class StructuredContextObject(BaseModel):
    user_question: str
    language: str = "en"
    intent: str
    crop: Optional[str] = None
    farm_context: Dict[str, Any] = Field(default_factory=dict)
    retrieved_evidence: List[GroundedEvidenceItem] = Field(default_factory=list)
    live_tool_results: List[Dict[str, Any]] = Field(default_factory=list)
    ml_results: List[Dict[str, Any]] = Field(default_factory=list)
    vision_results: List[Dict[str, Any]] = Field(default_factory=list)
    task_context: List[Dict[str, Any]] = Field(default_factory=list)
    safety_constraints: List[str] = Field(default_factory=list)
    has_sufficient_evidence: bool = True
    evidence_summary: str = ""


class ContextBuilder:
    """
    Constructs isolated, verified context for LLM response generation.
    """

    @classmethod
    def build_context(
        cls,
        query_info: QueryUnderstandingResult,
        reranked_chunks: List[RerankedChunk],
        farm_state: Optional[Any] = None,
        live_tools: Optional[List[Dict[str, Any]]] = None,
        ml_outputs: Optional[List[Dict[str, Any]]] = None,
        vision_outputs: Optional[List[Dict[str, Any]]] = None,
        pending_tasks: Optional[List[Any]] = None,
        safety_rules: Optional[List[str]] = None
    ) -> StructuredContextObject:
        evidence_items: List[GroundedEvidenceItem] = []
        for rc in reranked_chunks:
            meta = rc.metadata or {}
            doc_id = meta.get("id") or meta.get("chunk_id") or rc.chunk_id
            doc_title = meta.get("document_title") or meta.get("document") or f"Agricultural Advisory ({doc_id})"
            evidence_items.append(GroundedEvidenceItem(
                chunk_id=rc.chunk_id,
                document_id=str(doc_id),
                document_title=doc_title,
                authority=meta.get("authority", meta.get("source", "Agricultural Extension")),
                authority_tier=meta.get("source_authority", "tier_1"),
                content=rc.content,
                score=rc.rerank_score,
                source_url=meta.get("source_url", meta.get("url_or_ref")),
                section=meta.get("section", "Agronomic Practices"),
                retrieval_method=getattr(rc, "retrieval_method", "hybrid")
            ))

        # Build farm context from FarmState or DigitalTwinContext
        farm_ctx = {}
        if farm_state:
            if hasattr(farm_state, "soil_moisture_awc_pct") and farm_state.soil_moisture_awc_pct is not None:
                farm_ctx["soil_moisture_awc_pct"] = round(farm_state.soil_moisture_awc_pct, 1)
            elif hasattr(farm_state, "soil_moisture_percentage") and farm_state.soil_moisture_percentage is not None:
                farm_ctx["soil_moisture_pct"] = round(farm_state.soil_moisture_percentage, 1)

            if hasattr(farm_state, "soil_tension_kpa") and farm_state.soil_tension_kpa is not None:
                farm_ctx["soil_tension_kpa"] = round(farm_state.soil_tension_kpa, 1)

            if hasattr(farm_state, "active_crop") and farm_state.active_crop:
                farm_ctx["active_crop"] = farm_state.active_crop
            elif hasattr(farm_state, "active_crops") and farm_state.active_crops:
                farm_ctx["active_crops"] = farm_state.active_crops

            if hasattr(farm_state, "crop_stage") and farm_state.crop_stage:
                farm_ctx["crop_stage"] = farm_state.crop_stage

            if hasattr(farm_state, "soil_type") and farm_state.soil_type:
                farm_ctx["soil_type"] = farm_state.soil_type

            if hasattr(farm_state, "state") and farm_state.state:
                farm_ctx["state"] = farm_state.state
            if hasattr(farm_state, "district") and farm_state.district:
                farm_ctx["district"] = farm_state.district

            if hasattr(farm_state, "location") and farm_state.location:
                farm_ctx["location"] = farm_state.location

        # Build task context (Secondary only!)
        task_ctx = []
        if pending_tasks:
            for t in pending_tasks:
                if hasattr(t, "title"):
                    task_ctx.append({
                        "task_id": getattr(t, "task_id", getattr(t, "id", "task_0")),
                        "title": getattr(t, "title", ""),
                        "status": str(getattr(t, "status", "DUE")),
                        "reason": getattr(t, "reason", getattr(t, "postponement_reason", "")),
                        "evidence": getattr(t, "evidence", "")
                    })
                elif isinstance(t, dict):
                    task_ctx.append(t)

        has_sufficient = len(evidence_items) > 0 or (query_info.is_live_query and bool(live_tools))
        ev_summary = evidence_items[0].content if evidence_items else ""

        # Collect default safety constraints
        constraints = list(safety_rules) if safety_rules else []
        constraints.extend([
            "Never recommend banned organophosphate pesticides during active bloom.",
            "Mandate personal protective equipment (PPE - mask, gloves) for all chemical applications.",
            "Do not prescribe chemical doses without knowing exact crop and growth stage.",
            "Do not fabricate live weather or market prices; use only official tool outputs."
        ])

        return StructuredContextObject(
            user_question=query_info.original_query,
            language=query_info.language,
            intent=query_info.intent,
            crop=query_info.crop,
            farm_context=farm_ctx,
            retrieved_evidence=evidence_items,
            live_tool_results=live_tools or [],
            ml_results=ml_outputs or [],
            vision_results=vision_outputs or [],
            task_context=task_ctx,
            safety_constraints=constraints,
            has_sufficient_evidence=has_sufficient,
            evidence_summary=ev_summary
        )

    @classmethod
    def format_llm_prompt(cls, context: StructuredContextObject) -> str:
        """
        Constructs system and user instruction enforcing Step 18 Grounding Rules.
        """
        sections = []

        sections.append("=== BHOOMI GROUNDED AGRONOMIC CONTEXT ===")
        sections.append(f"User Question: \"{context.user_question}\"")
        sections.append(f"Language: {context.language}")
        sections.append(f"Intent: {context.intent}")
        if context.crop:
            sections.append(f"Target Crop: {context.crop.title()}")

        # RAG Evidence Section
        sections.append("\n--- VERIFIED EXTENSION EVIDENCE (RAG) ---")
        if context.retrieved_evidence:
            for idx, ev in enumerate(context.retrieved_evidence, 1):
                sections.append(
                    f"[{idx}] Source: {ev.authority} ({ev.document_title}, Section: {ev.section})\n"
                    f"    Confidence: {ev.score:.2f} | Tier: {ev.authority_tier} | Method: {ev.retrieval_method}\n"
                    f"    Content: {ev.content}"
                )
        else:
            sections.append("NO VERIFIED RAG EVIDENCE FOUND. Factual agronomic and chemical claims are STRICTLY PROHIBITED. Acknowledge uncertainty clearly or request needed farmer details. Do NOT hallucinate.")

        # Live Tool Data Section
        if context.live_tool_results:
            sections.append("\n--- LIVE TOOL REAL-TIME DATA ---")
            for t in context.live_tool_results:
                sections.append(f"• Tool: {t.get('tool_name')}: {t.get('output')}")

        # Farm Sensors / Digital Twin Evidence
        if context.farm_context:
            sections.append("\n--- FARM DIGITAL TWIN SENSOR & PROFILE EVIDENCE ---")
            for k, v in context.farm_context.items():
                sections.append(f"• {k}: {v}")

        # Secondary Task Reminders
        if context.task_context:
            sections.append("\n--- PENDING FARM TASKS (SECONDARY CONTEXT ONLY) ---")
            sections.append("NOTE: These tasks are background context. NEVER make a task status the direct answer to the farmer's question.")
            for t in context.task_context:
                sections.append(f"• Task: '{t.get('title')}' is {t.get('status')}. Context: {t.get('reason')}")

        # Safety Rules
        sections.append("\n--- MANDATORY SAFETY & GROUNDING CONSTRAINTS ---")
        for sc in context.safety_constraints:
            sections.append(f"• {sc}")
        sections.append("• If multiple causes are possible, explain that uncertainty and recommend visual inspection or photo upload.")
        sections.append(f"• Always respond in the farmer's language ({context.language}).")

        return "\n".join(sections)
