"""add status column to images

Revision ID: cb25bae3a344
Revises: 8fe6052182d6
Create Date: 2026-08-16 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'cb25bae3a344'
down_revision: Union[str, Sequence[str], None] = '8fe6052182d6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        'images',
        sa.Column(
            'status',
            sa.String(length=20),
            server_default=sa.text("'active'"),
            nullable=False,
        ),
    )
    op.create_index(op.f('ix_images_status'), 'images', ['status'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_images_status'), table_name='images')
    op.drop_column('images', 'status')
