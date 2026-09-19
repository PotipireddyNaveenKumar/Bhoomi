"""
BHOOMI — Vision Uncertainty and Safety Hardening Verification Script
Tests 9 categories:
1. Potato
2. Tomato
3. Chilli
4. Guava
5. Maize
6. Healthy leaf
7. Blurry image
8. Non-leaf image
9. Unsupported plant

Reports:
- Actual predictions
- Crop vs disease confidence
- Uncertainty level
- Safety behavior (chemical withholding on uncertainty)
"""

import os
import sys
import glob
import json
import asyncio

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
BACKEND_DIR = os.path.join(REPO_ROOT, "backend")
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from app.services.vision.vision_service import VisionService

async def run_vision_hardening_verification():
    print("=" * 95)
    print("TASK 2: VISION UNCERTAINTY AND SAFETY HARDENING VERIFICATION")
    print("=" * 95)

    test_cases = [
        ("Potato", "potato", glob.glob(os.path.join(REPO_ROOT, "data", "organized", "vision", "potato_diseases", "**", "*.jpg"), recursive=True)),
        ("Tomato", "tomato", glob.glob(os.path.join(REPO_ROOT, "data", "organized", "vision", "tomato_diseases", "**", "*.jpg"), recursive=True)),
        ("Chilli", "chilli", glob.glob(os.path.join(REPO_ROOT, "data", "organized", "vision", "chilli_diseases", "**", "*.jpg"), recursive=True)),
        ("Guava", "guava", glob.glob(os.path.join(REPO_ROOT, "data", "organized", "vision", "guava_diseases", "**", "*.png"), recursive=True)),
        ("Maize", "corn_maize", glob.glob(os.path.join(REPO_ROOT, "data", "organized", "vision", "corn_maize_diseases", "**", "*.jpg"), recursive=True)),
        ("Healthy Leaf", "apple", [os.path.join(REPO_ROOT, "data", "organized", "vision", "apple_diseases", "Apple", "Apple___healthy", "brightness_adjusted", "1000_brightness_adjusted.jpg")]),
        ("Blurry Image", None, [os.path.join(REPO_ROOT, "data", "benchmarks", "test_images", "blurry_leaf.jpg")]),
        ("Non-Leaf Image", None, [os.path.join(REPO_ROOT, "data", "benchmarks", "test_images", "non_leaf_blue_surface.jpg")]),
        ("Unsupported Plant", None, glob.glob(os.path.join(REPO_ROOT, "data", "organized", "vision", "other_crop_diseases", "**", "*.jpg"), recursive=True))
    ]

    results = []

    for name, hint, paths in test_cases:
        if not paths:
            print(f"Error: No image path found for {name}")
            continue

        img_path = paths[0]
        with open(img_path, "rb") as f:
            img_bytes = f.read()

        output = await VisionService.analyze_leaf_image(
            image_bytes=img_bytes,
            crop_hint=hint,
            language="en",
            farmer_name="Reviewer",
            synthesize_speech=False
        )

        row = {
            "test_category": name,
            "image_file": os.path.basename(img_path),
            "crop_identified": output.crop_identified,
            "disease_detected": output.disease_detected,
            "common_name": output.common_name,
            "crop_confidence": output.crop_confidence,
            "disease_confidence": output.disease_confidence,
            "uncertainty_level": output.uncertainty_level,
            "chemical_treatment": output.chemical_treatment[:75] + ("..." if len(output.chemical_treatment) > 75 else ""),
            "success": output.success
        }
        results.append(row)

    print(f"\n{'Category':<18} | {'Crop ID':<12} | {'Disease Detected':<22} | {'Crop Conf':<9} | {'Dis Conf':<8} | {'Uncertainty':<11} | {'Chemical Action'}")
    print("-" * 115)
    for r in results:
        print(f"{r['test_category']:<18} | {r['crop_identified']:<12} | {r['disease_detected'][:22]:<22} | {r['crop_confidence']:<9.2f} | {r['disease_confidence']:<8.2f} | {r['uncertainty_level']:<11} | {r['chemical_treatment']}")

    output_path = os.path.join(REPO_ROOT, "vision_hardening_verification.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    print("\n" + "=" * 95)
    print(f"TASK 2 VERIFICATION COMPLETE — Saved to {output_path}")
    print("=" * 95)

if __name__ == "__main__":
    asyncio.run(run_vision_hardening_verification())
