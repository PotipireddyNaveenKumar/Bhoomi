# BHOOMI V2 — Phase 5 Step 3: Edge AI Model Export & Benchmark Report

**Author**: Google DeepMind / Antigravity Agent  
**Date**: September 3, 2026  
**Architecture**: MobileNetV3-Small Edge Runtime Pipeline  
**Runtimes Supported**: PyTorch (Server Reference), ONNX Runtime (FP32, FP16, INT8)  
**Target Crops**: Tomato, Banana, Guava, Corn/Maize (Rice strictly isolated as `RESEARCH_ONLY`)  

---

## 1. Executive Summary & Boundary Guarantees

> [!IMPORTANT]
> **CRITICAL GOVERNANCE RULES**:
> 1. **Edge Optimization $\neq$ Agricultural Accuracy**: Exporting and quantizing models to ONNX/INT8 proves software execution feasibility on edge hardware, but **DOES NOT** prove field diagnostic accuracy on wild crop foliage.
> 2. **Zero Fabrication**: Mobile latency is reported as `PHYSICAL DEVICE BENCHMARK NOT AVAILABLE` when no USB-connected physical Android device is present.
> 3. **Server Reference Preserved**: The server-side PyTorch reference implementation remains the source of truth.
> 4. **No Production Promotion**: All edge artifacts are marked `TECHNICALLY_VALIDATED` for edge execution, but remain `FIELD_VALIDATION_NOT_YET_COMPLETED` and `NOT PRODUCTION READY`.

## 2. Artifact Size Comparison & Checksum Registry

| Crop | PyTorch Size | ONNX FP32 Size | ONNX FP16 Size | ONNX INT8 Size | INT8 Compression | ONNX FP32 SHA-256 Checksum |
| :--- | :---: | :---: | :---: | :---: | :---: | :--- |
| **Tomato** | 5.95 MB | 5.84 MB | 2.95 MB | 1.63 MB | **72.14%** | `c39d5bcbf14951510a83...` |
| **Banana** | 5.93 MB | 5.82 MB | 2.94 MB | 1.62 MB | **72.13%** | `2dc4af03da768d7c57b6...` |
| **Guava** | 5.93 MB | 5.82 MB | 2.94 MB | 1.62 MB | **72.13%** | `714ecaf7728b4330f230...` |
| **Corn_Maize** | 5.93 MB | 5.82 MB | 2.94 MB | 1.62 MB | **72.13%** | `c67dd00f1a3d690c521f...` |

---

## 3. Numerical Parity Analysis (PyTorch Reference vs ONNX Runtime)

| Crop | Max Abs Logit Diff | Mean Abs Logit Diff | Max Prob Diff | Prediction Agreement Rate | Parity Status |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Tomato** | 0.000197 | 0.000034 | 0.000023 | **100.0%** | `PERFECT MATCH` |
| **Banana** | 0.000021 | 0.000007 | 0.000005 | **100.0%** | `PERFECT MATCH` |
| **Guava** | 0.000006 | 0.000002 | 0.000001 | **100.0%** | `PERFECT MATCH` |
| **Corn_Maize** | 0.000012 | 0.000003 | 0.000002 | **100.0%** | `PERFECT MATCH` |

---

## 4. Latency Profiling (Desktop CPU Benchmark)

| Crop | Pure Model Latency (Mean) | Pure Model Latency (P95) | End-to-End Latency (Mean) | End-to-End Latency (P95) |
| :--- | :---: | :---: | :---: | :---: |
| **Tomato** | 2.56 ms | 3.85 ms | 5.04 ms | 6.48 ms |
| **Banana** | 2.98 ms | 3.6 ms | 6.31 ms | 6.85 ms |
| **Guava** | 2.54 ms | 3.71 ms | 5.12 ms | 6.23 ms |
| **Corn_Maize** | 2.67 ms | 3.33 ms | 5.95 ms | 7.64 ms |

---

## 5. Physical Mobile Hardware Status

> [!NOTE]
> **PHYSICAL DEVICE BENCHMARK NOT AVAILABLE**: No physical Android device connected via ADB. In accordance with BHOOMI transparency rules, zero mobile benchmark numbers are fabricated.

## 6. Recommended Edge Runtime & Hybrid Strategy

1. **Recommended Artifact**: **ONNX FP16** is the primary recommendation for mobile deployment (balancing 49.5% size compression with near-zero loss in precision). **ONNX INT8** achieves 72.4% compression (1.6 MB) and is recommended for ultra-low-memory budget devices ($<2\text{ GB}$ RAM).
2. **Hybrid Inference Rule**: In offline mode, the mobile app runs local ONNX inference, triggers ImageQualityGate, applies temperature calibration, and displays diagnostic observations. **Offline mode is strictly prohibited from prescribing synthetic pesticides** without reconnecting to the server `SafetyEngine`.
