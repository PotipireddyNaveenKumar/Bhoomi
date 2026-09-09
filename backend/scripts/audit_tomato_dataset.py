import os
import hashlib
from collections import defaultdict
from PIL import Image

def audit_tomato_vision(root_dir="data/organized/vision/tomato_diseases"):
    print("Auditing:", root_dir)
    image_paths = []
    for dirpath, dirnames, filenames in os.walk(root_dir):
        for f in filenames:
            ext = os.path.splitext(f)[1].lower()
            if ext in ('.jpg', '.jpeg', '.png', '.bmp', '.webp'):
                image_paths.append(os.path.join(dirpath, f))

    print(f"Total image files found: {len(image_paths)}")

    # Check directories
    dir_counts = defaultdict(int)
    for p in image_paths:
        rel = os.path.relpath(p, root_dir)
        parent = os.path.dirname(rel)
        dir_counts[parent] += 1

    print("\nDirectory breakdown:")
    for d, c in sorted(dir_counts.items()):
        print(f"  {d}: {c} images")

    # Audit readability, sizes, duplicates
    hashes = defaultdict(list)
    unreadable = []
    sizes = []
    aspect_ratios = []

    for p in image_paths:
        try:
            with Image.open(p) as img:
                w, h = img.size
                sizes.append((w, h))
                aspect_ratios.append(w / h)
                img.verify()
            with open(p, "rb") as f:
                h_md5 = hashlib.md5(f.read()).hexdigest()
                hashes[h_md5].append(p)
        except Exception as e:
            unreadable.append((p, str(e)))

    print(f"\nReadable images: {len(image_paths) - len(unreadable)}")
    print(f"Unreadable/Corrupted images: {len(unreadable)}")
    if unreadable:
        for p, err in unreadable[:5]:
            print(f"  Corrupt: {p} ({err})")

    # Duplicate check
    duplicates = {k: v for k, v in hashes.items() if len(v) > 1}
    total_dup_files = sum(len(v) for v in duplicates.values()) - len(duplicates)
    print(f"Unique image hashes: {len(hashes)}")
    print(f"Duplicate image sets: {len(duplicates)} (Total duplicate redundant images: {total_dup_files})")

    # Dimensions summary
    if sizes:
        unique_sizes = set(sizes)
        print(f"Distinct image dimensions: {len(unique_sizes)}")
        print(f"Sample dimensions: {list(unique_sizes)[:10]}")

if __name__ == "__main__":
    audit_tomato_vision()
