"""add_phone_check_constraint

Revision ID: c3f1a9e8b2d4
Revises: a8f3c2e7d1b9
Create Date: 2026-04-11 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'c3f1a9e8b2d4'
down_revision: Union[str, Sequence[str], None] = 'a8f3c2e7d1b9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add CHECK constraint to messages.recipient_phone enforcing E.164 format.

    The regex '^\\+[1-9]\\d{1,14}$' matches:
      - Starts with '+'
      - Followed by a non-zero digit (country code first digit)
      - Then 1-14 more digits (total digits: 2-15, per ITU-T E.164 max of 15)

    NOT NULL is not added here — that is already enforced by the initial schema.
    Existing rows that do not match will cause this migration to fail; run a
    data-cleanup script before applying in production if needed.
    """
    op.execute(
        "ALTER TABLE messages ADD CONSTRAINT chk_messages_recipient_phone_e164 "
        "CHECK (recipient_phone ~ '^\\+[1-9]\\d{1,14}$')"
    )


def downgrade() -> None:
    """Remove CHECK constraint from messages.recipient_phone."""
    op.execute(
        "ALTER TABLE messages DROP CONSTRAINT chk_messages_recipient_phone_e164"
    )
