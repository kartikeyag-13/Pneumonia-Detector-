import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class PredictionResponse(BaseModel):
    """
    Prediction result for a single image. The physical image is deleted
    from storage after inference, but this record (and the image metadata)
    is retained in PostgreSQL as history.
    """

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    image_id: uuid.UUID
    user_id: uuid.UUID
    prediction_code: int
    prediction_label: str
    confidence: float | None
    model_version: str | None
    created_at: datetime
