"""
Unit tests for E.164 phone normalization (EPIC-09)
"""
import pytest
from pydantic import ValidationError

from src.schemas.campaign import ContactData, normalize_phone


class TestNormalizePhone:
    """normalize_phone: normaliza ou retorna original sem erro"""

    def test_already_e164_unchanged(self):
        assert normalize_phone("+5511999998888") == "+5511999998888"

    def test_us_number_with_country_code(self):
        assert normalize_phone("+12125551234") == "+12125551234"

    def test_unparseable_returns_original(self):
        # Números que não fazem sentido devem retornar o valor original sem lançar exceção
        result = normalize_phone("not-a-phone")
        assert result == "not-a-phone"

    def test_empty_string_returns_original(self):
        assert normalize_phone("") == ""

    def test_br_number_without_plus_normalized(self):
        # "5511999998888" deve ser parseado como BR E.164 -> "+5511999998888"
        result = normalize_phone("5511999998888")
        assert result == "+5511999998888"

    def test_number_with_spaces_normalized(self):
        # "+55 11 99999-8888" deve virar "+5511999998888"
        result = normalize_phone("+55 11 99999-8888")
        assert result == "+5511999998888"

    def test_number_with_dashes_normalized(self):
        result = normalize_phone("+55-11-99999-8888")
        assert result == "+5511999998888"


class TestContactDataPhoneNormalization:
    """ContactData.phone_number normaliza E.164 via @field_validator"""

    def test_valid_e164_accepted(self):
        contact = ContactData(phone_number="+5511999998888")
        assert contact.phone_number == "+5511999998888"

    def test_phone_with_spaces_normalized(self):
        contact = ContactData(phone_number="+55 11 99999-8888")
        assert contact.phone_number == "+5511999998888"

    def test_unparseable_phone_kept_as_is(self):
        # Não deve lançar erro; retorna o valor original
        contact = ContactData(phone_number="abc-def")
        assert contact.phone_number == "abc-def"

    def test_empty_phone_rejected_by_min_length(self):
        # min_length=1 ainda bloqueia strings vazias
        with pytest.raises(ValidationError):
            ContactData(phone_number="")

    def test_us_phone_normalized(self):
        contact = ContactData(phone_number="+1 (212) 555-1234")
        assert contact.phone_number == "+12125551234"


class TestGHLContactsServicePhoneNormalization:
    """GHLContactsService normaliza o phone antes de chamar a API GHL"""

    def _make_service(self):
        from unittest.mock import MagicMock, AsyncMock, patch
        from src.services.ghl_contacts_service import GHLContactsService

        db = MagicMock()
        with patch.dict("os.environ", {"GHL_PRIVATE_TOKEN": "tok_test"}):
            svc = GHLContactsService(db)
        return svc

    @pytest.mark.asyncio
    async def test_search_normalizes_phone_before_api_call(self):
        from unittest.mock import AsyncMock, patch, MagicMock
        import httpx

        svc = self._make_service()

        mock_response = MagicMock()
        mock_response.json.return_value = {"contacts": [{"id": "c1"}]}
        mock_response.raise_for_status = MagicMock()

        captured_params = {}

        async def fake_get(url, params=None, headers=None):
            captured_params.update(params or {})
            return mock_response

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.get = fake_get

        with patch("httpx.AsyncClient", return_value=mock_client):
            result = await svc.search_contact_by_phone("loc_1", "+55 11 99999-8888")

        # O número enviado na query deve estar em E.164
        assert captured_params.get("query") == "+5511999998888"
        assert result == {"id": "c1"}

    @pytest.mark.asyncio
    async def test_search_passes_through_unparseable_phone(self):
        from unittest.mock import AsyncMock, patch, MagicMock

        svc = self._make_service()

        mock_response = MagicMock()
        mock_response.json.return_value = {"contacts": []}
        mock_response.raise_for_status = MagicMock()

        captured_params = {}

        async def fake_get(url, params=None, headers=None):
            captured_params.update(params or {})
            return mock_response

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.get = fake_get

        with patch("httpx.AsyncClient", return_value=mock_client):
            result = await svc.search_contact_by_phone("loc_1", "abc-not-a-phone")

        # Número não parseável é passado como está — sem erro
        assert captured_params.get("query") == "abc-not-a-phone"
        assert result is None
