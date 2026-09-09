from typing import Any, Dict, Optional
from fastapi import HTTPException, status

class BhoomiException(HTTPException):
    def __init__(
        self,
        status_code: int,
        code: str,
        message: str,
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            status_code=status_code,
            detail={
                "success": False,
                "error": {
                    "code": code,
                    "message": message,
                    "details": details or {}
                }
            }
        )

class EntityNotFoundException(BhoomiException):
    def __init__(self, entity: str, entity_id: Any):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            code="ENTITY_NOT_FOUND",
            message=f"{entity} with id {entity_id} was not found."
        )

class VoiceProcessingException(BhoomiException):
    def __init__(
        self,
        message: str = "Unable to process the audio. Please try again.",
        status_code: int = getattr(status, "HTTP_422_UNPROCESSABLE_CONTENT", 422),
    ):
        super().__init__(
            status_code=status_code,
            code="VOICE_PROCESSING_FAILED",
            message=message
        )

class SafetyViolationException(BhoomiException):
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            code="SAFETY_VIOLATION",
            message=message,
            details=details
        )
