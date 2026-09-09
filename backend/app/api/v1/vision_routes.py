from fastapi import APIRouter, UploadFile, File, Form, HTTPException, status
from typing import Optional, List, Dict, Any
import base64
import os
import io
from PIL import Image, ImageFilter
from app.services.vision.vision_service import VisionService, VisionAnalysisOutput

router = APIRouter(prefix="/vision", tags=["Computer Vision Pathology"])

@router.post("/analyze", response_model=VisionAnalysisOutput)
async def analyze_crop_image(
    file: UploadFile = File(...),
    crop_hint: Optional[str] = Form(None),
    language: Optional[str] = Form(None)
):
    """
    Modular Multimodal Plant Pathology Diagnostic Pipeline.
    Validates Image Quality Gate -> Identifies Crop -> Classifies Disease ->
    Evaluates OOD Uncertainty -> SafetyEngine Verification -> IPM Advice ->
    Persona Spoken Explanation -> Canonical Sarvam TTS Audio.
    """
    try:
        image_bytes = await file.read()
        return await VisionService.analyze_leaf_image(
            image_bytes=image_bytes,
            crop_hint=crop_hint,
            language=language or "en"
        )
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

@router.get("/samples")
async def get_sample_leaves():
    """
    Returns genuine pre-loaded sample leaves for web demonstration:
    1. Chilli Leaf Curl Virus
    2. Healthy Chilli Leaf
    3. Rice Leaf (Bacterial Blight - tests RESEARCH_ONLY safeguard)
    4. Blurry Leaf (tests Quality Gate rejection)
    """
    from app.core.config import settings
    if settings.APP_ENV in ["production", "staging"] and not settings.DEBUG:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sample leaves disabled in production.")

    samples = []
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "data", "organized", "vision"))

    # 1. Chilli Leaf Curl
    curl_dir = os.path.join(base_dir, "chilli_diseases", "Chilli Plant Diseases Dataset(Augmented)", "Chilli Plant Diseases Dataset", "test", "Chilli__Leaf_Curl_Virus")
    if os.path.isdir(curl_dir):
        files = [f for f in os.listdir(curl_dir) if f.endswith((".jpg", ".png"))]
        if files:
            im = Image.open(os.path.join(curl_dir, files[0])).convert("RGB")
            if im.width < 300 or im.height < 300:
                im = im.resize((max(im.width, 300), max(im.height, 300)), Image.Resampling.LANCZOS)
            buf = io.BytesIO()
            im.save(buf, format="JPEG", quality=95)
            samples.append({
                "id": "chilli_leaf_curl",
                "title": "Chilli Leaf Curl Virus",
                "crop": "Chilli",
                "description": "Viral infection causing severe upward curling and stunting",
                "image_base64": base64.b64encode(buf.getvalue()).decode("utf-8")
            })

    # 2. Healthy Chilli
    healthy_dir = os.path.join(base_dir, "chilli_diseases", "Chilli Plant Diseases Dataset(Augmented)", "Chilli Plant Diseases Dataset", "test", "Chilli___healthy")
    if os.path.isdir(healthy_dir):
        files = [f for f in os.listdir(healthy_dir) if f.endswith((".jpg", ".png"))]
        if files:
            im = Image.open(os.path.join(healthy_dir, files[0])).convert("RGB")
            if im.width < 300 or im.height < 300:
                im = im.resize((max(im.width, 300), max(im.height, 300)), Image.Resampling.LANCZOS)
            buf = io.BytesIO()
            im.save(buf, format="JPEG", quality=95)
            samples.append({
                "id": "chilli_healthy",
                "title": "Healthy Chilli Leaf",
                "crop": "Chilli",
                "description": "Vibrant green foliage with no pathogenic lesions",
                "image_base64": base64.b64encode(buf.getvalue()).decode("utf-8")
            })

    # 3. Rice Leaf (RESEARCH_ONLY)
    rice_dir = os.path.join(base_dir, "rice_diseases", "Bacterial Blight Disease")
    if os.path.isdir(rice_dir):
        files = [f for f in os.listdir(rice_dir) if f.endswith((".jpg", ".png"))]
        if files:
            im = Image.open(os.path.join(rice_dir, files[0])).convert("RGB")
            if im.width < 300 or im.height < 300:
                im = im.resize((max(im.width, 300), max(im.height, 300)), Image.Resampling.LANCZOS)
            buf = io.BytesIO()
            im.save(buf, format="JPEG", quality=95)
            samples.append({
                "id": "rice_blight",
                "title": "Rice Bacterial Blight (RESEARCH_ONLY)",
                "crop": "Rice",
                "description": "Demonstrates Phase 4/5 RESEARCH_ONLY safeguard blocking chemical prescriptions",
                "image_base64": base64.b64encode(buf.getvalue()).decode("utf-8")
            })

    # 4. Blurry / Quality Gate Test
    if samples:
        first_bytes = base64.b64decode(samples[0]["image_base64"])
        im = Image.open(io.BytesIO(first_bytes))
        im_blurred = im.filter(ImageFilter.GaussianBlur(radius=15))
        buf = io.BytesIO()
        im_blurred.save(buf, format="JPEG")
        samples.append({
            "id": "blurry_quality_gate",
            "title": "Blurry Leaf (Quality Gate Reject)",
            "crop": "Chilli",
            "description": "Severely blurred capture triggering ImageQualityGate rejection and retake advice",
            "image_base64": base64.b64encode(buf.getvalue()).decode("utf-8")
        })

    return {"samples": samples}
