# Model Card: Crop Recommendation Engine (v2.0)

## Model Details
- **Model Name**: BHOOMI Crop Recommendation Engine
- **Model ID**: `crop_recommendation_v2`
- **Model Version**: `v2.0-production`
- **Model Type**: `RandomForestClassifier` (100 estimators, stratified)
- **Framework**: `scikit-learn 1.6+`
- **Production Status**: `PROVISIONALLY_VALIDATED`

---

## Dataset Description
- **Dataset**: `crop_recommendation.csv` (Curated ICAR/Kaggle agro-climatic benchmark)
- **Total Samples**: 2,200
- **Class Balance**: Perfectly balanced across 22 crops (exactly 100 samples per crop)
- **Duplicate Rows**: 0 (0.0%)
- **Conflicting Labels**: 0 (0.0%)

### Features
| Feature Name | Type | Unit | Range in Dataset | Agronomic Interpretation |
|---|---|---|---|---|
| `nitrogen` | Numeric (int) | Ratio index (N) | 0 to 140 | Soil available nitrogen |
| `phosphorus` | Numeric (int) | Ratio index (P) | 5 to 145 | Soil available phosphorus |
| `potassium` | Numeric (int) | Ratio index (K) | 5 to 205 | Soil available potassium |
| `temperature` | Numeric (float) | °C | 8.8 to 43.7 | Mean ambient seasonal temperature |
| `humidity` | Numeric (float) | % | 14.3 to 99.9 | Relative humidity |
| `ph` | Numeric (float) | pH scale | 3.5 to 9.9 | Soil acidity/alkalinity |
| `rainfall` | Numeric (float) | mm | 20.2 to 298.6 | Seasonal cumulative rainfall |

### Target
- **Target Variable**: `crop`
- **Classes (22)**: `apple`, `banana`, `blackgram`, `chickpea`, `coconut`, `coffee`, `cotton`, `grapes`, `jute`, `kidneybeans`, `lentil`, `maize`, `mango`, `mothbeans`, `mungbean`, `muskmelon`, `orange`, `papaya`, `pigeonpeas`, `pomegranate`, `rice`, `watermelon`.

---

## Training & Preprocessing Process
1. **Label Encoding**: `LabelEncoder` maps 22 crop strings to integer targets [0..21].
2. **Train/Test Splitting**: Stratified 80/20 train/test split (`random_state=42`), preserving class ratios (80 train / 20 test per crop).
3. **Feature Scaling**: `StandardScaler` fitted **strictly on training set** (`X_train`), and applied via `.transform()` to `X_test` and production inference inputs.
4. **Target Leakage**: None. All features represent pre-sowing soil and climate inputs.

---

## Performance & Validation Metrics (Holdout Test Set $N=440$)
- **Accuracy**: 99.55%
- **Macro Precision**: 0.9957
- **Macro Recall**: 0.9955
- **Macro F1-Score**: 0.9955
- **Weighted F1-Score**: 0.9955

### Strongest Classes (F1 = 1.000)
- `apple`, `banana`, `chickpea`, `coconut`, `coffee`, `cotton`, `grapes`, `kidneybeans`, `lentil`, `mango`, `mothbeans`, `mungbean`, `muskmelon`, `orange`, `papaya`, `pigeonpeas`, `pomegranate`, `watermelon`.

### Weakest Classes (F1 < 0.980)
- `rice`: Precision = 0.950, Recall = 0.950, F1 = 0.950 (minor confusion with `jute` due to similar high-moisture/rainfall profile).
- `jute`: Precision = 0.952, Recall = 1.000, F1 = 0.976.
- `maize`: Precision = 1.000, Recall = 0.950, F1 = 0.974 (minor confusion with `blackgram`).
- `blackgram`: Precision = 0.952, Recall = 1.000, F1 = 0.976.

---

## Limitations & Edge Cases
1. **Geographic Limitation**: **Geographic validation is not possible with this dataset** because state, district, and coordinates are absent from `crop_recommendation.csv`.
2. **Temporal Limitation**: **Temporal validation is unavailable** as seasonal timestamps or multi-year tracking are absent.
3. **Synthetic / Curated Nature**: The dataset features very clean cluster boundaries with low intra-class variance. Real-world soil test reports exhibit higher measurement noise and sensor variability.
4. **Cultivar Specificity**: Does not differentiate specific high-yielding hybrids or pest-resistant cultivars (e.g. Teja Chilli, BT Cotton, BPT 5204 Paddy).

---

## Intended & Prohibited Use
- **Intended Use**: Initial agronomic filtering and candidate crop shortlisting based on regional Soil Health Card (SHC) parameters.
- **Prohibited / Unsafe Use**: Must NOT be used as the sole determinant for agricultural credit approval or single-crop mono-cropping mandates without local agricultural extension officer (AEO) or KVK ground-truthing.
