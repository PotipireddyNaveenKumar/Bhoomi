# BHOOMI V2 — Phase 4 ML Generalization & Validation Report

## Executive Summary
This report provides an independent, rigorous validation of the production machine learning models currently deployed in BHOOMI V2:
- **Crop Recommendation**: `RandomForestClassifier` (22 crops, Macro-F1 = 0.9955)
- **Yield Prediction**: `XGBoostRegressor` (20 crops, $R^2 = 0.9574$, MAE = 0.8192 t/ha)

All 43 automated baseline tests pass 100%. No production artifacts or application code were modified during this audit.

---

## 1. Core Evaluation Answers

### 1. Are the current models actually generalizing?
- **Crop Recommendation**: **Yes, within its agro-climatic feature domain.** The model scores **99.55% accuracy and 0.9955 Macro-F1** on the 20% holdout test set ($N=440$). The dataset is perfectly balanced (100 samples/crop) with zero duplicate rows and zero conflicting labels. However, because the dataset possesses high cluster separability across N-P-K, temperature, and rainfall, the model operates on clean agronomic boundaries.
- **Yield Prediction**: **Yes, across both time and geography.**
  - Holdout Test ($N=2,421$): **$R^2 = 0.9574$, MAE = 0.8192 t/ha**.
  - Temporal Holdout ($2016–2020$, $N=2,559$ future records): **$R^2 = 0.9891$, MAE = 0.4923 t/ha**.
  - Geographic Holdout (Andhra Pradesh, $N=773$ records): **$R^2 = 0.9912$, MAE = 0.5190 t/ha**.
  - Median absolute error is **0.2436 t/ha**, indicating that more than 50% of predictions are within 0.24 tonnes/hectare of actual yield.

---

### 2. Is there evidence of leakage?
- **Strictly Isolated — Zero Target Leakage.**
  - In `train_yield_prediction.py`, the dataset column `production` was **strictly excluded** from feature selection (`feature_cols = ['crop', 'season', 'state', 'area', 'annual_rainfall', 'fertilizer', 'pesticide']`). Because $\text{Yield} \equiv \text{Production} / \text{Area}$, including `production` would have produced trivial mathematical leakage.
  - In both pipelines, `StandardScaler` and `OneHotEncoder` are fit **strictly on training partitions** (`X_train`) and transformed on test sets.
  - Zero duplicate rows exist between train and test splits.

---

### 3. What is the strongest model?
- **Yield Prediction (`yield_prediction_v2`)** is the mathematically stronger and more robust model in real-world agricultural conditions. It demonstrates strong generalization across multi-year temporal holdouts (2016–2020) and handles unseen categories safely via `handle_unknown='ignore'`.
- While Crop Recommendation boasts a 0.9955 Macro-F1, this is partially an artifact of the clean benchmark dataset geometry rather than complex noisy field dynamics.

---

### 4. What are the weakest classes / crops?
- **In Crop Recommendation**:
  - `rice`: F1 = 0.950 (precision 0.950, recall 0.950). Confused slightly with `jute` due to similar requirements for heavy rainfall (>200mm) and high humidity.
  - `jute`: F1 = 0.976 (precision 0.952, recall 1.000).
  - `maize`: F1 = 0.974 (precision 1.000, recall 0.950). Minor boundary overlap with `blackgram`.
  - `blackgram`: F1 = 0.976 (precision 0.952, recall 1.000).
- **In Yield Prediction**:
  - Pulse crops with low variance: `Arhar/Tur` (MAE = 0.298 t/ha), `Gram` (MAE = 0.299 t/ha), `Moong` (MAE = 0.191 t/ha), and `Sesamum` (MAE = 0.298 t/ha).
  - *Finding*: While the absolute error on pulses is very small (<0.3 t/ha), the within-crop $R^2$ is negative because the historical yield of these crops is very flat (0.5 to 0.9 t/ha). The multi-crop XGBoost tree splits primarily prioritize the global scale (from 0.5 t/ha for pulses to 48 t/ha for sugarcane).

---

