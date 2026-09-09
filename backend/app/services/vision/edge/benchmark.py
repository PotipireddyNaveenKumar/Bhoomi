import os
import io
import time
import subprocess
import numpy as np
import onnxruntime as ort
from PIL import Image
from typing import Dict, Any, List

class EdgeLatencyBenchmarker:
    """
    Benchmarks edge inference latency, isolating preprocessing, pure model inference,
    and postprocessing (softmax + temperature scaling).
    """

    @classmethod
    def benchmark_onnx_model(
        cls,
        onnx_path: str,
        sample_image_bytes: bytes,
        warmup_runs: int = 5,
        benchmark_runs: int = 50,
        is_fp16: bool = False
    ) -> Dict[str, Any]:
        if not os.path.exists(onnx_path):
            raise FileNotFoundError(f"Model not found at {onnx_path}")

        sess = ort.InferenceSession(onnx_path, providers=["CPUExecutionProvider"])
        input_name = sess.get_inputs()[0].name

        # 1. Warm-up
        for _ in range(warmup_runs):
            with Image.open(io.BytesIO(sample_image_bytes)) as img:
                arr = np.array(img.convert("RGB").resize((224, 224)), dtype=np.float32) / 255.0
                arr = (arr - np.array([0.485, 0.456, 0.406], dtype=np.float32)) / np.array([0.229, 0.224, 0.225], dtype=np.float32)
                arr = np.expand_dims(np.transpose(arr, (2, 0, 1)), axis=0)
                if is_fp16:
                    arr = arr.astype(np.float16)
                sess.run(None, {input_name: arr})

        pre_times = []
        infer_times = []
        post_times = []
        e2e_times = []

        # 2. Benchmark iterations
        for _ in range(benchmark_runs):
            t0 = time.perf_counter()

            # Preprocessing
            with Image.open(io.BytesIO(sample_image_bytes)) as img:
                arr = np.array(img.convert("RGB").resize((224, 224)), dtype=np.float32) / 255.0
                arr = (arr - np.array([0.485, 0.456, 0.406], dtype=np.float32)) / np.array([0.229, 0.224, 0.225], dtype=np.float32)
                arr = np.expand_dims(np.transpose(arr, (2, 0, 1)), axis=0)
                if is_fp16:
                    arr = arr.astype(np.float16)

            t1 = time.perf_counter()

            # Pure Model Inference
            out = sess.run(None, {input_name: arr})

            t2 = time.perf_counter()

            # Postprocessing (softmax + top-1 argmax)
            logits = out[0][0].astype(np.float32)
            exp_logits = np.exp(logits - np.max(logits))
            probs = exp_logits / np.sum(exp_logits)
            _ = int(np.argmax(probs))

            t3 = time.perf_counter()

            pre_times.append((t1 - t0) * 1000.0)
            infer_times.append((t2 - t1) * 1000.0)
            post_times.append((t3 - t2) * 1000.0)
            e2e_times.append((t3 - t0) * 1000.0)

        return {
            "model_path": onnx_path,
            "benchmark_runs": benchmark_runs,
            "model_latency_mean_ms": round(float(np.mean(infer_times)), 2),
            "model_latency_median_ms": round(float(np.median(infer_times)), 2),
            "model_latency_p95_ms": round(float(np.percentile(infer_times, 95)), 2),
            "model_latency_min_ms": round(float(np.min(infer_times)), 2),
            "model_latency_max_ms": round(float(np.max(infer_times)), 2),
            "preprocessing_mean_ms": round(float(np.mean(pre_times)), 2),
            "postprocessing_mean_ms": round(float(np.mean(post_times)), 2),
            "end_to_end_mean_ms": round(float(np.mean(e2e_times)), 2),
            "end_to_end_median_ms": round(float(np.median(e2e_times)), 2),
            "end_to_end_p95_ms": round(float(np.percentile(e2e_times, 95)), 2)
        }

    @classmethod
    def check_physical_device_benchmark(cls) -> Dict[str, Any]:
        """
        Queries ADB to determine if an Android physical device is connected.
        If not connected, explicitly outputs 'PHYSICAL DEVICE BENCHMARK NOT AVAILABLE'.
        """
        try:
            res = subprocess.run(["adb", "devices"], capture_output=True, text=True, timeout=3)
            lines = [line.strip() for line in res.stdout.splitlines() if line.strip() and not line.startswith("List of devices")]
            devices = [line.split()[0] for line in lines if "device" in line]
            if devices:
                return {
                    "available": True,
                    "devices": devices,
                    "message": f"Connected mobile devices: {devices}"
                }
        except Exception:
            pass

        return {
            "available": False,
            "status": "PHYSICAL DEVICE BENCHMARK NOT AVAILABLE",
            "message": "No physical Android device connected via ADB. In accordance with BHOOMI transparency rules, zero mobile benchmark numbers are fabricated."
        }
