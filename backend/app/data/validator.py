from typing import List, Dict, Any, Optional, Tuple
import pandas as pd
import numpy as np

class ValidationIssue(BaseModel if False else object):
    def __init__(self, severity: str, column: str, message: str, count: int = 1):
        self.severity = severity  # ERROR, WARNING
        self.column = column
        self.message = message
        self.count = count

    def to_dict(self):
        return {
            "severity": self.severity,
            "column": self.column,
            "message": self.message,
            "count": self.count
        }

class ValidationResult:
    def __init__(self, is_valid: bool, issues: List[ValidationIssue], stats: Dict[str, Any]):
        self.is_valid = is_valid
        self.issues = issues
        self.stats = stats

    def to_dict(self):
        return {
            "is_valid": self.is_valid,
            "issues": [i.to_dict() for i in self.issues],
            "stats": self.stats
        }

class DatasetValidator:
    """
    Validates tabular agricultural datasets against schema, physical impossibility bounds,
    agricultural rules, and missingness thresholds.
    """
    @staticmethod
    def validate_crop_recommendation(df: pd.DataFrame) -> ValidationResult:
        issues: List[ValidationIssue] = []
        required_cols = ['nitrogen', 'phosphorus', 'potassium', 'temperature', 'humidity', 'ph', 'rainfall', 'crop']
        
        # 1. Schema check
        missing_cols = [c for c in required_cols if c not in df.columns]
        if missing_cols:
            issues.append(ValidationIssue("ERROR", "schema", f"Missing required columns: {missing_cols}"))
            return ValidationResult(False, issues, {"rows": len(df)})

        # 2. Null check
        null_counts = df[required_cols].isnull().sum()
        for col, cnt in null_counts.items():
            if cnt > 0:
                issues.append(ValidationIssue("ERROR", col, f"{cnt} null values detected", int(cnt)))

        # 3. Agricultural Physical Bounds Check
        # Nitrogen, Phosphorus, Potassium >= 0
        for col in ['nitrogen', 'phosphorus', 'potassium']:
            neg_count = (df[col] < 0).sum()
            if neg_count > 0:
                issues.append(ValidationIssue("ERROR", col, f"Found {neg_count} impossible negative nutrient values", int(neg_count)))

        # Temperature: 0 to 55 deg C
        temp_out = ((df['temperature'] < 0) | (df['temperature'] > 55)).sum()
        if temp_out > 0:
            issues.append(ValidationIssue("WARNING", "temperature", f"Found {temp_out} extreme temperature readings", int(temp_out)))

        # Humidity: 0 to 100%
        hum_out = ((df['humidity'] < 0) | (df['humidity'] > 100)).sum()
        if hum_out > 0:
            issues.append(ValidationIssue("ERROR", "humidity", f"Found {hum_out} humidity readings outside 0-100%", int(hum_out)))

        # pH: 3.5 to 9.5
        ph_out = ((df['ph'] < 3.5) | (df['ph'] > 9.5)).sum()
        if ph_out > 0:
            issues.append(ValidationIssue("WARNING", "ph", f"Found {ph_out} extreme soil pH values outside 3.5-9.5", int(ph_out)))

        # Rainfall >= 0
        rain_neg = (df['rainfall'] < 0).sum()
        if rain_neg > 0:
            issues.append(ValidationIssue("ERROR", "rainfall", f"Found {rain_neg} negative rainfall records", int(rain_neg)))

        # 4. Target validity
        crops_count = df['crop'].nunique()
        has_errors = any(i.severity == "ERROR" for i in issues)

        stats = {
            "rows": len(df),
            "columns": len(df.columns),
            "crops_count": crops_count,
            "crops": sorted(df['crop'].unique().tolist())
        }

        return ValidationResult(not has_errors, issues, stats)

    @staticmethod
    def validate_yield_data(df: pd.DataFrame) -> ValidationResult:
        issues: List[ValidationIssue] = []
        required = ['crop', 'area', 'yield']
        missing_cols = [c for c in required if c not in df.columns]
        if missing_cols:
            issues.append(ValidationIssue("ERROR", "schema", f"Missing essential columns: {missing_cols}"))
            return ValidationResult(False, issues, {"rows": len(df)})

        # Area and Yield must be > 0
        neg_area = (df['area'] < 0).sum()
        if neg_area > 0:
            issues.append(ValidationIssue("ERROR", "area", f"Found {neg_area} negative area values", int(neg_area)))

        neg_yield = (df['yield'] < 0).sum()
        if neg_yield > 0:
            issues.append(ValidationIssue("ERROR", "yield", f"Found {neg_yield} negative yield values", int(neg_yield)))

        # Unrealistic yield check (> 200 tons/ha)
        extreme_yield = (df['yield'] > 200).sum()
        if extreme_yield > 0:
            issues.append(ValidationIssue("WARNING", "yield", f"Found {extreme_yield} high yield outliers (>200 t/ha)", int(extreme_yield)))

        has_errors = any(i.severity == "ERROR" for i in issues)
        stats = {
            "rows": len(df),
            "columns": len(df.columns),
            "unique_crops": df['crop'].nunique() if 'crop' in df.columns else 0
        }
        return ValidationResult(not has_errors, issues, stats)

    @staticmethod
    def validate_fertilizer_data(df: pd.DataFrame) -> ValidationResult:
        issues: List[ValidationIssue] = []
        required = ['temperature', 'humidity', 'moisture', 'soil_type', 'crop_type', 'nitrogen', 'potassium', 'phosphorus', 'fertilizer_name']
        missing_cols = [c for c in required if c not in df.columns]
        if missing_cols:
            issues.append(ValidationIssue("ERROR", "schema", f"Missing columns: {missing_cols}"))
            return ValidationResult(False, issues, {"rows": len(df)})

        nulls = df[required].isnull().sum().sum()
        if nulls > 0:
            issues.append(ValidationIssue("ERROR", "nulls", f"{nulls} null values found in fertilizer dataset", int(nulls)))

        has_errors = any(i.severity == "ERROR" for i in issues)
        stats = {
            "rows": len(df),
            "fertilizers": sorted(df['fertilizer_name'].unique().tolist()) if 'fertilizer_name' in df.columns else []
        }
        return ValidationResult(not has_errors, issues, stats)
