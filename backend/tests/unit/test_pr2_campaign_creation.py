# backend/tests/unit/test_pr2_campaign_creation.py
import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, patch, AsyncMock
import json


def _make_app_with_mock_db(db_mock):
    """Helper: cria TestClient com DB mockado."""
    import src.main as main_module
    from src.main import app, get_db

    def override_get_db():
        yield db_mock

    app.dependency_overrides[get_db] = override_get_db
    return TestClient(app, raise_server_exceptions=False)


def _valid_payload(**overrides):
    base = {
        "ghl_location_id": "loc_abc",
        "name": "Test Campaign",
        "ghl_user_ids": ["user_xyz"],
        "sending_speed": "medium",
        "schedule_type": "immediate",
        "messages": [{"text": "Hello {{name}}"}],
        "audience_criteria": {"csv_data": [{"phone_number": "+5511999990001", "name": "Alice"}]},
    }
    base.update(overrides)
    return base


class TestWAHA12LocationValidation:
    """WAHA-12: criar campanha com location inexistente retorna 422."""

    def test_unknown_location_id_returns_422(self):
        """ghl_location_id não encontrado em ghl_locations → HTTP 422."""
        from src.main import app, get_db
        from src.models.ghl_location import GHLLocation

        db = MagicMock()
        # Location not found
        db.query.return_value.filter_by.return_value.first.return_value = None

        client = _make_app_with_mock_db(db)
        resp = client.post("/campaigns", json=_valid_payload())

        assert resp.status_code == 422, f"Expected 422, got {resp.status_code}: {resp.text}"
        assert "location" in resp.text.lower()

        app.dependency_overrides.clear()

    def test_known_location_id_does_not_reject(self):
        """ghl_location_id válido não é rejeitado por WAHA-12."""
        from src.main import app, get_db
        from src.models.ghl_location import GHLLocation
        from src.models.ghl_user import GHLUser

        db = MagicMock()

        # Simulate: location found, user found, campaign creation
        mock_location = MagicMock(spec=GHLLocation)
        mock_user = MagicMock(spec=GHLUser)
        mock_campaign = MagicMock()
        mock_campaign.id = 1
        mock_campaign.name = "Test"
        mock_campaign.status = "draft"
        mock_campaign.ghl_location_id = "loc_abc"
        mock_campaign.ghl_user_id = "user_xyz"
        mock_campaign.sending_speed = "medium"
        mock_campaign.schedule_type = "immediate"
        mock_campaign.created_at = None

        # Chain: db.query(X).filter_by(ghl_location_id=...).first() → mock_location
        # Chain: db.query(X).filter_by(ghl_user_id=...).first() → mock_user
        from src.models.ghl_location import GHLLocation as _GHLLocation
        from src.models.ghl_user import GHLUser as _GHLUser

        def query_side_effect(model):
            m = MagicMock()
            if model == _GHLLocation:
                m.filter_by.return_value.first.return_value = mock_location
            elif model == _GHLUser:
                m.filter_by.return_value.first.return_value = mock_user
            else:
                m.filter_by.return_value.first.return_value = MagicMock()
            return m

        db.query.side_effect = query_side_effect
        db.add = MagicMock()
        db.commit = MagicMock()
        db.refresh = MagicMock(side_effect=lambda c: None)

        # The actual campaign obj returned after add/refresh needs to behave
        # We just check the response is NOT 422
        client = _make_app_with_mock_db(db)

        with patch("src.main.asyncio.create_task"):
            resp = client.post("/campaigns", json=_valid_payload())

        app.dependency_overrides.clear()
        assert resp.status_code != 422, f"Should not get 422 for valid location, got {resp.status_code}: {resp.text}"


class TestGHL22UserValidation:
    """GHL-22: criar campanha com user inexistente retorna 422."""

    def test_unknown_user_id_returns_422(self):
        """ghl_user_ids com ID não encontrado em ghl_users → HTTP 422."""
        from src.main import app, get_db
        from src.models.ghl_location import GHLLocation
        from src.models.ghl_user import GHLUser

        db = MagicMock()

        mock_location = MagicMock(spec=GHLLocation)

        # Location found, user NOT found
        def query_side_effect(model):
            m = MagicMock()
            if model == GHLLocation:
                m.filter_by.return_value.first.return_value = mock_location
            else:
                m.filter_by.return_value.first.return_value = None
            return m

        db.query.side_effect = query_side_effect

        client = _make_app_with_mock_db(db)
        resp = client.post("/campaigns", json=_valid_payload())

        app.dependency_overrides.clear()
        assert resp.status_code == 422, f"Expected 422, got {resp.status_code}: {resp.text}"
        assert "user" in resp.text.lower()

    def test_no_user_ids_returns_422(self):
        """Criar campanha sem ghl_user_ids nem ghl_user_id → HTTP 422."""
        from src.main import app, get_db
        from src.models.ghl_location import GHLLocation

        db = MagicMock()
        mock_location = MagicMock(spec=GHLLocation)

        def query_side_effect(model):
            m = MagicMock()
            if model == GHLLocation:
                m.filter_by.return_value.first.return_value = mock_location
            else:
                m.filter_by.return_value.first.return_value = MagicMock()
            return m

        db.query.side_effect = query_side_effect
        client = _make_app_with_mock_db(db)

        # payload without ghl_user_ids or ghl_user_id
        payload = _valid_payload()
        del payload["ghl_user_ids"]

        resp = client.post("/campaigns", json=payload)
        app.dependency_overrides.clear()

        assert resp.status_code == 422, f"Expected 422 for no user IDs, got {resp.status_code}: {resp.text}"
        assert "user" in resp.text.lower()
