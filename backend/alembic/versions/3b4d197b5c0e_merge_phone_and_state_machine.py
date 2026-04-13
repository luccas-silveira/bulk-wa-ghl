"""merge_phone_and_state_machine

Revision ID: 3b4d197b5c0e
Revises: c3f1a9e8b2d4, e5f2a1c9b3d7
Create Date: 2026-04-13 10:20:46.581839

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '3b4d197b5c0e'
down_revision: Union[str, Sequence[str], None] = ('c3f1a9e8b2d4', 'e5f2a1c9b3d7')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
