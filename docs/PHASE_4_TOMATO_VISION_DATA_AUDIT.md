# BHOOMI V2 — Phase 4 Step 6A: Tomato Crop-Disease Vision Dataset Audit

**Author**: Google DeepMind / Antigravity Agent  
**Date**: September 3, 2026  
**Target Crop**: Tomato (*Solanum lycopersicum*)  
**Dataset Path**: `data/organized/vision/tomato_diseases/`  
**Status**: AUDIT COMPLETE — LEAKAGE IDENTIFIED & REMEDIATION PLAN ESTABLISHED

---

## 1. Dataset Overview & Inventory

An exhaustive file-system crawl and binary validation of `data/organized/vision/tomato_diseases/` was conducted to audit data hygiene, class definitions, image corruptions, and split leakage.

### Global File Counts:
- **Total Image Files Discovered**: 28,785 files
- **Readable / Valid Images**: 28,772 files (99.95%)
- **Corrupted / Unreadable Images**: 13 files (0.05%)
- **Unique Binary MD5 Hashes**: 28,252 hashes
- **Exact Duplicate File Pairs**: 520 files

---

## 2. Directory Structure & Taxonomy Breakdown

The directory contains two distinct sub-sources under `data/organized/vision/tomato_diseases/d1/`:

### Sub-Source A: `tomato_dataset` (PlantVillage Standard Taxonomy)
The primary high-quality dataset corresponds to the internationally recognized **PlantVillage Tomato Disease Benchmark** containing **10 well-defined classes**:

| Class ID | Canonical Class Name | Description & Pathogen | Image Count | Unique Hashes |
| :---: | :--- | :--- | :---: | :---: |
| 0 | `Tomato___Bacterial_spot` | *Xanthomonas perforans* | 2,132 | 2,127 |
| 1 | `Tomato___Early_blight` | *Alternaria solani* | 2,405 | 2,400 |
| 2 | `Tomato___Late_blight` | *Phytophthora infestans* | 2,319 | 2,304 |
| 3 | `Tomato___Leaf_Mold` | *Passalora fulva* | 2,357 | 2,352 |
| 4 | `Tomato___Septoria_leaf_spot` | *Septoria lycopersici* | 2,186 | 2,181 |
| 5 | `Tomato___Spider_mites Two-spotted_spider_mite` | *Tetranychus urticae* | 2,181 | 2,176 |
| 6 | `Tomato___Target_Spot` | *Corynespora cassiicola* | 2,289 | 2,284 |
| 7 | `Tomato___Tomato_Yellow_Leaf_Curl_Virus` | TYLCV (Begomovirus transmitted by Whiteflies) | 2,456 | 2,451 |
| 8 | `Tomato___Tomato_mosaic_virus` | ToMV (Tobamovirus) | 2,243 | 2,238 |
| 9 | `Tomato___healthy` | Healthy leaf tissue without foliar lesions | 2,412 | 2,401 |
| **Total**| **10 Classes** | | **22,980** | **22,914** |

- **Image Dimensions**: Exactly $256 \times 256$ pixels (100% square, aspect ratio 1.0).
- **Color Channels**: 3-channel RGB JPEG format.
- **Corruptions**: 0 unreadable images.

### Sub-Source B: Flat Folders in `d1/` (Uncurated Secondary Collection)
A secondary set of 5 flat directories containing 5,805 images at $400 \times 400$ resolution:
- `Tomato healthy`: 470 images
- `Tomato leaf blight`: 1,301 images (amalgamates early and late blight)
- `Tomato leaf curl`: 518 images
- `Tomato septoria leaf spot`: 2,743 images
- `Tomato verticulium wilt`: 773 images

#### Unreadable / Corrupted Files in Flat Folders (13 files):
1. `Tomato healthy\healthy443_.jpg` (Truncated file header)
2. `Tomato healthy\healthy77_.jpg` (Zero byte payload)
3. `Tomato leaf blight\leaf blight1232_.jpg` (Invalid JPEG marker)
4. `Tomato leaf blight\leaf blight471_.jpg` (Corrupted JFIF segment)
5. `Tomato leaf blight\leaf blight558_.jpg` (Corrupted JFIF segment)
6. Additional 8 unreadable files with byte truncation.

