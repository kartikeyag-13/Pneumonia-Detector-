"""enforce one active image per user with partial unique index

Revision ID: 38fc261e19d8
Revises: cb25bae3a344
Create Date: 2026-08-16 13:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '38fc261e19d8'
down_revision: Union[str, Sequence[str], None] = 'cb25bae3a344'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Guarantee at the database level that a user can have at most one
    # active (unprocessed) image, regardless of request concurrency.
    op.create_index(
        'uq_images_active_per_user',
        'images',
        ['user_id'],
        unique=True,
        postgresql_where=sa.text("status = 'active'"),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('uq_images_active_per_user', table_name='images')
