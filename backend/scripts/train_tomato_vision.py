import os
import sys
import json
import time
import random
import hashlib
from collections import defaultdict
from typing import Dict, List, Tuple

import torch
import torch.nn as nn
from torch.utils.data import Dataset, DataLoader
import torchvision.transforms as transforms
import torchvision.models as models
from PIL import Image
from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    classification_report,
    confusion_matrix
)

# Set seeds for reproducibility
SEED = 42
random.seed(SEED)
torch.manual_seed(SEED)

CLASSES = [
    "Tomato___Bacterial_spot",
    "Tomato___Early_blight",
    "Tomato___Late_blight",
    "Tomato___Leaf_Mold",
    "Tomato___Septoria_leaf_spot",
    "Tomato___Spider_mites Two-spotted_spider_mite",
    "Tomato___Target_Spot",
    "Tomato___Tomato_Yellow_Leaf_Curl_Virus",
    "Tomato___Tomato_mosaic_virus",
    "Tomato___healthy"
]
CLASS_TO_IDX = {c: i for i, c in enumerate(CLASSES)}

class TomatoImageDataset(Dataset):
    def __init__(self, samples: List[Tuple[str, int]], transform=None):
        self.samples = samples
        self.transform = transform

    def __len__(self):
        return len(self.samples)

    def __getitem__(self, idx):
        path, label = self.samples[idx]
        with Image.open(path) as img:
            img = img.convert("RGB")
        if self.transform:
            img = self.transform(img)
        return img, label

class TemperatureScaler(nn.Module):
    def __init__(self):
        super().__init__()
        self.temperature = nn.Parameter(torch.ones(1) * 1.2)

    def forward(self, logits):
        return logits / self.temperature

def build_dataset_splits(root_dir="data/organized/vision/tomato_diseases/d1/tomato_dataset"):
    print("[*] Collecting and de-duplicating dataset images...")
    class_unique_samples = defaultdict(list)
    seen_hashes = set()

    for split in ["train", "valid", "test"]:
        sdir = os.path.join(root_dir, split)
        if not os.path.exists(sdir):
            continue
        for cls_name in CLASSES:
            cdir = os.path.join(sdir, cls_name)
            if not os.path.exists(cdir):
                continue
            for fname in os.listdir(cdir):
                if not fname.lower().endswith((".jpg", ".jpeg", ".png")):
                    continue
                p = os.path.join(cdir, fname)
                try:
                    with open(p, "rb") as fp:
                        h = hashlib.md5(fp.read()).hexdigest()
                    if h not in seen_hashes:
                        seen_hashes.add(h)
                        class_unique_samples[cls_name].append(p)
                except Exception:
                    pass

    train_samples = []
    val_samples = []
    test_samples = []

    # To balance CPU training throughput with statistical rigor:
    # 350 train, 100 val, 100 test per class = 3,500 train, 1,000 val, 1,000 test
    TRAIN_PER_CLASS = 350
    VAL_PER_CLASS = 100
    TEST_PER_CLASS = 100

    print(f"[*] Partitioning dataset (Seed={SEED}, Train/Val/Test = {TRAIN_PER_CLASS}/{VAL_PER_CLASS}/{TEST_PER_CLASS} per class)...")
    for cls_name in CLASSES:
        samples = class_unique_samples[cls_name]
        random.shuffle(samples)
        cls_idx = CLASS_TO_IDX[cls_name]

        tr = samples[:TRAIN_PER_CLASS]
        va = samples[TRAIN_PER_CLASS:TRAIN_PER_CLASS + VAL_PER_CLASS]
        te = samples[TRAIN_PER_CLASS + VAL_PER_CLASS:TRAIN_PER_CLASS + VAL_PER_CLASS + TEST_PER_CLASS]

        train_samples.extend([(p, cls_idx) for p in tr])
        val_samples.extend([(p, cls_idx) for p in va])
        test_samples.extend([(p, cls_idx) for p in te])

    random.shuffle(train_samples)
    random.shuffle(val_samples)
    random.shuffle(test_samples)

    print(f"[*] Final Splits: Train={len(train_samples)}, Val={len(val_samples)}, Test={len(test_samples)}")
    return train_samples, val_samples, test_samples

