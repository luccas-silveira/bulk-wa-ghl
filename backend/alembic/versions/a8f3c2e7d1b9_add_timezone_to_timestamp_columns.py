"""add_timezone_to_timestamp_columns

Revision ID: a8f3c2e7d1b9
Revises: eb03c3cc8781
Create Date: 2026-04-10 16:00:00.000000

"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'a8f3c2e7d1b9'
down_revision: Union[str, Sequence[str], None] = 'eb03c3cc8781'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Convert all TIMESTAMP WITHOUT TIME ZONE to TIMESTAMP WITH TIME ZONE.

    Uses USING col AT TIME ZONE 'UTC' to correctly interpret existing values as
    UTC during conversion, preserving data integrity on databases with existing rows.
    """
    # campaigns
    op.execute("ALTER TABLE campaigns ALTER COLUMN created_at TYPE TIMESTAMP WITH TIME ZONE USING created_at AT TIME ZONE 'UTC'")
    op.execute("ALTER TABLE campaigns ALTER COLUMN updated_at TYPE TIMESTAMP WITH TIME ZONE USING updated_at AT TIME ZONE 'UTC'")
    op.execute("ALTER TABLE campaigns ALTER COLUMN scheduled_time TYPE TIMESTAMP WITH TIME ZONE USING scheduled_time AT TIME ZONE 'UTC'")
    op.execute("ALTER TABLE campaigns ALTER COLUMN paused_at TYPE TIMESTAMP WITH TIME ZONE USING paused_at AT TIME ZONE 'UTC'")

    # messages
    op.execute("ALTER TABLE messages ALTER COLUMN sent_at TYPE TIMESTAMP WITH TIME ZONE USING sent_at AT TIME ZONE 'UTC'")
    op.execute("ALTER TABLE messages ALTER COLUMN delivered_at TYPE TIMESTAMP WITH TIME ZONE USING delivered_at AT TIME ZONE 'UTC'")
    op.execute("ALTER TABLE messages ALTER COLUMN read_at TYPE TIMESTAMP WITH TIME ZONE USING read_at AT TIME ZONE 'UTC'")
    op.execute("ALTER TABLE messages ALTER COLUMN created_at TYPE TIMESTAMP WITH TIME ZONE USING created_at AT TIME ZONE 'UTC'")
    op.execute("ALTER TABLE messages ALTER COLUMN updated_at TYPE TIMESTAMP WITH TIME ZONE USING updated_at AT TIME ZONE 'UTC'")

    # ghl_conversations
    op.execute("ALTER TABLE ghl_conversations ALTER COLUMN last_message_at TYPE TIMESTAMP WITH TIME ZONE USING last_message_at AT TIME ZONE 'UTC'")
    op.execute("ALTER TABLE ghl_conversations ALTER COLUMN created_at TYPE TIMESTAMP WITH TIME ZONE USING created_at AT TIME ZONE 'UTC'")
    op.execute("ALTER TABLE ghl_conversations ALTER COLUMN updated_at TYPE TIMESTAMP WITH TIME ZONE USING updated_at AT TIME ZONE 'UTC'")

    # ghl_locations
    op.execute("ALTER TABLE ghl_locations ALTER COLUMN created_at TYPE TIMESTAMP WITH TIME ZONE USING created_at AT TIME ZONE 'UTC'")
    op.execute("ALTER TABLE ghl_locations ALTER COLUMN updated_at TYPE TIMESTAMP WITH TIME ZONE USING updated_at AT TIME ZONE 'UTC'")

    # ghl_oauth_tokens
    op.execute("ALTER TABLE ghl_oauth_tokens ALTER COLUMN expires_at TYPE TIMESTAMP WITH TIME ZONE USING expires_at AT TIME ZONE 'UTC'")
    op.execute("ALTER TABLE ghl_oauth_tokens ALTER COLUMN created_at TYPE TIMESTAMP WITH TIME ZONE USING created_at AT TIME ZONE 'UTC'")
    op.execute("ALTER TABLE ghl_oauth_tokens ALTER COLUMN updated_at TYPE TIMESTAMP WITH TIME ZONE USING updated_at AT TIME ZONE 'UTC'")

    # ghl_users
    op.execute("ALTER TABLE ghl_users ALTER COLUMN created_at TYPE TIMESTAMP WITH TIME ZONE USING created_at AT TIME ZONE 'UTC'")
    op.execute("ALTER TABLE ghl_users ALTER COLUMN updated_at TYPE TIMESTAMP WITH TIME ZONE USING updated_at AT TIME ZONE 'UTC'")

    # processed_webhooks
    op.execute("ALTER TABLE processed_webhooks ALTER COLUMN processed_at TYPE TIMESTAMP WITH TIME ZONE USING processed_at AT TIME ZONE 'UTC'")


