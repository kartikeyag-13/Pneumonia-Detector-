"""
Supabase Storage integration.

This module is the only place in the application that talks to the
low-level Supabase Storage API. The rest of the application depends on
the high-level ``upload_image`` / ``download_image`` / ``delete_image``
functions exposed here.

The bucket (``SUPABASE_BUCKET``) is a private bucket and is only ever
accessed with the service-role key, which stays server-side and is never
exposed to clients.

Storage paths follow the convention ``<user_id>/<unique_image_id>.jpg``.
"""

import logging
import uuid

from supabase import create_client

from app.config import settings

logger = logging.getLogger(__name__)


class StorageError(Exception):
    """
    Raised when a Supabase Storage operation fails.
    Callers translate this into an appropriate HTTP response.
    """


_client: object | None = None


def _get_client():
    global _client
    if _client is None:
        if not settings.SUPABASE_URL or not settings.SUPABASE_SERVICE_ROLE_KEY:
            raise StorageError(
                "Supabase Storage is not configured "
                "(SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY missing)"
            )
        _client = create_client(
            settings.SUPABASE_URL, settings.SUPABASE_SERVICE_ROLE_KEY
        )
    return _client


def _bucket():
    return _get_client().storage.from_(settings.SUPABASE_BUCKET)


def upload_image(user_id: uuid.UUID, data: bytes, content_type: str) -> str:
    """
    Upload raw image bytes to the private bucket under
    ``<user_id>/<unique_image_id>.jpg`` and return the storage path.
    """
    image_id = uuid.uuid4()
    storage_path = f"{user_id}/{image_id}.jpg"
    try:
        _bucket().upload(
            storage_path,
            data,
            file_options={"content-type": content_type},
        )
    except Exception as exc:  # noqa: BLE001 - normalize SDK errors
        logger.exception("Supabase Storage upload failed for %s", storage_path)
        # Do not expose the underlying SDK error detail to clients.
        raise StorageError("Failed to upload image to storage") from exc
    return storage_path


def download_image(storage_path: str) -> bytes:
    """
    Download the raw bytes of an image stored at ``storage_path``.
    """
    try:
        return _bucket().download(storage_path)
    except Exception as exc:  # noqa: BLE001 - normalize SDK errors
        logger.exception("Supabase Storage download failed for %s", storage_path)
        raise StorageError("Failed to download image from storage") from exc


def delete_image(storage_path: str) -> None:
    """
    Delete the physical image object at ``storage_path`` from the private
    bucket. Database metadata is intentionally left untouched so that
    historical records survive the deletion.
    """
    try:
        _bucket().remove([storage_path])
    except Exception as exc:  # noqa: BLE001 - normalize SDK errors
        logger.exception("Supabase Storage delete failed for %s", storage_path)
        raise StorageError("Failed to delete image from storage") from exc
