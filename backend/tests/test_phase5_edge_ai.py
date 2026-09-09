import os
import io
import json
import hashlib
import pytest
import numpy as np
import torch
from PIL import Image
import onnxruntime as ort

from app.services.vision.edge import (
    EdgeModelExporter,
    EdgeModelQuantizer,
    NumericalParityTester,
    EdgeLatencyBenchmarker,
    ONNXVisionModelProvider,
    EdgeModelManifest
)
from app.services.vision.crop_registry import CropModelRegistry
from app.services.vision.field_validation.domain_shift import DomainShiftAnalyzer


def make_leaf_bytes(color=(34, 139, 34), size=(256, 256)) -> bytes:
    from PIL import ImageDraw
    img = Image.new("RGB", size, color=color)
    if max(color) >= 20:
        draw = ImageDraw.Draw(img)
        for i in range(0, size[0], 8):
            draw.line([(i, 0), (i, size[1] - 1)], fill=(color[0] + 15, min(255, color[1] + 25), color[2] + 15), width=2)
            draw.line([(0, i), (size[0] - 1, i)], fill=(max(0, color[0] - 15), max(0, color[1] - 25), max(0, color[2] - 15)), width=2)
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()


# 1. ONNX Export Files Exist
def test_onnx_export_files_exist():
    for crop in ["tomato", "banana", "guava", "corn_maize"]:
        onnx_dir = os.path.join("models", "vision", crop, "edge", "onnx")
        fp32_path = os.path.join(onnx_dir, f"{crop}_model_fp32.onnx")
        fp16_path = os.path.join(onnx_dir, f"{crop}_model_fp16.onnx")
        assert os.path.exists(fp32_path), f"Missing FP32 ONNX for {crop}"
        assert os.path.exists(fp16_path), f"Missing FP16 ONNX for {crop}"


# 2. ONNX Model Loading
def test_onnx_model_loading():
    model_path = os.path.join("models", "vision", "tomato", "edge", "onnx", "tomato_model_fp32.onnx")
    sess = ort.InferenceSession(model_path, providers=["CPUExecutionProvider"])
    assert sess is not None
    assert len(sess.get_inputs()) == 1
    assert len(sess.get_outputs()) == 1


# 3. Input Shape Validation
def test_input_shape_validation():
    model_path = os.path.join("models", "vision", "banana", "edge", "onnx", "banana_model_fp32.onnx")
    sess = ort.InferenceSession(model_path, providers=["CPUExecutionProvider"])
    inp = sess.get_inputs()[0]
    assert inp.name == "input"
    # Dynamic batch dimension: [batch_size, 3, 224, 224]
    assert inp.shape[1:] == [3, 224, 224]


# 4. Class-Order Preservation
def test_class_order_preservation():
    for crop in ["tomato", "banana", "guava", "corn_maize"]:
        labels_path = os.path.join("models", "vision", crop, "labels.json")
        manifest_path = os.path.join("models", "vision", crop, "edge", "onnx", "manifest_fp32.json")
        with open(labels_path, "r", encoding="utf-8") as f:
            labels_data = json.load(f)
        with open(manifest_path, "r", encoding="utf-8") as f:
            manifest_data = json.load(f)

        if "classes" in labels_data and isinstance(labels_data["classes"], list):
            expected_classes = labels_data["classes"]
        else:
            expected_classes = [labels_data[str(i)] for i in range(len(labels_data))]

        assert manifest_data["classes"] == expected_classes


# 5. Preprocessing Parity
def test_preprocessing_parity():
    leaf_bytes = make_leaf_bytes()
    arr = NumericalParityTester.preprocess_tensor(leaf_bytes)
    assert arr.shape == (1, 3, 224, 224)
    assert arr.dtype == np.float32
    # Tensor should have normalized zero-mean distribution roughly
    assert -3.0 <= np.mean(arr) <= 3.0


