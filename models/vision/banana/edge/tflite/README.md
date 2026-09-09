# TFLite Edge Runtime Architecture for Banana

- Target Ops: TFLite 2.14+ (TensorFlow Lite FlatBuffers)
- Input Shape: [1, 224, 224, 3] (NHWC) or [1, 3, 224, 224] (NCHW)
- Color Format: RGB, Normalized with ImageNet mean/std
- Export Path: ONNX -> TFLite via onnx2tf or PyTorch -> ai-edge-torch
- Status: ONNX Runtime selected as primary multiplatform Flutter mobile runtime.
