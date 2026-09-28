import base64
import logging
from fastapi import APIRouter, File, UploadFile, Form, HTTPException, status

from app.services.llm_service import llm_service

logger = logging.getLogger("voxvision.vision_api")

router = APIRouter(prefix="/api", tags=["Vision Analysis"])

ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png"}
ALLOWED_MIME_TYPES = {"image/jpeg", "image/jpg", "image/png"}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB limit

@router.post("/vision")
async def vision_analysis(
    file: UploadFile = File(...),
    prompt: str = Form("Analyze this image in detail and describe what you see.")
):
    """
    Computer Vision Analysis Endpoint (Step 6).
    Accepts JPG, JPEG, or PNG image file (max 10MB) and user query prompt.
    Returns AI visual analysis response.
    """
    if not file or not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No image file provided."
        )

    filename = file.filename
    ext = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    mime_type = file.content_type or "image/jpeg"

    # Validate File Extension & MIME Type
    if ext not in ALLOWED_EXTENSIONS and mime_type not in ALLOWED_MIME_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file format '{ext}'. Only JPG, JPEG, and PNG images are supported."
        )

    try:
        content = await file.read()
        file_size = len(content)

        # Validate File Size (Max 10MB)
        if file_size == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Empty image file uploaded."
            )

        if file_size > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File size ({file_size / (1024*1024):.1f}MB) exceeds the 10MB maximum limit."
            )

        # Convert to Base64 Payload
        image_b64 = base64.b64encode(content).decode("utf-8")
        actual_mime = "image/png" if ext == ".png" else "image/jpeg"

        # Clean and fallback prompt
        clean_prompt = prompt.strip() if prompt and prompt.strip() else "Analyze this image in detail and describe what you see."

        logger.info(f"Processing vision analysis for {filename} ({file_size} bytes, {actual_mime}) - Prompt: '{clean_prompt[:60]}...'")

        # Query Multimodal Vision Model
        result = await llm_service.generate_vision(
            prompt=clean_prompt,
            image_b64=image_b64,
            mime_type=actual_mime
        )

        result["filename"] = filename
        result["file_size"] = file_size
        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Vision API exception: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Vision processing failure: {str(e)}"
        )
