import os
import hashlib
from collections import defaultdict
from PIL import Image

ROOT_DIR = "data/organized/vision"

CROPS = [
    "tomato_diseases",
    "chilli_diseases",
    "rice_diseases",
    "potato_diseases",
    "sugarcane_diseases",
    "banana_diseases",
    "corn_maize_diseases",
    "guava_diseases",
    "cucumber_pumpkin_diseases",
    "apple_diseases"
]

def audit_single_crop(crop_folder: str):
    crop_path = os.path.join(ROOT_DIR, crop_folder)
    print(f"[*] Auditing {crop_folder}...")

    total_images = 0
    corrupt_count = 0
    hashes = defaultdict(list)
    dimensions = set()
    class_counts = defaultdict(int)

    for dp, _, fns in os.walk(crop_path):
        for f in fns:
            if not f.lower().endswith(('.jpg', '.jpeg', '.png', '.bmp', '.webp')):
                continue
            total_images += 1
            p = os.path.join(dp, f)

            # Class determination from parent folder
            parent = os.path.basename(dp)
            # Avoid generic split names like train/val/test/augmented
            if parent.lower() in ("train", "test", "valid", "val", "augmented", "original", "single_prediction"):
                parent = os.path.basename(os.path.dirname(dp))
            class_counts[parent] += 1

            try:
                with Image.open(p) as img:
                    dimensions.add(img.size)
                    img.verify()
                with open(p, "rb") as fp:
                    h = hashlib.md5(fp.read()).hexdigest()
                    hashes[h].append(p)
            except Exception:
                corrupt_count += 1

    unique_hashes = len(hashes)
    exact_duplicates = total_images - corrupt_count - unique_hashes

    return {
        "crop_folder": crop_folder,
        "total_images": total_images,
        "valid_images": total_images - corrupt_count,
        "corrupt_images": corrupt_count,
        "unique_hashes": unique_hashes,
        "exact_duplicates": exact_duplicates,
        "classes": len(class_counts),
        "class_breakdown": dict(class_counts),
        "sample_dimensions": list(dimensions)[:5]
    }

def run_all_audits():
    results = []
    for c in CROPS:
        res = audit_single_crop(c)
        results.append(res)
    return results

if __name__ == "__main__":
    res = run_all_audits()
    print("\n" + "=" * 80)
    print("MULTI-CROP VISION DATASET AUDIT SUMMARY")
    print("=" * 80)
    print(f"{'Crop':<25} | {'Total':<7} | {'Valid':<7} | {'Corrupt':<7} | {'Unique':<7} | {'Duplicates':<10} | {'Classes':<7}")
    print("-" * 80)
    for r in res:
        print(f"{r['crop_folder']:<25} | {r['total_images']:<7} | {r['valid_images']:<7} | {r['corrupt_images']:<7} | {r['unique_hashes']:<7} | {r['exact_duplicates']:<10} | {r['classes']:<7}")
