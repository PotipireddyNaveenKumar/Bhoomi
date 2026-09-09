import os
import sys
sys.path.insert(0, os.path.abspath('backend'))
import json
import joblib
import pandas as pd
import numpy as np

from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler, OneHotEncoder, LabelEncoder
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, f1_score

def train_fertilizer_model():
    data_path = "data/organized/tabular/fertilizer_recommendation/fertilizer_recommendation.csv"
    model_dir = "models/fertilizer_recommendation"
    os.makedirs(model_dir, exist_ok=True)

    print("--- TRAINING FERTILIZER RECOMMENDATION MODEL ---")
    df = pd.read_csv(data_path)

    # Features: ['temperature', 'humidity', 'moisture', 'soil_type', 'crop_type', 'nitrogen', 'potassium', 'phosphorus']
    num_cols = ['temperature', 'humidity', 'moisture', 'nitrogen', 'potassium', 'phosphorus']
    cat_cols = ['soil_type', 'crop_type']

    X = df[num_cols + cat_cols].copy()
    y = df['fertilizer_name'].copy()

    label_encoder = LabelEncoder()
    y_encoded = label_encoder.fit_transform(y)
    classes = label_encoder.classes_.tolist()

    X_train, X_test, y_train, y_test = train_test_split(X, y_encoded, test_size=0.2, random_state=42, stratify=y_encoded)

    preprocessor = ColumnTransformer(
        transformers=[
            ('num', StandardScaler(), num_cols),
            ('cat', OneHotEncoder(handle_unknown='ignore', sparse_output=False), cat_cols)
        ]
    )

    clf = RandomForestClassifier(n_estimators=100, random_state=42)
    pipeline = Pipeline(steps=[
        ('preprocessor', preprocessor),
        ('classifier', clf)
    ])

    pipeline.fit(X_train, y_train)
    preds = pipeline.predict(X_test)

    acc = accuracy_score(y_test, preds)
    macro_f1 = f1_score(y_test, preds, average="macro")

    print(f"Fertilizer Model Accuracy: {acc:.4f} | Macro-F1: {macro_f1:.4f}")

    joblib.dump(pipeline, os.path.join(model_dir, "fertilizer_pipeline.joblib"))
    joblib.dump(label_encoder, os.path.join(model_dir, "fertilizer_label_encoder.joblib"))

    metadata = {
        "model_id": "fertilizer_recommendation_v1",
        "version": "v1.0-production",
        "accuracy": round(float(acc), 4),
        "macro_f1": round(float(macro_f1), 4),
        "classes": classes,
        "features": num_cols + cat_cols
    }

    with open(os.path.join(model_dir, "metadata.json"), "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)

    print(f"Fertilizer model saved to {model_dir}/")
    return metadata

if __name__ == "__main__":
    train_fertilizer_model()
