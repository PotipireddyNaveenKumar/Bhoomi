import io
import math
from typing import Tuple, Dict, Any
from PIL import Image

class ImageQualityGateResult:
    def __init__(self, is_valid: bool, reason: str, metrics: Dict[str, Any], farmer_advice: str):
        self.is_valid = is_valid
        self.reason = reason
        self.metrics = metrics
        self.farmer_advice = farmer_advice

    def to_dict(self):
        return {
            "is_valid": self.is_valid,
            "reason": self.reason,
            "metrics": self.metrics,
            "farmer_advice": self.farmer_advice
        }

class ImageQualityGate:
    """
    Enhanced Image Quality Gate.
    Validates resolution, blur, illumination, aspect ratio, and file integrity
    before passing image inputs to heavy Computer Vision models.
    
    Rule: Never pretend to diagnose a poor, blurred, or corrupted image.
    """
    MIN_WIDTH = 112
    MIN_HEIGHT = 112
    MIN_SHARPNESS = 4.5
    MAX_FILE_SIZE_MB = 15.0

    @classmethod
    def validate(cls, image_bytes: bytes) -> ImageQualityGateResult:
        if not image_bytes or len(image_bytes) == 0:
            return ImageQualityGateResult(
                False,
                "Empty image payload received.",
                {},
                "No image detected. Please take a photo of the affected plant leaf."
            )

        size_mb = len(image_bytes) / (1024 * 1024)
        if size_mb > cls.MAX_FILE_SIZE_MB:
            return ImageQualityGateResult(
                False,
                f"Image file size ({size_mb:.1f} MB) exceeds maximum allowed {cls.MAX_FILE_SIZE_MB} MB limit.",
                {"size_mb": round(size_mb, 2)},
                "Image file is too large. Please take a standard photo on your phone camera."
            )

        try:
            img = Image.open(io.BytesIO(image_bytes))
            width, height = img.size
            format_name = img.format

            # 1. Resolution Check
            if width < cls.MIN_WIDTH or height < cls.MIN_HEIGHT:
                return ImageQualityGateResult(
                    False,
                    f"Image resolution too low ({width}x{height}). Minimum required is {cls.MIN_WIDTH}x{cls.MIN_HEIGHT}.",
                    {"width": width, "height": height},
                    "I cannot see the leaf details clearly. Please hold the camera closer to the affected leaf."
                )

            # 2. Aspect Ratio Check (allow elongated crops, sugarcane/rice leaves, and uprooted seedlings)
            aspect_ratio = max(width, height) / max(min(width, height), 1)
            if aspect_ratio > 8.5:
                return ImageQualityGateResult(
                    False,
                    f"Extreme aspect ratio ({aspect_ratio:.1f}:1). Image appears cropped or stretched.",
                    {"aspect_ratio": round(aspect_ratio, 2)},
                    "Please take a regular photo of the plant leaf without extreme cropping."
                )

            # 3. Brightness / Illumination Analysis
            grayscale = img.convert("L")
            stat = list(grayscale.getdata())
            avg_brightness = sum(stat) / len(stat) if stat else 128.0
            max_brightness = max(stat) if stat else 255.0

            # Only reject if both average brightness is extremely dark and maximum brightness shows no visible plant detail
            if avg_brightness < 8.0 and max_brightness < 35.0:
                return ImageQualityGateResult(
                    False,
                    f"Image is severely underexposed and too dark (brightness: {avg_brightness:.1f}/255).",
                    {"avg_brightness": round(avg_brightness, 1), "max_brightness": round(max_brightness, 1)},
                    "The photo is too dark. Please take a photo in clear daylight or turn on your camera flash."
                )

            if avg_brightness > 248.0:
                return ImageQualityGateResult(
                    False,
                    f"Image is overexposed / washed out (brightness: {avg_brightness:.1f}/255).",
                    {"avg_brightness": round(avg_brightness, 1)},
                    "The photo has harsh glare or reflection. Please shade the leaf slightly and retake."
                )

            # 4. Blur / Sharpness Estimation
            small = grayscale.resize((100, 100))
            pixels = list(small.getdata())
            diffs = []
            for y in range(99):
                for x in range(99):
                    diff = abs(pixels[y * 100 + x] - pixels[y * 100 + x + 1]) + \
                           abs(pixels[y * 100 + x] - pixels[(y + 1) * 100 + x])
                    diffs.append(diff)

            mean_diff = sum(diffs) / len(diffs) if diffs else 10.0

            if mean_diff < cls.MIN_SHARPNESS:
                return ImageQualityGateResult(
                    False,
                    f"Image is blurry and out of focus (sharpness: {mean_diff:.2f}, minimum: {cls.MIN_SHARPNESS}).",
                    {
                        "width": width,
                        "height": height,
                        "format": format_name,
                        "brightness": round(avg_brightness, 1),
                        "sharpness": round(mean_diff, 2)
                    },
                    "The photo is too blurry to see the leaf symptoms clearly. Please hold the camera steady and take another photo in good light."
                )

            return ImageQualityGateResult(
                True,
                "Image passed all quality gate checks.",
                {
                    "width": width,
                    "height": height,
                    "format": format_name,
                    "brightness": round(avg_brightness, 1),
                    "sharpness": round(mean_diff, 2)
                },
                "Image quality is clear."
            )

        except Exception as e:
            return ImageQualityGateResult(
                False,
                f"Failed to decode image file: {str(e)}",
                {},
                "Unable to read this file. Please capture or upload a valid JPEG or PNG photo."
            )
