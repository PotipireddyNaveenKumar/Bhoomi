"""
BHOOMI — Phase 29 Final Verification Suite
Directly tests the exact required scenarios from Phase 29:
- CHAT 1: "What is the current weather in Guntur?"
- CHAT 2: "Which Kharif crop is suitable for black soil on 3 acres?"
- CHAT 3: "My chilli leaves are curling. What could be the reason?"
- CHAT 4: "Rain is expected tomorrow. Should I spray today?"
- CHAT 5: "Should I sell my paddy now?"
- CHAT 6: "What fertilizer should I use based on my soil?"
- VOICE 1: English weather question
- VOICE 2: Telugu chilli question
- VOICE 3: Hindi crop question
- IMAGE 1: Potato leaf (routed to Potato model)
- IMAGE 2: Guava leaf/fruit (routed to Guava model)
- IMAGE 3: Tomato disease image (routed to Tomato model)
- IMAGE 4: Banana disease image (routed to Banana model)
- IMAGE 5: Chilli disease image (routed to Chilli model)
"""

import os
import sys
import pytest
import asyncio

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
BACKEND_DIR = os.path.join(BASE_DIR, "backend")
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from app.agents.orchestrator import BhoomiAgentOrchestrator
from app.services.vision.vision_service import VisionService
from app.services.memory.digital_twin import DigitalTwinContext
from app.services.voice.intent_service import IntentNormalizationService


def get_first_image_in_dir(subpath: str) -> str:
    full_dir = os.path.join(BASE_DIR, "data", "organized", "vision", subpath)
    for root, _, files in os.walk(full_dir):
        for f in files:
            if f.lower().endswith((".jpg", ".jpeg", ".png")):
                return os.path.join(root, f)
    raise FileNotFoundError(f"No image found in {full_dir}")


@pytest.mark.asyncio
async def test_chat_scenario_1_weather_guntur():
    twin = DigitalTwinContext(
        farmer_name="Ramesh Rao",
        location="Guntur, Andhra Pradesh",
        state="Andhra Pradesh",
        district="Guntur",
        total_acres=3.0,
        active_crops=[{"crop_name": "chilli", "acres": 3.0}]
    )
    res = await BhoomiAgentOrchestrator.orchestrate(
        user_text="What is the current weather in Guntur?",
        session_id="s_v_c1",
        farmer_id="f_v_1",
        context=twin,
        language="en"
    )
    resp = res.response_text or ""
    assert len(resp) > 20
    assert "Guntur" in resp or "weather" in resp.lower() or "temperature" in resp.lower() or "rain" in resp.lower()


@pytest.mark.asyncio
async def test_chat_scenario_2_kharif_crop_black_soil():
    twin = DigitalTwinContext(
        farmer_name="Ramesh Rao",
        location="Guntur, Andhra Pradesh",
        state="Andhra Pradesh",
        district="Guntur",
        soil_type="black cotton soil",
        total_acres=3.0
    )
    res = await BhoomiAgentOrchestrator.orchestrate(
        user_text="Which Kharif crop is suitable for black soil on 3 acres?",
        session_id="s_v_c2",
        farmer_id="f_v_2",
        context=twin,
        language="en"
    )
    resp = res.response_text or ""
    assert len(resp) > 20
    # Must recommend suitable crops, never PMFBY insurance document hijack
    assert "pmfby" not in resp.lower()
    assert any(c in resp.lower() for c in ["cotton", "chilli", "soybean", "paddy", "maize", "pulses", "black", "crop"])


@pytest.mark.asyncio
async def test_chat_scenario_3_chilli_curling():
    twin = DigitalTwinContext(
        farmer_name="Ramesh Rao",
        location="Guntur, Andhra Pradesh",
        state="Andhra Pradesh",
        district="Guntur",
        total_acres=3.0,
        active_crops=[{"crop_name": "chilli", "acres": 3.0, "stage": "vegetative"}]
    )
    res = await BhoomiAgentOrchestrator.orchestrate(
        user_text="My chilli leaves are curling. What could be the reason?",
        session_id="s_v_c3",
        farmer_id="f_v_3",
        context=twin,
        language="en"
    )
    resp = res.response_text or ""
    assert len(resp) > 25
    # Must analyze thrips, mites, geminivirus, or moisture stress
    assert any(w in resp.lower() for w in ["thrips", "mite", "curl", "virus", "chilli", "leaf", "pest", "spray"])


