# BHOOMI V2 — Personal Crop Planner & Adaptive Farm Plan

## 1. Multi-Objective Transparent Crop Ranking
The `PersonalCropPlanner` evaluates candidate crops across 6 weighted dimensions:
$$\text{Composite Score} = 0.25 \cdot \text{AgriFit} + 0.30 \cdot \text{FinFit} + 0.15 \cdot \text{WaterFit} + 0.15 \cdot \text{MarketFit} + 0.15 \cdot \text{PrefScore}$$

### Ranking Example (3 Acres, Black Soil, Guntur, Kharif)
| Rank | Crop | Composite Score | Expected Yield | Gross Revenue | Total Cost | Net Profit | Duration |
|---|---|---|---|---|---|---|---|
| **#1** | **Chilli** | **89.5/100** | **10.0 Q/acre** | ₹3,66,000 | ₹70,000 | **₹2,96,000** | 150 days |
| **#2** | **Cotton** | **84.5/100** | **8.0 Q/acre** | ₹1,72,800 | ₹32,000 | **₹1,40,800** | 160 days |
| **#3** | **Soybean** | **81.2/100** | **7.5 Q/acre** | ₹1,03,500 | ₹16,000 | **₹87,500** | 95 days |
| **#4** | **Maize** | **80.5/100** | **24.0 Q/acre** | ₹1,54,800 | ₹22,000 | **₹1,32,800** | 100 days |

---

## 2. Adaptive Contingency Playbooks
`FarmPlan` embeds pre-calculated contingencies:
1. **Rainfall Deficit (>25% below normal)**:
   - Alternate furrow irrigation intervals.
   - Potassium Silicate anti-transpirant spray to maintain leaf turgor.
   - Organic straw mulching.
2. **Market Price Crash (>15% below ₹11,000/Q)**:
   - Produce deposit in certified Guntur cold storage (~₹35/bag/month).
   - Regional mandi transport arbitrage analysis (Khammam vs Warangal).
