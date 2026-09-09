import os
import shutil
import pandas as pd

def organize_tabular_datasets():
    data_dir = 'data'
    org_dir = os.path.join(data_dir, 'organized')
    org_tab_dir = os.path.join(org_dir, 'tabular')
    
    os.makedirs(os.path.join(org_tab_dir, 'crop_recommendation'), exist_ok=True)
    os.makedirs(os.path.join(org_tab_dir, 'fertilizer_recommendation'), exist_ok=True)
    os.makedirs(os.path.join(org_tab_dir, 'yield_prediction'), exist_ok=True)
    os.makedirs(os.path.join(org_tab_dir, 'climate_and_risk'), exist_ok=True)
    os.makedirs(os.path.join(org_tab_dir, 'iot_smart_farming'), exist_ok=True)

    summary = []

    # 1. Clean Crop Recommendation (2,200 rows)
    crop_src = os.path.join(data_dir, 'Crop_Recommendation.csv')
    if os.path.exists(crop_src):
        df_crop = pd.read_csv(crop_src)
        df_crop.columns = ['nitrogen', 'phosphorus', 'potassium', 'temperature', 'humidity', 'ph', 'rainfall', 'crop']
        df_crop['crop'] = df_crop['crop'].str.strip().str.lower()
        df_crop.drop_duplicates(inplace=True)
        out_path = os.path.join(org_tab_dir, 'crop_recommendation', 'crop_recommendation.csv')
        df_crop.to_csv(out_path, index=False)
        num_crops = df_crop['crop'].nunique()
        summary.append({
            "category": "Crop Recommendation",
            "file": "crop_recommendation.csv",
            "rows": len(df_crop),
            "cols": df_crop.shape[1],
            "crops_count": num_crops,
            "status": "ACTIVE / PRIMARY"
        })

    # 2. Clean Fertilizer Recommendation (8,000 rows)
    fert_src = os.path.join(data_dir, 'data_core.csv')
    if os.path.exists(fert_src):
        df_fert = pd.read_csv(fert_src)
        df_fert.columns = ['temperature', 'humidity', 'moisture', 'soil_type', 'crop_type', 'nitrogen', 'potassium', 'phosphorus', 'fertilizer_name']
        df_fert['soil_type'] = df_fert['soil_type'].str.strip().str.lower()
        df_fert['crop_type'] = df_fert['crop_type'].str.strip().str.lower()
        df_fert.drop_duplicates(inplace=True)
        out_path = os.path.join(org_tab_dir, 'fertilizer_recommendation', 'fertilizer_recommendation.csv')
        df_fert.to_csv(out_path, index=False)
        summary.append({
            "category": "Fertilizer Recommendation",
            "file": "fertilizer_recommendation.csv",
            "rows": len(df_fert),
            "cols": df_fert.shape[1],
            "status": "ACTIVE / PRIMARY"
        })

    # 3. Clean India Crop Production & Yield (345k rows)
    india_src = os.path.join(data_dir, 'India Agriculture Crop Production.csv')
    if os.path.exists(india_src):
        df_india = pd.read_csv(india_src)
        df_india.columns = [c.strip().lower().replace(' ', '_') for c in df_india.columns]
        df_india_clean = df_india.dropna(subset=['area', 'production']).copy()
        df_india_clean.drop_duplicates(inplace=True)
        out_path = os.path.join(org_tab_dir, 'yield_prediction', 'india_crop_yield_district.csv')
        df_india_clean.to_csv(out_path, index=False)
        summary.append({
            "category": "India District Yield & Production",
            "file": "india_crop_yield_district.csv",
            "rows": len(df_india_clean),
            "cols": df_india_clean.shape[1],
            "status": "ACTIVE / PRIMARY"
        })

    # 4. Clean Crop Yield Multivariate (19k rows)
    yield_src = os.path.join(data_dir, 'crop_yield.csv')
    if os.path.exists(yield_src):
        df_yield = pd.read_csv(yield_src)
        df_yield.columns = [c.strip().lower().replace(' ', '_') for c in df_yield.columns]
        df_yield.drop_duplicates(inplace=True)
        out_path = os.path.join(org_tab_dir, 'yield_prediction', 'crop_yield_multivariate.csv')
        df_yield.to_csv(out_path, index=False)
        summary.append({
            "category": "Crop Yield Multivariate (Rainfall, Fert, Pest)",
            "file": "crop_yield_multivariate.csv",
            "rows": len(df_yield),
            "cols": df_yield.shape[1],
            "status": "ACTIVE / PRIMARY"
        })

    # 5. Clean Climate & Risk Impact (10k rows)
    clim_src = os.path.join(data_dir, 'climate_change_impact_on_agriculture_2024.csv')
    if os.path.exists(clim_src):
        df_clim = pd.read_csv(clim_src)
        df_clim.columns = [c.strip().lower().replace(' ', '_') for c in df_clim.columns]
        df_clim.drop_duplicates(inplace=True)
        out_path = os.path.join(org_tab_dir, 'climate_and_risk', 'climate_risk_impact.csv')
        df_clim.to_csv(out_path, index=False)
        summary.append({
            "category": "Climate Risk & Impact",
            "file": "climate_risk_impact.csv",
            "rows": len(df_clim),
            "cols": df_clim.shape[1],
            "status": "ACTIVE / PRIMARY"
        })

    # 6. Clean Smart Farming Sensors (500 rows)
    iot_src = os.path.join(data_dir, 'Smart_Farming_Crop_Yield_2024.csv')
    if os.path.exists(iot_src):
        df_iot = pd.read_csv(iot_src)
        df_iot.columns = [c.strip().lower().replace(' ', '_') for c in df_iot.columns]
        df_iot.drop_duplicates(inplace=True)
        out_path = os.path.join(org_tab_dir, 'iot_smart_farming', 'smart_farming_sensors.csv')
        df_iot.to_csv(out_path, index=False)
        summary.append({
            "category": "IoT Smart Farming Sensors",
            "file": "smart_farming_sensors.csv",
            "rows": len(df_iot),
            "cols": df_iot.shape[1],
            "status": "ACTIVE / PRIMARY"
        })

    print("Tabular Organization Complete.")
    for s in summary:
        print(s)

if __name__ == "__main__":
    organize_tabular_datasets()
