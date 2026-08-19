import uuid
from io import BytesIO

from fastapi import APIRouter, Depends, HTTPException, Query, status
from PIL import Image as PILImage
from PIL import UnidentifiedImageError
from sqlalchemy import update
from sqlalchemy.orm import Session

from app.dependencies import get_current_user, get_db
from app.models.image import STATUS_ACTIVE, STATUS_PROCESSED, Image
from app.models.prediction import Prediction
from app.models.user import User
from app.schemas.prediction import PredictionResponse
from app.services.inference import (
    InferenceNotImplemented,
    label_for_class,
    predict_image,
)
from app.services.model import MODEL_VERSION
from app.services.storage import StorageError, delete_image, download_image

router = APIRouter(prefix="/predict", tags=["predictions"])


@router.post(
    "/{image_id}",
    response_model=PredictionResponse,
    status_code=status.HTTP_201_CREATED,
)
def predict(
    image_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Prediction:
    """
    Run inference on the user's active image.

    The image is downloaded from private storage, verified, and passed to
    the inference service. On success a Prediction record is created, the
    image is marked as processed, and its physical object is deleted from
    storage. The image metadata row and the prediction history are kept in
    PostgreSQL.
    """
    image = (
        db.query(Image)
        .filter(Image.id == image_id, Image.user_id == current_user.id)
        .first()
    )
    if image is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Image not found",
        )
    if image.status != STATUS_ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Image is not active; it has already been processed",
        )

    try:
        data = download_image(image.storage_path)
    except StorageError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc

    try:
        pil_image = PILImage.open(BytesIO(data))
        pil_image.load()
    except (UnidentifiedImageError, OSError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Stored image could not be read as a valid image",
        )

    # Atomically claim the active image for this inference so two concurrent
    # predict requests cannot both process the same image.
    claim = db.execute(
        update(Image)
        .where(Image.id == image.id, Image.status == STATUS_ACTIVE)
        .values(status=STATUS_PROCESSED)
    )
    if claim.rowcount == 0:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Image is not active; it has already been processed",
        )

    try:
        prediction_code, confidence = predict_image(pil_image)
    except FileNotFoundError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"ML model not available: {exc}",
        ) from exc
    except InferenceNotImplemented as exc:
        # Revert the claim so the image stays active for a later retry.
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Inference failed",
        ) from exc

    record = Prediction(
        image_id=image.id,
        user_id=current_user.id,
        prediction_code=prediction_code,
        prediction_label=label_for_class(prediction_code),
        confidence=confidence,
        model_version=MODEL_VERSION,
    )
    db.add(record)
    db.commit()
    db.refresh(record)

    try:
        delete_image(image.storage_path)
    except StorageError:
        # Physical cleanup is best-effort; the metadata and prediction
        # history are already persisted in PostgreSQL.
        pass

    return record


history_router = APIRouter(prefix="/predictions", tags=["predictions"])


@history_router.get("", response_model=list[PredictionResponse])
def list_predictions(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[Prediction]:
    """
    List the current user's prediction history, newest first. Simple
    ``limit``/``offset`` pagination is supported.
    """
    return (
        db.query(Prediction)
        .filter(Prediction.user_id == current_user.id)
        .order_by(Prediction.created_at.desc())
        .limit(limit)
        .offset(offset)
        .all()
    )


@history_router.get("/{prediction_id}", response_model=PredictionResponse)
def get_prediction(
    prediction_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Prediction:
    """
    Return a single prediction from the current user's history.
    """
    prediction = (
        db.query(Prediction)
        .filter(
            Prediction.id == prediction_id,
            Prediction.user_id == current_user.id,
        )
        .first()
    )
    if prediction is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Prediction not found",
        )
    return prediction
