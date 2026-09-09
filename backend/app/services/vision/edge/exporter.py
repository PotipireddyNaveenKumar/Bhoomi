import os
import sys
import io
import json
import logging
import torch
import torch.nn as nn
import torchvision.models as models
import onnx
from onnxconverter_common import float16
from typing import Dict, Any, List, Tuple

from app.services.vision.edge.model_manifest import EdgeManifestGenerator, EdgeModelManifest

logger = logging.getLogger(__name__)

class EdgeModelExporter:
    """
    Exports reference PyTorch crop pathology models to ONNX (FP32, FP16)
    with strict opset compliance and validation.
    """

    OPSET_VERSION = 13

    @classmethod
    def load_pytorch_model(cls, crop: str, base_dir: str = "models/vision") -> Tuple[nn.Module, List[str], float]:
        weights_path = os.path.join(base_dir, crop, "best_model.pth")
        labels_path = os.path.join(base_dir, crop, "labels.json")
        calib_path = os.path.join(base_dir, crop, "calibration.json")

        if not os.path.exists(weights_path):
            raise FileNotFoundError(f"PyTorch weights not found for {crop} at {weights_path}")
        if not os.path.exists(labels_path):
            raise FileNotFoundError(f"Labels file not found for {crop} at {labels_path}")

        with open(labels_path, "r", encoding="utf-8") as f:
            labels_data = json.load(f)
            if "classes" in labels_data and isinstance(labels_data["classes"], list):
                classes = labels_data["classes"]
            elif isinstance(labels_data, dict):
                # Sorted by integer key
                try:
                    classes = [labels_data[str(i)] for i in range(len(labels_data))]
                except KeyError:
                    classes = list(labels_data.values())
            elif isinstance(labels_data, list):
                classes = labels_data
            else:
                classes = []

        temperature = 1.0
        if os.path.exists(calib_path):
            try:
                with open(calib_path, "r", encoding="utf-8") as f:
                    cal_data = json.load(f)
                    temperature = float(cal_data.get("temperature", 1.0))
            except Exception:
                pass

        model = models.mobilenet_v3_small(weights=None)
        in_features = model.classifier[3].in_features
        model.classifier[3] = nn.Linear(in_features, len(classes))

        state_dict = torch.load(weights_path, map_location="cpu")
        model.load_state_dict(state_dict)
        model.eval()

        return model, classes, temperature

    @classmethod
    def export_to_onnx(
        cls,
        crop: str,
        base_dir: str = "models/vision"
    ) -> Dict[str, Any]:
        """
        Exports PyTorch model for crop to ONNX FP32 and ONNX FP16 under models/vision/<crop>/edge/onnx/.
        """
        # Ensure utf-8 encoding for stdout on windows
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except Exception:
            pass

        model, classes, temperature = cls.load_pytorch_model(crop, base_dir)

        edge_dir = os.path.join(base_dir, crop, "edge")
        onnx_dir = os.path.join(edge_dir, "onnx")
        pytorch_edge_dir = os.path.join(edge_dir, "pytorch")
        tflite_dir = os.path.join(edge_dir, "tflite")

        os.makedirs(onnx_dir, exist_ok=True)
        os.makedirs(pytorch_edge_dir, exist_ok=True)
        os.makedirs(tflite_dir, exist_ok=True)

        # 0. PyTorch Reference Artifact and Manifest
        source_weights = os.path.join(base_dir, crop, "best_model.pth")
        target_py_path = os.path.join(pytorch_edge_dir, f"{crop}_model_pytorch.pth")
        if not os.path.exists(target_py_path) and os.path.exists(source_weights):
            import shutil
            shutil.copy2(source_weights, target_py_path)

        manifest_pytorch = EdgeManifestGenerator.generate_manifest(
            crop=crop,
            model_path=target_py_path if os.path.exists(target_py_path) else source_weights,
            format_name="PyTorch_FP32",
            classes=classes,
            calibration_temperature=temperature,
            opset=0,
            quantization="none",
            runtime="pytorch"
        )
        EdgeManifestGenerator.save_manifest(
            manifest_pytorch,
            os.path.join(pytorch_edge_dir, "manifest_pytorch.json")
        )

        # TFLite Readiness Manifest & Guidance
        tflite_readme = os.path.join(tflite_dir, "README.md")
        if not os.path.exists(tflite_readme):
            with open(tflite_readme, "w", encoding="utf-8") as f:
                f.write(f"# TFLite Edge Runtime Architecture for {crop.title()}\n\n"
                        f"- Target Ops: TFLite 2.14+ (TensorFlow Lite FlatBuffers)\n"
                        f"- Input Shape: [1, 224, 224, 3] (NHWC) or [1, 3, 224, 224] (NCHW)\n"
                        f"- Color Format: RGB, Normalized with ImageNet mean/std\n"
                        f"- Export Path: ONNX -> TFLite via onnx2tf or PyTorch -> ai-edge-torch\n"
                        f"- Status: ONNX Runtime selected as primary multiplatform Flutter mobile runtime.\n")

        with open(os.path.join(tflite_dir, "tflite_readiness.json"), "w", encoding="utf-8") as f:
            json.dump({
                "crop": crop,
                "target_format": "TFLITE_FLATBUFFER",
                "primary_edge_runtime": "onnxruntime",
                "tflite_status": "READY_FOR_CONVERSION",
                "input_shape": [1, 224, 224, 3],
                "quantization_support": ["FP32", "FP16", "INT8"]
            }, f, indent=2)

        fp32_path = os.path.join(onnx_dir, f"{crop}_model_fp32.onnx")
        fp16_path = os.path.join(onnx_dir, f"{crop}_model_fp16.onnx")

        # 1. Export FP32 ONNX
        dummy_input = torch.randn(1, 3, 224, 224, dtype=torch.float32)
        torch.onnx.export(
            model,
            dummy_input,
            fp32_path,
            input_names=["input"],
            output_names=["logits"],
            dynamic_axes={"input": {0: "batch_size"}, "logits": {0: "batch_size"}},
            opset_version=cls.OPSET_VERSION,
            dynamo=False
        )

        # Check FP32 model validity
        onnx_fp32 = onnx.load(fp32_path)
        onnx.checker.check_model(onnx_fp32)
        logger.info("Exported and validated FP32 ONNX for %s at %s", crop, fp32_path)

        # Generate FP32 manifest
        manifest_fp32 = EdgeManifestGenerator.generate_manifest(
            crop=crop,
            model_path=fp32_path,
            format_name="ONNX_FP32",
            classes=classes,
            calibration_temperature=temperature,
            opset=cls.OPSET_VERSION,
            quantization="none"
        )
        EdgeManifestGenerator.save_manifest(
            manifest_fp32,
            os.path.join(onnx_dir, "manifest_fp32.json")
        )

        # 2. Export FP16 ONNX
        onnx_fp16 = float16.convert_float_to_float16(onnx_fp32)
        onnx.save(onnx_fp16, fp16_path)
        onnx.checker.check_model(onnx.load(fp16_path))
        logger.info("Exported and validated FP16 ONNX for %s at %s", crop, fp16_path)

        # Generate FP16 manifest
        manifest_fp16 = EdgeManifestGenerator.generate_manifest(
            crop=crop,
            model_path=fp16_path,
            format_name="ONNX_FP16",
            classes=classes,
            calibration_temperature=temperature,
            opset=cls.OPSET_VERSION,
            quantization="float16"
        )
        EdgeManifestGenerator.save_manifest(
            manifest_fp16,
            os.path.join(onnx_dir, "manifest_fp16.json")
        )

        return {
            "crop": crop,
            "fp32_path": fp32_path,
            "fp32_size_bytes": manifest_fp32.file_size_bytes,
            "fp32_size_mb": manifest_fp32.file_size_mb,
            "fp32_sha256": manifest_fp32.sha256,
            "fp16_path": fp16_path,
            "fp16_size_bytes": manifest_fp16.file_size_bytes,
            "fp16_size_mb": manifest_fp16.file_size_mb,
            "fp16_sha256": manifest_fp16.sha256,
            "classes": classes,
            "temperature": temperature
        }
