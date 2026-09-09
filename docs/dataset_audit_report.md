# BHOOMI V2 — Dataset Audit, Cleaning & Utilization Report

## 1. Executive Summary
A comprehensive audit and cleaning pipeline was executed across all provided datasets in `data/`. The datasets were evaluated for data hygiene, duplicate removal, schema consistency, Indian agricultural relevance, and mapping into BHOOMI V2's decision intelligence modules.

---

## 2. Active Cleaned Datasets (Organized & Ready for Phase 2)

| Dataset | Category / Purpose | Cleaned Rows | Features / Key Columns | BHOOMI Target Module |
|---|---|---|---|---|
| **`crop_recommendation.csv`** | Crop Recommendation ML | 2,200 | `nitrogen`, `phosphorus`, `potassium`, `temperature`, `humidity`, `ph`, `rainfall`, `crop` (22 crops) | 🌱 **Crop Recommendation Engine** |
| **`fertilizer_recommendation.csv`** | Fertilizer Planning ML | 8,000 | `temperature`, `humidity`, `moisture`, `soil_type`, `crop_type`, `nitrogen`, `potassium`, `phosphorus`, `fertilizer_name` | 🧪 **Fertilizer Planning & Dosage** |
| **`india_crop_yield_district.csv`** | District Crop Production & Yield | 340,414 | `state`, `district`, `crop`, `year`, `season`, `area`, `production`, `yield` | 📈 **District Yield Prediction ML** |
| **`crop_yield_multivariate.csv`** | Yield with Inputs & Climate | 19,689 | `crop`, `crop_year`, `season`, `state`, `area`, `production`, `annual_rainfall`, `fertilizer`, `pesticide`, `yield` | 📈 **Yield Regressor with Input Shocks** |
| **`climate_risk_impact.csv`** | Climate & Risk Prediction | 10,000 | `temperature`, `precipitation`, `extreme_weather_events`, `irrigation_access`, `soil_health_index`, `economic_impact` | 🛡️ **Risk Engine & What-If Simulator** |
| **`smart_farming_sensors.csv`** | IoT & Sensor Crop Health | 500 | `soil_moisture_%`, `soil_ph`, `temperature_c`, `rainfall_mm`, `sunlight_hours`, `ndvi_index`, `crop_disease_status` | 📡 **Digital Twin Sensor Feeds** |

---

## 3. Computer Vision (Plant Disease Diagnosis) Datasets

| Image Dataset | Crop Focus | Image Count | Key Diseases & Classes | BHOOMI Vision Integration |
|---|---|---|---|---|
| **Chilli Plant Diseases** | Chilli (Capsicum) | 6,755 | Leaf Curl, Leaf Spot, Yellowish, Whitefly, Healthy | **Primary Crop Vision Model (High Priority)** |
| **Rice Diseases Suite** | Rice / Paddy | 8,259 | Bacterial Blight, Blast, Brown Spot, False Smut, Hispa | **Staple Crop Vision Model (High Priority)** |
| **Potato Plant Diseases** | Potato | 29,257 | Early Blight, Late Blight, Healthy | **Vegetable Crop Vision Model** |
| **Sugarcane Leaves** | Sugarcane | 19,926 | Bacterial Blight, Mosaic, Red Rot, Rust, Healthy | **Cash Crop Vision Model** |
| **Tomato Diseases (`d1`)** | Tomato | 28,785 | Leaf Blight, Leaf Curl, Septoria, Verticillium, Healthy | **Vegetable Crop Vision Model** |
| **Banana LSD** | Banana | 2,537 | Leaf Speckle Disease, Sigatoka, Healthy | **Horticulture Vision Model** |
| **Guava Disease** | Guava | 3,784 | Canker, Dot, Mummification, Rust, Healthy | **Fruit Crop Vision Model** |
| **Corn / Maize Diseases** | Corn / Maize | 2,746 | Blight, Common Rust, Gray Leaf Spot, Armyworm | **Grain Crop Vision Model** |
| **Cucumber & Pumpkin** | Cucurbits | 2,695 | Powdery Mildew, Downy Mildew, Anthracnose | **Horticulture Vision Model** |
| **Apple Disease** | Apple | 43,531 | Scab, Black Rot, Cedar Apple Rust, Healthy | **Temperate Fruit Crop Model** |

---

## 4. Unused / Excluded Datasets & Rationale

| Dataset / Folder | Type | Status | Rationale for Exclusion |
|---|---|---|---|
| **`flower_data` & `flower_data1`** (50,400 images) | Vision | ❌ **EXCLUDED** | Contains Oxford 102 ornamental flowers (petunias, lilies, roses), not agricultural crop pathology or farmer decision intelligence. |
| **`worldwide_crop_consumption.csv`** | Tabular | ❌ **EXCLUDED** | Global OECD macroeconomic consumption aggregates; not applicable to farm-level Indian agronomy. |
| **`world_food_production.csv`** | Tabular | ❌ **EXCLUDED** | Macro-level global food production summary; replaced by official 340k Indian district-wise dataset. |
| **`crop_production.csv`** | Tabular | ❌ **EXCLUDED** | OECD country-level macro index containing 100% missing metadata flags. |
| **`rice_ countries.csv`** | Tabular | ❌ **EXCLUDED** | High-level 13-row historical international production stats. |
| **`crop_yield2.csv`** (89 MB) | Tabular | ❌ **EXCLUDED** | 1,000,000 synthetic random records with uniform distribution artifacts; superseded by real verified Indian agricultural yield data. |
| **Duplicate CSVs** (`Crop_recommendation1.csv`, `crop_production1.csv`, `crop_yield1.csv`, `data_core1.csv`) | Tabular | ❌ **DEDUPLICATED** | Exact byte-for-byte or column-renamed duplicates of primary datasets. Cleaned canonical copies preserved in `data/organized/tabular/`. |

---

## 5. Organized Directory Structure

```
data/
├── organized/
│   └── tabular/
│       ├── crop_recommendation/
│       │   └── crop_recommendation.csv
│       ├── fertilizer_recommendation/
│       │   └── fertilizer_recommendation.csv
│       ├── yield_prediction/
│       │   ├── india_crop_yield_district.csv
│       │   └── crop_yield_multivariate.csv
│       ├── climate_and_risk/
│       │   └── climate_risk_impact.csv
│       └── iot_smart_farming/
│           └── smart_farming_sensors.csv
```