---

## 3. Critical Data Leakage Audit

A hash-intersection analysis across the existing pre-partitioned directories (`train`, `valid`, `test`) in `tomato_dataset` revealed **severe data leakage**:

```text
Existing Pre-Split Hash Intersections:
  train & valid : 4 leaked duplicate images
  train & test  : 0 leaked images
  valid & test  : 50 leaked duplicate images (100% OF THE TEST SET!)
```

### Audit Finding:
**100% of the images in the existing `d1/tomato_dataset/test/` directory were exact binary duplicates of images in `d1/tomato_dataset/valid/`!**
Any model evaluated on the existing `test` directory would report inflated, fraudulent generalization scores.

### Corrective Split Protocol:
To eliminate data leakage:
1. Pool all 22,914 unique PlantVillage tomato images.
2. Group duplicate hashes into atomic clusters so that duplicate copies cannot straddle split boundaries.
3. Partition into clean, mutually exclusive subsets:
   - **TRAIN**: 70% (~16,040 images)
   - **VALIDATION**: 15% (~3,437 images)
   - **TEST**: 15% (~3,437 images)
4. Stratify exactly across all 10 classes to preserve balance.
5. Lock the 15% Test Set — **untouched during hyperparameter selection and training**.

---

## 4. Class Balance Analysis

The 10 PlantVillage classes exhibit remarkable balance in `tomato_dataset`:
- **Minimum class size**: `Tomato___Bacterial_spot` (2,127 images, 9.28%)
- **Maximum class size**: `Tomato___Tomato_Yellow_Leaf_Curl_Virus` (2,451 images, 10.70%)
- **Max/Min Imbalance Ratio**: $2451 / 2127 = 1.152$

Because the imbalance ratio is near unity ($1.15 \ll 3.0$), standard Cross-Entropy Loss without artificial class weighting is statistically appropriate, eliminating class-weight distortion.

---

## 5. Image Size & Aspect Ratio Distribution

- **`tomato_dataset`**: 100% of images are $256 \times 256$ pixels (aspect ratio 1.00).
- **Secondary flat folders**: 100% of images are $400 \times 400$ pixels (aspect ratio 1.00).
- **Zero extreme aspect ratios**: No panoramic or high-aspect distortion images detected.

---

## 6. Recommended Preprocessing & Augmentation Pipeline

### Inference Preprocessing:
1. Resize input image to $224 \times 224$ pixels using bilinear interpolation.
2. Normalize with ImageNet standard mean and standard deviation:
   - $\mu = [0.485, 0.456, 0.406]$
   - $\sigma = [0.229, 0.224, 0.225]$

### Training Augmentation:
To ensure realistic foliar appearance without destroying pathogen lesion morphology:
- Random horizontal flip ($p = 0.5$)
- Random slight rotation ($\pm 15^\circ$)
- Mild color jitter (brightness $\pm 10\%$, contrast $\pm 10\%$)
- **Disallowed Augmentations**: Extreme hue shifts (turns lesions unnatural colors), vertical inversion (disrupts leaf geotropism), and severe cutout/erasing (destroys fine fungal spots).

---

## 7. Model Selection & Architecture Target

- **Chosen Architecture**: `MobileNetV3-Small` (pre-trained on ImageNet-1K).
- **Rationale**:
  - Parameters: $\approx 2.5\text{M}$ (vs $5.3\text{M}$ for EfficientNet-B0 or $25.6\text{M}$ for ResNet50).
  - Target: Low latency on commodity Android smartphones and CPU servers.
  - Classification Head: Adapted to 10 tomato disease classes.
- **Next Step**: Train MobileNetV3-Small using transfer learning, calibrate confidence, and evaluate on the untouched 15% test set.
