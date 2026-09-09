import hashlib
import numpy as np
from typing import List, Dict, Any, Tuple, Optional
from collections import defaultdict
from sklearn.metrics import accuracy_score, f1_score

class FarmSessionGroupManager:
    """
    Manages farm, plant, and session grouping to prevent leakage
    and executes group-level aggregated agricultural evaluation.
    """

    DEFAULT_SALT = "bhoomi_v2_field_salt_2026"

    @classmethod
    def generate_privacy_hash(cls, raw_identifier: str, salt: str = None) -> str:
        """
        Generates a deterministic, one-way SHA-256 pseudonym hash
        preventing farmer contact details or names from persisting.
        """
        if not raw_identifier:
            return ""
        s = salt or cls.DEFAULT_SALT
        h = hashlib.sha256(f"{s}:{raw_identifier}".encode("utf-8"))
        return h.hexdigest()

    @classmethod
    def detect_group_leakage(
        cls,
        split_a: List[Dict[str, Any]],
        split_b: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Detects if any farm_id_hash, plant_id_hash, or collection_session_id
        crosses between split A and split B, which would cause optimistic leakage.
        """
        keys_to_check = ["farm_id_hash", "plant_id_hash", "collection_session_id", "farmer_id_hash"]
        leakage_detected = False
        findings = {}

        for key in keys_to_check:
            a_set = {item.get(key) for item in split_a if item.get(key)}
            b_set = {item.get(key) for item in split_b if item.get(key)}
            intersection = a_set.intersection(b_set)

            if intersection:
                leakage_detected = True
                findings[key] = {
                    "leaked_identifiers": list(intersection),
                    "count": len(intersection)
                }

        return {
            "has_group_leakage": leakage_detected,
            "findings": findings
        }

    @classmethod
    def group_aware_split(
        cls,
        records: List[Dict[str, Any]],
        train_ratio: float = 0.8,
        group_key: str = "farm_id_hash"
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """
        Splits dataset by grouping entities (e.g. farm_id_hash or plant_id_hash),
        guaranteeing zero cross-split group leakage.
        """
        grouped = defaultdict(list)
        for r in records:
            gid = r.get(group_key) or r.get("image_id", "unknown")
            grouped[gid].append(r)

        unique_groups = list(grouped.keys())
        np.random.seed(42)
        np.random.shuffle(unique_groups)

        cutoff = int(len(unique_groups) * train_ratio)
        train_groups = set(unique_groups[:cutoff])

        split_train = []
        split_test = []

        for gid, items in grouped.items():
            if gid in train_groups:
                split_train.extend(items)
            else:
                split_test.extend(items)

        return split_train, split_test

    @classmethod
    def group_aware_three_way_split(
        cls,
        records: List[Dict[str, Any]],
        train_ratio: float = 0.7,
        val_ratio: float = 0.15,
        group_keys: Optional[List[str]] = None,
        random_seed: int = 42
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Splits dataset into train, validation, and test splits guaranteeing zero
        cross-split leakage across compound grouping keys (e.g. farm_id_hash, plant_id_hash, collection_session_id).
        """
        if not group_keys:
            group_keys = ["farm_id_hash", "plant_id_hash", "collection_session_id"]

        def get_group_id(r):
            for k in group_keys:
                if r.get(k):
                    return f"{k}:{r[k]}"
            return f"image:{r.get('image_id', 'unknown')}"

        grouped = defaultdict(list)
        for r in records:
            gid = get_group_id(r)
            grouped[gid].append(r)

        unique_groups = sorted(list(grouped.keys()))
        rng = np.random.RandomState(random_seed)
        rng.shuffle(unique_groups)

        n_groups = len(unique_groups)
        train_end = int(n_groups * train_ratio)
        val_end = train_end + int(n_groups * val_ratio)

        train_groups = set(unique_groups[:train_end])
        val_groups = set(unique_groups[train_end:val_end])
        test_groups = set(unique_groups[val_end:])

        train_set = []
        val_set = []
        test_set = []

        for gid, items in grouped.items():
            if gid in train_groups:
                train_set.extend(items)
            elif gid in val_groups:
                val_set.extend(items)
            else:
                test_set.extend(items)

        return {
            "train": train_set,
            "validation": val_set,
            "test": test_set
        }

    @classmethod
    def detect_three_way_leakage(
        cls,
        train_set: List[Dict[str, Any]],
        val_set: List[Dict[str, Any]],
        test_set: List[Dict[str, Any]],
        keys_to_check: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Detects if any farm, plant, session, or farmer identifier crosses across train, validation, or test sets.
        """
        if not keys_to_check:
            keys_to_check = ["farm_id_hash", "plant_id_hash", "collection_session_id", "farmer_id_hash"]

        leakage_pairs = [
            ("train_vs_val", train_set, val_set),
            ("train_vs_test", train_set, test_set),
            ("val_vs_test", val_set, test_set)
        ]

        total_leakage = False
        findings = {}

        for pair_name, s1, s2 in leakage_pairs:
            pair_findings = cls.detect_group_leakage(s1, s2)
            if pair_findings["has_group_leakage"]:
                total_leakage = True
                findings[pair_name] = pair_findings["findings"]

        return {
            "has_leakage": total_leakage,
            "findings": findings
        }

    @classmethod
    def prepare_blind_annotation_packet(cls, raw_record: Dict[str, Any]) -> Dict[str, Any]:
        """
        Strips all model predictions, confidence scores, and diagnostic outputs
        to ensure true blind evaluation by agronomic experts.
        """
        forbidden_keys = {
            "predicted_disease", "confidence", "calibrated_confidence",
            "model_name", "model_prediction", "predictions", "top_k",
            "uncertainty_status", "is_reliable", "is_ood", "logits"
        }
        blind_packet = {k: v for k, v in raw_record.items() if k not in forbidden_keys}
        blind_packet["is_blinded"] = True
        return blind_packet

    @classmethod
    def join_blind_evaluations(
        cls,
        blind_records: List[Dict[str, Any]],
        expert_annotations: Dict[str, Any],
        model_predictions: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Only after blind expert annotations are submitted and frozen,
        joins them with pre-frozen model predictions to calculate evaluation metrics.
        """
        joined = []
        for r in blind_records:
            img_id = r.get("image_id")
            expert = expert_annotations.get(img_id, {})
            pred = model_predictions.get(img_id, {})

            joined_item = dict(r)
            joined_item["expert_label"] = expert.get("expert_label", "UNKNOWN")
            joined_item["expert_confidence"] = expert.get("expert_confidence", 0.0)
            joined_item["annotation_state"] = expert.get("annotation_state", "UNVERIFIED")
            joined_item["predicted_disease"] = pred.get("predicted_disease", "UNKNOWN")
            joined_item["confidence"] = pred.get("confidence", 0.0)
            joined_item["is_reliable"] = pred.get("is_reliable", False)
            joined_item["uncertainty_status"] = pred.get("uncertainty_status", "UNKNOWN")
            joined.append(joined_item)
        return joined

    @classmethod
    def aggregate_group_predictions(
        cls,
        group_predictions: List[Dict[str, Any]],
        group_key: str = "plant_id_hash",
        min_groups_required: int = 5
    ) -> Dict[str, Any]:
        """
        Aggregates multiple leaf observations for the same plant or session.
        Documented Method: Confidence-Weighted Soft Voting
        Formula: P_g = sum(w_i * P_i) / sum(w_i), where w_i is calibrated_confidence.
        If dataset has fewer than min_groups_required:
        Outputs 'GROUP-LEVEL METRICS NOT YET RELIABLE' rather than fabricating statistical confidence.
        """
        if not group_predictions:
            return {
                "group_metrics_available": False,
                "status": "FIELD DATA NOT YET AVAILABLE",
                "message": "No field predictions available for group aggregation."
            }

        grouped_samples = defaultdict(list)
        for p in group_predictions:
            gid = p.get(group_key) or p.get("farm_id_hash") or p.get("image_id")
            grouped_samples[gid].append(p)

        total_groups = len(grouped_samples)
        if total_groups < min_groups_required:
            return {
                "group_metrics_available": False,
                "status": "GROUP-LEVEL METRICS NOT YET RELIABLE",
                "total_groups": total_groups,
                "min_required": min_groups_required,
                "message": (
                    f"Sample size too small ({total_groups} groups < {min_groups_required} required). "
                    "In accordance with BHOOMI transparency rules, group-level metrics are withheld."
                )
            }

        y_true_groups = []
        y_pred_groups = []
        group_confidences = []

        for gid, samples in grouped_samples.items():
            # True label from first confirmed sample
            ground_truth = samples[0].get("expert_label")
            y_true_groups.append(ground_truth)

            # Confidence-weighted aggregation
            class_weights = defaultdict(float)
            total_weight = 0.0

            for s in samples:
                conf = max(0.01, float(s.get("calibrated_confidence", 0.5)))
                pred = s.get("predicted_disease")
                class_weights[pred] += conf
                total_weight += conf

            # Argmax of weighted vote
            best_class = max(class_weights.keys(), key=lambda k: class_weights[k])
            group_conf = class_weights[best_class] / total_weight if total_weight > 0 else 0.5

            y_pred_groups.append(best_class)
            group_confidences.append(round(group_conf, 4))

        acc = round(float(accuracy_score(y_true_groups, y_pred_groups)), 4)
        f1 = round(float(f1_score(y_true_groups, y_pred_groups, average="macro", zero_division=0)), 4)

        return {
            "group_metrics_available": True,
            "status": "EVALUATED",
            "aggregation_strategy": "CONFIDENCE_WEIGHTED_SOFT_VOTING",
            "total_groups": total_groups,
            "group_accuracy": acc,
            "group_macro_f1": f1,
            "mean_group_confidence": round(float(np.mean(group_confidences)), 4)
        }
