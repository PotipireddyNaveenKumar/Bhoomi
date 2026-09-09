import os
import json
import logging
import onnx
from onnxruntime.quantization import quantize_dynamic, QuantType

from app.services.vision.edge.model_manifest import EdgeManifestGenerator

logger = logging.getLogger(__name__)

class EdgeModelQuantizer:
    """
    Executes dynamic INT8 quantization experiments for MobileNetV3 ONNX models.
    Measures exact compression ratios and generates cryptographic manifests.
    """

    @classmethod
    def quantize_to_int8(
        cls,
        crop: str,
        fp32_onnx_path: str,
        classes: list,
        temperature: float = 1.0,
        output_dir: str = None
    ) -> dict:
        if not os.path.exists(fp32_onnx_path):
            raise FileNotFoundError(f"Source FP32 ONNX model not found at {fp32_onnx_path}")

        if output_dir is None:
            output_dir = os.path.dirname(fp32_onnx_path)

        os.makedirs(output_dir, exist_ok=True)
        int8_path = os.path.join(output_dir, f"{crop}_model_int8.onnx")

        # Execute dynamic INT8 quantization on weights
        quantize_dynamic(
            model_input=fp32_onnx_path,
            model_output=int8_path,
            weight_type=QuantType.QInt8
        )

        fp32_size = os.path.getsize(fp32_onnx_path)
        int8_size = os.path.getsize(int8_path)
        compression = round((1.0 - (int8_size / fp32_size)) * 100.0, 2) if fp32_size > 0 else 0.0

        manifest_int8 = EdgeManifestGenerator.generate_manifest(
            crop=crop,
            model_path=int8_path,
            format_name="ONNX_INT8",
            classes=classes,
            calibration_temperature=temperature,
            opset=13,
            quantization="dynamic_int8"
        )
        EdgeManifestGenerator.save_manifest(
            manifest_int8,
            os.path.join(output_dir, "manifest_int8.json")
        )

        logger.info(
            "Quantized %s to INT8: %s bytes -> %s bytes (%s%% compression)",
            crop, fp32_size, int8_size, compression
        )

        return {
            "crop": crop,
            "int8_path": int8_path,
            "int8_size_bytes": manifest_int8.file_size_bytes,
            "int8_size_mb": manifest_int8.file_size_mb,
            "int8_sha256": manifest_int8.sha256,
            "compression_percent": compression
        }
