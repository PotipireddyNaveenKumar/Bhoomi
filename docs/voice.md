# BHOOMI V2 — Voice Pipeline & Sarvam AI Integration

## 1. Provider Abstraction
Voice capabilities are decoupled using the `VoiceProvider` interface:
```python
class VoiceProvider(ABC):
    @abstractmethod
    async def transcribe(self, audio_bytes: bytes, language_code: Optional[str] = None) -> TranscriptionResult: ...

    @abstractmethod
    async def synthesize(self, text: str, language_code: str = "en", speaker_gender: str = "female") -> SynthesisResult: ...
```

## 2. Supported Voice Providers
- **`SarvamVoiceProvider`**: Production provider using Sarvam AI Speech-to-Text (`saaras:v2`) and Text-to-Speech (`bulbul:v1`). API keys remain strictly configured in the backend environment.
- **`MockVoiceProvider`**: Zero-dependency deterministic provider for offline development and CI/CD testing.
- **`WhisperVoiceProvider`**: Fallback / local Whisper transcription.
- **Future Bhashini Integration**: Ready to plug in via `VOICE_PROVIDER=bhashini`.

## 3. Supported Languages
1. **Telugu (`te`)** — `te-IN`
2. **Hindi (`hi`)** — `hi-IN`
3. **English (`en`)** — `en-IN`
4. **Tamil (`ta`)** — `ta-IN`
5. **Kannada (`kn`)** — `kn-IN`
6. **Malayalam (`ml`)** — `ml-IN`

## 4. Voice State Machine
The UI implements 6 reassuring voice states:
- `IDLE`: "Tap and speak"
- `LISTENING`: "Listening..."
- `PROCESSING`: "Understanding..."
- `THINKING`: "Checking farm information..."
- `RESPONDING`: "Speaking..."
- `ERROR`: "Tap to retry"
