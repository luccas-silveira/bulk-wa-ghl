"""epic10_indexes

Revision ID: e5f2a1c9b3d7
Revises: d20974da6dc5
Create Date: 2026-04-12 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e5f2a1c9b3d7'
down_revision: Union[str, Sequence[str], None] = 'd20974da6dc5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add composite indexes on campaigns and partial index on messages (PERS-17, PERS-18)."""
    op.create_index(
        'idx_campaigns_status_location',
        'campaigns', ['status', 'ghl_location_id']
    )
    op.create_index(
        'idx_campaigns_status_created_at',
        'campaigns', ['status', 'created_at']
    )
    op.create_index(
        'idx_messages_pending_sent',
        'messages', ['campaign_id', 'status'],
        postgresql_where=sa.text("status IN ('pending', 'sent')")
    )


def downgrade() -> None:
    """Remove composite and partial indexes."""
    op.drop_index('idx_messages_pending_sent', table_name='messages')
    op.drop_index('idx_campaigns_status_created_at', table_name='campaigns')
    op.drop_index('idx_campaigns_status_location', table_name='campaigns')
