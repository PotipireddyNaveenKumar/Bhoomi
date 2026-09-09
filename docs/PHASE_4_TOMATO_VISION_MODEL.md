# BHOOMI V2 — Phase 4 Step 6A: Real Tomato Crop-Disease Vision Model

**Author**: Google DeepMind / Antigravity Agent  
**Date**: September 3, 2026  
**Target Crop**: Tomato (*Solanum lycopersicum*)  
**Architecture**: MobileNetV3-Small (Transfer Learning from ImageNet-1K)  
**Model Version**: `tomato_vision_v1.0`  
**Model Status**: `VALIDATED` (Candidate for Field Pilot Trials)  
**Automated Tests**: 145/145 tests passing (125 baseline + 20 Phase 4 tomato vision tests)

---

## 1. Executive Summary

Phase 4 Step 6A replaces BHOOMI's previous heuristic/color-ratio tomato disease classification with a **genuinely trained deep learning Computer Vision model**. 

Key accomplishments:
1. **Exhaustive Data Audit & Leakage Elimination**: Discovered that 100% of images in the pre-existing test directory were duplicates of validation images. Constructed an audited, de-duplicated 70/15/15 split.
2. **MobileNetV3-Small Deployment**: Lightweight CNN backbone with 1,528,106 parameters (6.24 MB checkpoint), optimized for mobile devices and low-latency CPU servers.
3. **High Generalization Performance**:
   - **Test Accuracy**: **93.50%**
   - **Macro Precision**: **94.02%**
   - **Macro Recall**: **93.50%**
   - **Macro F1**: **93.56%**
   - **Weighted F1**: **93.56%**
   - **Mean CPU Latency**: **3.55 ms per image** (>280 FPS on CPU).
4. **Confidence Calibration**: Implemented Temperature Scaling ($T = 1.1249$), mapping uncalibrated raw logits into reliable probabilistic confidence.
5. **Multi-Stage Defense-in-Depth Pipeline**:
   $$\text{Farmer Photo} \longrightarrow \text{ImageQualityGate} \longrightarrow \text{TomatoVisionModel} \longrightarrow \text{VisionPredictionValidator (OOD)} \longrightarrow \text{Agricultural RAG} \longrightarrow \text{SafetyEngine} \longrightarrow \text{BhoomiAgentOrchestrator}$$
6. **Strict Field Validation Status**: Marked as `FIELD_VALIDATION_NOT_YET_COMPLETED` to maintain transparency regarding synthetic vs in-field variable lighting conditions.

---

## 2. Dataset Architecture & Class Taxonomy

Trained on the internationally recognized PlantVillage benchmark across **10 pathological foliar classes**:

| Class ID | PlantVillage Label | Registry Disease Key | Scientific Name | Pathogen Type |
| :---: | :--- | :--- | :--- | :---: |
| 0 | `Tomato___Bacterial_spot` | `bacterial_spot` | *Xanthomonas perforans* | Bacterial |
| 1 | `Tomato___Early_blight` | `early_blight` | *Alternaria solani* | Fungal |
| 2 | `Tomato___Late_blight` | `late_blight` | *Phytophthora infestans* | Fungal |
| 3 | `Tomato___Leaf_Mold` | `leaf_mold` | *Passalora fulva* | Fungal |
| 4 | `Tomato___Septoria_leaf_spot` | `septoria_leaf_spot` | *Septoria lycopersici* | Fungal |
| 5 | `Tomato___Spider_mites Two-spotted_spider_mite` | `spider_mites` | *Tetranychus urticae* | Pest-Induced |
| 6 | `Tomato___Target_Spot` | `target_spot` | *Corynespora cassiicola* | Fungal |
| 7 | `Tomato___Tomato_Yellow_Leaf_Curl_Virus` | `yellow_leaf_curl_virus` | Begomovirus (TYLCV) | Viral |
| 8 | `Tomato___Tomato_mosaic_virus` | `mosaic_virus` | Tobamovirus (ToMV) | Viral |
| 9 | `Tomato___healthy` | `healthy` | N/A (Healthy Foliage) | Healthy |

---

## 3. Data Leakage Elimination & Split Protocol

Prior to training, a hash audit uncovered that all 50 images in the original `test` directory were duplicates of images in `valid`.
The dataset was re-partitioned from 22,914 unique MD5 hashes with fixed random seed (`42`):
- **Train Set**: 3,500 images (350 per class)
- **Validation Set**: 1,000 images (100 per class)
- **Test Set**: 1,000 images (100 per class) — **strictly untouched during training and calibration**.

---

## 4. Preprocessing & Augmentation Strategy

### Inference Preprocessing:
- Resize to $224 \times 224$ pixels.
- Normalize using standard ImageNet parameters:
  - Mean: $[0.485, 0.456, 0.406]$
  - Std: $[0.229, 0.224, 0.225]$

### Training Augmentation:
- Random horizontal flip ($p = 0.5$)
- Random slight rotation ($\pm 15^\circ$)
- Mild color jitter (brightness $\pm 10\%$, contrast $\pm 10\%$)
- *Avoided transformations*: Vertical flipping, extreme hue shifts, cutouts that destroy lesion margins.

---

## 5. Training Protocol

1. **Backbone**: `torchvision.models.mobilenet_v3_small(weights='DEFAULT')`.
2. **Head Modification**:
   - Replaced `classifier[3]` (`Linear(1024, 1000)`) with `Linear(1024, 10)`.