# 6. PyTorch vs ONNX Prediction Agreement
def test_pytorch_vs_onnx_prediction_agreement():
    leaf_bytes = make_leaf_bytes(color=(45, 150, 45))
    py_model, classes, temp = EdgeModelExporter.load_pytorch_model("tomato")
    onnx_path = os.path.join("models", "vision", "tomato", "edge", "onnx", "tomato_model_fp32.onnx")

    parity = NumericalParityTester.compare_logits_and_probs(
        crop="tomato",
        pytorch_model=py_model,
        onnx_path=onnx_path,
        test_images=[leaf_bytes],
        temperature=temp
    )
    assert parity["prediction_agreement_rate"] == 1.0


# 7. Logit Parity
def test_logit_parity():
    leaf_bytes = make_leaf_bytes()
    py_model, _, temp = EdgeModelExporter.load_pytorch_model("guava")
    onnx_path = os.path.join("models", "vision", "guava", "edge", "onnx", "guava_model_fp32.onnx")

    parity = NumericalParityTester.compare_logits_and_probs(
        crop="guava",
        pytorch_model=py_model,
        onnx_path=onnx_path,
        test_images=[leaf_bytes],
        temperature=temp
    )
    # Logit difference must be within tight tolerance
    assert parity["max_abs_logit_diff"] < 0.001


# 8. Probability Parity
def test_probability_parity():
    leaf_bytes = make_leaf_bytes()
    py_model, _, temp = EdgeModelExporter.load_pytorch_model("corn_maize")
    onnx_path = os.path.join("models", "vision", "corn_maize", "edge", "onnx", "corn_maize_model_fp32.onnx")

    parity = NumericalParityTester.compare_logits_and_probs(
        crop="corn_maize",
        pytorch_model=py_model,
        onnx_path=onnx_path,
        test_images=[leaf_bytes],
        temperature=temp
    )
    assert parity["max_prob_diff"] < 0.001


# 9. Accuracy Parity
def test_accuracy_parity():
    # Evaluate synthetic variations to confirm 100% agreement
    test_samples = [(make_leaf_bytes(color=(30 + i * 10, 140, 30)), "healthy") for i in range(5)]
    results = NumericalParityTester.evaluate_test_split_accuracy_parity("banana", test_samples)
    assert results["ONNX_FP32"]["available"] is True
    assert results["ONNX_FP32"]["accuracy"] == results["PyTorch_FP32"]["accuracy"]


# 10. Macro-F1 Parity
def test_macro_f1_parity():
    test_samples = [(make_leaf_bytes(color=(40, 130 + i * 5, 40)), "healthy") for i in range(5)]
    results = NumericalParityTester.evaluate_test_split_accuracy_parity("guava", test_samples)
    assert results["ONNX_FP32"]["macro_f1"] == results["PyTorch_FP32"]["macro_f1"]


# 11. INT8 Model Validity
def test_int8_model_validity():
    for crop in ["tomato", "banana", "guava", "corn_maize"]:
        int8_path = os.path.join("models", "vision", crop, "edge", "onnx", f"{crop}_model_int8.onnx")
        assert os.path.exists(int8_path)
        sess = ort.InferenceSession(int8_path, providers=["CPUExecutionProvider"])
        dummy = np.random.randn(1, 3, 224, 224).astype(np.float32)
        out = sess.run(None, {sess.get_inputs()[0].name: dummy})
        assert len(out) == 1
        assert out[0].shape[0] == 1


