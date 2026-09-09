import os
import json
import hashlib
from datetime import datetime
from typing import Dict, Any, List, Optional
from pydantic import BaseModel

class EdgeModelManifest(BaseModel):
    crop: str
    model_version: str
    runtime: str
    format: str
    architecture: str
    input_size: List[int]
    classes: List[str]
    class_names: List[str] = []
    class_order: List[str] = []
    num_classes: int
    parameter_count: int = 0
    checkpoint_hash: str = ""
    pytorch_model_size_bytes: int = 0
    preprocessing_version: str
    preprocessing_config: Dict[str, Any]
    normalization: Dict[str, Any] = {}
    calibration_temperature: float
    confidence_threshold: float
    ood_threshold: float
    file_size_bytes: int
    file_size_mb: float
    sha256: str
    export_opset: int
    quantization: str
    exported_at: str

class EdgeManifestGenerator:
    """
    Generates cryptographic, machine-readable manifests for exported edge models.
    """

    @staticmethod
    def compute_sha256(file_path: str) -> str:
        h = hashlib.sha256()
        with open(file_path, "rb") as f:
            while chunk := f.read(65536):
                h.update(chunk)
        return h.hexdigest()

    @classmethod
    def generate_manifest(
        cls,
        crop: str,
        model_path: str,
        format_name: str,
        classes: List[str],
        calibration_temperature: float = 1.0,
        confidence_threshold: float = 0.55,
        ood_threshold: float = 0.55,
        opset: int = 13,
        quantization: str = "none",
        runtime: str = "onnxruntime"
    ) -> EdgeModelManifest:
        size_bytes = os.path.getsize(model_path)
        size_mb = round(size_bytes / (1024 * 1024), 2)
        sha256_hash = cls.compute_sha256(model_path)

        norm = {
            "mean": [0.485, 0.456, 0.406],
            "std": [0.229, 0.224, 0.225],
            "color_format": "RGB",
            "resize": [224, 224]
        }

        manifest = EdgeModelManifest(
            crop=crop,
            model_version=f"{crop}_edge_{format_name.lower()}_v1.0",
            runtime=runtime,
            format=format_name,
            architecture="MobileNetV3-Small",
            input_size=[1, 3, 224, 224],
            classes=classes,
            class_names=classes,
            class_order=classes,
            num_classes=len(classes),
            parameter_count=930000,
            checkpoint_hash=sha256_hash if "pytorch" in format_name.lower() else "",
            pytorch_model_size_bytes=size_bytes if "pytorch" in format_name.lower() else 0,
            preprocessing_version="v1.0_imagenet_224",
            preprocessing_config={
                "resize": [224, 224],
                "mean": [0.485, 0.456, 0.406],
                "std": [0.229, 0.224, 0.225],
                "color_format": "RGB",
                "interpolation": "BILINEAR"
            },
            normalization=norm,
            calibration_temperature=round(calibration_temperature, 4),
            confidence_threshold=confidence_threshold,
            ood_threshold=ood_threshold,
            file_size_bytes=size_bytes,
            file_size_mb=size_mb,
            sha256=sha256_hash,
            export_opset=opset,
            quantization=quantization,
            exported_at=datetime.now().isoformat()
        )
        return manifest

    @classmethod
    def save_manifest(cls, manifest: EdgeModelManifest, save_path: str):
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        with open(save_path, "w", encoding="utf-8") as f:
            json.dump(manifest.model_dump(), f, indent=2)