def downgrade() -> None:
    """Revert TIMESTAMP WITH TIME ZONE back to TIMESTAMP WITHOUT TIME ZONE.

    Uses USING col AT TIME ZONE 'UTC' to strip the timezone info while preserving
    the UTC wall-clock values.
    """
    # campaigns
    op.execute("ALTER TABLE campaigns ALTER COLUMN created_at TYPE TIMESTAMP WITHOUT TIME ZONE USING created_at AT TIME ZONE 'UTC'")
    op.execute("ALTER TABLE campaigns ALTER COLUMN updated_at TYPE TIMESTAMP WITHOUT TIME ZONE USING updated_at AT TIME ZONE 'UTC'")
    op.execute("ALTER TABLE campaigns ALTER COLUMN scheduled_time TYPE TIMESTAMP WITHOUT TIME ZONE USING scheduled_time AT TIME ZONE 'UTC'")
    op.execute("ALTER TABLE campaigns ALTER COLUMN paused_at TYPE TIMESTAMP WITHOUT TIME ZONE USING paused_at AT TIME ZONE 'UTC'")

    # messages
    op.execute("ALTER TABLE messages ALTER COLUMN sent_at TYPE TIMESTAMP WITHOUT TIME ZONE USING sent_at AT TIME ZONE 'UTC'")
    op.execute("ALTER TABLE messages ALTER COLUMN delivered_at TYPE TIMESTAMP WITHOUT TIME ZONE USING delivered_at AT TIME ZONE 'UTC'")
    op.execute("ALTER TABLE messages ALTER COLUMN read_at TYPE TIMESTAMP WITHOUT TIME ZONE USING read_at AT TIME ZONE 'UTC'")
    op.execute("ALTER TABLE messages ALTER COLUMN created_at TYPE TIMESTAMP WITHOUT TIME ZONE USING created_at AT TIME ZONE 'UTC'")
    op.execute("ALTER TABLE messages ALTER COLUMN updated_at TYPE TIMESTAMP WITHOUT TIME ZONE USING updated_at AT TIME ZONE 'UTC'")

    # ghl_conversations
    op.execute("ALTER TABLE ghl_conversations ALTER COLUMN last_message_at TYPE TIMESTAMP WITHOUT TIME ZONE USING last_message_at AT TIME ZONE 'UTC'")
    op.execute("ALTER TABLE ghl_conversations ALTER COLUMN created_at TYPE TIMESTAMP WITHOUT TIME ZONE USING created_at AT TIME ZONE 'UTC'")
    op.execute("ALTER TABLE ghl_conversations ALTER COLUMN updated_at TYPE TIMESTAMP WITHOUT TIME ZONE USING updated_at AT TIME ZONE 'UTC'")

    # ghl_locations
    op.execute("ALTER TABLE ghl_locations ALTER COLUMN created_at TYPE TIMESTAMP WITHOUT TIME ZONE USING created_at AT TIME ZONE 'UTC'")
    op.execute("ALTER TABLE ghl_locations ALTER COLUMN updated_at TYPE TIMESTAMP WITHOUT TIME ZONE USING updated_at AT TIME ZONE 'UTC'")

    # ghl_oauth_tokens
    op.execute("ALTER TABLE ghl_oauth_tokens ALTER COLUMN expires_at TYPE TIMESTAMP WITHOUT TIME ZONE USING expires_at AT TIME ZONE 'UTC'")
    op.execute("ALTER TABLE ghl_oauth_tokens ALTER COLUMN created_at TYPE TIMESTAMP WITHOUT TIME ZONE USING created_at AT TIME ZONE 'UTC'")
    op.execute("ALTER TABLE ghl_oauth_tokens ALTER COLUMN updated_at TYPE TIMESTAMP WITHOUT TIME ZONE USING updated_at AT TIME ZONE 'UTC'")

    # ghl_users
    op.execute("ALTER TABLE ghl_users ALTER COLUMN created_at TYPE TIMESTAMP WITHOUT TIME ZONE USING created_at AT TIME ZONE 'UTC'")
    op.execute("ALTER TABLE ghl_users ALTER COLUMN updated_at TYPE TIMESTAMP WITHOUT TIME ZONE USING updated_at AT TIME ZONE 'UTC'")

    # processed_webhooks
    op.execute("ALTER TABLE processed_webhooks ALTER COLUMN processed_at TYPE TIMESTAMP WITHOUT TIME ZONE USING processed_at AT TIME ZONE 'UTC'")
