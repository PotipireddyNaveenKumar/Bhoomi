import os
import json
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

class DatasetMetadata(BaseModel):
    dataset_id: str
    dataset_name: str
    version: str = "v1.0"
    domain: str = "agriculture"
    task: str  # crop_recommendation, yield_prediction, fertilizer_recommendation, climate_risk, vision_disease
    source: str
    provenance: str
    license: Optional[str] = "Open Agricultural Dataset"
    geography: str = "India"
    time_period: Optional[str] = None
    number_of_rows: int
    number_of_columns: int
    target_column: Optional[str] = None
    feature_columns: List[str] = []
    categorical_columns: List[str] = []
    numerical_columns: List[str] = []
    missing_value_rate: float = 0.0
    duplicate_rate: float = 0.0
    class_distribution: Optional[Dict[str, int]] = None
    unit_information: Dict[str, str] = {}
    validation_status: str = "PENDING"  # PENDING, VALIDATED, REJECTED
    approved_for_training: bool = False
    notes: Optional[str] = None

class DatasetMetadataStore:
    def __init__(self, metadata_dir: str = "data/metadata"):
        self.metadata_dir = metadata_dir
        os.makedirs(self.metadata_dir, exist_ok=True)

    def save_metadata(self, metadata: DatasetMetadata) -> str:
        filepath = os.path.join(self.metadata_dir, f"{metadata.dataset_id}.json")
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(metadata.model_dump(), f, indent=2)
        return filepath

    def get_metadata(self, dataset_id: str) -> Optional[DatasetMetadata]:
        filepath = os.path.join(self.metadata_dir, f"{dataset_id}.json")
        if not os.path.exists(filepath):
            return None
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
            return DatasetMetadata(**data)

    def list_all(self) -> List[DatasetMetadata]:
        result = []
        if not os.path.exists(self.metadata_dir):
            return result
        for fname in os.listdir(self.metadata_dir):
            if fname.endswith(".json"):
                with open(os.path.join(self.metadata_dir, fname), "r", encoding="utf-8") as f:
                    result.append(DatasetMetadata(**json.load(f)))
        return result

class DatasetRegistry:
    def __init__(self, metadata_store: Optional[DatasetMetadataStore] = None):
        self.store = metadata_store or DatasetMetadataStore()

    def register_dataset(self, metadata: DatasetMetadata) -> DatasetMetadata:
        self.store.save_metadata(metadata)
        return metadata

    def get(self, dataset_id: str) -> Optional[DatasetMetadata]:
        return self.store.get_metadata(dataset_id)

    def list_datasets(self, approved_only: bool = False) -> List[DatasetMetadata]:
        datasets = self.store.list_all()
        if approved_only:
            return [d for d in datasets if d.approved_for_training]
        return datasets
