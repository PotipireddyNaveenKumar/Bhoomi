import os
import sys
sys.path.insert(0, os.path.abspath('backend'))
import json
import joblib
import pandas as pd
import numpy as np

from sklearn.model_selection import train_test_split, KFold, cross_val_score
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.linear_model import Ridge
from sklearn.ensemble import RandomForestRegressor, ExtraTreesRegressor, GradientBoostingRegressor
import xgboost as xgb

def train_and_benchmark_yield_prediction():
    data_path = "data/organized/tabular/yield_prediction/crop_yield_multivariate.csv"
    model_dir = "models/yield_prediction"
    os.makedirs(model_dir, exist_ok=True)

    print("--- BENCHMARKING CROP YIELD REGRESSION MODELS ---")
    df = pd.read_csv(data_path)

    # Feature isolation: Strictly EXCLUDE 'production' to prevent target leakage (Yield = Production / Area)
    # Filter realistic yields (< 100 metric tonnes/ha)
    df_clean = df[(df['yield'] > 0) & (df['yield'] <= 100) & (df['area'] > 0)].copy()

    # Drop any nulls
    df_clean.dropna(subset=['crop', 'season', 'state', 'area', 'annual_rainfall', 'fertilizer', 'pesticide', 'yield'], inplace=True)

    # Focus on top 20 dominant crops to keep one-hot dimensions robust
    top_crops = df_clean['crop'].value_counts().nlargest(20).index
    df_filtered = df_clean[df_clean['crop'].isin(top_crops)].copy()

    feature_cols = ['crop', 'season', 'state', 'area', 'annual_rainfall', 'fertilizer', 'pesticide']
    cat_cols = ['crop', 'season', 'state']
    num_cols = ['area', 'annual_rainfall', 'fertilizer', 'pesticide']

    X = df_filtered[feature_cols].copy()
    y = df_filtered['yield'].copy()

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    preprocessor = ColumnTransformer(
        transformers=[
            ('num', StandardScaler(), num_cols),
            ('cat', OneHotEncoder(handle_unknown='ignore', sparse_output=False), cat_cols)
        ]
    )

    candidate_regressors = {
        "Ridge": Ridge(alpha=1.0, random_state=42),
        "RandomForest": RandomForestRegressor(n_estimators=100, max_depth=15, random_state=42, n_jobs=-1),
        "ExtraTrees": ExtraTreesRegressor(n_estimators=100, max_depth=15, random_state=42, n_jobs=-1),
        "GradientBoosting": GradientBoostingRegressor(n_estimators=100, max_depth=5, random_state=42),
        "XGBoost": xgb.XGBRegressor(n_estimators=100, max_depth=6, random_state=42, n_jobs=-1)
    }

    benchmark_results = {}
    best_model_name = None
    best_r2 = -999.0
    trained_pipelines = {}

    cv = KFold(n_splits=3, shuffle=True, random_state=42)

    for name, reg in candidate_regressors.items():
        pipe = Pipeline(steps=[
            ('preprocessor', preprocessor),
            ('regressor', reg)
        ])

        cv_scores = cross_val_score(pipe, X_train, y_train, cv=cv, scoring="r2", n_jobs=-1)
        pipe.fit(X_train, y_train)
        preds = pipe.predict(X_test)

        mae = mean_absolute_error(y_test, preds)
        rmse = np.sqrt(mean_squared_error(y_test, preds))
        r2 = r2_score(y_test, preds)

        benchmark_results[name] = {
            "cv_mean_r2": round(float(np.mean(cv_scores)), 4),
            "test_mae": round(float(mae), 4),
            "test_rmse": round(float(rmse), 4),
            "test_r2": round(float(r2), 4)
        }
        trained_pipelines[name] = pipe

        print(f"Regressor: {name:<18} | CV R2: {np.mean(cv_scores):.4f} | Test R2: {r2:.4f} | Test MAE: {mae:.4f} | RMSE: {rmse:.4f}")

        if r2 > best_r2:
            best_r2 = r2
            best_model_name = name

    print(f"\n=> Best Performing Regressor: {best_model_name} with R2: {best_r2:.4f}")

    best_pipeline = trained_pipelines[best_model_name]
    joblib.dump(best_pipeline, os.path.join(model_dir, "yield_prediction_pipeline.joblib"))

    metadata = {
        "model_id": "yield_prediction_v2",
        "model_name": best_model_name,
        "version": "v2.0-production",
        "training_dataset": "crop_yield_multivariate_v1",
        "training_rows": len(X_train),
        "test_rows": len(X_test),
        "features": feature_cols,
        "benchmark_comparison": benchmark_results,
        "best_metrics": benchmark_results[best_model_name],
        "target_unit": "metric tonnes per hectare",
        "leakage_guard": "Production strictly excluded from predictors."
    }

    with open(os.path.join(model_dir, "metadata.json"), "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)

    print(f"Yield model artifacts saved to {model_dir}/")
    return metadata

if __name__ == "__main__":
    train_and_benchmark_yield_prediction()
