import pytest
from app.agents.missing_info_detector import MissingInformationDetector
from app.services.voice.mock import MockVoiceProvider

def test_missing_info_detector_fertilizer_without_crop():
    user_query = "What fertilizer should I use?"
    clarification = MissingInformationDetector.check_missing_info(
        user_text=user_query,
        context_memories={},
        active_crops=[]
    )
    assert clarification is not None
    assert "Which crop are you growing" in clarification

def test_missing_info_detector_with_existing_crop():
    user_query = "What fertilizer should I use for my chilli?"
    clarification = MissingInformationDetector.check_missing_info(
        user_text=user_query,
        context_memories={"soil_type": "black soil"},
        active_crops=[{"crop_name": "Chilli"}]
    )
    assert clarification is None  # Sufficient context, proceeds to advice

@pytest.mark.asyncio
async def test_mock_voice_provider_transcribe_and_synthesize():
    mock_voice = MockVoiceProvider()
    
    # STT Test
    trans = await mock_voice.transcribe(b"dummy_bytes", language_code="te")
    assert trans.language_code == "te"
    assert "మిర్చి" in trans.text

    # TTS Test
    synth = await mock_voice.synthesize("నమస్కారం", language_code="te")
    assert synth.audio_bytes.startswith(b"RIFF")
    assert synth.content_type == "audio/wav"
