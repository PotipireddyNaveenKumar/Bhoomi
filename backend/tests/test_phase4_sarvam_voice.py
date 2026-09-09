import os
import base64
import pytest
from unittest.mock import AsyncMock, patch
import httpx
from fastapi import UploadFile, HTTPException
from app.services.voice.base import VoiceProvider, TranscriptionResult, SynthesisResult
from app.services.voice.mock import MockVoiceProvider
from app.services.voice.sarvam import SarvamVoiceProvider
from app.services.voice.factory import get_voice_provider
from app.core.exceptions import VoiceProcessingException
from app.api.v1.voice import validate_audio_file
from app.agents.orchestrator import BhoomiAgentOrchestrator
from app.services.safety.safety_engine import SafetyEngine

SAMPLE_WAV_BYTES = b"RIFF$\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00\x80>\x00\x00\x00}\x00\x00\x02\x00\x10\x00data\x00\x00\x00\x00"

# 1. Voice Provider Factory Resolution
def test_voice_factory_resolution():
    # Mock resolution
    p_mock = get_voice_provider("mock")
    assert isinstance(p_mock, MockVoiceProvider)

    # Sarvam resolution when key is present
    with patch.dict(os.environ, {"SARVAM_API_KEY": "sk_test_mock_sarvam_key"}):
        p_sarvam = get_voice_provider("sarvam")
        assert isinstance(p_sarvam, SarvamVoiceProvider)

    # Safe fallback to Mock when key is missing
    with patch.dict(os.environ, {"SARVAM_API_KEY": ""}):
        p_fallback = get_voice_provider("sarvam")
        assert isinstance(p_fallback, MockVoiceProvider)

# 2. Mock Provider Operation
@pytest.mark.asyncio
async def test_mock_provider_operation():
    provider = MockVoiceProvider()
    # English STT
    stt_en = await provider.transcribe(SAMPLE_WAV_BYTES, language_code="en")
    assert "chilli" in stt_en.text.lower()
    assert stt_en.language_code == "en"

    # Telugu STT
    stt_te = await provider.transcribe(SAMPLE_WAV_BYTES, language_code="te")
    assert "తోటలో" in stt_te.text
    assert stt_te.language_code == "te"

    # TTS
    tts = await provider.synthesize("Test advisory", language_code="en")
    assert len(tts.audio_bytes) > 44  # Has WAV header
    assert tts.content_type == "audio/wav"

# 3. Sarvam Provider Configuration
def test_sarvam_provider_configuration():
    provider = SarvamVoiceProvider(api_key="sk_test_cfg_key")
    assert provider.stt_model == "saaras:v3"
    assert provider.tts_model == "bulbul:v3"
    assert "speech-to-text" in provider.stt_url
    assert "text-to-speech" in provider.tts_url

# 4. Missing API Key Handling
@pytest.mark.asyncio
async def test_missing_api_key_handling():
    provider = SarvamVoiceProvider(api_key=None)
    with pytest.raises(VoiceProcessingException) as exc_info:
        await provider.transcribe(SAMPLE_WAV_BYTES)
    assert "SARVAM_API_KEY is not configured" in str(exc_info.value)

    with pytest.raises(VoiceProcessingException) as exc_info_tts:
        await provider.synthesize("Sample message")
    assert "SARVAM_API_KEY is not configured" in str(exc_info_tts.value)

# 5. Invalid Audio Handling
@pytest.mark.asyncio
async def test_invalid_audio_handling():
    provider = SarvamVoiceProvider(api_key="sk_test_valid_key")
    
    # Empty audio
    with pytest.raises(VoiceProcessingException) as exc:
        await provider.transcribe(b"")
    assert "empty" in str(exc.value).lower()

    # Oversized audio > 10MB
    oversized = b"0" * (11 * 1024 * 1024)
    with pytest.raises(VoiceProcessingException) as exc_large:
        await provider.transcribe(oversized)
    assert "exceeds maximum size" in str(exc_large.value).lower()

# 6. Network Failure Handling
@pytest.mark.asyncio
async def test_network_failure_handling():
    provider = SarvamVoiceProvider(api_key="sk_test_key")
    
    with patch("httpx.AsyncClient.post", side_effect=httpx.RequestError("Host unreachable")):
        with pytest.raises(VoiceProcessingException) as exc:
            await provider.transcribe(SAMPLE_WAV_BYTES)
        assert "Unable to connect" in str(exc.value)

