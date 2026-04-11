"""state_machine_constraints

Revision ID: d20974da6dc5
Revises: a8f3c2e7d1b9
Create Date: 2026-04-11 16:32:37.379363

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd20974da6dc5'
down_revision: Union[str, Sequence[str], None] = 'a8f3c2e7d1b9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # PERS-06: CHECK constraints for valid status values
    op.execute("""
        ALTER TABLE campaigns
        ADD CONSTRAINT chk_campaign_status
        CHECK (status IN ('draft','scheduled','executing','paused','completed','failed','cancelled'))
    """)
    op.execute("""
        ALTER TABLE messages
        ADD CONSTRAINT chk_message_status
        CHECK (status IN ('pending','sent','delivered','read','failed'))
    """)

    # PERS-11: paused_at must be NULL unless status='paused'
    op.execute("""
        ALTER TABLE campaigns
        ADD CONSTRAINT chk_campaign_paused_at
        CHECK (paused_at IS NULL OR status = 'paused')
    """)

    # PERS-13: if ghl_location_id is set, ghl_location_name must also be set
    op.execute("""
        ALTER TABLE campaigns
        ADD CONSTRAINT chk_campaign_location_name
        CHECK (ghl_location_id IS NULL OR ghl_location_name IS NOT NULL)
    """)

    # PERS-08: ghl_location_id NOT NULL
    op.execute("ALTER TABLE campaigns ALTER COLUMN ghl_location_id SET NOT NULL")

    # PERS-09: campaign_id NOT NULL (standalone messages feature removed — DECISAO-04)
    op.execute("ALTER TABLE messages ALTER COLUMN campaign_id SET NOT NULL")

    # PERS-15: messages.campaign_id CASCADE → RESTRICT
    op.drop_constraint('messages_campaign_id_fkey', 'messages', type_='foreignkey')
    op.create_foreign_key(
        'messages_campaign_id_fkey', 'messages', 'campaigns',
        ['campaign_id'], ['id'], ondelete='RESTRICT'
    )

    # PERS-16: ghl_conversations FK → RESTRICT
    try:
        op.drop_constraint('ghl_conversations_campaign_id_fkey', 'ghl_conversations', type_='foreignkey')
        op.create_foreign_key(
            'ghl_conversations_campaign_id_fkey', 'ghl_conversations', 'campaigns',
            ['campaign_id'], ['id'], ondelete='RESTRICT'
        )
    except Exception:
        pass  # constraint may not exist in all environments


def downgrade() -> None:
    """Downgrade schema."""
    try:
        op.drop_constraint('ghl_conversations_campaign_id_fkey', 'ghl_conversations', type_='foreignkey')
        op.create_foreign_key(
            'ghl_conversations_campaign_id_fkey', 'ghl_conversations', 'campaigns',
            ['campaign_id'], ['id'], ondelete='CASCADE'
        )
    except Exception:
        pass

    op.drop_constraint('messages_campaign_id_fkey', 'messages', type_='foreignkey')
    op.create_foreign_key(
        'messages_campaign_id_fkey', 'messages', 'campaigns',
        ['campaign_id'], ['id'], ondelete='CASCADE'
    )

    op.execute("ALTER TABLE messages ALTER COLUMN campaign_id DROP NOT NULL")
    op.execute("ALTER TABLE campaigns ALTER COLUMN ghl_location_id DROP NOT NULL")
    op.execute("ALTER TABLE campaigns DROP CONSTRAINT IF EXISTS chk_campaign_location_name")
    op.execute("ALTER TABLE campaigns DROP CONSTRAINT IF EXISTS chk_campaign_paused_at")
    op.execute("ALTER TABLE messages DROP CONSTRAINT IF EXISTS chk_message_status")
    op.execute("ALTER TABLE campaigns DROP CONSTRAINT IF EXISTS chk_campaign_status")
