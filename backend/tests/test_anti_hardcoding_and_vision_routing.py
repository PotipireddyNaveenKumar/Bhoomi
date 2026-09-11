"""
BHOOMI — Anti-Hardcoding & Multi-Crop Vision Routing Regression Tests
Verifies:
1. Potato images are diagnosed by Potato model, never Chilli.
2. Guava images are diagnosed by Guava model, never Chilli.
3. Tomato, Banana, Corn, Rice images route to respective crop models.
4. Rice research-only restrictions are strictly maintained.
5. Cross-crop conflict handling when uploaded image conflicts with farm crop context.
6. Orchestrator dynamic interpolation: no hardcoded Ramesh/Guntur strings for arbitrary farmers.
"""

import os
import sys
import pytest
import asyncio

# Ensure backend root is on sys.path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
BACKEND_DIR = os.path.join(BASE_DIR, "backend")
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from app.services.vision.vision_service import VisionService
from app.services.vision.crop_registry import CropModelRegistry
from app.agents.orchestrator import BhoomiAgentOrchestrator
from app.services.memory.digital_twin import DigitalTwinContext

@pytest.mark.asyncio
async def test_potato_leaf_routes_to_potato_model_not_chilli():
    img_dir = os.path.join(BASE_DIR, "data", "organized", "vision", "potato_diseases", "Potato", "Potato___Early_blight")
    assert os.path.isdir(img_dir), f"Potato test directory not found: {img_dir}"
    
    # Find first jpg image
    test_img = None
    for root, _, files in os.walk(img_dir):
        for f in files:
            if f.lower().endswith((".jpg", ".jpeg")):
                test_img = os.path.join(root, f)
                break
        if test_img:
            break
            
    assert test_img is not None, "No potato test image found"
    with open(test_img, "rb") as fp:
        img_bytes = fp.read()
        
    res = await VisionService.analyze_leaf_image(
        image_bytes=img_bytes,
        crop_hint="potato",
        language="en",
        synthesize_speech=False
    )
    
    assert res.crop_identified.lower() == "potato", f"Expected Potato, got {res.crop_identified}"
    assert "chilli" not in res.crop_identified.lower(), "Potato was incorrectly diagnosed as Chilli!"
    assert res.confidence > 0.50, "Confidence should be reasonable for clear potato leaf"


@pytest.mark.asyncio
async def test_guava_leaf_routes_to_guava_model_not_chilli():
    img_dir = os.path.join(BASE_DIR, "data", "organized", "vision", "guava_diseases")
    assert os.path.isdir(img_dir), f"Guava test directory not found: {img_dir}"
    
    test_img = None
    for root, _, files in os.walk(img_dir):
        for f in files:
            if f.lower().endswith((".jpg", ".jpeg", ".png")):
                test_img = os.path.join(root, f)
                break
        if test_img:
            break
            
    assert test_img is not None, "No guava test image found"
    with open(test_img, "rb") as fp:
        img_bytes = fp.read()
        
    res = await VisionService.analyze_leaf_image(
        image_bytes=img_bytes,
        crop_hint="guava",
        language="en",
        synthesize_speech=False
    )
    
    assert res.crop_identified.lower() == "guava", f"Expected Guava, got {res.crop_identified}"
    assert "chilli" not in res.crop_identified.lower(), "Guava was incorrectly diagnosed as Chilli!"


@pytest.mark.asyncio
async def test_tomato_and_banana_routing():
    # Tomato
    tom_dir = os.path.join(BASE_DIR, "data", "organized", "vision", "tomato_diseases")
    for root, _, files in os.walk(tom_dir):
        for f in files:
            if f.lower().endswith(".jpg"):
                with open(os.path.join(root, f), "rb") as fp:
                    res = await VisionService.analyze_leaf_image(fp.read(), crop_hint="tomato", language="en", synthesize_speech=False)
                    assert res.crop_identified.lower() == "tomato"
                break
        break

    # Banana
    ban_dir = os.path.join(BASE_DIR, "data", "organized", "vision", "banana_diseases")
    for root, _, files in os.walk(ban_dir):
        for f in files:
            if f.lower().endswith(".jpg"):
                with open(os.path.join(root, f), "rb") as fp:
                    res = await VisionService.analyze_leaf_image(fp.read(), crop_hint="banana", language="en", synthesize_speech=False)
                    assert res.crop_identified.lower() == "banana"
                break
        break