# 7. HTTP 429 Rate Limit Handling
@pytest.mark.asyncio
async def test_http_429_handling():
    provider = SarvamVoiceProvider(api_key="sk_test_key")
    mock_resp = httpx.Response(429, text="Too Many Requests")

    with patch("httpx.AsyncClient.post", return_value=mock_resp):
        with pytest.raises(VoiceProcessingException) as exc:
            await provider.transcribe(SAMPLE_WAV_BYTES)
        assert "Rate Limit" in str(exc.value)

# 8. STT Response Parsing
@pytest.mark.asyncio
async def test_stt_response_parsing():
    provider = SarvamVoiceProvider(api_key="sk_test_key")
    mock_resp = httpx.Response(
        200,
        json={
            "transcript": "What is the market price of chilli today?",
            "language_code": "te-IN",
            "confidence": 0.96
        }
    )

    with patch("httpx.AsyncClient.post", return_value=mock_resp):
        res = await provider.transcribe(SAMPLE_WAV_BYTES, language_code="te")
        assert res.text == "What is the market price of chilli today?"
        assert res.language_code == "te"
        assert res.confidence == 0.96
        assert res.provider == "sarvam"

# 9. TTS Response Parsing
@pytest.mark.asyncio
async def test_tts_response_parsing():
    provider = SarvamVoiceProvider(api_key="sk_test_key")
    dummy_wav_base64 = base64.b64encode(SAMPLE_WAV_BYTES).decode("utf-8")
    mock_resp = httpx.Response(
        200,
        json={
            "audios": [dummy_wav_base64]
        }
    )

    with patch("httpx.AsyncClient.post", return_value=mock_resp):
        res = await provider.synthesize("Advisory response text", language_code="en")
        assert res.audio_bytes == SAMPLE_WAV_BYTES
        assert res.content_type == "audio/wav"
        assert res.provider == "sarvam"

# 10. Six-Language Configuration
def test_six_language_configuration():
    provider = SarvamVoiceProvider(api_key="sk_test_key")
    required_langs = ["en", "te", "hi", "ta", "kn", "ml"]
    
    for lang in required_langs:
        # Check BCP-47 tag
        tag = provider.get_sarvam_language_tag(lang)
        assert tag == f"{lang}-IN"
        # Check normalization
        assert provider.normalize_language_code(f"{lang}-IN") == lang
        # Check speaker resolution
        female_spk = provider.get_speaker(lang, "female")
        male_spk = provider.get_speaker(lang, "male")
        assert female_spk is not None and len(female_spk) > 0
        assert male_spk is not None and len(male_spk) > 0

# 11. Unified Voice Endpoint Validation
def test_unified_voice_endpoint_validation():
    # Valid audio types
    class MockFile:
        def __init__(self, filename, content_type):
            self.filename = filename
            self.content_type = content_type

    validate_audio_file(MockFile("speech.wav", "audio/wav"))
    validate_audio_file(MockFile("voice.mp3", "audio/mpeg"))
    validate_audio_file(MockFile("record.m4a", "audio/m4a"))

    # Invalid executable/text file
    with pytest.raises(HTTPException) as exc:
        validate_audio_file(MockFile("malicious.exe", "application/x-msdownload"))
    assert exc.value.status_code == 400

# 12. Voice -> Orchestrator Integration
@pytest.mark.asyncio
async def test_voice_orchestrator_integration():
    result = await BhoomiAgentOrchestrator.process_turn(
        farmer_id="farmer_voice_test",
        user_text="What should I do this week on my chilli farm?",
        input_mode="voice"
    )
    assert result.response_text is not None
    assert len(result.response_text) > 10
    assert result.voice_state == "RESPONDING"
    assert len(result.visual_cards) > 0

# 13. SafetyEngine Still Blocks Banned Chemicals in Voice
@pytest.mark.asyncio
async def test_safety_engine_blocks_banned_chemicals_in_voice():
    unsafe_text = "I recommend spraying Monocrotophos to protect your chilli crop."
    eval_result = SafetyEngine.evaluate(unsafe_text)
    assert eval_result.is_safe is False
    assert eval_result.status == "BLOCK"
    assert "restricted/banned" in eval_result.blocked_reasons[0]
    assert "Safety Alert" in eval_result.modified_text

# 14. No API Key Leakage in Logs or Errors
@pytest.mark.asyncio
async def test_no_api_key_leakage_in_logs_or_errors():
    secret_key = "sk_very_confidential_key_123456789"
    provider = SarvamVoiceProvider(api_key=secret_key)
    
    with patch("httpx.AsyncClient.post", side_effect=httpx.HTTPStatusError("Auth fail", request=None, response=None)):
        try:
            await provider.transcribe(SAMPLE_WAV_BYTES)
        except VoiceProcessingException as e:
            error_message = str(e)
            assert secret_key not in error_message
