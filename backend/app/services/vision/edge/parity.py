import os
import io
import json
import logging
import numpy as np
import torch
import onnxruntime as ort
from PIL import Image
from typing import Dict, Any, List, Tuple
from sklearn.metrics import accuracy_score, f1_score

from app.services.vision.edge.exporter import EdgeModelExporter

logger = logging.getLogger(__name__)

class NumericalParityTester:
    """
    Evaluates exact numerical and accuracy parity between reference PyTorch model
    and exported edge runtimes (ONNX FP32, ONNX FP16, ONNX INT8).
    """

    @staticmethod
    def preprocess_tensor(img_bytes: bytes) -> np.ndarray:
        with Image.open(io.BytesIO(img_bytes)) as img:
            img_rgb = img.convert("RGB").resize((224, 224), Image.Resampling.BILINEAR)
            arr = np.array(img_rgb, dtype=np.float32) / 255.0
            # ImageNet mean and std
            mean = np.array([0.485, 0.456, 0.406], dtype=np.float32)
            std = np.array([0.229, 0.224, 0.225], dtype=np.float32)
            arr = (arr - mean) / std
            # Transpose from HWC to CHW and add batch dimension: (1, 3, 224, 224)
            arr = np.transpose(arr, (2, 0, 1))
            return np.expand_dims(arr, axis=0)

    @classmethod
    def compare_logits_and_probs(
        cls,
        crop: str,
        pytorch_model: torch.nn.Module,
        onnx_path: str,
        test_images: List[bytes],
        temperature: float = 1.0,
        is_fp16: bool = False
    ) -> Dict[str, Any]:
        """
        Runs identical inputs through PyTorch and ONNX Runtime to calculate
        exact maximum and mean logit/probability discrepancies and prediction agreement.
        """
        sess = ort.InferenceSession(onnx_path, providers=["CPUExecutionProvider"])
        input_name = sess.get_inputs()[0].name

        logit_diffs = []
        prob_diffs = []
        agreements = []

        pytorch_model.eval()

        for img_bytes in test_images:
            arr = cls.preprocess_tensor(img_bytes)
            torch_tensor = torch.from_numpy(arr)

            # PyTorch inference
            with torch.no_grad():
                py_logits = pytorch_model(torch_tensor).numpy()[0]
                py_probs = torch.softmax(torch.from_numpy(py_logits) / temperature, dim=0).numpy()

            # ONNX inference
            onnx_input = arr.astype(np.float16) if is_fp16 else arr
            onnx_out = sess.run(None, {input_name: onnx_input})[0][0]
            onnx_logits = onnx_out.astype(np.float32)
            onnx_probs = torch.softmax(torch.from_numpy(onnx_logits) / temperature, dim=0).numpy()

            # Discrepancies
            l_diff = np.abs(py_logits - onnx_logits)
            p_diff = np.abs(py_probs - onnx_probs)

            logit_diffs.append(l_diff)
            prob_diffs.append(p_diff)

            # Class agreement
            agreed = int(np.argmax(py_logits) == np.argmax(onnx_logits))
            agreements.append(agreed)

        all_l_diffs = np.concatenate(logit_diffs)
        all_p_diffs = np.concatenate(prob_diffs)

        return {
            "max_abs_logit_diff": float(np.max(all_l_diffs)),
            "mean_abs_logit_diff": float(np.mean(all_l_diffs)),
            "max_prob_diff": float(np.max(all_p_diffs)),
            "mean_prob_diff": float(np.mean(all_p_diffs)),
            "prediction_agreement_rate": float(np.mean(agreements)),
            "sample_count": len(test_images)
        }

    @classmethod
    def evaluate_test_split_accuracy_parity(
        cls,
        crop: str,
        test_samples: List[Tuple[bytes, str]],
        base_dir: str = "models/vision"
    ) -> Dict[str, Any]:
        """
        Runs the held-out test split across PyTorch, ONNX FP32, ONNX FP16, and ONNX INT8,
        computing comparative Accuracy, Macro-F1, and exact degradation deltas.
        """
        model, classes, temperature = EdgeModelExporter.load_pytorch_model(crop, base_dir)
        edge_onnx_dir = os.path.join(base_dir, crop, "edge", "onnx")

        fp32_path = os.path.join(edge_onnx_dir, f"{crop}_model_fp32.onnx")
        fp16_path = os.path.join(edge_onnx_dir, f"{crop}_model_fp16.onnx")
        int8_path = os.path.join(edge_onnx_dir, f"{crop}_model_int8.onnx")

        models_to_eval = [
            ("PyTorch_FP32", None, False),
            ("ONNX_FP32", fp32_path, False),
            ("ONNX_FP16", fp16_path, True),
            ("ONNX_INT8", int8_path, False)
        ]

        results = {}
        y_true = [s[1] for s in test_samples]

        for name, path, is_fp16 in models_to_eval:
            if path and not os.path.exists(path):
                results[name] = {"available": False}
                continue

            sess = ort.InferenceSession(path, providers=["CPUExecutionProvider"]) if path else None
            y_pred = []

            for img_bytes, _ in test_samples:
                arr = cls.preprocess_tensor(img_bytes)
                if sess is None:
                    with torch.no_grad():
                        logits = model(torch.from_numpy(arr)).numpy()[0]
                else:
                    onnx_input = arr.astype(np.float16) if is_fp16 else arr
                    logits = sess.run(None, {sess.get_inputs()[0].name: onnx_input})[0][0].astype(np.float32)

                pred_class_idx = int(np.argmax(logits))
                y_pred.append(classes[pred_class_idx])

            acc = round(float(accuracy_score(y_true, y_pred)), 4)
            macro_f1 = round(float(f1_score(y_true, y_pred, average="macro", zero_division=0)), 4)

            results[name] = {
                "available": True,
                "accuracy": acc,
                "macro_f1": macro_f1
            }

        ref_acc = results["PyTorch_FP32"]["accuracy"]
        ref_f1 = results["PyTorch_FP32"]["macro_f1"]

        for name in ["ONNX_FP32", "ONNX_FP16", "ONNX_INT8"]:
            if results.get(name, {}).get("available"):
                results[name]["delta_accuracy"] = round(results[name]["accuracy"] - ref_acc, 4)
                results[name]["delta_macro_f1"] = round(results[name]["macro_f1"] - ref_f1, 4)

        return results
