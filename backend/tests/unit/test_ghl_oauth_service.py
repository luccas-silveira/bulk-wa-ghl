# backend/tests/unit/test_ghl_oauth_service.py
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import httpx

from src.services.ghl_oauth_service import GHLOAuthService


@pytest.fixture
def db():
    return MagicMock()


@pytest.fixture
def oauth_service(db):
    with patch.dict("os.environ", {
        "GHL_CLIENT_ID": "cid",
        "GHL_CLIENT_SECRET": "csecret",
        "GHL_REDIRECT_URI": "http://localhost/callback",
    }):
        return GHLOAuthService(db)


class TestErrorMessages:
    """GHL-23: generic error messages, no internal details exposed"""

    @pytest.mark.asyncio
    async def test_exchange_code_http_error_generic_message(self, oauth_service):
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.text = "client_id is invalid INTERNAL_SECRET_DETAIL"

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client.post = AsyncMock(
                side_effect=httpx.HTTPStatusError("err", request=MagicMock(), response=mock_response)
            )
            mock_client_cls.return_value = mock_client

            with pytest.raises(ValueError) as exc_info:
                await oauth_service.exchange_code_for_token("code123")

        assert "INTERNAL_SECRET_DETAIL" not in str(exc_info.value)
        assert "Token exchange failed" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_refresh_token_http_error_generic_message(self, oauth_service, db):
        mock_token = MagicMock()
        mock_token.refresh_token_encrypted = b"encrypted"
        db.query.return_value.filter.return_value.first.return_value = mock_token

        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.text = "refresh_token expired INTERNAL"

        with patch.object(oauth_service.encryption_service, "decrypt", return_value="rt"):
            with patch("httpx.AsyncClient") as mock_client_cls:
                mock_client = AsyncMock()
                mock_client.__aenter__ = AsyncMock(return_value=mock_client)
                mock_client.__aexit__ = AsyncMock(return_value=False)
                mock_client.post = AsyncMock(
                    side_effect=httpx.HTTPStatusError("err", request=MagicMock(), response=mock_response)
                )
                mock_client_cls.return_value = mock_client

                with pytest.raises(ValueError) as exc_info:
                    await oauth_service.refresh_token("loc123")

        assert "INTERNAL" not in str(exc_info.value)
        assert "Token refresh failed" in str(exc_info.value)


class TestRetryBehavior:
    """GHL-16: retry on transient network errors and 5xx"""

    @pytest.mark.asyncio
    async def test_exchange_retries_on_network_error_then_succeeds(self, oauth_service):
        success_response = MagicMock()
        success_response.status_code = 200
        success_response.json.return_value = {
            "access_token": "at", "refresh_token": "rt",
            "expires_in": 3600, "locationId": "loc1", "scope": "x"
        }
        success_response.raise_for_status = MagicMock()

        call_count = {"n": 0}

        async def post_side_effect(*args, **kwargs):
            call_count["n"] += 1
            if call_count["n"] < 3:
                raise httpx.RequestError("network error")
            return success_response

        with patch.object(oauth_service, "_store_tokens", new_callable=AsyncMock):
            with patch("httpx.AsyncClient") as mock_cls:
                mock_client = AsyncMock()
                mock_client.__aenter__ = AsyncMock(return_value=mock_client)
                mock_client.__aexit__ = AsyncMock(return_value=False)
                mock_client.post = AsyncMock(side_effect=post_side_effect)
                mock_cls.return_value = mock_client

                result = await oauth_service.exchange_code_for_token("code")
                assert call_count["n"] == 3  # failed twice, succeeded on 3rd

    @pytest.mark.asyncio
    async def test_exchange_does_not_retry_on_4xx(self, oauth_service):
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.text = "bad request"

        call_count = {"n": 0}

        async def post_side_effect(*args, **kwargs):
            call_count["n"] += 1
            raise httpx.HTTPStatusError("err", request=MagicMock(), response=mock_response)

        with patch("httpx.AsyncClient") as mock_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client.post = AsyncMock(side_effect=post_side_effect)
            mock_cls.return_value = mock_client

            with pytest.raises(ValueError):
                await oauth_service.exchange_code_for_token("code")

        assert call_count["n"] == 1  # no retry on 4xx


