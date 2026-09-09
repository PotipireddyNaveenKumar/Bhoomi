import hashlib
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from app.services.farm_manager.state_engine import FarmState


class FarmerThresholds(BaseModel):
    min_selling_price_per_quintal: float = 11500.0
    max_fertilizer_budget: float = 25000.0
    preferred_crops: List[str] = ["chilli", "cotton", "soybean"]
    irrigation_availability: str = "moderate"  # limited, moderate, abundant
    risk_tolerance: str = "medium"             # low, medium, high


class FarmerContactPreferences(BaseModel):
    preferred_language: str = "en"
    voice_enabled: bool = True
    reminders_enabled: bool = True
    preferred_reminder_time: str = "07:00"
    notification_channel: str = "voice"  # voice, in_app, sms
    max_daily_reminders: int = 3
    quiet_hours_start: str = "22:00"
    quiet_hours_end: str = "06:00"


class AlertStatus:
    CREATED = "CREATED"
    DELIVERED = "DELIVERED"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    DISMISSED = "DISMISSED"
    EXPIRED = "EXPIRED"
    RESOLVED = "RESOLVED"


class ProactiveAlert(BaseModel):
    alert_id: str
    category: str  # WEATHER, MARKET, STAGE, DISEASE, FINANCIAL, RISK
    severity: str  # CRITICAL, WARNING, INFO
    title: str
    message: str
    recommended_action: str
    evidence_source: str
    requires_acknowledgement: bool = False
    status: str = AlertStatus.CREATED
    trigger: str = ""
    urgency: str = "WITHIN_24_HOURS"
    expiry: str = "Within 48 hours"
    freshness: str = "CURRENT"
    dedup_hash: str = ""


