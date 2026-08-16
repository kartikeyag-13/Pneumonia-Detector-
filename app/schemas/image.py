import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ImageResponse(BaseModel):
    """
    Metadata for a stored chest X-ray image. This is returned after a
    successful upload and describes where the image lives and its state.
    """

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    storage_path: str
    original_filename: str
    content_type: str
    file_size: int
    status: str
    created_at: datetime