class TestStoreTokens:
    """GHL-02 + GHL-17: raw_response filtering and required field validation"""

    @pytest.mark.asyncio
    async def test_raw_response_excludes_tokens(self, oauth_service, db):
        captured = {}

        def fake_add(record):
            captured["record"] = record

        db.query.return_value.filter.return_value.first.return_value = None
        db.add.side_effect = fake_add
        db.commit = MagicMock()

        token_data = {
            "access_token": "plaintext_at",
            "refresh_token": "plaintext_rt",
            "expires_in": 3600,
            "locationId": "loc1",
            "scope": "conversations.write",
            "companyId": "comp1",
        }

        with patch.object(oauth_service.encryption_service, "encrypt", return_value=b"enc"):
            await oauth_service._store_tokens("loc1", token_data)

        stored = captured["record"].raw_response
        assert "access_token" not in stored
        assert "refresh_token" not in stored
        assert stored["locationId"] == "loc1"
        assert stored["companyId"] == "comp1"

    @pytest.mark.asyncio
    async def test_missing_location_id_raises(self, oauth_service):
        token_data = {
            "access_token": "at",
            "refresh_token": "rt",
            "expires_in": 3600,
            # locationId missing
        }
        with pytest.raises(ValueError, match="locationId"):
            await oauth_service._store_tokens("loc1", token_data)

    @pytest.mark.asyncio
    async def test_missing_access_token_raises(self, oauth_service):
        token_data = {
            "refresh_token": "rt",
            "expires_in": 3600,
            "locationId": "loc1",
        }
        with pytest.raises(ValueError, match="access_token"):
            await oauth_service._store_tokens("loc1", token_data)


class TestGetValidAccessToken:
    """GHL-01: with_for_update() prevents concurrent refresh race condition"""

    @pytest.mark.asyncio
    async def test_uses_with_for_update(self, oauth_service, db):
        """Verify the query uses with_for_update() for locking"""
        mock_query = MagicMock()
        mock_filter = MagicMock()
        mock_locked = MagicMock()
        mock_token = MagicMock()
        mock_token.is_expired.return_value = False
        mock_token.access_token_encrypted = b"enc"

        db.query.return_value = mock_query
        mock_query.filter.return_value = mock_filter
        mock_filter.with_for_update.return_value = mock_locked
        mock_locked.first.return_value = mock_token

        with patch.object(oauth_service.encryption_service, "decrypt", return_value="token"):
            result = await oauth_service.get_valid_access_token("loc1")

        # Assert with_for_update() was called
        mock_filter.with_for_update.assert_called_once()
        assert result == "token"

    @pytest.mark.asyncio
    async def test_refreshes_expired_token(self, oauth_service, db):
        mock_token = MagicMock()
        mock_token.is_expired.return_value = True
        mock_token.access_token_encrypted = b"enc_new"

        db.query.return_value.filter.return_value.with_for_update.return_value.first.return_value = mock_token

        with patch.object(oauth_service, "refresh_token", new_callable=AsyncMock) as mock_refresh:
            with patch.object(oauth_service.encryption_service, "decrypt", return_value="new_token"):
                result = await oauth_service.get_valid_access_token("loc1")

        mock_refresh.assert_awaited_once_with("loc1")


class TestExchangeCodeReturnsOnlyMetadata:
    """GHL-12: exchange_code_for_token must not return raw tokens"""

    @pytest.mark.asyncio
    async def test_result_excludes_access_token(self, oauth_service):
        token_data = {
            "access_token": "secret_at",
            "refresh_token": "secret_rt",
            "expires_in": 3600,
            "locationId": "loc1",
            "scope": "conversations.write",
            "companyId": "comp1",
        }

        with patch.object(oauth_service, "_call_token_endpoint", new_callable=AsyncMock, return_value=token_data):
            with patch.object(oauth_service, "_store_tokens", new_callable=AsyncMock):
                result = await oauth_service.exchange_code_for_token("code")

        assert "access_token" not in result
        assert "refresh_token" not in result
        assert result["location_id"] == "loc1"
        assert result["expires_in"] == 3600
        assert result["scope"] == "conversations.write"