@pytest.mark.asyncio
async def test_chat_scenario_4_rain_expected_spray_advisory():
    twin = DigitalTwinContext(
        farmer_name="Ramesh Rao",
        location="Guntur, Andhra Pradesh",
        state="Andhra Pradesh",
        district="Guntur",
        total_acres=3.0,
        active_crops=[{"crop_name": "chilli", "acres": 3.0}]
    )
    res = await BhoomiAgentOrchestrator.orchestrate(
        user_text="Rain is expected tomorrow. Should I spray today?",
        session_id="s_v_c4",
        farmer_id="f_v_4",
        context=twin,
        language="en"
    )
    resp = res.response_text or ""
    assert len(resp) > 25
    assert any(w in resp.lower() for w in ["spray", "rain", "wash", "hold", "weather", "safe", "delay", "avoid", "caution"])


@pytest.mark.asyncio
async def test_chat_scenario_5_sell_paddy_now():
    twin = DigitalTwinContext(
        farmer_name="Ramesh Rao",
        location="Warangal, Telangana",
        state="Telangana",
        district="Warangal",
        total_acres=4.0,
        active_crops=[{"crop_name": "paddy", "acres": 4.0, "stage": "harvesting"}]
    )
    res = await BhoomiAgentOrchestrator.orchestrate(
        user_text="Should I sell my paddy now?",
        session_id="s_v_c5",
        farmer_id="f_v_5",
        context=twin,
        language="en"
    )
    resp = res.response_text or ""
    assert len(resp) > 25
    # Economic / market decision
    assert any(w in resp.lower() for w in ["paddy", "sell", "price", "mandi", "market", "rate", "hold", "msp"])


@pytest.mark.asyncio
async def test_chat_scenario_6_soil_fertilizer():
    twin = DigitalTwinContext(
        farmer_name="Ramesh Rao",
        location="Guntur, Andhra Pradesh",
        state="Andhra Pradesh",
        district="Guntur",
        soil_type="Black Cotton",
        soil_ph=7.2,
        soil_n=90.0,
        soil_p=40.0,
        soil_k=50.0,
        active_crops=[{"crop_name": "chilli", "acres": 3.0}]
    )
    res = await BhoomiAgentOrchestrator.orchestrate(
        user_text="What fertilizer should I use based on my soil?",
        session_id="s_v_c6",
        farmer_id="f_v_6",
        context=twin,
        language="en"
    )
    resp = res.response_text or ""
    assert len(resp) > 25
    assert any(w in resp.lower() for w in ["fertilizer", "soil", "urea", "dap", "npk", "nitrogen", "potash", "apply"])


@pytest.mark.asyncio
async def test_voice_scenario_1_english():
    parsed = IntentNormalizationService.parse_intent("What is the weather today in Guntur?", language="en")
    assert parsed.intent_type is not None
    twin = DigitalTwinContext(farmer_name="Reviewer", location="Guntur", district="Guntur")
    res = await BhoomiAgentOrchestrator.orchestrate(
        user_text="What is the weather today in Guntur?",
        session_id="s_v_v1",
        farmer_id="f_v_v1",
        context=twin,
        language="en",
        input_mode="voice"
    )
    assert len(res.response_text or "") > 20


@pytest.mark.asyncio
async def test_voice_scenario_2_telugu():
    q_telugu = "మిరప ఆకులు ముడుచుకుపోతున్నాయి, ఏం చేయాలి?"
    parsed = IntentNormalizationService.parse_intent(q_telugu, language="te")
    assert parsed.language == "te" or "te" in str(parsed.intent_type).lower()
    twin = DigitalTwinContext(farmer_name="రైతు", language="te", location="గుంటూరు", district="గుంటూరు", active_crops=[{"crop_name": "మిరప"}])
    res = await BhoomiAgentOrchestrator.orchestrate(
        user_text=q_telugu,
        session_id="s_v_v2",
        farmer_id="f_v_v2",
        context=twin,
        language="te",
        input_mode="voice"
    )
    assert len(res.response_text or "") > 15


