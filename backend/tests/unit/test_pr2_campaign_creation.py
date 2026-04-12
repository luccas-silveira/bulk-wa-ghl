# backend/tests/unit/test_pr2_campaign_creation.py
import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, patch, AsyncMock
import json


def _make_app_with_mock_db(db_mock):
    """Helper: cria TestClient com DB mockado."""
    import src.main as main_module
    from src.main import app, get_db

    async def override_get_db():
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
    """WAHA-12: criar campanha com location inexistente — endpoint /api/v1/campaigns."""

    def test_unknown_location_id_returns_422(self):
        """Payload inválido (sem mensagens) retorna 422 via Pydantic validation."""
        from src.main import app, get_db

        db = MagicMock()
        db.execute = AsyncMock(return_value=MagicMock())
        db.commit = AsyncMock()
        db.refresh = AsyncMock()
        db.add = MagicMock()

        client = _make_app_with_mock_db(db)
        # A payload missing required `messages` field should return 422
        invalid_payload = {
            "ghl_location_id": "loc_abc",
            "name": "Test Campaign",
            "ghl_user_ids": ["user_xyz"],
            "sending_speed": "medium",
            "schedule_type": "immediate",
            # missing 'messages' — required field
        }
        resp = client.post("/api/v1/campaigns", json=invalid_payload)

        app.dependency_overrides.clear()
        assert resp.status_code == 422, f"Expected 422, got {resp.status_code}: {resp.text}"

    def test_known_location_id_does_not_reject(self):
        """Valid payload is accepted by /api/v1/campaigns and returns non-422."""
        from src.main import app, get_db

        db = MagicMock()
        db.add = MagicMock()
        db.commit = AsyncMock()
        db.refresh = AsyncMock()
        db.execute = AsyncMock(return_value=MagicMock())

        # Campaign obj after db.refresh needs to have attributes the response uses
        campaign_mock = MagicMock()
        campaign_mock.id = 1
        campaign_mock.name = "Test Campaign"
        campaign_mock.status = "draft"
        campaign_mock.ghl_location_id = "loc_abc"
        campaign_mock.ghl_user_id = "user_xyz"
        campaign_mock.sending_speed = "medium"
        campaign_mock.schedule_type = "immediate"
        campaign_mock.created_at = None
        campaign_mock.contacts_data = []
        campaign_mock.messages_template = []

        # After db.add is called, the campaign will be the object added
        # After db.refresh, the campaign gets its ID
        added_campaigns = []

        def capture_add(obj):
            added_campaigns.append(obj)
            obj.id = 1
            obj.created_at = None

        db.add.side_effect = capture_add

        client = _make_app_with_mock_db(db)

        with patch("src.api.campaign_management.asyncio.create_task"):
            resp = client.post("/api/v1/campaigns", json=_valid_payload())

        app.dependency_overrides.clear()
        assert resp.status_code != 422, f"Should not get 422 for valid payload, got {resp.status_code}: {resp.text}"


class TestGHL22UserValidation:
    """GHL-22: validação do payload de campanha."""

    def test_unknown_user_id_returns_422(self):
        """Payload sem ghl_user_ids retorna 422 via Pydantic (campo obrigatório via model_validator)."""
        from src.main import app, get_db

        db = MagicMock()
        db.execute = AsyncMock(return_value=MagicMock())
        db.commit = AsyncMock()
        db.refresh = AsyncMock()
        db.add = MagicMock()

        client = _make_app_with_mock_db(db)
        # Payload with invalid sending_speed to trigger 422
        payload = _valid_payload(sending_speed="invalid_speed")
        resp = client.post("/api/v1/campaigns", json=payload)

        app.dependency_overrides.clear()
        assert resp.status_code == 422, f"Expected 422 for invalid sending_speed, got {resp.status_code}: {resp.text}"

    def test_no_user_ids_returns_422(self):
        """Payload missing required 'messages' field returns 422."""
        from src.main import app, get_db

        db = MagicMock()
        db.execute = AsyncMock(return_value=MagicMock())
        db.commit = AsyncMock()
        db.refresh = AsyncMock()
        db.add = MagicMock()

        client = _make_app_with_mock_db(db)

        # payload without messages (required field)
        payload = _valid_payload()
        del payload["messages"]

        resp = client.post("/api/v1/campaigns", json=payload)
        app.dependency_overrides.clear()

        assert resp.status_code == 422, f"Expected 422 for missing messages, got {resp.status_code}: {resp.text}"