class ProactiveAlertEngine:
    """
    Proactive Alert Engine.
    Monitors environmental conditions, mandi markets, disease trends, and personal thresholds.
    Implements a 6-stage alert lifecycle (CREATED, DELIVERED, ACKNOWLEDGED, DISMISSED, EXPIRED, RESOLVED)
    and deduplicates alerts to avoid alert fatigue.
    """
    _alert_registry: Dict[str, ProactiveAlert] = {}
    _acknowledged_hashes: Dict[str, str] = {}  # dedup_hash -> alert_id

    @classmethod
    def _compute_hash(cls, category: str, trigger: str, value_signature: str) -> str:
        raw = f"{category}_{trigger}_{value_signature}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]

    @classmethod
    def acknowledge_alert(cls, alert_id: str) -> Optional[ProactiveAlert]:
        alert = cls._alert_registry.get(alert_id)
        if alert:
            alert.status = AlertStatus.ACKNOWLEDGED
            if alert.dedup_hash:
                cls._acknowledged_hashes[alert.dedup_hash] = alert_id
        return alert

    @classmethod
    def dismiss_alert(cls, alert_id: str) -> Optional[ProactiveAlert]:
        alert = cls._alert_registry.get(alert_id)
        if alert:
            alert.status = AlertStatus.DISMISSED
        return alert

    @classmethod
    def resolve_alert(cls, alert_id: str) -> Optional[ProactiveAlert]:
        alert = cls._alert_registry.get(alert_id)
        if alert:
            alert.status = AlertStatus.RESOLVED
            if alert.dedup_hash in cls._acknowledged_hashes:
                del cls._acknowledged_hashes[alert.dedup_hash]
        return alert

    @classmethod
    def evaluate_alerts(
        cls,
        state: FarmState,
        thresholds: Optional[FarmerThresholds] = None,
        suppress_acknowledged: bool = True
    ) -> List[ProactiveAlert]:
        th = thresholds or FarmerThresholds()
        raw_alerts: List[ProactiveAlert] = []

        # 1. Market Selling Opportunity Alert
        market_freshness = state.data_freshness.get("market")
        is_market_unavail = market_freshness and market_freshness.freshness_status == "UNAVAILABLE"
        if not is_market_unavail and state.net_realization_per_quintal is not None and state.net_realization_per_quintal >= th.min_selling_price_per_quintal:
            diff = state.net_realization_per_quintal - th.min_selling_price_per_quintal
            trigger = "net_realization_target_exceeded"
            val_sig = f"{round(state.net_realization_per_quintal, -2)}"
            h = cls._compute_hash("MARKET", trigger, val_sig)
            raw_alerts.append(ProactiveAlert(
                alert_id=f"alert_market_{h}",
                category="MARKET",
                severity="INFO",
                title="Mandi Target Price Reached",
                message=f"Current Net Realization at {state.best_mandi_name} is ₹{state.net_realization_per_quintal:,.0f}/Q (₹{diff:,.0f} above your minimum ₹{th.min_selling_price_per_quintal:,.0f} target).",
                recommended_action="Review harvest readiness and consider scheduling mandi dispatch.",
                evidence_source=market_freshness.source if market_freshness else "AGMARKNET Guntur APMC Feed",
                requires_acknowledgement=False,
                trigger=trigger,
                freshness=market_freshness.freshness_status if market_freshness else "CURRENT",
                dedup_hash=h
            ))

        # 2. Weather Alert
        rain_prob = state.weather_summary.get("rain_probability") or 0
        if rain_prob >= 50:
            trigger = "rain_prob_gte_50"
            val_sig = f"{rain_prob // 10 * 10}"
            h = cls._compute_hash("WEATHER", trigger, val_sig)
            raw_alerts.append(ProactiveAlert(
                alert_id=f"alert_weather_{h}",
                category="WEATHER",
                severity="WARNING",
                title="Rainfall Forecast Alert",
                message=f"Precipitation probability is elevated ({rain_prob}%). Waterlogging and chemical runoff risk detected.",
                recommended_action="Hold planned irrigation and chemical spraying for 48 hours; clear drainage channels.",
                evidence_source="IMD Agro-Meteorological Bulletin",
                requires_acknowledgement=True,
                trigger=trigger,
                freshness=state.data_freshness.get("weather", {}).freshness_status if hasattr(state.data_freshness.get("weather"), "freshness_status") else "CURRENT",
                dedup_hash=h
            ))

        # 3. Stage & Pollinator Safety Alert
        if state.crop_stage.lower() == "flowering":
            trigger = "stage_flowering"
            val_sig = state.active_crop
            h = cls._compute_hash("STAGE", trigger, val_sig)
            raw_alerts.append(ProactiveAlert(
                alert_id=f"alert_stage_{h}",
                category="STAGE",
                severity="WARNING",
                title="Flowering Stage Pollinator Protection",
                message=f"Your {state.active_crop} crop is in flowering. Broad-spectrum daytime insecticides endanger pollinating honeybees.",
                recommended_action="Spray only bio-pesticides or approved formulations after 5:30 PM.",
                evidence_source="CIBRC Pollinator Safety Protocol",
                requires_acknowledgement=True,
                trigger=trigger,
                freshness="CURRENT",
                dedup_hash=h
            ))

        # Deduplicate and register
        final_alerts: List[ProactiveAlert] = []
        seen_hashes = set()

        for a in raw_alerts:
            if a.dedup_hash in seen_hashes:
                continue
            seen_hashes.add(a.dedup_hash)

            # Check if previously registered
            if a.alert_id in cls._alert_registry:
                existing = cls._alert_registry[a.alert_id]
                a.status = existing.status

            if suppress_acknowledged and a.dedup_hash in cls._acknowledged_hashes:
                # Suppress re-notifying already acknowledged alerts unless condition materially changes
                continue

            cls._alert_registry[a.alert_id] = a
            final_alerts.append(a)

        return final_alerts

    @classmethod
    def evaluate_task_nudges(
        cls,
        tasks: List[Any],
        preferences: Optional[FarmerContactPreferences] = None,
        current_time_str: Optional[str] = None,
        state: Optional[FarmState] = None
    ) -> List[ProactiveAlert]:
        """
        Generates proactive nudges and smart reminders for scheduled, overdue, and postponed tasks.
        Respects quiet hours, notification caps, and reminder preferences.
        Deduplicates reminders to prevent alert fatigue.
        """
        pref = preferences or FarmerContactPreferences()
        if not pref.reminders_enabled:
            return []

        # Check quiet hours (e.g. 22:00 to 06:00)
        from datetime import datetime, timezone
        if current_time_str:
            time_part = current_time_str
        else:
            time_part = datetime.now(timezone.utc).strftime("%H:%M")

        q_start = pref.quiet_hours_start
        q_end = pref.quiet_hours_end
        if q_start > q_end:  # Over midnight: e.g. 22:00 to 06:00
            if time_part >= q_start or time_part < q_end:
                return []
        else:
            if q_start <= time_part < q_end:
                return []

        nudges: List[ProactiveAlert] = []
        for t in tasks:
            from app.schemas.task import TaskStatus
            task_status = getattr(t, "status", None)
            is_overdue = getattr(t, "is_overdue", False)
            task_id = getattr(t, "task_id", "task_unknown")
            task_title = getattr(t, "title", "Scheduled Farm Task")

            if is_overdue:
                trigger = f"overdue_{task_id}"
                h = cls._compute_hash("REMINDER", trigger, "OVERDUE")
                nudges.append(ProactiveAlert(
                    alert_id=f"nudge_overdue_{h}",
                    category="REMINDER",
                    severity="WARNING",
                    title=f"Overdue Task: {task_title}",
                    message=f"Your scheduled task '{task_title}' is overdue. Would you like to complete or reschedule it?",
                    recommended_action="Complete task or say 'Postpone by two days'.",
                    evidence_source="TaskIntelligenceEngine Schedule Monitor",
                    requires_acknowledgement=True,
                    trigger=trigger,
                    freshness="CURRENT",
                    dedup_hash=h
                ))
            elif task_status == TaskStatus.DUE:
                trigger = f"due_today_{task_id}"
                h = cls._compute_hash("REMINDER", trigger, "DUE")
                nudges.append(ProactiveAlert(
                    alert_id=f"nudge_due_{h}",
                    category="REMINDER",
                    severity="INFO",
                    title=f"Task Due Today: {task_title}",
                    message=f"Your task '{task_title}' is due today ({getattr(t, 'reason', '')}).",
                    recommended_action="Execute task today or record status via voice.",
                    evidence_source="TaskIntelligenceEngine",
                    requires_acknowledgement=False,
                    trigger=trigger,
                    freshness="CURRENT",
                    dedup_hash=h
                ))
            elif task_status == TaskStatus.POSTPONED:
                trigger = f"postponed_{task_id}"
                h = cls._compute_hash("REMINDER", trigger, "POSTPONED")
                nudges.append(ProactiveAlert(
                    alert_id=f"nudge_postponed_{h}",
                    category="REMINDER",
                    severity="INFO",
                    title=f"Task Postponed: {task_title}",
                    message=f"Task '{task_title}' is postponed: {getattr(t, 'postponement_reason', 'Delay scheduled')}.",
                    recommended_action="No immediate action required until rescheduled window.",
                    evidence_source="WeatherDecisionEngine",
                    requires_acknowledgement=False,
                    trigger=trigger,
                    freshness="CURRENT",
                    dedup_hash=h
                ))

        # Enforce max daily reminders and deduplication
        final_nudges = []
        seen = set()
        for n in nudges:
            if n.dedup_hash in seen:
                continue
            seen.add(n.dedup_hash)
            if n.dedup_hash in cls._acknowledged_hashes:
                continue
            cls._alert_registry[n.alert_id] = n
            final_nudges.append(n)
            if len(final_nudges) >= pref.max_daily_reminders:
                break

        return final_nudges
