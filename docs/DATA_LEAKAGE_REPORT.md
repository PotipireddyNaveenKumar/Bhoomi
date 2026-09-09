# BHOOMI V2 — Data Leakage & Feature Hygiene Report

## 1. Leakage Analysis Summary
Agricultural yield modeling is notoriously prone to target leakage when post-harvest statistics (such as total recorded production or sales volume) are included alongside pre-sowing predictors. This report defines the strict feature isolation rules enforced in BHOOMI V2.

## 2. Dataset Leakage Audits
| Dataset | Duplicate Rows | Target Leakage Risk | Temporal / Spatial Risk | Approval Status |
|---|---|---|---|---|
| **crop_recommendation** | 0 | None (features are independent environmental and soil readings) | None (non-temporal point measurements) | `APPROVED` |
| **fertilizer_recommendation** | 0 | None (nutrient requirement based on soil deficiencies) | None | `APPROVED` |
| **crop_yield_multivariate** | 0 | Caution: Production and Area are mathematically related to Yield (Yield = Production / Area). Production must NOT be used as a predictor feature during training to avoid target leakage. | Year-based splitting recommended. | `APPROVED_WITH_GUARD (Drop 'production' during training)` |

## 3. Strict Feature Isolation Rules Enforced
1. **Production Exclusion**: In `crop_yield_multivariate`, `production` is strictly excluded from training features because `yield = production / area`. Using production guarantees artificial ~1.0 R² in training while failing completely on farmer forward-looking planning queries.
2. **Pre-Sowing / Forward-Looking Separation**: Predictive yield models rely strictly on pre-season variables: `crop`, `state`, `district`, `season`, `area_acres`, historical `annual_rainfall`, and planned `fertilizer` / `pesticide` application.
3. **Train-Test Independence**: Scalers and encoders are fit strictly on training splits.