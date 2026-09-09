# Model Card: Multivariate Crop Yield Prediction Regressor (v2.0)

## Model Details
- **Model Name**: BHOOMI Crop Yield Prediction Pipeline
- **Model ID**: `yield_prediction_v2`
- **Model Version**: `v2.0-production`
- **Model Type**: `XGBoostRegressor` (100 estimators, max_depth=6) wrapped in a scikit-learn `Pipeline` with `ColumnTransformer`
- **Framework**: `xgboost 2.1+`, `scikit-learn 1.6+`
- **Production Status**: `PROVISIONALLY_VALIDATED`

---

## Dataset Description
- **Dataset**: `crop_yield_multivariate.csv` (Compiled agricultural statistics across Indian states and districts, 1997–2020)
- **Total Historical Records**: 19,689 rows
- **Pre-Filtering**: Cleaned to remove non-positive yields, non-positive areas, and extreme unphysical outliers ($> 100$ t/ha).
- **Dominant Focus**: Top 20 Indian agricultural crops by representation (12,105 cleaned records).

### Features
| Feature Name | Type | Unit | Preprocessing | Description |
|---|---|---|---|---|
| `crop` | Categorical | String | `OneHotEncoder(handle_unknown='ignore')` | Crop name (Rice, Wheat, Maize, Cotton, Chilli, etc.) |
| `season` | Categorical | String | `OneHotEncoder(handle_unknown='ignore')` | Agricultural season (Kharif, Rabi, Summer, Whole Year) |
| `state` | Categorical | String | `OneHotEncoder(handle_unknown='ignore')` | Indian state / union territory |
| `area` | Numeric | Hectares | `StandardScaler()` | Cultivated plot area |
| `annual_rainfall` | Numeric | mm | `StandardScaler()` | Annual cumulative regional rainfall |
| `fertilizer` | Numeric | Metric Tonnes | `StandardScaler()` | Total fertilizer consumed in area |
| `pesticide` | Numeric | Metric Tonnes | `StandardScaler()` | Total pesticide consumed in area |

### Target Variable
- **Target**: `yield`
- **Unit**: Metric Tonnes per Hectare (t/ha).
- **Leakage Isolation**: The dataset column `production` was **strictly excluded** from features to eliminate mathematical leakage ($\text{Yield} \equiv \text{Production} / \text{Area}$).

---

## Training & Preprocessing Process
1. **Pipeline Architecture**:
   ```
   Pipeline([
       ('preprocessor', ColumnTransformer([
           ('num', StandardScaler(), ['area', 'annual_rainfall', 'fertilizer', 'pesticide']),
           ('cat', OneHotEncoder(handle_unknown='ignore', sparse_output=False), ['crop', 'season', 'state'])
       ])),
       ('regressor', XGBRegressor(n_estimators=100, max_depth=6, random_state=42))
   ])
   ```
2. **Train/Test Splitting**: 80/20 train/test split (`random_state=42`), $N_{\text{train}} = 9,684$, $N_{\text{test}} = 2,421$.
3. **Preprocessing Hygiene**: Both `StandardScaler` and `OneHotEncoder` are fit strictly on $X_{\text{train}}$ inside the scikit-learn pipeline, eliminating data leakage.

---

## Performance & Validation Metrics (Holdout Test Set $N=2,421$)
- **$R^2$ Score**: 0.9574
- **Mean Absolute Error (MAE)**: 0.8192 t/ha
- **Root Mean Squared Error (RMSE)**: 2.5421 t/ha
- **Median Absolute Error**: 0.2436 t/ha
- **Mean Residual**: -0.0470 t/ha (near zero bias)
- **Temporal Holdout (2016–2020, $N=2,559$)**: $R^2 = 0.9891$, $\text{MAE} = 0.4923$ t/ha
- **Geographic Andhra Pradesh Holdout ($N=773$)**: $R^2 = 0.9912$, $\text{MAE} = 0.5190$ t/ha

---

## Performance By Crop Category
1. **High Accuracy Crops (Grains & Fibers)**:
   - **Wheat**: Actual Mean = 2.09 t/ha, MAE = 0.296 t/ha, $R^2 = 0.866$
   - **Rice**: Actual Mean = 2.22 t/ha, MAE = 0.344 t/ha, $R^2 = 0.480$
   - **Bajra**: Actual Mean = 1.92 t/ha, MAE = 0.538 t/ha, $R^2 = 0.947$
   - **Dry Chillies**: Actual Mean = 2.00 t/ha, MAE = 0.881 t/ha, $R^2 = 0.739$
2. **High-Yield Root & Tuber Crops (Higher Residual Magnitude)**:
   - **Sugarcane**: Actual Mean = 48.10 t/ha, MAE = 6.168 t/ha ($R^2 = 0.861$). Residual scale reflects large base tonnage.
   - **Potato**: Actual Mean = 11.73 t/ha, MAE = 1.857 t/ha ($R^2 = 0.794$).
   - **Onion**: Actual Mean = 11.39 t/ha, MAE = 2.547 t/ha ($R^2 = 0.743$).
3. **Low-Variance Pulse Crops (Flat Yield Distribution)**:
   - **Moong (Green Gram)**: Actual Mean = 0.51 t/ha, MAE = 0.191 t/ha.
   - **Gram**: Actual Mean = 0.88 t/ha, MAE = 0.299 t/ha.
   - **Arhar / Tur**: Actual Mean = 0.86 t/ha, MAE = 0.298 t/ha.
   - *Note*: While absolute MAE is very low (<0.3 t/ha), within-crop $R^2$ is negative due to narrow variance clustering near 0.5–0.9 t/ha.

---

## Prediction Intervals & Uncertainty Method
- **Current Method**: The API currently generates an empirical residual band of $\pm 12\%$ around the point forecast.
- **Statistical Assessment**: This is an **estimated empirical uncertainty range**, NOT a formal statistically calibrated conformal prediction interval or quantile regression interval.
- **Recommendation**: Implement Conformalized Quantile Regression (CQR) or Split Conformal Prediction in Phase 4 to guarantee exact 90% coverage guarantees.

---

## Sanity & Boundary Stress Testing
| Test Input | Input Profile | Predicted Yield (t/ha) | Safety Evaluation |
|---|---|---|---|
| Normal Wheat | 2 ha, Punjab, Rabi, 650mm rain | 4.38 t/ha | Realistic (matches Punjab state average ~4.2–4.5 t/ha) |
| Arid Moong | 0.5 ha, Rajasthan, 200mm rain | 0.46 t/ha | Realistic (arid pulse harvest baseline) |
| Zero Rainfall | 2 ha, Punjab, 0mm rainfall | 2.51 t/ha | Safe floor enforced; reflects residual/borewell capacity |
| Massive Area | 500 ha, Andhra Pradesh, Rice | 2.45 t/ha | Safe (does not blow up with large acreage) |

---

## Intended & Prohibited Use
- **Intended Use**: Pre-sowing yield estimation, operational harvest planning, and financial revenue forecasting for small and marginal farmers.
- **Prohibited / Unsafe Use**: Must NOT be used for insurance claim settlements or crop loss compensation without independent remote sensing (satellite NDVI) or crop-cutting experiment (CCE) ground validation.
