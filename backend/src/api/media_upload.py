"""
Media Upload API
Handles file uploads for campaign messages
"""
import os
import uuid
import logging
from pathlib import Path
from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse
import aiofiles

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/media", tags=["Media Upload"])

UPLOAD_DIR = Path("/app/uploads/media")
MAX_FILE_SIZE = 25 * 1024 * 1024  # 25MB (WhatsApp limit)
MEDIA_BASE_URL = os.getenv("MEDIA_BASE_URL", "").rstrip("/")
ALLOWED_EXTENSIONS = {
    '.jpg', '.jpeg', '.png', '.gif', '.webp',
    '.mp4', '.avi', '.mov', '.mkv',
    '.mp3', '.ogg', '.wav', '.m4a',
    '.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx',
}


def _get_ext(filename: str) -> str:
    return Path(filename).suffix.lower()


def _allowed(filename: str) -> bool:
    return _get_ext(filename) in ALLOWED_EXTENSIONS


def _unique_name(original: str) -> str:
    return f"{uuid.uuid4().hex}{_get_ext(original)}"


@router.post("/upload", status_code=201)
async def upload_media(file: UploadFile = File(...)):
    """Upload media file (image/video/audio/document) for campaign messages. Max 25 MB."""
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

    if not file.filename:
        raise HTTPException(status_code=400, detail="Filename is required")
    if not _allowed(file.filename):
        raise HTTPException(
            status_code=400,
            detail=f"File type not allowed. Allowed: {', '.join(sorted(ALLOWED_EXTENSIONS))}",
        )

    contents = await file.read()
    size = len(contents)

    if size == 0:
        raise HTTPException(status_code=400, detail="File is empty")
    if size > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"File too large ({size / 1024 / 1024:.1f} MB). Max is 25 MB.",
        )

    unique = _unique_name(file.filename)
    async with aiofiles.open(UPLOAD_DIR / unique, "wb") as f:
        await f.write(contents)

    relative_url = f"/uploads/media/{unique}"
    absolute_url = f"{MEDIA_BASE_URL}{relative_url}" if MEDIA_BASE_URL else relative_url

    logger.info("Media uploaded: %s (%d KB)", unique, size // 1024)

    return JSONResponse(
        status_code=201,
        content={
            "success": True,
            "url": absolute_url,
            "relative_url": relative_url,
            "filename": unique,
            "original_filename": file.filename,
            "size": size,
            "content_type": file.content_type,
        },
    )


@router.delete("/upload/{filename}")
async def delete_media(filename: str):
    """Delete a previously uploaded media file."""
    file_path = UPLOAD_DIR / filename

    # Prevent path traversal
    try:
        file_path.resolve().relative_to(UPLOAD_DIR.resolve())
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid filename")

    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")

    file_path.unlink()
    logger.info("Media deleted: %s", filename)
    return {"success": True, "message": "File deleted"}