# 12. Model Manifest Validation
def test_model_manifest_validation():
    manifest_path = os.path.join("models", "vision", "tomato", "edge", "onnx", "manifest_fp32.json")
    with open(manifest_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    manifest = EdgeModelManifest(**data)
    assert manifest.crop == "tomato"
    assert manifest.runtime == "onnxruntime"
    assert manifest.architecture == "MobileNetV3-Small"
    assert manifest.file_size_mb > 0
    assert len(manifest.sha256) == 64


# 13. SHA-256 Checksum Validation
def test_sha256_checksum_validation():
    manifest_path = os.path.join("models", "vision", "banana", "edge", "onnx", "manifest_fp32.json")
    with open(manifest_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    model_path = os.path.join("models", "vision", "banana", "edge", "onnx", "banana_model_fp32.onnx")

    # Recompute SHA-256 independently
    hasher = hashlib.sha256()
    with open(model_path, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    actual_hash = hasher.hexdigest()

    assert data["sha256"] == actual_hash


# 14. Confidence Preservation on Edge Provider
def test_confidence_preservation():
    leaf_bytes = make_leaf_bytes()
    model_path = os.path.join("models", "vision", "tomato", "edge", "onnx", "tomato_model_fp32.onnx")
    labels_path = os.path.join("models", "vision", "tomato", "labels.json")
    calib_path = os.path.join("models", "vision", "tomato", "calibration.json")

    provider = ONNXVisionModelProvider("tomato", model_path, labels_path, calib_path)
    pred = provider.predict(leaf_bytes)
    assert 0.0 <= pred.confidence <= 1.0
    assert 0.0 <= pred.calibrated_confidence <= 1.0
    assert pred.model_version == "tomato_edge_onnx_v1.0"


# 15. OOD Preservation on Edge Provider
def test_ood_preservation():
    flat_gray = make_leaf_bytes(color=(128, 128, 128))
    model_path = os.path.join("models", "vision", "banana", "edge", "onnx", "banana_model_fp32.onnx")
    labels_path = os.path.join("models", "vision", "banana", "labels.json")
    provider = ONNXVisionModelProvider("banana", model_path, labels_path)
    pred = provider.predict(flat_gray)
    assert pred.uncertainty_status in ["LOW", "MODERATE", "UNRELIABLE"]


# 16. Abstention Preservation
def test_abstention_preservation():
    # Corrupted bytes trigger ImageQualityGate rejection
    corrupt_bytes = b"CORRUPTED_BYTES"
    model_path = os.path.join("models", "vision", "guava", "edge", "onnx", "guava_model_fp32.onnx")
    labels_path = os.path.join("models", "vision", "guava", "labels.json")
    provider = ONNXVisionModelProvider("guava", model_path, labels_path)
    pred = provider.predict(corrupt_bytes)
    assert pred.quality_status == "FAILED"
    assert pred.is_reliable is False
    assert pred.uncertainty_status == "REJECTED"


# 17. Rice RESEARCH_ONLY Enforcement
def test_rice_research_only_enforcement():
    base = DomainShiftAnalyzer.get_benchmark_baseline("rice")
    assert base["status"] == "RESEARCH_ONLY"
    # Rice is not in target crops for mobile deployment
    edge_dir = os.path.join("models", "vision", "rice", "edge", "onnx")
    assert not os.path.exists(os.path.join(edge_dir, "rice_model_fp32.onnx"))


# 18. No-Secret Model Artifact Check
def test_no_secret_model_artifact_check():
    secret_keys = ["sk-", "api_key", "bearer", "password", "token", "secret"]
    for crop in ["tomato", "banana", "guava", "corn_maize"]:
        onnx_dir = os.path.join("models", "vision", crop, "edge", "onnx")
        manifest_files = [f for f in os.listdir(onnx_dir) if f.endswith(".json")]
        for mf in manifest_files:
            with open(os.path.join(onnx_dir, mf), "r", encoding="utf-8") as f:
                content = f.read().lower()
                for key in secret_keys:
                    assert key not in content, f"Possible secret '{key}' found in {mf}"


# 19. Flutter Provider Abstraction
def test_flutter_provider_abstraction():
    dart_path = os.path.join("frontend", "mobile", "lib", "features", "vision", "edge_vision_provider.dart")
    assert os.path.exists(dart_path)
    with open(dart_path, "r", encoding="utf-8") as f:
        content = f.read()
    assert "abstract class EdgeVisionProvider" in content
    assert "class ServerVisionProvider" in content
    assert "class LocalEdgeVisionProvider" in content
    assert "class HybridVisionOrchestrator" in content


# 20. Existing Server Inference Remains Available
def test_server_inference_remains_available():
    leaf_bytes = make_leaf_bytes()
    # Server reference model dispatch
    pred = CropModelRegistry.predict(leaf_bytes, crop_hint="tomato")
    assert pred.crop == "tomato"
    assert pred.model_version.startswith("tomato_vision_v1")
    assert hasattr(pred, "calibrated_confidence")
