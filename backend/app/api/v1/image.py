from fastapi import APIRouter, UploadFile, File, Form, Depends, HTTPException, status
from typing import Optional
from app.api.deps import get_current_farmer_profile
from app.models.farmer import FarmerProfile
from app.services.vision.vision_service import VisionService, VisionAnalysisOutput

router = APIRouter(prefix="/image", tags=["Vision & Image Diagnostics"])

@router.post("/analyze", response_model=VisionAnalysisOutput)
async def analyze_crop_image(
    file: UploadFile = File(...),
    crop_name: str = Form(default="Chilli"),
    farmer: FarmerProfile = Depends(get_current_farmer_profile),
):
    """
    Canonical plant pathology leaf image analysis route.
    Delegates to VisionService image quality gate and deep learning model inference.
    """
    try:
        image_bytes = await file.read()
        return await VisionService.analyze_leaf_image(image_bytes, crop_hint=crop_name)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Computer vision diagnostic error: {str(e)}"
        )
