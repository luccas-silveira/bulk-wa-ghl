"""Integration tests for state machine DB constraints.
Require PostgreSQL with migrations applied.
Run: cd backend && DATABASE_URL=<url> pytest tests/integration/test_state_machine_constraints.py -v
"""
import pytest
from sqlalchemy.exc import IntegrityError
from src.database import SessionLocal


@pytest.fixture
def db():
    session = SessionLocal()
    yield session
    session.rollback()
    session.close()


class TestCampaignStatusConstraint:
    def test_invalid_status_rejected(self, db):
        db.execute(
            "INSERT INTO campaigns (name, status, ghl_location_id, ghl_location_name) "
            "VALUES ('test_constraint_bad', 'not_valid', 'test_loc', 'Test')"
        )
        with pytest.raises(IntegrityError, match="chk_campaign_status"):
            db.commit()

    def test_valid_statuses_accepted(self, db):
        for s in ('draft', 'scheduled', 'executing', 'paused', 'completed', 'failed', 'cancelled'):
            db.execute(
                f"INSERT INTO campaigns (name, status, ghl_location_id, ghl_location_name) "
                f"VALUES ('test_constraint_{s}', '{s}', 'test_loc', 'Test')"
            )
        db.commit()
        db.execute("DELETE FROM campaigns WHERE name LIKE 'test_constraint_%'")
        db.commit()


class TestCampaignPausedAtConstraint:
    def test_paused_at_with_non_paused_status_rejected(self, db):
        db.execute(
            "INSERT INTO campaigns (name, status, ghl_location_id, ghl_location_name, paused_at) "
            "VALUES ('test_constraint_paused_at', 'executing', 'test_loc', 'Test', now())"
        )
        with pytest.raises(IntegrityError, match="chk_campaign_paused_at"):
            db.commit()


class TestMessageStatusConstraint:
    def test_invalid_message_status_rejected(self, db):
        result = db.execute("SELECT id FROM campaigns LIMIT 1").fetchone()
        if not result:
            pytest.skip("No campaigns in DB for FK reference")
        campaign_id = result[0]
        db.execute(
            f"INSERT INTO messages (campaign_id, recipient_phone, content, status) "
            f"VALUES ({campaign_id}, '+5511999990000', 'test', 'invalid_status')"
        )
        with pytest.raises(IntegrityError, match="chk_message_status"):
            db.commit()
