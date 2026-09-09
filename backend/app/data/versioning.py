import os
import shutil
from datetime import datetime, timezone
from typing import Dict, Any

class DatasetVersionManager:
    """
    Manages dataset versioning across lifecycle stages:
    Raw -> Validated -> Processed -> Training Splits
    """
    def __init__(self, base_dir: str = "data"):
        self.base_dir = base_dir
        self.validated_dir = os.path.join(base_dir, "validated")
        self.processed_dir = os.path.join(base_dir, "processed")
        self.metadata_dir = os.path.join(base_dir, "metadata")
        self.rejected_dir = os.path.join(base_dir, "rejected")

        for d in [self.validated_dir, self.processed_dir, self.metadata_dir, self.rejected_dir]:
            os.makedirs(d, exist_ok=True)

    def promote_to_validated(self, src_path: str, dataset_name: str, version: str = "v1.0") -> str:
        dst_dir = os.path.join(self.validated_dir, dataset_name)
        os.makedirs(dst_dir, exist_ok=True)
        dst_path = os.path.join(dst_dir, f"{dataset_name}_{version}.csv")
        shutil.copy2(src_path, dst_path)
        return dst_path

    def save_processed(self, df_processed, dataset_name: str, version: str = "v1.0") -> str:
        dst_dir = os.path.join(self.processed_dir, dataset_name)
        os.makedirs(dst_dir, exist_ok=True)
        dst_path = os.path.join(dst_dir, f"{dataset_name}_processed_{version}.parquet" if False else f"{dataset_name}_processed_{version}.csv")
        df_processed.to_csv(dst_path, index=False)
        return dst_path
