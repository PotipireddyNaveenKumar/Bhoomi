from typing import List, Dict, Any, Tuple
from app.schemas.decision import FarmDecision, DecisionType, DecisionPriority


class DecisionConflictResolver:
    """
    Deterministic Decision Conflict Resolver.
    Identifies mutually conflicting recommendations across domain engines
    (e.g., Harvest vs Weather vs Market, Spraying vs Rain, Irrigation vs Rain)
    and resolves them using deterministic agricultural hierarchy and safety rules.
    """

    @classmethod
    def resolve_conflicts(
        cls,
        decisions: List[FarmDecision],
        weather_summary: Dict[str, Any],
        crop_stage: str,
        has_storage: bool = True
    ) -> Tuple[List[FarmDecision], List[Dict[str, Any]]]:
        """
        Reconciles decisions and returns (resolved_decisions, conflict_logs).
        """
        resolved: List[FarmDecision] = []
        conflict_logs: List[Dict[str, Any]] = []

        rain_prob = weather_summary.get("rain_probability") or 0
        rainfall_mm = weather_summary.get("rainfall_mm") or 0.0

        # Index decisions by type
        dec_by_type: Dict[DecisionType, List[FarmDecision]] = {}
        for d in decisions:
            dec_by_type.setdefault(d.decision_type, []).append(d)

        # Conflict Rule 1: Spraying vs Imminent Rain (Rain Prob >= 50% or rainfall >= 10mm)
        # Chemical sprays wash off in rain, causing financial waste and chemical runoff pollution.
        if rain_prob >= 50 or rainfall_mm >= 10.0:
            spraying_decisions = dec_by_type.get(DecisionType.SPRAYING, []) + [
                d for d in decisions if d.decision_type in [DecisionType.CROP_HEALTH, DecisionType.FERTILIZATION]
                and "spray" in d.recommended_action.lower()
            ]
            for sd in spraying_decisions:
                conflict_logs.append({
                    "conflict_type": "SPRAYING_VS_IMMINENT_RAIN",
                    "competing_signals": [
                        f"Action: {sd.recommended_action}",
                        f"Weather: Rain probability {rain_prob}%, rainfall {rainfall_mm}mm"
                    ],
                    "resolution": "HOLD_SPRAYING",
                    "reasoning": "Chemical foliar wash-off hazard. Spraying postponed until 24 hours post-rainfall."
                })
                # Reconfigure decision to a HOLD / DELAY
                sd.priority = DecisionPriority.HIGH
                sd.title = f"Hold Spraying: Rain Expected ({rain_prob}%)"
                sd.recommended_action = f"Postpone foliar application by 48 hours until canopy dries."
                sd.reason = f"Imminent rainfall ({rain_prob}% probability, {rainfall_mm}mm) will wash off chemical active ingredients."
                sd.deadline = "Post-rainfall"
                sd.risks.append("Chemical wash-off and non-target runoff contamination if sprayed before rain.")

        # Conflict Rule 2: Irrigation vs Imminent Rain (Rain Prob >= 40% or rainfall >= 10mm)
        # Delay surface irrigation to prevent root hypoxia and waterlogging.
        if rain_prob >= 40 or rainfall_mm >= 10.0:
            irrigation_decisions = dec_by_type.get(DecisionType.IRRIGATION, [])
            for id_dec in irrigation_decisions:
                if "delay" not in id_dec.recommended_action.lower() and "postpone" not in id_dec.recommended_action.lower():
                    conflict_logs.append({
                        "conflict_type": "IRRIGATION_VS_RAIN_FORECAST",
                        "competing_signals": [
                            f"Action: {id_dec.recommended_action}",
                            f"Weather: Rain probability {rain_prob}%"
                        ],
                        "resolution": "DELAY_IRRIGATION",
                        "reasoning": "Precipitation will naturally recharge soil moisture; prevents waterlogging."
                    })
                    id_dec.title = "Delay Irrigation: Rain In Forecast"
                    id_dec.recommended_action = "Postpone Surface Irrigation by 48 Hours"
                    id_dec.reason = f"Rain forecast ({rain_prob}% probability, ~{rainfall_mm}mm) provides adequate moisture."
                    id_dec.priority = DecisionPriority.HIGH

        # Conflict Rule 3: Harvest vs Weather Rain Risk vs Market Wait
        # If crop is mature (Harvest recommended), rain is expected, but market says WAIT:
        # Agronomic spoilage from rain > speculative price gain.
        harvest_decs = dec_by_type.get(DecisionType.HARVEST, [])
        market_wait_decs = dec_by_type.get(DecisionType.MARKET_WAIT, [])
        if harvest_decs and (rain_prob >= 50 or rainfall_mm >= 15.0):
            for hd in harvest_decs:
                if market_wait_decs:
                    conflict_logs.append({
                        "conflict_type": "HARVEST_NOW_VS_MARKET_WAIT_VS_RAIN",
                        "competing_signals": [
                            "Harvest: Mature crop ready for picking",
                            f"Weather: Imminent heavy rain ({rain_prob}%)",
                            "Market: Speculative price wait recommended"
                        ],
                        "resolution": "EXPEDITE_HARVEST_AND_STORE",
                        "reasoning": (
                            "Field spoilage and fungal rot risk from rain outweighs speculative price gains. "
                            "Harvest immediately and hold in protective storage or covered yard."
                            if has_storage else
                            "Harvest selectively and arrange immediate covered transport to prevent rain rot."
                        )
                    })
                    hd.priority = DecisionPriority.CRITICAL
                    hd.title = "Emergency Harvest: Complete Picking Before Rain"
                    hd.recommended_action = "Expedite selective harvest of mature produce before rainfall starts."
                    hd.reason = f"Rain ({rain_prob}%) will cause fruit cracking, mold, and secondary fungal rot in ripe pods."
                    # Adjust market wait priority
                    for md in market_wait_decs:
                        md.priority = DecisionPriority.LOW
                        md.summary += " (Deferred pending safe harvest and drying)."

        # Conflict Rule 4: Flowering Stage vs Daytime Pesticide Spray
        if crop_stage.lower() == "flowering":
            spray_decs = [
                d for d in decisions if d.decision_type in [DecisionType.SPRAYING, DecisionType.CROP_HEALTH, DecisionType.FERTILIZATION]
                and "spray" in d.recommended_action.lower()
            ]
            for sd in spray_decs:
                if "evening" not in sd.recommended_action.lower():
                    conflict_logs.append({
                        "conflict_type": "FLOWERING_STAGE_POLLINATOR_PROTECTION",
                        "competing_signals": [
                            f"Action: {sd.recommended_action}",
                            "Stage: Peak Flowering (Honeybee & pollinator activity)"
                        ],
                        "resolution": "RESTRICT_SPRAY_TIMING_TO_EVENING",
                        "reasoning": "Daytime spraying kills honeybees and beneficial pollinators, severely reducing fruit set."
                    })
                    sd.recommended_action += " (Strictly spray after 5:30 PM in the evening)"
                    sd.constraints.append("CIBRC Pollinator Guard: Zero daytime foliar applications during peak bloom.")

        # Re-sort decisions deterministically: CRITICAL -> HIGH -> MEDIUM -> LOW -> INFORMATIONAL
        priority_order = {
            DecisionPriority.CRITICAL: 0,
            DecisionPriority.HIGH: 1,
            DecisionPriority.MEDIUM: 2,
            DecisionPriority.LOW: 3,
            DecisionPriority.INFORMATIONAL: 4,
        }
        decisions.sort(key=lambda x: priority_order.get(x.priority, 5))

        return decisions, conflict_logs
