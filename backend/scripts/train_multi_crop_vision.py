import os
import sys
import json
import time
import random
import hashlib
from collections import defaultdict
from typing import Dict, List, Tuple, Any

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

SEED = 42
random.seed(SEED)
torch.manual_seed(SEED)

CROP_CONFIGS = {
    "chilli": {
        "root": "data/organized/vision/chilli_diseases/Chilli Plant Diseases Dataset(Augmented)/Chilli Plant Diseases Dataset/train",
        "classes": [
            "Chilli__Anthracnos",
            "Chilli__Leaf_Curl_Virus",
            "Chilli__Leaf_Spot",
            "Chilli___healthy",
            "Chilli __Whitefly",
            "Chilli __Yellowish"
        ],
        "train_per_class": 200,
        "val_per_class": 50,
        "test_per_class": 50
    },
    "rice": {
        "root": "data/organized/vision/rice_diseases/rice_images",
        "classes": [
            "_BrownSpot",
            "_Healthy",
            "_Hispa",
            "_LeafBlast"
        ],
        "train_per_class": 200,
        "val_per_class": 50,
        "test_per_class": 50
    },
    "potato": {
        "root": "data/organized/vision/potato_diseases/Potato",
        "classes": [
            "Potato___Early_blight",
            "Potato___Late_blight",
            "Potato___healthy"
        ],
        "train_per_class": 250,
        "val_per_class": 60,
        "test_per_class": 60
    },
    "sugarcane": {
        "root": "data/organized/vision/sugarcane_diseases/Sugarcane_leafs",
        "classes": [
            "BacterialBlights",
            "Healthy",
            "Mosaic",
            "RedRot",
            "Rust",
            "Yellow"
        ],
        "train_per_class": 200,
        "val_per_class": 50,
        "test_per_class": 50
    },
    "banana": {
        "root": "data/organized/vision/banana_diseases/BananaLSD/OriginalSet",
        "classes": [
            "cordana",
            "healthy",
            "pestalotiopsis",
            "sigatoka"
        ],
        "train_per_class": 100,
        "val_per_class": 30,
        "test_per_class": 30
    },
    "corn_maize": {
        "root": "data/organized/vision/corn_maize_diseases/d7",
        "classes": [
            "Blight",
            "Common_Rust",
            "Gray_Leaf_Spot",
            "Healthy"
        ],
        "train_per_class": 200,
        "val_per_class": 50,
        "test_per_class": 50
    },
    "guava": {
        "root": "data/organized/vision/guava_diseases/GuavaDiseaseDataset/GuavaDiseaseDataset/train",
        "classes": [
            "Anthracnose",
            "fruit_fly",
            "healthy_guava"
        ],
        "train_per_class": 200,
        "val_per_class": 50,
        "test_per_class": 50
    },
    "cucumber_pumpkin": {
        "root": "data/organized/vision/cucumber_pumpkin_diseases/Pumpkin Leaf Diseases Dataset From Bangladesh/Original Dataset",
        "classes": [
            "Bacterial Leaf Spot",
            "Downy Mildew",
            "Healthy Leaf",
            "Mosaic Disease",
            "Powdery_Mildew"
        ],
        "train_per_class": 200,
        "val_per_class": 50,
        "test_per_class": 50
    },
    "apple": {
        "root": "data/organized/vision/apple_diseases/Apple",
        "classes": [
            "Apple___Apple_scab",
            "Apple___Black_rot",
            "Apple___Cedar_apple_rust",
            "Apple___healthy"
        ],
        "train_per_class": 200,
        "val_per_class": 50,
        "test_per_class": 50
    }
}

class FastImageDataset(Dataset):
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

def get_crop_samples(cfg: Dict[str, Any]):
    root = cfg["root"]
    classes = cfg["classes"]
    class_to_idx = {c: i for i, c in enumerate(classes)}
    class_samples = defaultdict(list)
    seen_hashes = set()

    for cls in classes:
        cdir = os.path.join(root, cls)
        if not os.path.exists(cdir):
            continue
        for dp, _, fns in os.walk(cdir):
            for f in fns:
                if not f.lower().endswith(('.jpg', '.jpeg', '.png')):
                    continue
                p = os.path.join(dp, f)
                try:
                    with open(p, "rb") as fp:
                        h = hashlib.md5(fp.read()).hexdigest()
                    if h not in seen_hashes:
                        seen_hashes.add(h)
                        class_samples[cls].append((p, class_to_idx[cls]))
                except Exception:
                    pass

    train_samples, val_samples, test_samples = [], [], []
    for cls in classes:
        slist = class_samples[cls]
        random.shuffle(slist)
        n_train = min(cfg["train_per_class"], int(len(slist) * 0.7))
        n_val = min(cfg["val_per_class"], int(len(slist) * 0.15))
        n_test = min(cfg["test_per_class"], len(slist) - n_train - n_val)

        tr = slist[:n_train]
        va = slist[n_train:n_train + n_val]
        te = slist[n_train + n_val:n_train + n_val + n_test]

        train_samples.extend(tr)
        val_samples.extend(va)
        test_samples.extend(te)

    random.shuffle(train_samples)
    random.shuffle(val_samples)
    random.shuffle(test_samples)

    return train_samples, val_samples, test_samples, classes

