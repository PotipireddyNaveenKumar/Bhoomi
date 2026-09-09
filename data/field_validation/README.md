# BHOOMI V2 — Real-World Vision Field Validation Repository

This directory serves as the strictly isolated, independent evaluation repository for real-world on-farm smartphone foliar disease images in BHOOMI V2.

## 1. Directory Structure

```text
data/field_validation/
├── README.md
├── schema/
│   └── field_validation_schema.json    # JSON Schema definition for validation metadata
├── images/                             # Real field smartphone photographs (per crop)
│   ├── tomato/
│   ├── banana/
│   ├── guava/
│   ├── corn_maize/
│   ├── apple/
│   ├── chilli/
│   ├── cucumber_pumpkin/
│   ├── sugarcane/
│   ├── potato/
│   └── rice/
├── metadata/
│   └── field_validation.csv            # Tabular metadata index (device, lighting, distance, privacy hash)
├── labels/
│   └── expert_labels.csv               # Agronomist/Pathologist ground-truth consensus labels
└── reports/
    └── field_validation_report.md      # Auto-generated domain-shift & performance delta audits
```

## 2. Strict Data Integrity Rules

1. **Zero Contamination**: Images deposited in this folder must **NEVER** enter training, validation, or tuning pipelines. They constitute an out-of-sample real-world field audit set.
2. **No PlantVillage/Lab Images**: Only photographs taken on real farm plots, open polyhouses, or agricultural research station fields using handheld mobile cameras are permitted.
3. **Strict Privacy**: Under no circumstances should farmer names, phone numbers, village addresses, Aadhaar numbers, or exact residential coordinates be stored. One-way pseudonymous SHA-256 hashes (`farmer_id_hash`) and truncated 2-decimal coordinates are enforced.
4. **Current Status**: As of Phase 5 Step 1 initialization, field collection protocols are formalized. Real on-farm images will be ingested through controlled pilot deployments. In the absence of live field submissions, the pipeline outputs `FIELD DATA NOT YET AVAILABLE` without fabricating synthetic or fake scores.
