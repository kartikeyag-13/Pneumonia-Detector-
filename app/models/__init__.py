"""
Import all models here so that Base.metadata is aware of them.
This is important for Alembic autogeneration to detect all tables.
"""

from app.models.user import User
from app.models.image import Image
from app.models.prediction import Prediction

__all__ = ["User", "Image", "Prediction"]
