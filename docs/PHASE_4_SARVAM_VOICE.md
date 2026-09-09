# Phase 4 Step 3: Real Sarvam AI Voice Provider Activation & Verification

**Platform**: BHOOMI V2 — Voice-First Personal AI Farm Manager & Agricultural Decision Intelligence Platform  
**Phase**: Phase 4 — Real-World Readiness & Generalization Audit  
**Step**: Step 3 — Real Sarvam AI Voice Provider Activation & Verification  
**Status**: COMPLETE  
**Test Suite**: 62/62 tests passing (48 baseline tests + 14 new Sarvam voice integration tests)

---

## 1. Executive Summary

Phase 4 Step 3 activates the production-grade **Sarvam AI Voice Engine** (`saaras:v3` for Speech-to-Text and `bulbul:v3` for Text-to-Speech) into BHOOMI V2's decision intelligence loop.

Voice interactions and text chat share the **exact same BHOOMI agent reasoning pipeline**, guaranteeing that voice queries adhere to the same deterministic domain tools, Decimal financial math, and strict `SafetyEngine` pesticide safeguards:

```
[Farmer Microphone]
        ↓
[Flutter Audio Capture] (16kHz 16-bit Mono WAV)
        ↓
[POST /api/v1/voice/interact] (FastAPI Unified Endpoint)
        ↓
[VoiceProvider Factory] (Resolves SarvamVoiceProvider or MockVoiceProvider)
        ↓
[Sarvam STT: saaras:v3] (Multilingual Speech-to-Text)
        ↓
[Language Normalization] (en, te, hi, ta, kn, ml)
        ↓
[BhoomiAgentOrchestrator] (SAME Decision Intelligence Loop as Typing)
        ↓
[Digital Twin Context + Farm Memory]
        ↓
[ToolRegistry] (ML Crop Recommendation, XGBoost Yield, FinancialService Decimal Math, Weather, Market)
        ↓
[SafetyEngine.evaluate()] (Mandatory CIBRC Banned Chemical & Pollinator Gate)
        ↓
[Final Farmer Advisory] (Grounded in Tool Outputs)
        ↓
[Sarvam TTS: bulbul:v3] (Language-Optimized Voice Synthesis)
        ↓
[Structured Response (Audio Base64 + Text + Visual Cards)]
        ↓
[Flutter Playback & Visual Card Presentation]
```

---

## 2. VoiceProvider Abstraction

The voice architecture implements clean polymorphism through `VoiceProvider`:

```
VoiceProvider (backend/app/services/voice/base.py)
├── SarvamVoiceProvider (backend/app/services/voice/sarvam.py)
└── MockVoiceProvider   (backend/app/services/voice/mock.py)
```

### Methods
- `async def transcribe(self, audio_bytes: bytes, language_code: Optional[str] = None) -> TranscriptionResult`:
  Converts voice audio bytes into structured text with detected language and confidence score.
- `async def synthesize(self, text: str, language_code: str = "en", speaker_gender: str = "female") -> SynthesisResult`:
  Synthesizes agricultural advisory text into WAV audio bytes using language-optimized neural speakers.

---

## 3. Supported Six-Language Architecture

BHOOMI V2 maintains a strict multi-lingual design across six foundational Indian agricultural languages:

| Language | ISO Code | Sarvam BCP-47 Tag | bulbul:v3 Female Speaker | bulbul:v3 Male Speaker |
| :--- | :--- | :--- | :--- | :--- |
| **English** | `en` | `en-IN` | `kavya` | `aditya` |
| **Telugu** | `te` | `te-IN` | `kavitha` | `mani` |
| **Hindi** | `hi` | `hi-IN` | `kavya` | `rahul` |
| **Tamil** | `ta` | `ta-IN` | `kavitha` | `mani` |
| **Kannada** | `kn` | `kn-IN` | `roopa` | `mani` |
| **Malayalam** | `ml` | `ml-IN` | `kavitha` | `mani` |

*The provider interface is completely decoupled from Telugu/English specifics and easily accommodates additional regional languages (Marathi, Bengali, Gujarati, Punjabi) without code refactoring.*