3. **Stage 1 (Head Training)**:
   - Features frozen. Trained classifier with `AdamW(lr=1e-3, weight_decay=1e-4)`.
   - Epoch 1: Train Loss = 0.9623, Val Acc = 80.00%, Val F1 = 0.7973
   - Epoch 2: Train Loss = 0.4754, Val Acc = 84.30%, Val F1 = 0.8396
4. **Stage 2 (Fine-Tuning Upper Layers)**:
   - Unfroze `features[8:]`. Trained with `AdamW(lr=1e-4, weight_decay=1e-4)`.
   - Epoch 1: Train Loss = 0.3081, Val Acc = 91.50%, Val F1 = 0.9144
   - Epoch 2: Train Loss = 0.2129, Val Acc = 92.40%, Val F1 = 0.9236

---

## 6. Confidence Calibration (Temperature Scaling)

Uncalibrated neural networks frequently output overconfident softmax probabilities. 
Using validation logits, scalar temperature $T$ was optimized via NLL:
- **Learned Temperature**: $T = 1.1249$
- Calibrated probability formula:
  $$p_i = \frac{\exp(z_i / T)}{\sum_j \exp(z_j / T)}$$
- Mitigates overconfidence on borderline and out-of-distribution inputs.

---

## 7. Untouched Test Set Evaluation Metrics

Evaluated across **1,000 completely unseen test images** (100 per class):

### Global Metrics:
- **Test Accuracy**: **93.50%**
- **Macro Precision**: **94.02%**
- **Macro Recall**: **93.50%**
- **Macro F1-Score**: **93.56%**
- **Weighted F1-Score**: **93.56%**
- **Mean CPU Latency**: **3.55 ms**

### Per-Class Detailed Performance:

| Class Name | Precision | Recall | F1-Score | Support |
| :--- | :---: | :---: | :---: | :---: |
| `Tomato___Bacterial_spot` | 0.8919 | **0.9900** | 0.9384 | 100 |
| `Tomato___Early_blight` | 0.9375 | 0.9000 | 0.9184 | 100 |
| `Tomato___Late_blight` | 0.9681 | 0.9100 | 0.9381 | 100 |
| `Tomato___Leaf_Mold` | 0.9796 | 0.9600 | 0.9697 | 100 |
| `Tomato___Septoria_leaf_spot` | 0.9556 | 0.8600 | 0.9053 | 100 |
| `Tomato___Spider_mites Two-spotted_spider_mite`| 0.9773 | 0.8600 | 0.9149 | 100 |
| `Tomato___Target_Spot` | 0.7805 | 0.9600 | **0.8610** | 100 |
| `Tomato___Tomato_Yellow_Leaf_Curl_Virus` | **1.0000** | 0.9700 | **0.9848** | 100 |
| `Tomato___Tomato_mosaic_virus` | 0.9515 | 0.9800 | 0.9655 | 100 |
| `Tomato___healthy` | 0.9600 | 0.9600 | 0.9600 | 100 |

### Observations:
- **Best Performing Class**: `Tomato_Yellow_Leaf_Curl_Virus` (F1 = 0.9848, 100% precision) due to distinctive severe leaf curling and chlorosis.
- **Lowest Performing Class**: `Tomato___Target_Spot` (F1 = 0.8610), primarily due to morphological confusion with early concentric lesions of early blight and mite speckling.

---

## 8. Multi-Stage Pipeline Integration

### 1. ImageQualityGate:
Rejects blur, darkness ($<30/255$), extreme glare ($>245/255$), resolution $<224\times224$, extreme aspect ratios ($>4.5:1$), and corrupted payloads before deep model inference.

### 2. OOD & Uncertainty Handling (`VisionPredictionValidator`):
- Calibrated confidence $\ge 0.80 \implies \text{LOW uncertainty}$.
- $0.55 \le \text{confidence} < 0.80 \implies \text{MODERATE uncertainty}$ (monitored).
- $\text{confidence} < 0.55 \implies \text{UNRELIABLE / OOD}$ (forces retake advisory; never outputs an unverified diagnosis).

### 3. Agricultural RAG Integration:
Indexed authoritative ICAR/ANGRAU bulletins for tomato foliar management, providing cited package-of-practices evidence.

### 4. SafetyEngine Guardrails:
Chemical treatments pass through CIBRC safety filters. Toxic or banned substances (e.g. monocrotophos) are strictly blocked with mandatory PPE advisories.

### 5. ToolRegistry & Agent Orchestration:
Registered as `diagnose_plant_disease` tool returning structured visual cards (`leaf_diagnosis_card`) to the Flutter client.

---

## 9. Model Artifacts & File Structure

Stored in `models/vision/tomato/`:
```text
models/vision/tomato/
├── best_model.pth         # PyTorch weights (6.24 MB)
├── labels.json            # Index-to-label dictionary (10 classes)
├── preprocessing.json     # Normalization and resolution parameters
├── calibration.json       # Learned temperature scaling parameter (1.1249)
├── metrics.json           # Comprehensive test metrics and confusion matrix
└── metadata.json          # Model version, parameter count, training metadata
```

---

## 10. Production Readiness Assessment & Limitations

- **Current Status**: `VALIDATED`
- **Inference Location**: `BACKEND ONLY` (FastAPI CPU runtime, 3.55 ms/image)
- **Field Validation Status**: `FIELD_VALIDATION_NOT_YET_COMPLETED`
  - PlantVillage images were captured under controlled lighting with uniform backgrounds.
  - Performance on farmer smartphone photos in direct tropical sunlight with dusty/overlapping leaves must be validated during Phase 5 pilot trials before upgrading to `PRODUCTION_READY`.
