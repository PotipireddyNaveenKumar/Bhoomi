import io
from PIL import Image
from app.services.vision.quality_gate import ImageQualityGate

def test_image_quality_gate_valid():
    from PIL import ImageDraw
    img = Image.new("RGB", (400, 400), color=(100, 180, 100))
    draw = ImageDraw.Draw(img)
    for i in range(0, 400, 10):
        draw.line([(i, 0), (i, 399)], fill=(120, 200, 120), width=2)
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    
    res = ImageQualityGate.validate(buf.getvalue())
    assert res.is_valid is True
    assert res.metrics["width"] == 400

def test_image_quality_gate_low_resolution():
    # Low resolution 100x100
    img = Image.new("RGB", (100, 100), color=(100, 180, 100))
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    
    res = ImageQualityGate.validate(buf.getvalue())
    assert res.is_valid is False
    assert "too low" in res.reason.lower()

def test_image_quality_gate_dark():
    # Too dark (0 brightness)
    img = Image.new("RGB", (300, 300), color=(5, 5, 5))
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    
    res = ImageQualityGate.validate(buf.getvalue())
    assert res.is_valid is False
    assert "too dark" in res.reason.lower()
