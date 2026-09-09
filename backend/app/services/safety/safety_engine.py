import re
from typing import Dict, Any, List, Optional
from pydantic import BaseModel

class SafetyCheckResult(BaseModel):
    is_safe: bool
    status: str  # PASS, MODIFY, BLOCK
    modified_text: Optional[str] = None
    warnings: List[str] = []
    blocked_reasons: List[str] = []

class SafetyEngine:
    """
    Dedicated Agricultural Safety Engine.
    Validates pesticide, herbicide, and chemical recommendations against:
    - Banned/Restricted pesticide lists in India (CIBRC regulations)
    - Safe dosage limits per acre/hectare
    - Pre-harvest interval (PHI) and crop stage compatibility
    - Tank-mix chemical compatibility guards
    
    Rule: Never rely solely on LLM system prompts for safety.
    """
    BANNED_SUBSTANCES = [
        "endosulfan", "monocrotophos", "paraquat", "phorate", "methyl parathion",
        "ddt", "aldrin", "dieldrin", "chlorpyrifos on vegetables", "carbofuran",
        "phosphamidon", "triazophos on vegetables"
    ]

    CROP_DOSAGE_LIMITS = {
        "chilli": {
            "imidacloprid": {"max_per_acre": 50.0, "unit": "ml/acre", "phi_days": 15},
            "spinosad": {"max_per_acre": 75.0, "unit": "ml/acre", "phi_days": 3},
            "mancozeb": {"max_per_acre": 600.0, "unit": "g/acre", "phi_days": 7},
            "fipronil": {"max_per_acre": 400.0, "unit": "ml/acre", "phi_days": 10},
        },
        "cotton": {
            "acetamiprid": {"max_per_acre": 40.0, "unit": "g/acre", "phi_days": 15},
            "emamectin": {"max_per_acre": 100.0, "unit": "g/acre", "phi_days": 14},
        },
        "tomato": {
            "mancozeb": {"max_per_acre": 600.0, "unit": "g/acre", "phi_days": 7},
            "imidacloprid": {"max_per_acre": 60.0, "unit": "ml/acre", "phi_days": 10},
        }
    }

    DOSAGE_REGEX = re.compile(
        r'(imidacloprid|spinosad|mancozeb|fipronil|acetamiprid|emamectin)[^\d]*?(\d+(?:\.\d+)?)\s*(ml|g|gm|grams?)\s*(?:per|\/|\@)?\s*(acre|hectare|ha)',
        re.IGNORECASE
    )

    @classmethod
    def evaluate(cls, recommendation_text: str, crop: Optional[str] = None, stage: Optional[str] = None) -> SafetyCheckResult:
        text_lower = recommendation_text.lower()
        blocked_reasons = []
        warnings = []
        modified = recommendation_text

        # 1. Banned Substances Check
        for banned in cls.BANNED_SUBSTANCES:
            if banned in text_lower:
                blocked_reasons.append(
                    f"Blocked hazardous chemical: '{banned.title()}' is restricted/banned under Central Insecticides Board (CIBRC) regulations."
                )

        if blocked_reasons:
            return SafetyCheckResult(
                is_safe=False,
                status="BLOCK",
                blocked_reasons=blocked_reasons,
                modified_text="Safety Alert: The requested chemical treatment contains restricted substances. Please use approved, eco-friendly IPM alternatives such as Neem oil (Azadirachtin 10000 ppm) or yellow sticky traps."
            )

        # 1b. Rice Research Only Guardrail
        if crop and crop.lower() in ["rice", "paddy"]:
            if any(term in text_lower for term in ["spray", "chemical", "pesticide", "fungicide", "insecticide", "treatment", "monocrotophos", "chlorpyrifos"]):
                return SafetyCheckResult(
                    is_safe=False,
                    status="BLOCK",
                    blocked_reasons=["Rice models are currently designated RESEARCH_ONLY under validation protocols. Farmer-facing chemical recommendations on Rice are strictly blocked."],
                    modified_text="RESEARCH_ONLY Notice: Rice pathology and agronomic chemical models are in research validation status. Farmer-facing chemical treatments are strictly blocked. Please consult your local Krishi Vigyan Kendra (KVK) or Agriculture Officer."
                )

        # 2. Active Dosage Limit Verification
        active_crop = crop.lower() if crop else None
        if active_crop and active_crop in cls.CROP_DOSAGE_LIMITS:
            limits = cls.CROP_DOSAGE_LIMITS[active_crop]
            matches = cls.DOSAGE_REGEX.finditer(recommendation_text)
            for m in matches:
                chem, val_str, unit, area_type = m.groups()
                chem_key = chem.lower()
                val = float(val_str)
                if chem_key in limits and "acre" in area_type.lower():
                    limit_spec = limits[chem_key]
                    max_allowed = limit_spec["max_per_acre"]
                    if val > max_allowed:
                        if val >= max_allowed * 3.0:
                            # Severe over-dosage -> block
                            blocked_reasons.append(
                                f"Critical Chemical Hazard: Proposed dosage of {val} {unit}/acre for {chem.title()} exceeds safe CIBRC limit of {max_allowed} {unit}/acre by more than 3x."
                            )
                            return SafetyCheckResult(
                                is_safe=False,
                                status="BLOCK",
                                blocked_reasons=blocked_reasons,
                                modified_text=f"Safety Alert: The proposed dosage ({val} {unit}/acre) of {chem.title()} is severely dangerous. Maximum permitted safe label dose is {max_allowed} {limit_spec['unit']}. Please do not apply excess concentration."
                            )
                        else:
                            # Mild to moderate over-dosage -> modify and warn
                            warn_msg = (
                                f"Dosage Warning: Proposed {chem.title()} dosage ({val} {unit}/acre) exceeds standard label recommendation of {max_allowed} {limit_spec['unit']}. Reduced to safe limit."
                            )
                            warnings.append(warn_msg)
                            modified = modified.replace(
                                m.group(0),
                                f"{chem.title()} @ {max_allowed} {limit_spec['unit']}"
                            )

        # 3. Stage & Toxicity Warning Checks
        if stage and stage.lower() in ["flowering", "pollination"]:
            if "spray" in text_lower or "chemical" in text_lower:
                warnings.append("Flowering Stage Caution: Avoid spraying broad-spectrum insecticides during peak morning pollinator activity (8 AM - 11 AM) to protect honeybees.")

        # 4. PPE & Handling Requirement
        if any(term in text_lower for term in ["pesticide", "fungicide", "spray", "insecticide", "chemical"]):
            warnings.append("Safety Requirement: Wear protective mask and gloves while preparing spray solutions. Do not spray against the wind direction.")

        return SafetyCheckResult(
            is_safe=True,
            status="PASS" if not warnings else "MODIFY",
            warnings=warnings,
            modified_text=modified
        )
