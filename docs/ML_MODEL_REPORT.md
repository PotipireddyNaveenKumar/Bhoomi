# BHOOMI V2 — Machine Learning Benchmark & Model Report

## 1. Crop Recommendation Model Benchmark

### Dataset
- **Source**: Cleaned Indian Agro-Climatic Dataset (`data/organized/tabular/crop_recommendation/crop_recommendation.csv`)
- **Features (7)**: `nitrogen`, `phosphorus`, `potassium`, `temperature`, `humidity`, `ph`, `rainfall`
- **Target**: `crop` (22 classes: rice, maize, chickpea, kidneybeans, pigeonpeas, mothbeans, mungbean, blackgram, lentil, pomegranate, banana, mango, grapes, watermelon, muskmelon, apple, orange, papaya, coconut, cotton, jute, coffee)
- **Train/Test Split**: 80/20 Stratified K-Fold

### Benchmark Results
| Model Candidate | 5-Fold CV Macro-F1 | Test Accuracy | Test Macro-F1 | Deployment Status |
|---|---|---|---|---|
| **RandomForestClassifier** | **0.9931** | **0.9955** | **0.9955** | **PROMOTED TO PRODUCTION** |
| ExtraTreesClassifier | 0.9937 | 0.9955 | 0.9955 | Candidate |
| XGBoostClassifier | 0.9914 | 0.9932 | 0.9931 | Candidate |
| GradientBoostingClassifier | 0.9869 | 0.9886 | 0.9887 | Baseline |
| DecisionTreeClassifier | 0.9841 | 0.9795 | 0.9794 | Baseline |
| LogisticRegression | 0.9678 | 0.9727 | 0.9725 | Linear Baseline |

**Saved Artifacts**: `models/crop_recommendation/` (`crop_recommendation_model.joblib`, `crop_scaler.joblib`, `crop_label_encoder.joblib`, `metadata.json`).

---

## 2. Yield Prediction Regressor Benchmark

### Dataset
- **Source**: Indian Multivariate Agricultural Yield Dataset (`crop_yield_multivariate.csv`)
- **Predictors**: `crop`, `season`, `state`, `area`, `annual_rainfall`, `fertilizer`, `pesticide`
- **Leakage Prevention**: Strictly excluded `production` because $\text{Yield} = \text{Production} / \text{Area}$.
- **Target**: `yield` (metric tonnes per hectare)

### Benchmark Results
| Regressor Candidate | 3-Fold CV $R^2$ | Test $R^2$ | Test MAE (t/ha) | Test RMSE | Deployment Status |
|---|---|---|---|---|---|
| **XGBoostRegressor** | 0.9225 | **0.9574** | **0.8192** | **2.5421** | **PROMOTED TO PRODUCTION** |
| GradientBoostingRegressor | 0.9237 | 0.9563 | 0.9969 | 2.5723 | Candidate |
| RandomForestRegressor | **0.9315** | 0.9542 | 0.8348 | 2.6360 | Candidate |
| ExtraTreesRegressor | 0.9360 | 0.9509 | 0.8575 | 2.7280 | Candidate |
| Ridge Regression | 0.7187 | 0.7462 | 2.7215 | 6.2024 | Linear Baseline |

**Saved Artifacts**: `models/yield_prediction/` (`yield_prediction_pipeline.joblib`, `metadata.json`).

---

## 3. Fertilizer Recommendation Engine

### Architecture
$$\text{Soil Nutrient Ratios (N, P, K, pH)} \longrightarrow \text{Deficiency Classification} \longrightarrow \text{ICAR/SAU Package of Practices} \longrightarrow \text{SafetyEngine Guard} \longrightarrow \text{Farmer Dosage Advisory}$$

- **Safety Interception**: Prevents arbitrary chemical mixtures or toxic overdoses.
- **Stage Specificity**: Custom dosage splits for Vegetative, Flowering, and Fruit Enlargement stages.