def train_tomato_model():
    output_dir = "models/vision/tomato"
    os.makedirs(output_dir, exist_ok=True)

    train_samples, val_samples, test_samples = build_dataset_splits()

    # Preprocessing
    train_transform = transforms.Compose([
        transforms.Resize((224, 224)),
        transforms.RandomHorizontalFlip(p=0.5),
        transforms.RandomRotation(degrees=15),
        transforms.ColorJitter(brightness=0.1, contrast=0.1),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
    ])

    eval_transform = transforms.Compose([
        transforms.Resize((224, 224)),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
    ])

    train_loader = DataLoader(TomatoImageDataset(train_samples, train_transform), batch_size=32, shuffle=True, num_workers=0)
    val_loader = DataLoader(TomatoImageDataset(val_samples, eval_transform), batch_size=32, shuffle=False, num_workers=0)
    test_loader = DataLoader(TomatoImageDataset(test_samples, eval_transform), batch_size=32, shuffle=False, num_workers=0)

    print("[*] Instantiating MobileNetV3-Small backbone...")
    model = models.mobilenet_v3_small(weights="DEFAULT")
    in_features = model.classifier[3].in_features
    model.classifier[3] = nn.Linear(in_features, len(CLASSES))

    criterion = nn.CrossEntropyLoss()

    # Stage 1: Freeze features, train classifier head
    print("\n--- STAGE 1: Train Classification Head (Backbone Frozen) ---")
    for param in model.features.parameters():
        param.requires_grad = False

    optimizer_head = torch.optim.AdamW(model.classifier.parameters(), lr=1e-3, weight_decay=1e-4)

    best_val_f1 = 0.0
    best_weights = None

    for epoch in range(1, 3):
        t0 = time.time()
        model.train()
        total_loss = 0.0
        for x, y in train_loader:
            optimizer_head.zero_grad()
            out = model(x)
            loss = criterion(out, y)
            loss.backward()
            optimizer_head.step()
            total_loss += loss.item() * len(y)

        train_loss = total_loss / len(train_samples)

        # Validation
        model.eval()
        val_preds, val_targets = [], []
        with torch.no_grad():
            for x, y in val_loader:
                out = model(x)
                preds = out.argmax(dim=1)
                val_preds.extend(preds.cpu().numpy())
                val_targets.extend(y.cpu().numpy())

        val_acc = accuracy_score(val_targets, val_preds)
        val_f1 = f1_score(val_targets, val_preds, average="macro")
        elapsed = time.time() - t0
        print(f"Epoch {epoch}/2 [Head]: Train Loss={train_loss:.4f} | Val Acc={val_acc:.4f} | Val Macro-F1={val_f1:.4f} ({elapsed:.1f}s)")
        if val_f1 > best_val_f1:
            best_val_f1 = val_f1
            best_weights = {k: v.cpu() for k, v in model.state_dict().items()}

    # Stage 2: Fine-tune upper feature layers
    print("\n--- STAGE 2: Fine-Tune Upper Layers ---")
    for param in model.features[8:].parameters():
        param.requires_grad = True

    optimizer_ft = torch.optim.AdamW([
        {"params": model.features[8:].parameters(), "lr": 1e-4},
        {"params": model.classifier.parameters(), "lr": 3e-4}
    ], weight_decay=1e-4)

    for epoch in range(1, 3):
        t0 = time.time()
        model.train()
        total_loss = 0.0
        for x, y in train_loader:
            optimizer_ft.zero_grad()
            out = model(x)
            loss = criterion(out, y)
            loss.backward()
            optimizer_ft.step()
            total_loss += loss.item() * len(y)

        train_loss = total_loss / len(train_samples)

        # Validation
        model.eval()
        val_preds, val_targets = [], []
        with torch.no_grad():
            for x, y in val_loader:
                out = model(x)
                preds = out.argmax(dim=1)
                val_preds.extend(preds.cpu().numpy())
                val_targets.extend(y.cpu().numpy())

        val_acc = accuracy_score(val_targets, val_preds)
        val_f1 = f1_score(val_targets, val_preds, average="macro")
        elapsed = time.time() - t0
        print(f"Epoch {epoch}/2 [Fine-Tune]: Train Loss={train_loss:.4f} | Val Acc={val_acc:.4f} | Val Macro-F1={val_f1:.4f} ({elapsed:.1f}s)")
        if val_f1 > best_val_f1:
            best_val_f1 = val_f1
            best_weights = {k: v.cpu() for k, v in model.state_dict().items()}

    # Load best weights
    model.load_state_dict(best_weights)
    model.eval()

    # Stage 3: Calibrate Confidence (Temperature Scaling on Val)
    print("\n--- STAGE 3: Temperature Scaling Calibration ---")
    val_logits_list, val_labels_list = [], []
    with torch.no_grad():
        for x, y in val_loader:
            logits = model(x)
            val_logits_list.append(logits)
            val_labels_list.append(y)
    val_logits = torch.cat(val_logits_list, dim=0)
    val_labels = torch.cat(val_labels_list, dim=0)

    scaler = TemperatureScaler()
    optimizer_calib = torch.optim.LBFGS([scaler.temperature], lr=0.01, max_iter=50)

    def eval_nll():
        optimizer_calib.zero_grad()
        loss = criterion(scaler(val_logits), val_labels)
        loss.backward()
        return loss

    optimizer_calib.step(eval_nll)
    learned_temp = float(scaler.temperature.item())
    print(f"[*] Learned Optimal Temperature: {learned_temp:.4f}")

    # Stage 4: Test Set Evaluation
    print("\n--- STAGE 4: Final Evaluation on Untouched Test Set ---")
    test_preds, test_targets = [], []
    test_confidences, test_calibrated_conf = [], []
    inf_times = []

    with torch.no_grad():
        for x, y in test_loader:
            t_start = time.perf_counter()
            logits = model(x)
            inf_times.append((time.perf_counter() - t_start) / len(y))

            calib_logits = logits / learned_temp
            probs = torch.softmax(logits, dim=1)
            calib_probs = torch.softmax(calib_logits, dim=1)

            conf, preds = probs.max(dim=1)
            c_conf, _ = calib_probs.max(dim=1)

            test_preds.extend(preds.cpu().numpy())
            test_targets.extend(y.cpu().numpy())
            test_confidences.extend(conf.cpu().numpy())
            test_calibrated_conf.extend(c_conf.cpu().numpy())

    test_acc = accuracy_score(test_targets, test_preds)
    macro_prec = precision_score(test_targets, test_preds, average="macro", zero_division=0)
    macro_rec = recall_score(test_targets, test_preds, average="macro", zero_division=0)
    macro_f1 = f1_score(test_targets, test_preds, average="macro", zero_division=0)
    weighted_f1 = f1_score(test_targets, test_preds, average="weighted", zero_division=0)
    avg_cpu_inf_ms = (sum(inf_times) / len(inf_times)) * 1000

    report = classification_report(test_targets, test_preds, target_names=CLASSES, output_dict=True)
    c_matrix = confusion_matrix(test_targets, test_preds).tolist()

    print(f"\n==================================================")
    print(f"FINAL UNTOUCHED TEST SET METRICS (Support={len(test_samples)} images)")
    print(f"==================================================")
    print(f"Accuracy         : {test_acc:.4f} ({test_acc*100:.2f}%)")
    print(f"Macro Precision  : {macro_prec:.4f}")
    print(f"Macro Recall     : {macro_rec:.4f}")
    print(f"Macro F1         : {macro_f1:.4f}")
    print(f"Weighted F1      : {weighted_f1:.4f}")
    print(f"Mean CPU Latency : {avg_cpu_inf_ms:.2f} ms per image")

    # Save artifacts
    print(f"\n[*] Saving model artifacts to {output_dir}...")
    torch.save(model.state_dict(), os.path.join(output_dir, "best_model.pth"))

    labels_map = {i: c for i, c in enumerate(CLASSES)}
    with open(os.path.join(output_dir, "labels.json"), "w") as f:
        json.dump(labels_map, f, indent=2)

    preprocessing_cfg = {
        "input_size": [224, 224],
        "mean": [0.485, 0.456, 0.406],
        "std": [0.229, 0.224, 0.225],
        "channels": 3,
        "color_space": "RGB",
        "interpolation": "bilinear"
    }
    with open(os.path.join(output_dir, "preprocessing.json"), "w") as f:
        json.dump(preprocessing_cfg, f, indent=2)

    calibration_cfg = {
        "method": "temperature_scaling",
        "temperature": learned_temp,
        "validation_samples": len(val_samples)
    }
    with open(os.path.join(output_dir, "calibration.json"), "w") as f:
        json.dump(calibration_cfg, f, indent=2)

    metrics_cfg = {
        "test_samples": len(test_samples),
        "accuracy": test_acc,
        "macro_precision": macro_prec,
        "macro_recall": macro_rec,
        "macro_f1": macro_f1,
        "weighted_f1": weighted_f1,
        "avg_cpu_latency_ms": avg_cpu_inf_ms,
        "per_class": report,
        "confusion_matrix": c_matrix
    }
    with open(os.path.join(output_dir, "metrics.json"), "w") as f:
        json.dump(metrics_cfg, f, indent=2)

    param_count = sum(p.numel() for p in model.parameters())
    metadata_cfg = {
        "model_name": "tomato_mobilenet_v3_small",
        "model_version": "tomato_vision_v1.0",
        "architecture": "MobileNetV3-Small",
        "num_classes": len(CLASSES),
        "total_parameters": param_count,
        "train_samples": len(train_samples),
        "val_samples": len(val_samples),
        "test_samples": len(test_samples),
        "training_hardware": "CPU",
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "status": "VALIDATED"
    }
    with open(os.path.join(output_dir, "metadata.json"), "w") as f:
        json.dump(metadata_cfg, f, indent=2)

    print("[*] All training artifacts successfully saved!")

if __name__ == "__main__":
    train_tomato_model()
