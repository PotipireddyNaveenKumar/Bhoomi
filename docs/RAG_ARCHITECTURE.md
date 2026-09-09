# BHOOMI V2 — Agricultural RAG Architecture

## 1. Grounding Principles
LLMs must never hallucinate agricultural chemical dosages, pesticide mixtures, or plant disease treatments.
All high-risk recommendations in BHOOMI V2 require verified evidence retrieval from authoritative national agricultural institutes:
- **ICAR**: Indian Council of Agricultural Research
- **SAUs**: Acharya N.G. Ranga Agricultural University (ANGRAU), Tamil Nadu Agricultural University (TNAU), Professor Jayashankar Telangana State Agricultural University (PJTSAU)
- **CIBRC**: Central Insecticides Board & Registration Committee

---

## 2. Retrieval Pipeline Architecture

```mermaid
graph LR
    FarmerQuery[Farmer Question] --> Embedder[Domain Semantic Embedder]
    Embedder --> VectorStore[VectorStore (InMemory / Chroma)]
    VectorStore --> ChunkerMetadata[Filtered Chunks with Metadata]
    ChunkerMetadata --> CitationBuilder[Citation & Authority Builder]
    CitationBuilder --> SafetyEngine[SafetyEngine Compliance]
    SafetyEngine --> Orchestrator[Agent Response Synthesis]
```

---

## 3. Metadata Schema
Every chunk in the vector index contains:
- `crop`: Target crop (e.g. `chilli`, `rice`, `cotton`)
- `state`: State applicability (`Andhra Pradesh`, `Telangana`, `All-India`)
- `topic`: Domain area (`pest_management`, `nutrient_management`, `water_management`)
- `document`: Official publication title
- `authority`: Publishing research body (e.g. `ICAR-IIHR`, `ANGRAU`, `CRIDA`)
- `publication_date`: Year of advisory publication
- `section`: Specific chapter or section