---

## 4. Configuration & Environment Variables

All voice credentials remain strictly isolated on the backend. No secret keys are ever exposed to the Flutter application, Dart constants, Git repositories, or logs.

```bash
# Set in backend/.env or system environment:
VOICE_PROVIDER=sarvam              # Options: "sarvam" | "mock"
SARVAM_API_KEY=your_sarvam_api_key_here
SARVAM_STT_MODEL=saaras:v3
SARVAM_TTS_MODEL=bulbul:v3
```

### Fallback Guarantee
If `VOICE_PROVIDER=sarvam` is configured but `SARVAM_API_KEY` is missing or placeholder (`your_...`), the factory logs a controlled warning and gracefully falls back to `MockVoiceProvider`. This ensures that automated tests, CI/CD runners, and offline environments run reliably without crashing.

---

## 5. Unified Voice Endpoint (`POST /api/v1/voice/interact`)

The unified voice endpoint coordinates speech processing and domain reasoning:

### Request
- `file`: `UploadFile` (WAV, MP3, M4A, OGG, WebM; max 10MB; non-empty)
- `session_id`: `str` (Optional chat session identifier)

### Pipeline Stages
1. **Audio Validation**: Validates MIME prefixes (`audio/*`, `application/octet-stream`) and validates file size boundary (10MB maximum).
2. **Sarvam STT**: Converts audio to text via `saaras:v3`.
3. **Empty Transcript Handling**: If audio is silent or unintelligible, returns a polite clarification request in the farmer's language rather than an HTTP 500 error.
4. **Chat Persistence**: Records farmer audio query in `ChatRepository`.
5. **Agent Reasoning**: Invokes `BhoomiAgentOrchestrator.process_turn(...)` — identical reasoning engine used by text queries.
6. **Deterministic Tool Execution**: Executes domain tools (`calculate_profit`, `recommend_crops`, `predict_crop_yield`, `get_weather_forecast`, `get_mandi_prices`).
7. **Mandatory SafetyEngine Gate**: Validates recommendation against CIBRC banned chemical list (blocking Monocrotophos, Endosulfan, Paraquat, etc.) and appends required pollinator/PPE safeguards.
8. **Sarvam TTS**: Synthesizes final approved advisory into WAV audio using `bulbul:v3`.
9. **Response Payload**: Returns `VoiceInteractResponse` containing base64 audio, transcription, assistant text, visual cards, and state `RESPONDING`.

---

## 6. Flutter Mobile Integration

