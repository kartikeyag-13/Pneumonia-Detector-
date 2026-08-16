import uuid
from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, Index, String, func, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

STATUS_ACTIVE = "active"
STATUS_PROCESSED = "processed"


class Image(Base):
    """
    Represents an uploaded chest X-ray image record.
    The storage_path holds the private Supabase Storage object path, not a
    public URL. The row is kept as metadata even after the physical image is
    deleted from Storage.

    A user may have at most one image with ``status == STATUS_ACTIVE``
    (uploaded but not yet processed). Once the image is processed or
    superseded by a newer upload it becomes ``STATUS_PROCESSED``, and the
    physical object may be deleted while the metadata row is retained.
    """

    __tablename__ = "images"

    # Enforces at the database level that a user can have at most one
    # active (unprocessed) image, regardless of request concurrency.
    __table_args__ = (
        Index(
            "uq_images_active_per_user",
            "user_id",
            unique=True,
            postgresql_where=text("status = 'active'"),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True
    )
    storage_path: Mapped[str] = mapped_column(String(500), nullable=False)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    content_type: Mapped[str] = mapped_column(String(100), nullable=False)
    file_size: Mapped[int] = mapped_column(BigInteger, nullable=False)
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=STATUS_ACTIVE,
        server_default=STATUS_ACTIVE,
        index=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    user: Mapped["User"] = relationship(back_populates="images")
    prediction: Mapped["Prediction | None"] = relationship(
        back_populates="image", uselist=False
    )
