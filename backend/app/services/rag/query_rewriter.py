"""
Controlled Query Expansion & Rewriting Service for BHOOMI Agricultural RAG.
Generates focused retrieval queries preserving farmer's intent without making
unsupported diagnostic assumptions.

Rule: Rewriting is strictly for candidate RETRIEVAL, not clinical diagnosis.
"""
from typing import List
from app.services.rag.query_understanding import QueryUnderstandingResult


class QueryRewriter:
    """
    Produces deterministic, controlled query expansions across multilingual terms.
    """

    @classmethod
    def rewrite(cls, parsed: QueryUnderstandingResult) -> List[str]:
        queries: List[str] = [parsed.original_query]

        crop = parsed.crop or ""
        symptoms = parsed.symptoms
        intent = parsed.intent

        # 1. Foliar symptom / disease / pest diagnosis queries
        if intent in ["CROP_SYMPTOM", "PEST_QUERY", "DISEASE_QUERY"] or symptoms:
            if "leaf_curling" in symptoms:
                if crop:
                    queries.extend([
                        f"{crop} leaf curling causes",
                        f"{crop} leaf curl symptoms pests disease",
                        f"{crop} leaf curling water stress soil moisture",
                        f"{crop} leaf curl sucking pests thrips mites whitefly"
                    ])
                else:
                    queries.extend([
                        "crop leaf curling causes",
                        "leaf curl symptoms pests disease",
                        "leaf curling water stress"
                    ])
            elif "yellowing_chlorosis" in symptoms:
                if crop:
                    queries.extend([
                        f"{crop} yellow leaves chlorosis causes",
                        f"{crop} nitrogen deficiency yellowing",
                        f"{crop} yellow leaves waterlogging micronutrient"
                    ])
                else:
                    queries.extend([
                        "yellow leaves chlorosis causes",
                        "nitrogen deficiency yellow leaves",
                        "micronutrient deficiency iron zinc yellow leaves"
                    ])
            elif "spots_blight" in symptoms:
                if crop:
                    queries.extend([
                        f"{crop} leaf spots blight management",
                        f"{crop} early blight late blight fungal spots",
                        f"{crop} brown spots lesions fungicide spray"
                    ])
                else:
                    queries.extend([
                        "leaf spots blight fungal disease",
                        "brown spots on leaves management"
                    ])
            elif "fruit_rot" in symptoms:
                if crop:
                    queries.extend([
                        f"{crop} fruit rot anthracnose pod rot",
                        f"{crop} blossom end rot calcium deficiency"
                    ])
                else:
                    queries.append("fruit rot anthracnose management")
            elif parsed.pest:
                if crop:
                    queries.extend([
                        f"{crop} {parsed.pest} control management",
                        f"{crop} {parsed.pest} damage symptoms ipm"
                    ])
                else:
                    queries.append(f"{parsed.pest} control management ipm")

        # 2. Spray Weather Safety Queries
        elif intent == "SPRAY_WEATHER_SAFETY":
            loc_str = ""
            if parsed.location and parsed.location.get("district"):
                loc_str = parsed.location["district"]
            queries.extend([
                "weather safety rules for spraying agrochemicals",
                "safe spraying conditions wind rain temperature limits",
                f"can i spray agrochemicals weather conditions {loc_str}".strip(),
                "cibrc safe pesticide spraying meteorological parameters"
            ])

        # 3. Irrigation Queries
        elif intent == "IRRIGATION_QUERY":
            if crop:
                queries.extend([
                    f"when to irrigate {crop} critical growth stages",
                    f"{crop} irrigation water requirements soil moisture tension",
                    "tensiometer soil moisture sensor interpretation irrigation"
                ])
            else:
                queries.extend([
                    "when to irrigate critical growth stages",
                    "soil tension awc interpretation irrigation",
                    "drip irrigation water saving schedule"
                ])

        # 4. Fertilizer Queries
        elif intent == "FERTILIZER_QUERY":
            if crop:
                queries.extend([
                    f"{crop} fertilizer dose npk recommendation",
                    f"{crop} balanced fertilization soil health card"
                ])
            else:
                queries.extend([
                    "how much fertilizer should i apply general principles",
                    "balanced npk fertilization soil health card missing crop"
                ])

        # 5. Soil Queries
        elif intent == "SOIL_QUERY":
            if parsed.soil == "black_cotton_soil":
                queries.extend([
                    "black cotton soil vertisols suitable crops management",
                    "black soil drainage broad bed furrow chilli cotton"
                ])
            elif parsed.soil == "saline_alkaline_soil":
                queries.extend([
                    "reclamation of saline alkaline sodic soils gypsum",
                    "green manuring dhaincha soil salinity management"
                ])
            elif parsed.soil == "red_sandy_loam":
                queries.extend([
                    "red sandy loam alfisols soil management groundnut",
                    "red soil water retention fym organic matter"
                ])
            else:
                queries.append("soil testing soil health card interpretation")

        # 6. Economics / Profit Queries
        elif intent in ["PROFIT_SIMULATION", "ECONOMICS"]:
            if crop:
                queries.extend([
                    f"{crop} cost of cultivation economics yield per acre",
                    f"one acre {crop} profit margin cost breakdown"
                ])
            else:
                queries.append("crop economics cost of cultivation profit per acre")

        # 7. Market / Sell Decision Queries
        elif intent == "SELL_DECISION":
            if crop:
                queries.extend([
                    f"should i sell {crop} now or hold cold storage",
                    f"{crop} warehousing moisture content price realization"
                ])
            else:
                queries.append("sell now vs cold storage warehousing decision framework")

        # 8. Government Schemes
        elif intent == "GOVERNMENT_SCHEME":
            orig_lower = parsed.original_query.lower()
            if "kisan" in orig_lower or "pm-kisan" in orig_lower:
                queries.append("pm-kisan eligibility installment 6000 financial assistance")
            elif "bima" in orig_lower or "insurance" in orig_lower or "pmfby" in orig_lower:
                queries.append("pmfby crop insurance localized risk claim 72 hours")
            elif "drip" in orig_lower or "subsidy" in orig_lower or "pmksy" in orig_lower:
                queries.append("pmksy per drop more crop drip irrigation subsidy percentage")
            elif "kcc" in orig_lower or "credit" in orig_lower:
                queries.append("kisan credit card kcc 4% interest collateral free loan")
            else:
                queries.extend([
                    "pm-kisan scheme eligibility guidelines",
                    "pmfby crop insurance guidelines"
                ])

        # Fallback query with crop if not already present
        if crop and not any(crop in q for q in queries):
            queries.append(f"{crop} agronomy package of practices")

        # Deduplicate while preserving order
        seen = set()
        deduped = []
        for q in queries:
            q_norm = q.strip().lower()
            if q_norm not in seen and len(q_norm) > 2:
                seen.add(q_norm)
                deduped.append(q)

        return deduped[:5]
