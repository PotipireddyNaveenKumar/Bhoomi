# BHOOMI V2 — Development Roadmap & Phase 2 Integration Guide

## Phase 1 (Completed Foundation)
- [x] Complete FastAPI async backend + PostgreSQL relational schema.
- [x] Flutter mobile application with Voice Orb, 6 regional Indian languages, and accessible visual information cards.
- [x] Provider abstractions for Sarvam AI Voice, LLMs, Weather, Mandi Market, VectorDB, and Vision Gate.
- [x] Deterministic Financial Engine (`Decimal` precision arithmetic for profit, cost, ROI).
- [x] Deterministic What-If Farm Simulator (price drops, yield shocks, rainfall deficit).
- [x] Multi-factor Risk Engine and dynamic Smart Reminder Condition Engine.
- [x] Agricultural SafetyEngine (banned substance interception, pollinator protection).
- [x] Docker configuration, database migrations, and 100% passing automated test suite.

## Phase 2 (Data Science, ML & Live Intelligence)
1. **Dataset Ingestion & EDA**:
   - Clean and evaluate agricultural datasets for geography, leakage, class imbalance, and provenance.
2. **Crop Recommendation Models**:
   - Benchmark Random Forest vs LightGBM vs XGBoost on soil/climate datasets.
3. **Yield Prediction Regressors**:
   - Benchmark Gradient Boosted Regressors with weather history and crop variety features.
4. **Computer Vision Leaf Disease Diagnosis**:
   - Integrate fine-tuned Vision Transformers / YOLOv8 for crop pest & disease localization.
5. **RAG Knowledge Base**:
   - Ingest verified ICAR, State Agricultural University (SAU), and KVK advisory documents into Chroma / pgvector with document provenance citations.
6. **Live Data Integration**:
   - Connect live IMD weather APIs and official Agmarknet mandi market streams.