### 5. Where does yield prediction perform poorly?
- **High-Yield Root & Tuber Crops**:
  - `Sugarcane`: MAE = 6.168 t/ha (mean actual: 48.10 t/ha).
  - `Onion`: MAE = 2.547 t/ha (mean actual: 11.39 t/ha).
  - `Potato`: MAE = 1.857 t/ha (mean actual: 11.73 t/ha).
  - *Reason*: Residual scale correlates with base crop tonnage. A 10% error on sugarcane is ~5 t/ha, whereas a 10% error on wheat is only ~0.2 t/ha.

---

### 6. Are geographic and temporal tests possible?
- **Crop Recommendation**:
  - **Geographic validation is not possible with this dataset.** `crop_recommendation.csv` contains only biochemical and meteorological measurements; state and district coordinates are absent.
  - **Temporal validation is unavailable.** Seasonal timestamps or multi-year tracking are absent.
- **Yield Prediction**:
  - **Both Geographic and Temporal validations are fully possible and verified.**
  - Temporal holdout (2016–2020) validated: MAE = 0.4923 t/ha ($R^2 = 0.9891$).
  - Geographic state holdout (Andhra Pradesh) validated: MAE = 0.5190 t/ha ($R^2 = 0.9912$).

---

### 7. Are prediction intervals trustworthy?
- **Current Status**: **Empirical Heuristic Band ($\pm 12\%$).**
- In `yield_service.py:71-73`, the 90% confidence interval is generated via a fixed heuristic multiplier (`total_quintals * 0.88` to `total_quintals * 1.12`).
- **Audit Verdict**: It is **NOT** a statistically calibrated confidence interval (e.g. from Conformalized Quantile Regression). While it provides a reasonable operational buffer for farmers, it should be formally documented as an *"estimated empirical uncertainty range"* until conformal calibration is added.

---

### 8. What should be improved before production?
1. **Conformal Prediction Intervals**: Replace the fixed $\pm 12\%$ heuristic with Split Conformal Prediction or Quantile XGBoost to provide mathematically guaranteed 90% coverage intervals.
2. **Crop-Grouped Ensembles**: Train specialized sub-models for:
   - Staple cereals & cash crops (Rice, Wheat, Maize, Cotton, Chillies)
   - High-tonnage tubers & canes (Potato, Onion, Sugarcane)
   - Low-yield pulse crops (Gram, Moong, Urad, Tur)
3. **Pydantic Pre-Validation in Recommendation Service**: Mirror the boundary validation checks in the API schema to reject out-of-range sensor spikes.

---

### 9. What data is needed next?
1. **Soil Health Card (SHC) Empirical Datasets**: Real field soil test lab results with natural measurement variance to validate the Crop Recommendation model against noisy farmer inputs.
2. **District-Level Mandi & Weather Linkages**: Link hyper-local daily weather station data (rainfall distribution during flowering rather than annual cumulative sum) to enhance yield forecasting resolution.
3. **Cultivar-Specific Yield Data**: Differentiate yields by cultivar (e.g., Guntur Teja Chilli vs. Byadagi Chilli).

---

## 2. Production Readiness Classifications

| Model | ID | Assigned Classification | Primary Justification |
|---|---|---|---|
| **Crop Recommendation** | `crop_recommendation_v2` | `PROVISIONALLY_VALIDATED` | 0.9955 Macro-F1 across 22 crops with zero leakage and perfect class balance. Provisional because dataset lacks geographic/temporal fields and exhibits benchmark-level cluster separation. |
| **Yield Prediction** | `yield_prediction_v2` | `PROVISIONALLY_VALIDATED` | 0.9574 $R^2$ with zero leakage, verified temporal holdout ($R^2=0.9891$), and verified geographic holdout. Provisional pending crop-specific error scaling and conformal prediction intervals. |

---

## 3. Regression Protection Confirmation
The complete test suite was executed after generating reports and model cards:
```bash
python -m pytest backend/tests -v
======================= 43 passed, 60 warnings in 2.84s =======================
```
All 43 tests continue passing with zero regressions.