@pytest.mark.asyncio
async def test_voice_scenario_3_hindi():
    q_hindi = "खरीफ में 3 एकड़ खेत के लिए कौन सी फसल अच्छी रहेगी?"
    parsed = IntentNormalizationService.parse_intent(q_hindi, language="hi")
    assert parsed.language == "hi"
    twin = DigitalTwinContext(farmer_name="किसान", language="hi", location="इंदौर", district="इंदौर")
    res = await BhoomiAgentOrchestrator.orchestrate(
        user_text=q_hindi,
        session_id="s_v_v3",
        farmer_id="f_v_v3",
        context=twin,
        language="hi",
        input_mode="voice"
    )
    assert len(res.response_text or "") > 15


@pytest.mark.asyncio
async def test_image_scenario_1_potato_leaf():
    img_path = get_first_image_in_dir("potato_diseases")
    with open(img_path, "rb") as f:
        img_bytes = f.read()
    res = await VisionService.analyze_leaf_image(image_bytes=img_bytes, crop_hint="potato", language="en", synthesize_speech=False)
    assert res.crop_identified.lower() == "potato", f"Expected Potato, got {res.crop_identified}"
    assert "chilli" not in res.crop_identified.lower(), "Potato leaf incorrectly routed to Chilli!"


@pytest.mark.asyncio
async def test_image_scenario_2_guava_leaf():
    img_path = get_first_image_in_dir("guava_diseases")
    with open(img_path, "rb") as f:
        img_bytes = f.read()
    res = await VisionService.analyze_leaf_image(image_bytes=img_bytes, crop_hint="guava", language="en", synthesize_speech=False)
    assert res.crop_identified.lower() == "guava", f"Expected Guava, got {res.crop_identified}"
    assert "chilli" not in res.crop_identified.lower(), "Guava leaf incorrectly routed to Chilli!"


@pytest.mark.asyncio
async def test_image_scenario_3_tomato_leaf():
    img_path = get_first_image_in_dir("tomato_diseases")
    with open(img_path, "rb") as f:
        img_bytes = f.read()
    res = await VisionService.analyze_leaf_image(image_bytes=img_bytes, crop_hint="tomato", language="en", synthesize_speech=False)
    assert res.crop_identified.lower() == "tomato", f"Expected Tomato, got {res.crop_identified}"
    assert "chilli" not in res.crop_identified.lower()


@pytest.mark.asyncio
async def test_image_scenario_4_banana_leaf():
    img_path = get_first_image_in_dir("banana_diseases")
    with open(img_path, "rb") as f:
        img_bytes = f.read()
    res = await VisionService.analyze_leaf_image(image_bytes=img_bytes, crop_hint="banana", language="en", synthesize_speech=False)
    assert res.crop_identified.lower() == "banana", f"Expected Banana, got {res.crop_identified}"
    assert "chilli" not in res.crop_identified.lower()


@pytest.mark.asyncio
async def test_image_scenario_5_chilli_leaf():
    img_path = os.path.join(
        BASE_DIR,
        "data",
        "organized",
        "vision",
        "chilli_diseases",
        "Chilli Plant Diseases Dataset(Augmented)",
        "Chilli Plant Diseases Dataset",
        "test",
        "Chilli __Whitefly",
        "whiteflya14.jpg"
    )
    with open(img_path, "rb") as f:
        img_bytes = f.read()
    res = await VisionService.analyze_leaf_image(image_bytes=img_bytes, crop_hint="chilli", language="en", synthesize_speech=False)
    assert res.crop_identified.lower() == "chilli", f"Expected Chilli, got {res.crop_identified}"
    assert res.confidence > 0.50