In [voice_assistant_screen.dart](file:///c:/Users/SURESH/SIH/frontend/mobile/lib/features/voice/voice_assistant_screen.dart):
- **Voice State Machine**:
  - `IDLE`: Displays initial microphone prompt ("Tap microphone to speak with BHOOMI").
  - `LISTENING`: Animated emerald pulsing orb during farmer speech capture.
  - `PROCESSING`: Transmitting audio to backend (`POST /api/v1/voice/interact`).
  - `THINKING`: Agent orchestrating ML models, financial math, and safety rules.
  - `RESPONDING`: Audio playback active, rendering transcription, advisory text, and interactive visual cards.
  - `ERROR`: Displays controlled offline warning with automatic local advisory fallback.
- **Multipart Networking**: Utilizes `ApiClient.postMultipart` to stream audio bytes with authentication tokens.

---

## 7. Security Audit & Secret Isolation

A full repository audit confirmed:
- **Zero API Key Leakage**: No active API keys committed to Git or documentation.
- **Header Isolation**: `api-subscription-key` is encapsulated in backend requests only.
- **Redacted Exceptions**: `VoiceProcessingException` strips all sensitive network URLs and authentication headers from user-facing error messages.
- **Bounded In-Memory Streaming**: Strict 10MB threshold prevents memory denial-of-service.

---

## 8. Controlled Real Sarvam Live Verification

A controlled live verification was executed using real Sarvam AI production endpoints:

```bash
$ python backend/scripts/verify_phase4_sarvam_live.py
```

### Live Test Results

#### 1. English Roundtrip Pipeline
- **Input Query**: *"How is the weather for my farm?"*
- **Sarvam TTS Output**: 90,360 bytes WAV audio generated
- **Sarvam STT Input**: Audio transmitted to `saaras:v3`
- **STT Transcript**: `"How is the weather for my farm?"` (Confidence: 1.00, Language: `en`)
- **BHOOMI Orchestrator**: Received transcript, loaded farm Digital Twin, and generated weather advisory
- **SafetyEngine**: Verified status `PASS` (Is Safe: True)
- **Sarvam TTS Response**: Synthesized 353,784 bytes WAV speech audio

#### 2. Telugu Roundtrip Pipeline
- **Input Query**: *"నా పొలానికి ఈ వారం వాతావరణం ఎలా ఉంటుంది?"*
- **Sarvam TTS Output**: 169,388 bytes WAV audio generated (`speaker: kavitha`)
- **Sarvam STT Input**: Audio transmitted to `saaras:v3`
- **STT Transcript**: `"నా పొలానికి ఈ వారం వాతావరణం ఎలా ఉంటుంది?"` (Language: `te`)
- **BHOOMI Orchestrator**: Generated Telugu agricultural advisory with visual weather card
- **SafetyEngine**: Verified status `MODIFY` (Injected pollinator and protective equipment precautions)
- **Sarvam TTS Response**: Synthesized 751,508 bytes WAV Telugu speech audio

**Roundtrip End-to-End Success**: **100% Verified on Production Sarvam API**.

---

## 9. Automated Regression Test Suite

All tests executed with zero failures:

```bash
$ python -m pytest backend/tests -v
======================= 62 passed, 67 warnings in 6.65s =======================
```

- **Phase 1 Baseline**: 13/13 PASSED
- **Phase 2 Baseline**: 14/14 PASSED
- **Phase 3 Baseline**: 16/16 PASSED
- **Phase 4 Step 2 Real LLM Suite**: 5/5 PASSED
- **Phase 4 Step 3 Sarvam Voice Suite** ([test_phase4_sarvam_voice.py](file:///c:/Users/SURESH/SIH/backend/tests/test_phase4_sarvam_voice.py)): 14/14 PASSED
  1. `test_voice_factory_resolution` — Verified resolution of `mock` and `sarvam` with fallback.
  2. `test_mock_provider_operation` — Verified deterministic mock STT & TTS in English and Telugu.
  3. `test_sarvam_provider_configuration` — Verified model tags (`saaras:v3`, `bulbul:v3`) and URLs.
  4. `test_missing_api_key_handling` — Verified controlled `VoiceProcessingException`.
  5. `test_invalid_audio_handling` — Verified rejection of empty and oversized (>10MB) payloads.
  6. `test_network_failure_handling` — Verified graceful error handling when remote host is unreachable.
  7. `test_http_429_handling` — Verified rate-limit detection and farmer-friendly notification.
  8. `test_stt_response_parsing` — Verified JSON parsing, language detection, and confidence scoring.
  9. `test_tts_response_parsing` — Verified base64 audio decoding into raw WAV bytes.
  10. `test_six_language_configuration` — Verified canonical tags (`en`, `te`, `hi`, `ta`, `kn`, `ml`) and speaker mapping.
  11. `test_unified_voice_endpoint_validation` — Verified MIME and extension safety gate.
  12. `test_voice_orchestrator_integration` — Verified `input_mode="voice"` generates visual cards and sets `voice_state="RESPONDING"`.
  13. `test_safety_engine_blocks_banned_chemicals_in_voice` — Verified pesticide restriction gate in voice pipeline.
  14. `test_no_api_key_leakage_in_logs_or_errors` — Verified that secret keys are never leaked in error strings.

**Total**: **62 / 62 PASSING (100%)**

---

## 10. Known Limitations & Roadmap

1. **Streaming Audio / WebSockets**: Current implementation utilizes standard HTTP multipart request/response (REST). Full duplex streaming voice via WebSockets will be introduced in future phases.
2. **Background Audio Noise Filtering**: Relies on Sarvam's built-in acoustic model; on-device noise reduction can further improve field transcription in high-wind conditions.
