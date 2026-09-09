import struct
from typing import Optional
from app.services.voice.base import VoiceProvider, TranscriptionResult, SynthesisResult

class MockVoiceProvider(VoiceProvider):
    """
    Deterministic mock voice provider for local testing, development, and CI/CD
    without requiring active internet or paid external API keys.
    """
    async def transcribe(self, audio_bytes: bytes, language_code: Optional[str] = None) -> TranscriptionResult:
        # Returns a realistic farmer prompt for mock speech testing
        lang = language_code or "en"
        sample_texts = {
            "en": "What should I do this week on my chilli farm?",
            "te": "నా మిర్చి తోటలో ఈ వారం నేను ఏమి చేయాలి?",
            "hi": "मेरी मिर्च की फसल में इस हफ्ते मुझे क्या करना चाहिए?",
            "ta": "என் மிளகாய் பயிரில் இந்த வாரம் நான் என்ன செய்ய வேண்டும்?",
            "kn": "ನನ್ನ ಮೆಣಸಿನಕಾಯಿ ತೋಟದಲ್ಲಿ ಈ ವಾರ ಏನು ಮಾಡಬೇಕು?",
            "ml": "എന്റെ മുളക് കൃഷിയിൽ ഈ ആഴ്ച ഞാൻ എന്താണ് ചെയ്യേണ്ടത്?"
        }
        text = sample_texts.get(lang, "What should I do this week on my chilli farm?")
        return TranscriptionResult(
            text=text,
            language_code=lang,
            confidence=0.98,
            provider="mock"
        )

    async def synthesize(self, text: str, language_code: str = "en", speaker_gender: str = "female") -> SynthesisResult:
        # Generates a valid minimal 1-second silent WAV audio file for UI/API verification
        sample_rate = 16000
        num_samples = 16000
        num_channels = 1
        bits_per_sample = 16
        byte_rate = sample_rate * num_channels * (bits_per_sample // 8)
        block_align = num_channels * (bits_per_sample // 8)
        data_size = num_samples * block_align
        
        # RIFF Header
        header = b"RIFF"
        header += struct.pack("<I", 36 + data_size)
        header += b"WAVE"
        header += b"fmt "
        header += struct.pack("<I", 16)               # Subchunk1Size
        header += struct.pack("<H", 1)                # AudioFormat (PCM)
        header += struct.pack("<H", num_channels)     # NumChannels
        header += struct.pack("<I", sample_rate)      # SampleRate
        header += struct.pack("<I", byte_rate)        # ByteRate
        header += struct.pack("<H", block_align)      # BlockAlign
        header += struct.pack("<H", bits_per_sample)  # BitsPerSample
        header += b"data"
        header += struct.pack("<I", data_size)
        
        audio_bytes = header + (b"\x00" * data_size)
        return SynthesisResult(
            audio_bytes=audio_bytes,
            content_type="audio/wav",
            provider="mock",
            duration_seconds=1.0
        )
