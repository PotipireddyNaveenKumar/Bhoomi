import os
import io
import sys
import json
import uuid
import time
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Tuple, Set
from PIL import Image

from app.services.vision.field_validation.schemas import (
    FieldImageMetadata,
    ExpertLabelRecord,
    ManifestItem,
    FieldDatasetManifest,
    DuplicateStatus,
    DuplicateClassification,
    LeakageStatus,
    PilotQualityReport,
    DataProvenance,
    ProvenanceSourceType,
    VoicePilotRecord,
    TaskOutcomeRecord
)
from app.services.vision.field_validation.validator import FieldDatasetValidator

class FieldPilotIngestionService:
    """
    Controlled ingestion pipeline for real smartphone photographs, voice recordings,
    and longitudinal task outcomes. Enforces image validity, MIME/size, schema,
    PII filtering, duplicate/near-duplicate classification, and provenance records.
    Produces deterministic manifests and quality reports.
    """

    @classmethod
    def ingest_pilot_batch(
        cls,
        metadata_csv: str = "data/field_validation/metadata/field_validation.csv",
        labels_csv: str = "data/field_validation/labels/expert_labels.csv",
        benchmark_root: str = "data/organized/vision",
        manifest_dir: str = "data/field_validation/manifests"
    ) -> FieldDatasetManifest:
        run_id = f"INGEST_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        timestamp = datetime.now().isoformat()

        # Step 1: Read metadata and labels
        meta_res = FieldDatasetValidator.validate_metadata_file(metadata_csv)
        label_res = FieldDatasetValidator.validate_expert_labels_file(labels_csv)

        metadata_records: List[FieldImageMetadata] = meta_res.get("records", [])
        expert_records: Dict[str, ExpertLabelRecord] = {
            r.image_id: r for r in label_res.get("records", [])
        }

        if len(metadata_records) == 0:
            quality_report = PilotQualityReport(
                run_id=run_id,
                timestamp=timestamp,
                total_records=0,
                accepted=0,
                rejected=0,
                rejection_details=["No metadata records found to ingest."]
            )
            manifest = FieldDatasetManifest(
                run_id=run_id,
                timestamp=timestamp,
                total_submitted=0,
                accepted_for_eval=0,
                rejected_count=0,
                flagged_near_duplicate_count=0,
                items=[],
                quality_report=quality_report.model_dump()
            )
            cls._save_manifest(manifest, manifest_dir)
            return manifest

        # Step 2: Build file list and check duplicates & leakage
        image_paths = []
        path_to_record = {}
        for r in metadata_records:
            p = r.image_path
            if not os.path.isabs(p) and not os.path.exists(p):
                p = os.path.join("data", "field_validation", r.image_path)
            image_paths.append(p)
            path_to_record[r.image_id] = p

        exact_dups = FieldDatasetValidator.detect_duplicates(image_paths)
        near_dup_pairs = FieldDatasetValidator.detect_near_duplicates(image_paths, max_distance=5)
        near_dup_paths = set()
        for p1, p2, _ in near_dup_pairs:
            near_dup_paths.add(p1)
            near_dup_paths.add(p2)

        # Precompute file hashes for benchmark leakage check
        hash_to_path = {}
        for p in image_paths:
            if os.path.exists(p):
                h = FieldDatasetValidator.compute_file_hash(p)
                hash_to_path[h] = p

        leaked_hashes = set(FieldDatasetValidator.check_cross_split_leakage(
            list(hash_to_path.keys()),
            benchmark_root=benchmark_root
        ))

        # Step 3: Evaluate each item
        manifest_items: List[ManifestItem] = []
        accepted = 0
        rejected = 0
        flagged_near = 0

        for r in metadata_records:
            img_path = path_to_record[r.image_id]
            rejection_reasons = []

            # 1. File existence & readability
            width, height, size_bytes = 0, 0, 0
            file_ok = False
            img_hash = ""
            p_hash = ""

            if os.path.exists(img_path):
                try:
                    size_bytes = os.path.getsize(img_path)
                    img_hash = FieldDatasetValidator.compute_file_hash(img_path)
                    p_hash = FieldDatasetValidator.compute_perceptual_hash(img_path)
                    with Image.open(img_path) as im:
                        width, height = im.size
                    file_ok = True
                except Exception as e:
                    rejection_reasons.append(f"Image decode failure: {str(e)}")
            else:
                rejection_reasons.append(f"Image file not found on disk at {img_path}")

            # 2. Metadata check
            meta_ok = True
            # Privacy check
            priv_ok, priv_errors = FieldDatasetValidator.validate_privacy(r.model_dump())
            if not priv_ok:
                rejection_reasons.extend(priv_errors)

            # 3. Duplicate status & classification
            dup_status = DuplicateStatus.CLEAN.value
            dup_class = FieldDatasetValidator.classify_duplicate(
                image_path=img_path,
                image_hash=img_hash,
                exact_dups=exact_dups,
                near_dup_paths=near_dup_paths
            )

            if dup_class == DuplicateClassification.EXACT_DUPLICATE:
                dup_paths = exact_dups.get(img_hash, [])
                dup_status = DuplicateStatus.REJECT_EXACT_DUPLICATE.value
                rejection_reasons.append(f"Exact duplicate of {dup_paths[0]} (MD5 {img_hash})")
            elif dup_class == DuplicateClassification.NEAR_DUPLICATE:
                dup_status = DuplicateStatus.FLAG_NEAR_DUPLICATE.value
                flagged_near += 1

            # 4. Leakage status
            leak_status = LeakageStatus.CLEAN.value
            if img_hash and img_hash in leaked_hashes:
                leak_status = LeakageStatus.REJECT_BENCHMARK_LEAKAGE.value
                rejection_reasons.append(f"Cross-split benchmark leakage: matches training/test hash {img_hash}")

            # 5. Expert label status
            expert_rec = expert_records.get(r.image_id)
            if expert_rec:
                expert_status = expert_rec.annotation_state.value
            else:
                expert_status = "MISSING_LABEL"
                rejection_reasons.append("Missing expert review in expert_labels.csv")

            # Final acceptance decision
            include_in_eval = (
                file_ok and
                priv_ok and
                dup_status != DuplicateStatus.REJECT_EXACT_DUPLICATE.value and
                leak_status != LeakageStatus.REJECT_BENCHMARK_LEAKAGE.value and
                expert_status in ["CONFIRMED", "PROBABLE"]
            )

            if include_in_eval:
                accepted += 1
            else:
                rejected += 1

            item = ManifestItem(
                image_id=r.image_id,
                crop=r.crop,
                image_path=img_path,
                image_hash=img_hash,
                perceptual_hash=p_hash,
                image_size_bytes=size_bytes,
                image_width=width,
                image_height=height,
                metadata_valid=meta_ok,
                privacy_valid=priv_ok,
                duplicate_status=dup_status,
                benchmark_leakage_status=leak_status,
                expert_label_status=expert_status,
                included_in_evaluation=include_in_eval,
                rejection_reasons=rejection_reasons,
                duplicate_classification=dup_class.value,
                provenance_source=r.annotation_source
            )
            manifest_items.append(item)

        exact_count = sum(1 for i in manifest_items if i.duplicate_classification == DuplicateClassification.EXACT_DUPLICATE.value)
        priv_viol_count = sum(1 for i in manifest_items if not i.privacy_valid)
        corrupt_count = sum(1 for i in manifest_items if any("decode failure" in r or "not found" in r for r in i.rejection_reasons))
        missing_lbl_count = sum(1 for i in manifest_items if i.expert_label_status == "MISSING_LABEL")

        quality_report = PilotQualityReport(
            run_id=run_id,
            timestamp=timestamp,
            total_records=len(manifest_items),
            accepted=accepted,
            rejected=rejected,
            exact_duplicates=exact_count,
            near_duplicates=flagged_near,
            missing_metadata=len(meta_res.get("errors", [])),
            invalid_metadata=0,
            missing_labels=missing_lbl_count,
            privacy_violations=priv_viol_count,
            unsupported_crop=0,
            unsupported_language=0,
            corrupt_media=corrupt_count,
            provenance_failures=0,
            rejection_details=[f"Image {item.image_id}: {', '.join(item.rejection_reasons)}" for item in manifest_items if item.rejection_reasons][:50]
        )

        manifest = FieldDatasetManifest(
            run_id=run_id,
            timestamp=timestamp,
            total_submitted=len(manifest_items),
            accepted_for_eval=accepted,
            rejected_count=rejected,
            flagged_near_duplicate_count=flagged_near,
            items=manifest_items,
            quality_report=quality_report.model_dump()
        )

        cls._save_manifest(manifest, manifest_dir)
        return manifest

    @classmethod
    def ingest_single_image(
        cls,
        image_bytes: bytes,
        filename: str,
        metadata: Dict[str, Any],
        expert_label: Optional[Dict[str, Any]] = None,
        known_exact_hashes: Optional[Dict[str, List[str]]] = None,
        near_dup_paths: Optional[Set[str]] = None
    ) -> Dict[str, Any]:
        """
        Executes complete production ingestion pipeline on a single image record:
        RAW INPUT -> FILE/MIME/SIZE -> HASHING -> DUPLICATE -> PII -> METADATA -> SCHEMA -> PROVENANCE -> ACCEPT/QUARANTINE
        """
        rejection_reasons = []

        # 1. Media Validation (File, MIME, Size, Dimensions)
        media_ok, media_errors, media_info = FieldDatasetValidator.validate_media_file(
            media_input=image_bytes,
            filename=filename,
            max_size_bytes=20 * 1024 * 1024,
            min_dimension=64
        )
        if not media_ok:
            rejection_reasons.extend(media_errors)

        img_hash = media_info.get("md5_hash", "")
        p_hash = media_info.get("perceptual_hash", "")

        # 2. Duplicate Detection
        dup_class = DuplicateClassification.UNIQUE
        if known_exact_hashes and img_hash in known_exact_hashes:
            dup_class = DuplicateClassification.EXACT_DUPLICATE
            rejection_reasons.append(f"Exact duplicate detected (MD5 {img_hash})")
        elif near_dup_paths and filename in near_dup_paths:
            dup_class = DuplicateClassification.NEAR_DUPLICATE

        # 3. Privacy & PII
        priv_ok, priv_errors = FieldDatasetValidator.validate_privacy(metadata)
        if not priv_ok:
            rejection_reasons.extend(priv_errors)

        # 4. Schema & Metadata Validation
        schema_ok = False
        parsed_meta = None
        try:
            parsed_meta = FieldImageMetadata(**metadata)
            schema_ok = True
        except Exception as e:
            rejection_reasons.append(f"Metadata schema validation error: {str(e)}")

        # 5. Provenance Record
        prov_dict = metadata.get("provenance")
        provenance = None
        if prov_dict:
            try:
                provenance = DataProvenance(**prov_dict)
            except Exception as e:
                rejection_reasons.append(f"Invalid provenance record: {str(e)}")
        else:
            # Default to DEVICE_CAPTURE or FARMER_CAPTURED if source specified
            src_type = metadata.get("source_type", ProvenanceSourceType.FARMER_CAPTURED.value)
            try:
                provenance = DataProvenance(
                    source_type=ProvenanceSourceType(src_type),
                    source_reference=filename,
                    collected_at=metadata.get("capture_timestamp", datetime.now(timezone.utc).isoformat()),
                    imported_at=datetime.now(timezone.utc).isoformat(),
                    collector_id_hash=metadata.get("farmer_id_hash"),
                    annotation_source=metadata.get("annotation_source"),
                    verification_status="UNVERIFIED"
                )
            except Exception as e:
                rejection_reasons.append(f"Provenance generation error: {str(e)}")

        # 6. Expert Annotation Status (Blind evaluation isolation)
        expert_status = "MISSING_LABEL"
        if expert_label:
            try:
                parsed_expert = ExpertLabelRecord(**expert_label)
                expert_status = parsed_expert.annotation_state.value
            except Exception as e:
                rejection_reasons.append(f"Expert label schema error: {str(e)}")

        # Acceptance Decision
        accepted = (
            media_ok and
            priv_ok and
            schema_ok and
            dup_class != DuplicateClassification.EXACT_DUPLICATE and
            len(rejection_reasons) == 0
        )

        manifest_item = None
        if parsed_meta and media_ok:
            manifest_item = ManifestItem(
                image_id=parsed_meta.image_id,
                crop=parsed_meta.crop,
                image_path=filename,
                image_hash=img_hash,
                perceptual_hash=p_hash,
                image_size_bytes=media_info.get("size_bytes", 0),
                image_width=media_info.get("width", 0),
                image_height=media_info.get("height", 0),
                metadata_valid=schema_ok,
                privacy_valid=priv_ok,
                duplicate_status=DuplicateStatus.CLEAN.value if dup_class == DuplicateClassification.UNIQUE else DuplicateStatus.FLAG_NEAR_DUPLICATE.value,
                benchmark_leakage_status=LeakageStatus.CLEAN.value,
                expert_label_status=expert_status,
                included_in_evaluation=accepted and expert_status in ["CONFIRMED", "PROBABLE"],
                rejection_reasons=rejection_reasons,
                duplicate_classification=dup_class.value,
                provenance_source=provenance.source_type.value if provenance else None
            )

        return {
            "status": "ACCEPTED" if accepted else "QUARANTINED",
            "accepted": accepted,
            "duplicate_classification": dup_class.value,
            "media_info": media_info,
            "provenance": provenance.model_dump() if provenance else None,
            "manifest_item": manifest_item.model_dump() if manifest_item else None,
            "rejection_reasons": rejection_reasons
        }

    @classmethod
    def ingest_voice_pilot_record(cls, record_dict: Dict[str, Any]) -> Dict[str, Any]:
        """
        Ingests and validates a field voice pilot record with PII check and provenance.
        """
        rejection_reasons = []

        # PII check on transcript
        transcript = record_dict.get("transcript", "")
        if FieldDatasetValidator.PHONE_REGEX.search(transcript):
            rejection_reasons.append("PII Detected: Phone number in transcript")
        if FieldDatasetValidator.AADHAAR_REGEX.search(transcript):
            rejection_reasons.append("PII Detected: Aadhaar in transcript")

        # Schema validation
        parsed_record = None
        try:
            parsed_record = VoicePilotRecord(**record_dict)
        except Exception as e:
            rejection_reasons.append(f"Voice record schema error: {str(e)}")

        accepted = len(rejection_reasons) == 0
        return {
            "status": "ACCEPTED" if accepted else "QUARANTINED",
            "accepted": accepted,
            "record": parsed_record.model_dump() if parsed_record else None,
            "rejection_reasons": rejection_reasons
        }

    @classmethod
    def ingest_task_outcome_record(cls, record_dict: Dict[str, Any]) -> Dict[str, Any]:
        """
        Ingests and validates a longitudinal task outcome log.
        """
        rejection_reasons = []
        parsed_record = None
        try:
            parsed_record = TaskOutcomeRecord(**record_dict)
        except Exception as e:
            rejection_reasons.append(f"Task record schema error: {str(e)}")

        accepted = len(rejection_reasons) == 0
        return {
            "status": "ACCEPTED" if accepted else "QUARANTINED",
            "accepted": accepted,
            "record": parsed_record.model_dump() if parsed_record else None,
            "rejection_reasons": rejection_reasons
        }

    @staticmethod
    def _save_manifest(manifest: FieldDatasetManifest, manifest_dir: str):
        os.makedirs(manifest_dir, exist_ok=True)
        out_path = os.path.join(manifest_dir, f"manifest_{manifest.run_id}.json")
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(manifest.model_dump(), f, indent=2)


def run_field_ingestion_cli():
    print("=" * 80)
    print("BHOOMI V2 — PHASE 5 STEP 2: CONTROLLED FIELD PILOT INGESTION WORKFLOW")
    print("=" * 80)
    manifest = FieldPilotIngestionService.ingest_pilot_batch()
    print(f"\n[*] Ingestion Run ID: {manifest.run_id}")
    print(f"[*] Total Images Processed: {manifest.total_submitted}")
    print(f"[*] Accepted for Blind Evaluation: {manifest.accepted_for_eval}")
    print(f"[*] Rejected Images: {manifest.rejected_count}")
    print(f"[*] Flagged Near-Duplicates: {manifest.flagged_near_duplicate_count}")
    if manifest.total_submitted == 0:
        print("[*] STATUS: No real on-farm pilot images queued yet ('FIELD DATA NOT YET AVAILABLE').")
    print("=" * 80)
    return manifest


if __name__ == "__main__":
    run_field_ingestion_cli()
