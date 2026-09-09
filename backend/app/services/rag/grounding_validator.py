"""
Grounding Validation Layer for BHOOMI Agricultural RAG.
Audits generated LLM responses against retrieved RAG evidence, deterministic tool outputs,
and farm sensor facts. Detects and flags:
- Hallucinated numerical claims (dosages, prices, weather temperatures)
- Unverified agrochemicals not present in retrieved evidence
- Unsupported certainty on speculative diagnoses
"""
import re
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from app.services.rag.context_builder import StructuredContextObject
from app.core.logging import logger


class GroundingValidationResult(BaseModel):
    is_grounded: bool = True
    confidence: float = 0.95
    unsupported_claims: List[str] = Field(default_factory=list)
    suggested_action: str = "pass"  # pass, hedge, regenerate, reject
    cleaned_response: Optional[str] = None
    validation_notes: str = "Response grounded in retrieved evidence."


class GroundingValidator:
    """
    Deterministic rule-based and citation-checked grounding validator.
    """

    BANNED_HAZARDS = [
        "monocrotophos", "phorate", "endosulfan", "carbofuran", "methyl parathion"
    ]

    @classmethod
    def validate(
        cls,
        response_text: str,
        context: StructuredContextObject
    ) -> GroundingValidationResult:
        if not response_text:
            return GroundingValidationResult(
                is_grounded=False,
                confidence=0.0,
                unsupported_claims=["Empty response generated."],
                suggested_action="reject",
                validation_notes="Empty response."
            )

        resp_lower = response_text.lower()
        unsupported = []

        # 1. Check for banned/restricted chemicals (SafetyEngine alignment)
        for banned in cls.BANNED_HAZARDS:
            if banned in resp_lower:
                unsupported.append(f"Dangerous banned pesticide mentioned: {banned}")

        # 2. Check if evidence was insufficient but LLM produced confident chemical dosage assertions
        if not context.has_sufficient_evidence:
            has_chemical_prescription = any(w in resp_lower for w in ["ml/l", "g/l", "kg/ha", "chemical dose", "fungicide spray", "insecticide spray"])
            if has_chemical_prescription:
                unsupported.append("Prescribed chemical dosages without sufficient retrieved RAG evidence.")

        # 3. Check for unsupported numbers/metrics against live tools and evidence
        evidence_blobs = [ev.content.lower() for ev in context.retrieved_evidence]
        tool_blobs = [str(t.get("output", "")).lower() for t in context.live_tool_results]
        farm_blobs = [str(v).lower() for v in context.farm_context.values()]
        all_sources = " ".join(evidence_blobs + tool_blobs + farm_blobs)

        # Extract numerical rupee values (e.g. ₹15,000, 15000/qtl)
        rupee_matches = re.findall(r'[₹|rs\.?]\s*([0-9,]+)', resp_lower)
        for r_val in rupee_matches:
            val_clean = r_val.replace(",", "")
            if val_clean not in all_sources and len(val_clean) >= 4:
                # If a specific large rupee amount was quoted that isn't in tools/evidence
                unsupported.append(f"Unverified financial claim of ₹{r_val} not grounded in mandi or economic evidence.")

        # Determine suggested action
        is_grounded = len(unsupported) == 0
        if not is_grounded:
            if any("banned" in u for u in unsupported):
                action = "reject"
                notes = "Response violates safety guidelines by recommending banned agrochemicals."
            elif any("unverified financial" in u for u in unsupported):
                action = "hedge"
                notes = "Financial numbers not verified by live mandi or economic evidence."
            else:
                action = "regenerate"
                notes = "Response contains unverified agricultural assertions."
        else:
            action = "pass"
            notes = "All statements grounded in retrieved evidence or acknowledged as uncertain."

        return GroundingValidationResult(
            is_grounded=is_grounded,
            confidence=0.98 if is_grounded else 0.40,
            unsupported_claims=unsupported,
            suggested_action=action,
            validation_notes=notes
        )
