# BHOOMI V2 — API Documentation

Base URL: `/api/v1`

## 1. Authentication
- `POST /auth/register` — Register farmer phone, credentials, preferred regional language, and location.
- `POST /auth/login` — Login with phone and password, returns JWT token.

## 2. Farmer & Farm Digital Twin
- `GET /farmer` & `PUT /farmer` — Get / update farmer profile.
- `GET /farms` & `POST /farms` — Manage land records, soil type, and irrigation sources.
- `POST /farms/{id}/crops` — Register active and planned crop cycles with lifecycle stages.

## 3. Unified Voice & Chat Pipeline
- `POST /voice/transcribe` — Multipart audio upload -> Sarvam STT.
- `POST /voice/synthesize` — Text -> Sarvam TTS audio bytes.
- `POST /voice/interact` — End-to-end voice round-trip: audio in -> STT -> Agent -> TTS -> audio out + visual cards.
- `POST /chat` — Multi-turn text chat with context retention and visual cards.

## 4. Decision Intelligence & Deterministic Engines
- `GET /weather` — Weather facts, 3-day forecast, and advisory.
- `GET /market` — Mandi prices and Net Realization comparisons.
- `POST /profit/calculate` — Exact Decimal revenue, cultivation cost, and net profit calculations.
- `POST /simulation/run` — What-If scenario simulations (price, yield, rainfall, cost shifts).
- `POST /risk/assess` — 5-dimension risk scoring (Weather, Yield, Market, Crop Health, Economics).
- `POST /image/analyze` — Image Quality Gate validation and CV diagnosis stub.
- `GET /tasks` & `POST /tasks` — Task scheduling and dynamic condition-based reminder evaluation.
