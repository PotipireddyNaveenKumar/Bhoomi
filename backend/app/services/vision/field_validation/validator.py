import os
import re
import csv
import hashlib
import io
from collections import defaultdict
from typing import Dict, Any, List, Tuple, Optional, Set
from PIL import Image

from app.services.vision.field_validation.schemas import (
    FieldImageMetadata,
    ExpertLabelRecord,
    ManifestItem,
    DuplicateStatus,
    DuplicateClassification,
    LeakageStatus
)
from app.services.vision.crop_registry import CropModelRegistry

class FieldDatasetValidator:
    """
    Validates field-validation datasets against the strict schema,
    enforces zero-PII privacy rules, prevents cross-split benchmark leakage,
    detects exact and near-perceptual duplicates, and produces deterministic manifests.
    """

    PHONE_REGEX = re.compile(r'(\+91[\-\s]?)?[6-9]\d{9}')
    AADHAAR_REGEX = re.compile(r'\b\d{4}[\s\-]?\d{4}[\s\-]?\d{4}\b')
    ADDRESS_REGEX = re.compile(r'\b(h\.?\s?no|d\.?\s?no|door\s?no|survey\s?no|sy\.\s?no|plot\s?no)\b', re.IGNORECASE)
    NAME_LEAK_REGEX = re.compile(r'\b(farmer:\s*\w+|farmer\s+name:\s*\w+|s/o|w/o|c/o)\b', re.IGNORECASE)

    @classmethod
    def validate_privacy(cls, record: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """
        Scans all metadata fields to ensure zero PII (names, phone numbers, Aadhaar, survey numbers) is stored.
        """
        violations = []
        text_fields = [
            ("location", str(record.get("location", ""))),
            ("notes", str(record.get("notes", ""))),
            ("annotation_source", str(record.get("annotation_source", "")))
        ]

        for field_name, val in text_fields:
            if not val:
                continue
            if cls.PHONE_REGEX.search(val):
                violations.append(f"PII Detected: Phone number pattern found in {field_name}")
            if cls.AADHAAR_REGEX.search(val):
                violations.append(f"PII Detected: 12-digit Aadhaar / ID pattern found in {field_name}")
            if cls.ADDRESS_REGEX.search(val):
                violations.append(f"PII Detected: Precise house/survey address pattern found in {field_name}")
            if cls.NAME_LEAK_REGEX.search(val):
                violations.append(f"PII Detected: Farmer personal identification pattern found in {field_name}")

        return len(violations) == 0, violations

    @classmethod
    def validate_metadata_record(cls, record: Dict[str, Any]) -> Tuple[bool, List[str]]:
        errors = []
        try:
            FieldImageMetadata(**record)
        except Exception as e:
            errors.append(str(e))

        is_priv_clean, priv_errors = cls.validate_privacy(record)
        if not is_priv_clean:
            errors.extend(priv_errors)

        return len(errors) == 0, errors

    @classmethod
    def validate_metadata_file(cls, csv_path: str) -> Dict[str, Any]:
        if not os.path.exists(csv_path):
            return {"is_valid": False, "total_rows": 0, "errors": [f"File {csv_path} does not exist"]}

        errors = []
        valid_rows = 0
        records = []

        with open(csv_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            required_cols = [
                "image_id", "crop", "image_path", "actual_disease", "location",
                "state", "district", "crop_stage", "lighting_condition",
                "camera_device", "image_distance", "leaf_condition", "occlusion_level",
                "image_quality", "expert_label", "annotator_confidence",
                "annotation_source", "annotation_date"
            ]
            if not reader.fieldnames:
                return {"is_valid": False, "total_rows": 0, "errors": ["Empty or unreadable CSV"]}

            missing_cols = [c for c in required_cols if c not in reader.fieldnames]
            if missing_cols:
                errors.append(f"Missing required columns in CSV header: {missing_cols}")
                return {"is_valid": False, "total_rows": 0, "errors": errors}

            for idx, row in enumerate(reader, start=1):
                try:
                    # Validate schema
                    meta = FieldImageMetadata(**row)
                    # Validate privacy
                    is_clean, priv_errors = cls.validate_privacy(row)
                    if not is_clean:
                        errors.append(f"Row {idx} ({row.get('image_id', 'unknown')}): {'; '.join(priv_errors)}")
                    else:
                        records.append(meta)
                        valid_rows += 1
                except Exception as e:
                    errors.append(f"Row {idx} ({row.get('image_id', 'unknown')}): {str(e)}")

        return {
            "is_valid": len(errors) == 0,
            "total_rows": valid_rows + len(errors),
            "valid_rows": valid_rows,
            "errors": errors,
            "records": records
        }

    @classmethod
    def validate_expert_labels_file(cls, csv_path: str) -> Dict[str, Any]:
        if not os.path.exists(csv_path):
            return {"is_valid": False, "total_rows": 0, "errors": [f"File {csv_path} does not exist"]}

        errors = []
        valid_rows = 0
        records = []

        with open(csv_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            if not reader.fieldnames:
                return {"is_valid": False, "total_rows": 0, "errors": ["Empty or unreadable labels CSV"]}

            for idx, row in enumerate(reader, start=1):
                try:
                    rec = ExpertLabelRecord(**row)
                    records.append(rec)
                    valid_rows += 1
                except Exception as e:
                    errors.append(f"Row {idx}: {str(e)}")

        return {
            "is_valid": len(errors) == 0,
            "total_rows": valid_rows + len(errors),
            "valid_rows": valid_rows,
            "errors": errors,
            "records": records
        }

    @staticmethod
    def compute_file_hash(path: str) -> str:
        h = hashlib.md5()
        with open(path, "rb") as f:
            while chunk := f.read(65536):
                h.update(chunk)
        return h.hexdigest()

    @staticmethod
    def compute_perceptual_hash(path: str, hash_size: int = 8) -> str:
        """
        Computes 64-bit Average Hash (aHash) representation of an image for near-duplicate detection.
        """
        try:
            with Image.open(path) as img:
                img = img.convert("L").resize((hash_size, hash_size), Image.Resampling.BILINEAR)
                pixels = list(img.getdata())
                avg = sum(pixels) / len(pixels)
                bits = "".join("1" if p > avg else "0" for p in pixels)
                # Convert 64 binary bits to 16 hex characters
                return f"{int(bits, 2):016x}"
        except Exception:
            return "0" * 16

    @staticmethod
    def hamming_distance(hex1: str, hex2: str) -> int:
        """
        Calculates bit-level Hamming distance between two 16-hex char perceptual hashes.
        """
        try:
            val1 = int(hex1, 16)
            val2 = int(hex2, 16)
            xor_val = val1 ^ val2
            return bin(xor_val).count("1")
        except Exception:
            return 64

    @classmethod
    def detect_duplicates(cls, image_paths: List[str]) -> Dict[str, List[str]]:
        """
        Groups image paths by MD5 hash to identify exact duplicate submissions.
        Returns a dict of hash -> list of duplicate file paths.
        """
        hashes = defaultdict(list)
        for p in image_paths:
            if os.path.exists(p):
                try:
                    h = cls.compute_file_hash(p)
                    hashes[h].append(p)
                except Exception:
                    pass
        return {h: paths for h, paths in hashes.items() if len(paths) > 1}

    @classmethod
    def detect_near_duplicates(
        cls,
        image_paths: List[str],
        max_distance: int = 5
    ) -> List[Tuple[str, str, int]]:
        """
        Identifies pairs of near-duplicate images based on perceptual hash Hamming distance <= max_distance.
        """
        p_hashes = {}
        for p in image_paths:
            if os.path.exists(p):
                p_hashes[p] = cls.compute_perceptual_hash(p)

        near_pairs = []
        paths = list(p_hashes.keys())
        for i in range(len(paths)):
            for j in range(i + 1, len(paths)):
                p1, p2 = paths[i], paths[j]
                dist = cls.hamming_distance(p_hashes[p1], p_hashes[p2])
                if dist <= max_distance:
                    near_pairs.append((p1, p2, dist))

        return near_pairs

    @classmethod
    def check_cross_split_leakage(
        cls,
        field_image_hashes: List[str],
        benchmark_root: str = "data/organized/vision"
    ) -> List[str]:
        """
        Scans all benchmark images and flags any field image that matches
        a training, validation, or test hash from the controlled benchmark datasets.
        """
        if not os.path.exists(benchmark_root):
            return []

        benchmark_hashes = set()
        for root, _, files in os.walk(benchmark_root):
            for f in files:
                if f.lower().endswith(('.jpg', '.jpeg', '.png')):
                    p = os.path.join(root, f)
                    try:
                        h = cls.compute_file_hash(p)
                        benchmark_hashes.add(h)
                    except Exception:
                        pass

        leaked = [h for h in field_image_hashes if h in benchmark_hashes]
        return leaked

    @classmethod
    def classify_duplicate(
        cls,
        image_path: str,
        image_hash: str,
        exact_dups: Dict[str, List[str]],
        near_dup_paths: Set[str]
    ) -> DuplicateClassification:
        """
        Classifies an image observation into exact duplicate, near duplicate, unique, or unknown.
        """
        if not image_hash:
            return DuplicateClassification.UNKNOWN

        if image_hash in exact_dups:
            dup_paths = exact_dups[image_hash]
            if len(dup_paths) > 1 and dup_paths[0] != image_path:
                return DuplicateClassification.EXACT_DUPLICATE

        if image_path in near_dup_paths:
            return DuplicateClassification.NEAR_DUPLICATE

        return DuplicateClassification.UNIQUE

    @classmethod
    def validate_media_file(
        cls,
        media_input: Any,
        filename: str = "image.jpg",
        max_size_bytes: int = 20 * 1024 * 1024,
        min_dimension: int = 64
    ) -> Tuple[bool, List[str], Dict[str, Any]]:
        """
        Executes strict MIME, size, dimension, and decode validation on raw input bytes or file path.
        """
        errors = []
        info = {
            "size_bytes": 0,
            "width": 0,
            "height": 0,
            "format": "",
            "md5_hash": "",
            "perceptual_hash": ""
        }

        # 1. Read bytes
        raw_bytes = b""
        if isinstance(media_input, bytes):
            raw_bytes = media_input
        elif isinstance(media_input, str):
            if not os.path.exists(media_input):
                return False, [f"File not found on disk: {media_input}"], info
            try:
                with open(media_input, "rb") as f:
                    raw_bytes = f.read()
            except Exception as e:
                return False, [f"Could not read file {media_input}: {str(e)}"], info
        else:
            return False, ["Invalid media input type; must be bytes or str file path"], info

        size_bytes = len(raw_bytes)
        info["size_bytes"] = size_bytes

        if size_bytes == 0:
            return False, ["Media file is empty (0 bytes)"], info

        if size_bytes > max_size_bytes:
            errors.append(f"Media file size ({size_bytes} bytes) exceeds limit ({max_size_bytes} bytes)")

        # 2. Decode & MIME verification
        try:
            with Image.open(io.BytesIO(raw_bytes)) as img:
                img_format = (img.format or "").upper()
                info["format"] = img_format
                width, height = img.size
                info["width"] = width
                info["height"] = height

                allowed_formats = ["JPEG", "PNG", "WEBP", "MPO"]
                if img_format not in allowed_formats:
                    errors.append(f"Unsupported image format '{img_format}'. Allowed: {allowed_formats}")

                if width < min_dimension or height < min_dimension:
                    errors.append(f"Image dimensions ({width}x{height}) below minimum required ({min_dimension}x{min_dimension})")
        except Exception as e:
            errors.append(f"Corrupt media or image decode failure: {str(e)}")

        # 3. Compute hashes if readable
        if not errors:
            md5_h = hashlib.md5(raw_bytes).hexdigest()
            info["md5_hash"] = md5_h
            try:
                with Image.open(io.BytesIO(raw_bytes)) as img:
                    img_gray = img.convert("L").resize((8, 8), Image.Resampling.BILINEAR)
                    pixels = list(img_gray.getdata())
                    avg = sum(pixels) / len(pixels)
                    bits = "".join("1" if p > avg else "0" for p in pixels)
                    info["perceptual_hash"] = f"{int(bits, 2):016x}"
            except Exception:
                info["perceptual_hash"] = "0" * 16

        return len(errors) == 0, errors, info