def train_single_crop(crop_name: str):
    if crop_name not in CROP_CONFIGS:
        print(f"[-] Unknown crop {crop_name}")
        return

    cfg = CROP_CONFIGS[crop_name]
    output_dir = os.path.join("models", "vision", crop_name)
    os.makedirs(output_dir, exist_ok=True)

    print(f"\n========================================================")
    print(f"TRAINING VISION MODEL FOR: {crop_name.upper()}")
    print(f"========================================================")

    train_samples, val_samples, test_samples, classes = get_crop_samples(cfg)
    print(f"[*] Partitions: Train={len(train_samples)}, Val={len(val_samples)}, Test={len(test_samples)} across {len(classes)} classes")

    eval_transform = transforms.Compose([
        transforms.Resize((224, 224)),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
    ])

    train_transform = transforms.Compose([
        transforms.Resize((224, 224)),
        transforms.RandomHorizontalFlip(p=0.5),
        transforms.RandomRotation(degrees=15),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
    ])

    train_loader = DataLoader(FastImageDataset(train_samples, train_transform), batch_size=32, shuffle=True)
    val_loader = DataLoader(FastImageDataset(val_samples, eval_transform), batch_size=32, shuffle=False)
    test_loader = DataLoader(FastImageDataset(test_samples, eval_transform), batch_size=32, shuffle=False)

    model = models.mobilenet_v3_small(weights="DEFAULT")
    in_features = model.classifier[3].in_features
    model.classifier[3] = nn.Linear(in_features, len(classes))
    criterion = nn.CrossEntropyLoss()

    # Stage 1: Freeze features, train classifier head (2 epochs)
    for param in model.features.parameters():
        param.requires_grad = False

    optimizer = torch.optim.AdamW(model.classifier.parameters(), lr=1e-3, weight_decay=1e-4)

    best_val_f1 = 0.0
    best_weights = None

    for epoch in range(1, 3):
        t0 = time.time()
        model.train()
        total_loss = 0.0
        for x, y in train_loader:
            optimizer.zero_grad()
            out = model(x)
            loss = criterion(out, y)
            loss.backward()
            optimizer.step()
            total_loss += loss.item() * len(y)

        train_loss = total_loss / max(len(train_samples), 1)

        model.eval()
        val_preds, val_targets = [], []
        with torch.no_grad():
            for x, y in val_loader:
                out = model(x)
                val_preds.extend(out.argmax(dim=1).cpu().numpy())
                val_targets.extend(y.cpu().numpy())

        val_acc = accuracy_score(val_targets, val_preds) if val_targets else 0.0
        val_f1 = f1_score(val_targets, val_preds, average="macro", zero_division=0) if val_targets else 0.0
        print(f"Epoch {epoch}/2 [Head]: Train Loss={train_loss:.4f} | Val Acc={val_acc:.4f} | Val Macro-F1={val_f1:.4f} ({time.time()-t0:.1f}s)")
        if val_f1 >= best_val_f1:
            best_val_f1 = val_f1
            best_weights = {k: v.cpu() for k, v in model.state_dict().items()}

    # Stage 2: Fine-tune upper layers (1 epoch)
    for param in model.features[9:].parameters():
        param.requires_grad = True

    optimizer_ft = torch.optim.AdamW([
        {"params": model.features[9:].parameters(), "lr": 1e-4},
        {"params": model.classifier.parameters(), "lr": 3e-4}
    ], weight_decay=1e-4)

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

    model.eval()
    val_preds, val_targets = [], []
    with torch.no_grad():
        for x, y in val_loader:
            out = model(x)
            val_preds.extend(out.argmax(dim=1).cpu().numpy())
            val_targets.extend(y.cpu().numpy())

    val_acc = accuracy_score(val_targets, val_preds) if val_targets else 0.0
    val_f1 = f1_score(val_targets, val_preds, average="macro", zero_division=0) if val_targets else 0.0
    print(f"Epoch 1/1 [Fine-Tune]: Train Loss={total_loss/max(len(train_samples), 1):.4f} | Val Acc={val_acc:.4f} | Val Macro-F1={val_f1:.4f} ({time.time()-t0:.1f}s)")
    if val_f1 >= best_val_f1:
        best_val_f1 = val_f1
        best_weights = {k: v.cpu() for k, v in model.state_dict().items()}

    if best_weights:
        model.load_state_dict(best_weights)
    model.eval()

    # Temperature Scaling on Validation
    val_logits_list, val_labels_list = [], []
    with torch.no_grad():
        for x, y in val_loader:
            val_logits_list.append(model(x))
            val_labels_list.append(y)
    
    if val_logits_list:
        val_logits = torch.cat(val_logits_list, dim=0)
        val_labels = torch.cat(val_labels_list, dim=0)
        scaler = TemperatureScaler()
        opt_calib = torch.optim.LBFGS([scaler.temperature], lr=0.01, max_iter=30)
        def eval_nll():
            opt_calib.zero_grad()
            loss = criterion(scaler(val_logits), val_labels)
            loss.backward()
            return loss
        opt_calib.step(eval_nll)
        learned_temp = float(scaler.temperature.item())
    else:
        learned_temp = 1.1

    # Evaluation on Untouched Test Set
    test_preds, test_targets, inf_times = [], [], []
    with torch.no_grad():
        for x, y in test_loader:
            t_start = time.perf_counter()
            logits = model(x)
            inf_times.append((time.perf_counter() - t_start) / len(y))
            preds = (logits / learned_temp).argmax(dim=1)
            test_preds.extend(preds.cpu().numpy())
            test_targets.extend(y.cpu().numpy())

    test_acc = accuracy_score(test_targets, test_preds) if test_targets else 0.0
    macro_prec = precision_score(test_targets, test_preds, average="macro", zero_division=0) if test_targets else 0.0
    macro_rec = recall_score(test_targets, test_preds, average="macro", zero_division=0) if test_targets else 0.0
    macro_f1 = f1_score(test_targets, test_preds, average="macro", zero_division=0) if test_targets else 0.0
    weighted_f1 = f1_score(test_targets, test_preds, average="weighted", zero_division=0) if test_targets else 0.0
    avg_inf_ms = (sum(inf_times) / max(len(inf_times), 1)) * 1000

    report = classification_report(test_targets, test_preds, target_names=classes, output_dict=True, zero_division=0)
    c_matrix = confusion_matrix(test_targets, test_preds).tolist() if test_targets else []

    print(f"\n[*] {crop_name.upper()} FINAL TEST RESULTS: Accuracy={test_acc*100:.2f}%, Macro-F1={macro_f1*100:.2f}%, Latency={avg_inf_ms:.2f}ms")

    # Save artifacts
    torch.save(model.state_dict(), os.path.join(output_dir, "best_model.pth"))
    labels_map = {i: c for i, c in enumerate(classes)}
    with open(os.path.join(output_dir, "labels.json"), "w") as f:
        json.dump(labels_map, f, indent=2)

    with open(os.path.join(output_dir, "preprocessing.json"), "w") as f:
        json.dump({
            "input_size": [224, 224],
            "mean": [0.485, 0.456, 0.406],
            "std": [0.229, 0.224, 0.225],
            "channels": 3
        }, f, indent=2)

    with open(os.path.join(output_dir, "calibration.json"), "w") as f:
        json.dump({
            "method": "temperature_scaling",
            "temperature": learned_temp
        }, f, indent=2)

    with open(os.path.join(output_dir, "metrics.json"), "w") as f:
        json.dump({
            "test_samples": len(test_samples),
            "accuracy": test_acc,
            "macro_precision": macro_prec,
            "macro_recall": macro_rec,
            "macro_f1": macro_f1,
            "weighted_f1": weighted_f1,
            "avg_cpu_latency_ms": avg_inf_ms,
            "per_class": report,
            "confusion_matrix": c_matrix
        }, f, indent=2)

    param_count = sum(p.numel() for p in model.parameters())
    with open(os.path.join(output_dir, "metadata.json"), "w") as f:
        json.dump({
            "model_name": f"{crop_name}_mobilenet_v3_small",
            "model_version": f"{crop_name}_vision_v1.0",
            "crop": crop_name,
            "architecture": "MobileNetV3-Small",
            "num_classes": len(classes),
            "total_parameters": param_count,
            "train_samples": len(train_samples),
            "val_samples": len(val_samples),
            "test_samples": len(test_samples),
            "accuracy": test_acc,
            "macro_f1": macro_f1,
            "status": "VALIDATED" if macro_f1 >= 0.85 else "CANDIDATE",
            "field_validation": "FIELD_VALIDATION_NOT_YET_COMPLETED"
        }, f, indent=2)

    print(f"[*] {crop_name.upper()} artifacts successfully saved to {output_dir}/")

def main():
    crops = sys.argv[1:] if len(sys.argv) > 1 else list(CROP_CONFIGS.keys())
    print(f"[*] Target Crops for Training: {crops}")
    for c in crops:
        train_single_crop(c)

if __name__ == "__main__":
    main()
