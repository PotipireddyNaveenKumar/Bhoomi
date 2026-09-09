# BHOOMI V2 — Voice-First Multilingual Personal AI Farm Manager

BHOOMI V2 is a **Voice-First Multilingual Personal AI Farm Manager & Agricultural Decision Intelligence Platform** built for Indian farmers.

It guides the farmer through the core continuous agricultural loop:
$$\text{ASK} \rightarrow \text{REMEMBER} \rightarrow \text{PLAN} \rightarrow \text{MONITOR} \rightarrow \text{PREDICT} \rightarrow \text{COMPARE} \rightarrow \text{DECIDE} \rightarrow \text{REMIND} \rightarrow \text{ADAPT}$$

---

## 🌾 Features & Architecture Highlights

1. **Voice-First Interaction (Sarvam AI Provider)**:
   - Official Sarvam AI STT (`saaras:v2`) and TTS (`bulbul:v1`) integration.
   - Provider abstraction supporting Sarvam, Whisper, Mock, and future Bhashini.
   - Fully localized in **6 Indian Languages**: Telugu (`te`), Hindi (`hi`), English (`en`), Tamil (`ta`), Kannada (`kn`), and Malayalam (`ml`).
2. **Farm Digital Twin & Long-Term Memory**:
   - Stores farmer profile, land acreage, soil type, irrigation source, and active crop stage.
   - Retains conversational and episodic farm memories across multiple turns.
3. **Deterministic Financial & Simulation Engines**:
   - Exact `Decimal` arithmetic for revenue, cultivation cost, profit per acre, and ROI.
   - What-If Farm Simulator for price fluctuations, rainfall shocks, and yield variations.
4. **Mandi Market Intelligence**:
   - Computes true **Net Realization** (`Modal Price - Transport Cost - Handling Fees`) rather than just naive maximum displayed prices.
5. **Agricultural SafetyEngine**:
   - Intercepts and blocks banned chemicals (Monocrotophos, Endosulfan, Paraquat).
   - Enforces pollinator protection warnings during crop flowering stages.
6. **Smart Reminders**:
   - Evaluates real-time weather and farm conditions before firing reminders (e.g. postponing irrigation if rainfall $\ge 40\%$).

---

## 🚀 Quick Start Guide

### 1. Prerequisites
- Python 3.10+
- Flutter SDK 3.0+
- Docker & Docker Compose (Optional for containerized run)

### 2. Backend Setup
```bash
# Navigate to backend
cd backend

# Install dependencies
pip install -r requirements.txt

# Run automated unit tests
python -m pytest tests -v

# Start FastAPI development server
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```
API Documentation will be accessible at: `http://localhost:8000/docs`

### 3. Running with Docker Compose
```bash
docker-compose up --build
```
This starts:
- **PostgreSQL 15** on `localhost:5432`
- **Redis 7** on `localhost:6379`
- **BHOOMI FastAPI Backend** on `localhost:8000`

### 4. Running the Flutter Mobile App
```bash
# Navigate to mobile app directory
cd frontend/mobile

# Get dependencies
flutter pub get

# Run on Web / Android emulator / connected device
flutter run
```

---

## 📁 Repository Structure
- `backend/app/` — FastAPI core, database models, repositories, agents, and provider services.
- `backend/tests/` — Pytest test suite covering financial precision, simulations, safety engine, and agent routing.
- `frontend/mobile/` — Flutter mobile application with voice orb, multi-language support, and visual card components.
- `docs/` — Architectural designs, API contracts, database schemas, voice pipelines, safety specs, and Phase 2 roadmap.
- `docker-compose.yml` — Multi-container orchestration.