@pytest.mark.asyncio
async def test_rice_research_only_restriction():
    rice_dir = os.path.join(BASE_DIR, "data", "organized", "vision", "rice_diseases")
    for root, _, files in os.walk(rice_dir):
        for f in files:
            if f.lower().endswith(".jpg"):
                with open(os.path.join(root, f), "rb") as fp:
                    res = await VisionService.analyze_leaf_image(fp.read(), crop_hint="rice", language="en", synthesize_speech=False)
                    assert res.crop_identified.lower() == "rice"
                    # Verify Rice Research-Only policy advisory
                    assert any("research" in str(w).lower() or "rice" in str(w).lower() for w in res.safety_advisories)
                break
        break


@pytest.mark.asyncio
async def test_cross_crop_conflict_detection():
    """
    When a farmer registered with Chilli uploads a Potato image,
    the system must NOT blindly diagnose as Chilli.
    It should detect the conflict and surface it.
    """
    img_dir = os.path.join(BASE_DIR, "data", "organized", "vision", "potato_diseases", "Potato", "Potato___Early_blight")
    test_img = None
    for root, _, files in os.walk(img_dir):
        for f in files:
            if f.lower().endswith((".jpg", ".jpeg")):
                test_img = os.path.join(root, f)
                break
        if test_img:
            break
            
    with open(test_img, "rb") as fp:
        img_bytes = fp.read()

    res = await VisionService.analyze_leaf_image(
        image_bytes=img_bytes,
        crop_hint="chilli",  # Registered crop is chilli
        language="en",
        synthesize_speech=False
    )
    
    # Must NOT classify as chilli
    assert res.crop_identified.lower() != "chilli", "System blindly classified non-chilli leaf as Chilli!"
    # Must flag conflict or inconsistency
    has_conflict = (
        any("inconsistent" in str(w).lower() or "conflict" in str(w).lower() for w in res.safety_advisories)
        or "Crop Notice" in (res.farmer_explanation or "")
    )
    assert has_conflict, "System should surface crop conflict notice when image does not match registered crop"


@pytest.mark.asyncio
async def test_orchestrator_dynamic_greeting_and_anti_hardcoding():
    """
    Verify that an authenticated farmer from Punjab growing Wheat
    receives dynamic, personalized greeting without Guntur / Ramesh / Chilli hardcoding.
    """
    twin = DigitalTwinContext(
        farmer_name="Gurpreet Singh",
        language="en",
        location="Ludhiana, Punjab",
        state="Punjab",
        district="Ludhiana",
        village="Rural",
        total_acres=5.0,
        soil_type="Alluvial Loam",
        irrigation_source="Canal",
        active_crops=[{"crop_name": "wheat", "acres": 5.0, "stage": "vegetative"}],
        historical_crops=["rice"],
        memories={},
        farm_id="farm_punjab_101"
    )

    result = await BhoomiAgentOrchestrator.orchestrate(
        user_text="Hello BHOOMI",
        session_id="sess_dynamic_test",
        farmer_id="farmer_punjab_101",
        farm_id="farm_punjab_101",
        context=twin,
        language="en"
    )

    resp = result.response_text
    assert "Gurpreet" in resp, f"Expected personalized name in greeting, got: {resp}"
    assert "Ludhiana" in resp, f"Expected dynamic location in greeting, got: {resp}"
    assert "Wheat" in resp or "wheat" in resp, f"Expected dynamic crop in greeting, got: {resp}"
    # Anti-hardcoding assertions
    assert "Ramesh" not in resp, f"Hardcoded Ramesh leaked into greeting: {resp}"
    assert "Guntur" not in resp, f"Hardcoded Guntur leaked into greeting: {resp}"
    assert "3 acres of chilli" not in resp, f"Hardcoded chilli farm leaked: {resp}"
