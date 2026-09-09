from app.services.safety.safety_engine import SafetyEngine

def test_safety_engine_blocks_monocrotophos():
    """
    Ensures SafetyEngine strictly blocks banned substances regardless of prompt.
    """
    unsafe_text = "To control severe leaf curl, spray 2ml Monocrotophos per litre of water immediately."
    res = SafetyEngine.evaluate(unsafe_text, crop="chilli", stage="vegetative")
    
    assert res.is_safe is False
    assert res.status == "BLOCK"
    assert any("monocrotophos" in r.lower() for r in res.blocked_reasons)
    assert "Safety Alert" in res.modified_text

def test_safety_engine_flowering_warning():
    """
    Ensures pollinator and PPE safety warnings are appended during flowering stage.
    """
    safe_text = "Apply recommended micronutrient chemical spray on chilli foliage."
    res = SafetyEngine.evaluate(safe_text, crop="chilli", stage="flowering")

    assert res.is_safe is True
    assert len(res.warnings) >= 1
    assert any("pollinator" in w.lower() for w in res.warnings)
