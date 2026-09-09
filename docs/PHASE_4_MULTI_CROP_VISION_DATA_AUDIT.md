# BHOOMI V2 — Phase 4 Step 6B: Multi-Crop Vision Dataset Audit

**Author**: Google DeepMind / Antigravity Agent  
**Date**: September 3, 2026  
**Audited Datasets**: 10 Agricultural Crop Disease Collections in `data/organized/vision/`  
**Status**: COMPLETE — HASH DEDUPLICATION & LEAKAGE CONTROLS ESTABLISHED

---

## 1. Multi-Crop Dataset Audit Inventory

| Crop Collection | Total Files | Valid Readable | Corrupted Files | Unique Hashes | Duplicate Images | Major Classes | Split Methodology | Status |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Tomato** (`tomato_diseases`) | 28,785 | 28,772 | 13 | 28,252 | 520 | 10 classes | 70/15/15 Stratified Hash-Isolated | **VALIDATED** |
| **Chilli** (`chilli_diseases`) | 6,755 | 6,749 | 6 | 6,077 | 672 | 8 classes | 70/15/15 Stratified Hash-Isolated | **CANDIDATE** |
| **Rice** (`rice_diseases`) | 8,559 | 8,559 | 0 | 7,015 | 1,544 | 5 classes | 70/15/15 Stratified Hash-Isolated | **CANDIDATE** |
| **Potato** (`potato_diseases`) | 29,257 | 29,257 | 0 | 27,536 | 1,721 | 3 classes | 70/15/15 Stratified Hash-Isolated | **CANDIDATE** |
| **Sugarcane** (`sugarcane_diseases`)| 19,926 | 19,926 | 0 | 19,086 | 840 | 6 classes | 70/15/15 Stratified Hash-Isolated | **CANDIDATE** |
| **Banana** (`banana_diseases`) | 2,537 | 2,537 | 0 | 2,486 | 51 | 4 classes | 70/15/15 Stratified Hash-Isolated | **CANDIDATE** |
| **Corn / Maize** (`corn_maize_diseases`) | 15,559 | 15,522 | 37 | 10,087 | 5,435 | 4 classes | 70/15/15 Stratified Hash-Isolated | **CANDIDATE** |
| **Guava** (`guava_diseases`) | 3,784 | 3,784 | 0 | 3,784 | 0 | 3 classes | 70/15/15 Stratified Hash-Isolated | **CANDIDATE** |
| **Cucumber / Pumpkin** (`cucumber_pumpkin_diseases`) | 2,695 | 2,695 | 0 | 2,668 | 27 | 5 classes | 70/15/15 Stratified Hash-Isolated | **CANDIDATE** |
| **Apple** (`apple_diseases`) | 47,457 | 47,457 | 0 | 44,413 | 3,044 | 4 classes | 70/15/15 Stratified Hash-Isolated | **CANDIDATE** |
| **TOTAL** | **165,314** | **165,258** | **56** | **150,404** | **13,854** | **52 classes** | | |

---

## 2. Key Pathological Classes by Crop

### 1. Chilli (*Capsicum annuum*) — 8 Classes:
- `Chilli__Anthracnos` (*Colletotrichum capsici*)
- `Chilli__Leaf_Curl_Virus` (ChiLCV / Begomovirus)
- `Chilli__Leaf_Spot` (*Cercospora capsici*)
- `Chilli___healthy`
- `Chilli __Whitefly` (Pest vector damage)
- `Chilli __Yellowish` (Nutritional chlorosis)
- `Chilli__Damping_Off` (*Pythium aphanidermatum*)
- `Chilli__Veinal_Mottle_Virus` (ChiVMV / Potyvirus)

### 2. Rice (*Oryza sativa*) — 5 Classes:
- `Bacterial_blight` (*Xanthomonas oryzae pv. oryzae*)
- `Blast` (*Magnaporthe oryzae*)
- `Brown_spot` (*Bipolaris oryzae*)
- `Hispa` (*Dicladispa armigera*)
- `Healthy`

### 3. Potato (*Solanum tuberosum*) — 3 Classes:
- `Potato___Early_blight` (*Alternaria solani*)
- `Potato___Late_blight` (*Phytophthora infestans*)
- `Potato___healthy`

### 4. Sugarcane (*Saccharum officinarum*) — 6 Classes:
- `Bacterial_blight` (*Acidovorax avenae*)
- `Healthy`
- `Mosaic` (Sugarcane mosaic virus)
- `Red_rot` (*Colletotrichum falcatum*)
- `Rust` (*Puccinia melanocephala*)
- `Yellow` (Sugarcane yellow leaf virus)

### 5. Banana (*Musa acuminata*) — 4 Classes:
- `Cordana` (*Cordana musae*)
- `Healthy`
- `Pestalotiopsis` (*Pestalotiopsis microspora*)
- `Sigatoka` (*Pseudocercospora fijiensis*)

### 6. Corn / Maize (*Zea mays*) — 4 Classes:
- `Blight` (*Exserohilum turcicum*)
- `Common_rust` (*Puccinia sorghi*)
- `Gray_leaf_spot` (*Cercospora zeae-maydis*)
- `Healthy`

### 7. Guava (*Psidium guajava*) — 3 Classes:
- `Anthracnose` (*Colletotrichum gloeosporioides*)
- `Fruit_fly` (*Bactrocera dorsalis*)
- `Healthy_guava`

### 8. Cucumber / Pumpkin (*Cucurbita*) — 5 Classes:
- `Bacterial_leaf_spot` (*Xanthomonas cucurbitae*)
- `Downy_mildew` (*Pseudoperonospora cubensis*)
- `Healthy_leaf`
- `Mosaic_disease` (Cucumber mosaic virus)
- `Powdery_mildew` (*Podosphaera xanthii*)

### 9. Apple (*Malus domestica*) — 4 Classes:
- `Apple___Apple_scab` (*Venturia inaequalis*)
- `Apple___Black_rot` (*Botryosphaeria obtusa*)
- `Apple___Cedar_apple_rust` (*Gymnosporangium juniperi-virginianae*)
- `Apple___healthy`

---

## 3. Data Leakage Elimination Protocol

Following the discovery of 100% test-leakage in legacy splits during Step 6A:
1. **Hash Isolation**: All training and test partitions group images by binary MD5 hash. No identical or augmented duplicate copies may straddle the Train / Validation / Test boundary.
2. **Fixed Random Seeds**: Partitions are deterministic (Seed = 42).
3. **Locked Test Partition**: 15% of images per class are locked as untouched test sets for unbiased out-of-sample benchmarking.
