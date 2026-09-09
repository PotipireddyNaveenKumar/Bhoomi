import os
import json
from typing import Dict, Any, List
import pandas as pd
import numpy as np

class DatasetProfiler:
    """
    Automated Exploratory Data Analysis & statistical profiler for agricultural datasets.
    """
    @staticmethod
    def profile_dataframe(df: pd.DataFrame, dataset_name: str, reports_dir: str = "reports/eda") -> Dict[str, Any]:
        os.makedirs(reports_dir, exist_ok=True)
        
        num_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        cat_cols = df.select_dtypes(exclude=[np.number]).columns.tolist()

        num_stats = {}
        for c in num_cols:
            series = df[c].dropna()
            num_stats[c] = {
                "count": int(series.count()),
                "mean": round(float(series.mean()), 3),
                "std": round(float(series.std()), 3) if len(series) > 1 else 0.0,
                "min": round(float(series.min()), 3),
                "q25": round(float(series.quantile(0.25)), 3),
                "median": round(float(series.median()), 3),
                "q75": round(float(series.quantile(0.75)), 3),
                "max": round(float(series.max()), 3),
                "null_count": int(df[c].isnull().sum()),
                "zeros_count": int((series == 0).sum())
            }

        cat_stats = {}
        for c in cat_cols:
            val_counts = df[c].value_counts().head(10).to_dict()
            cat_stats[c] = {
                "unique_count": int(df[c].nunique()),
                "top_values": {str(k): int(v) for k, v in val_counts.items()},
                "null_count": int(df[c].isnull().sum())
            }

        profile = {
            "dataset_name": dataset_name,
            "total_rows": int(len(df)),
            "total_columns": int(len(df.columns)),
            "duplicate_rows": int(df.duplicated().sum()),
            "numerical_columns": num_cols,
            "categorical_columns": cat_cols,
            "numerical_stats": num_stats,
            "categorical_stats": cat_stats,
            "memory_usage_mb": round(float(df.memory_usage(deep=True).sum() / (1024 * 1024)), 2)
        }

        report_file = os.path.join(reports_dir, f"{dataset_name.lower().replace(' ', '_')}_profile.json")
        with open(report_file, "w", encoding="utf-8") as f:
            json.dump(profile, f, indent=2)

        return profile
