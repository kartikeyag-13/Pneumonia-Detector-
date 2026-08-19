from io import BytesIO

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from PIL import Image as PILImage
from PIL import UnidentifiedImageError
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.config import settings
from app.dependencies import get_current_user, get_db
from app.models.image import STATUS_ACTIVE, STATUS_PROCESSED, Image
from app.models.user import User
from app.schemas.image import ImageResponse
from app.services.storage import StorageError, delete_image, upload_image

router = APIRouter(prefix="/images", tags=["images"])

ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png"}
ALLOWED_IMAGE_FORMATS = {"JPEG", "PNG"}
MIME_BY_FORMAT = {"JPEG": "image/jpeg", "PNG": "image/png"}
MAX_IMAGE_PIXELS = 50_000_000

CHUNK_SIZE = 1024 * 1024


def _read_upload(file: UploadFile) -> bytes:
    """
    Read the uploaded file in chunks, aborting early if it exceeds the
    configured maximum size so oversized uploads cannot exhaust memory.
    """
    chunks: list[bytes] = []
    total = 0
    while True:
        chunk = file.file.read(CHUNK_SIZE)
        if not chunk:
            break
        total += len(chunk)
        if total > settings.MAX_UPLOAD_SIZE_BYTES:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=(
                    f"Image exceeds the maximum allowed size of "
                    f"{settings.MAX_UPLOAD_SIZE_BYTES} bytes"
                ),
            )
        chunks.append(chunk)
    return b"".join(chunks)


def _validate_image(data: bytes, declared_content_type: str | None) -> str:
    """
    Validate that the upload is a JPEG or PNG: check the declared MIME
    type, then independently verify the actual contents with Pillow.
    Returns the content type to store (derived from the verified contents).
    """
    if declared_content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Only JPEG and PNG images are allowed",
        )

    try:
        with PILImage.open(BytesIO(data)) as image:
            image.load()
            image_format = image.format
            pixel_count = image.width * image.height
    except (UnidentifiedImageError, OSError, ValueError, PILImage.DecompressionBombError):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is not a valid image",
        )

    if image_format not in ALLOWED_IMAGE_FORMATS:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=(
                f"Unsupported image format '{image_format}'; "
                "only JPEG and PNG are allowed"
            ),
        )
    if pixel_count > MAX_IMAGE_PIXELS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Image dimensions are too large",
        )

    verified_content_type = MIME_BY_FORMAT[image_format]
    if verified_content_type != declared_content_type:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Declared MIME type does not match the actual image contents",
        )
    return verified_content_type


@router.post(
    "/upload",
    response_model=ImageResponse,
    status_code=status.HTTP_201_CREATED,
)
def upload(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Image:
    """
    Upload a chest X-ray image (JPEG/PNG only) to the user's private
    storage bucket and record its metadata.

    A user may have only ONE active (unprocessed) image. If one already
    exists, its physical object is deleted from storage and its metadata
    row is marked as processed before the new image becomes active.
    """
    data = _read_upload(file)
    content_type = _validate_image(data, file.content_type)

    storage_path: str | None = None
    try:
        storage_path = upload_image(current_user.id, data, content_type)
    except StorageError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc

    try:
        active_image = (
            db.query(Image)
            .filter(
                Image.user_id == current_user.id,
                Image.status == STATUS_ACTIVE,
            )
            .first()
        )
        if active_image is not None:
            try:
                delete_image(active_image.storage_path)
            except StorageError:
                # Physical cleanup is best-effort; the metadata row is kept.
                pass
            active_image.status = STATUS_PROCESSED
            db.add(active_image)
            # Flush now so the old row is no longer active before the new
            # active row is inserted; the partial unique index
            # (uq_images_active_per_user) enforces the invariant.
            db.flush()

        record = Image(
            user_id=current_user.id,
            storage_path=storage_path,
            original_filename=file.filename or "image.jpg",
            content_type=content_type,
            file_size=len(data),
            status=STATUS_ACTIVE,
        )
        db.add(record)
        db.commit()
        db.refresh(record)
    except IntegrityError:
        # A concurrent upload created an active image first.
        db.rollback()
        if storage_path is not None:
            try:
                delete_image(storage_path)
            except StorageError:
                pass
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Only one active image is allowed per user",
        )
    except Exception:
        db.rollback()
        if storage_path is not None:
            try:
                delete_image(storage_path)
            except StorageError:
                pass
        raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail=f"Failed to save image metadata: {str(exc)}",
    ) from exc

    return record
