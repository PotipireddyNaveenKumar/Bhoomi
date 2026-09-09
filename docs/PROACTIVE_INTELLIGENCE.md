# BHOOMI V2 — Proactive Intelligence, Change Detection & Alerts

## 1. "What Changed?" Engine
`FarmChangeDetectionService` performs structured delta analysis between consecutive check-ins:
- **Weather Delta**: Tracks shifts in precipitation probability ($\ge 15\%$), temperature anomalies, and humidity spikes.
- **Market Delta**: Flags shifts in modal spot price ($\ge 3\%$) and alerts when net realization crosses target thresholds.
- **Crop Stage Delta**: Automatically handles lifecycle transitions (e.g. Vegetative $\rightarrow$ Flowering) and loads stage-specific tasks.

---

## 2. Personal Farm Thresholds
Farmers can customize operational thresholds:
- Minimum acceptable selling price (₹/Q)
- Maximum chemical/fertilizer budget (₹)
- Preferred crops
- Irrigation availability (limited, moderate, abundant)
- Risk tolerance (low, medium, high)

> [!IMPORTANT]
> Safety rules and ICAR package-of-practices always override unsafe farmer preferences.

---

## 3. Event-Driven Proactive Alerts
Monitors environmental triggers and dispatches high-priority notifications:
- **Rain Warning**: Rain probability $\ge 50\%$ $\rightarrow$ irrigation and foliar sprays deferred.
- **Pollinator Safety Warning**: Flowering crop $\rightarrow$ insecticide application restricted to late evening.
- **Market Peak Alert**: Mandi price reaches target threshold $\rightarrow$ harvest logistics triggered.
