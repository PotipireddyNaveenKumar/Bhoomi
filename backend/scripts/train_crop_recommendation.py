import os
import sys
sys.path.insert(0, os.path.abspath('backend'))
import json
import joblib
import pandas as pd
import numpy as np

from sklearn.model_selection import train_test_split, cross_val_score, StratifiedKFold
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, classification_report
from sklearn.linear_model import LogisticRegression
from sklearn.tree import DecisionTreeClassifier
from sklearn.ensemble import RandomForestClassifier, ExtraTreesClassifier, GradientBoostingClassifier
import xgboost as xgb

def train_and_benchmark_crop_recommendation():
    data_path = "data/organized/tabular/crop_recommendation/crop_recommendation.csv"
    model_dir = "models/crop_recommendation"
    os.makedirs(model_dir, exist_ok=True)

    print("--- BENCHMARKING CROP RECOMMENDATION MODELS ---")
    df = pd.read_csv(data_path)
    feature_cols = ['nitrogen', 'phosphorus', 'potassium', 'temperature', 'humidity', 'ph', 'rainfall']
    X = df[feature_cols].copy()
    y = df['crop'].copy()

    # Encode labels
    label_encoder = LabelEncoder()
    y_encoded = label_encoder.fit_transform(y)
    classes = label_encoder.classes_.tolist()

    # Split train/test (80/20) with stratification
    X_train, X_test, y_train, y_test = train_test_split(
        X, y_encoded, test_size=0.2, random_state=42, stratify=y_encoded
    )

    # Scale features
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)

    candidate_models = {
        "LogisticRegression": LogisticRegression(max_iter=1000, random_state=42),
        "DecisionTree": DecisionTreeClassifier(random_state=42, max_depth=12),
        "RandomForest": RandomForestClassifier(n_estimators=100, random_state=42),
        "ExtraTrees": ExtraTreesClassifier(n_estimators=100, random_state=42),
        "GradientBoosting": GradientBoostingClassifier(n_estimators=100, random_state=42),
        "XGBoost": xgb.XGBClassifier(n_estimators=100, random_state=42, eval_metric="mlogloss")
    }

    benchmark_results = {}
    best_model_name = None
    best_f1 = -1.0
    trained_models = {}

    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)

    for name, model in candidate_models.items():
        # Cross validation
        cv_scores = cross_val_score(model, X_train_scaled, y_train, cv=cv, scoring="f1_macro")
        model.fit(X_train_scaled, y_train)
        preds = model.predict(X_test_scaled)

        acc = accuracy_score(y_test, preds)
        macro_prec = precision_score(y_test, preds, average="macro", zero_division=0)
        macro_rec = recall_score(y_test, preds, average="macro", zero_division=0)
        macro_f1 = f1_score(y_test, preds, average="macro", zero_division=0)

        benchmark_results[name] = {
            "cv_mean_f1": round(float(np.mean(cv_scores)), 4),
            "cv_std_f1": round(float(np.std(cv_scores)), 4),
            "test_accuracy": round(float(acc), 4),
            "test_macro_precision": round(float(macro_prec), 4),
            "test_macro_recall": round(float(macro_rec), 4),
            "test_macro_f1": round(float(macro_f1), 4)
        }
        trained_models[name] = model

        print(f"Model: {name:<18} | CV F1: {np.mean(cv_scores):.4f} | Test Acc: {acc:.4f} | Test F1: {macro_f1:.4f}")

        if macro_f1 > best_f1:
            best_f1 = macro_f1
            best_model_name = name

    print(f"\n=> Best Performing Model: {best_model_name} with Macro-F1: {best_f1:.4f}")

    # Save artifacts for the best model
    best_model = trained_models[best_model_name]
    joblib.dump(best_model, os.path.join(model_dir, "crop_recommendation_model.joblib"))
    joblib.dump(scaler, os.path.join(model_dir, "crop_scaler.joblib"))
    joblib.dump(label_encoder, os.path.join(model_dir, "crop_label_encoder.joblib"))

    metadata = {
        "model_id": "crop_recommendation_v2",
        "model_name": best_model_name,
        "version": "v2.0-production",
        "training_dataset": "crop_recommendation_v1",
        "training_rows": len(X_train),
        "test_rows": len(X_test),
        "feature_schema": feature_cols,
        "classes": classes,
        "benchmark_comparison": benchmark_results,
        "best_metrics": benchmark_results[best_model_name],
        "limitations": "Trained on 22 standard Indian agro-climatic crops. Extreme micro-climates or untested exotic cultivars may require expert agronomic consultation."
    }

    with open(os.path.join(model_dir, "metadata.json"), "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)

    print(f"Model artifacts saved to {model_dir}/")
    return metadata

if __name__ == "__main__":
    train_and_benchmark_crop_recommendation()
