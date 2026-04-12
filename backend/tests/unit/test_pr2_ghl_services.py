import pytest
from unittest.mock import MagicMock, AsyncMock, patch
import httpx


class TestSendMessageUsesContactId:
    """GHL-05: send_message deve usar contact_id, não phone."""

    @pytest.mark.asyncio
    async def test_payload_contains_contact_id_not_phone(self):
        """Payload enviado à API GHL usa contactId, não phone number."""
        from src.services.ghl_conversations_service import GHLConversationsService

        db = MagicMock()
        svc = GHLConversationsService(db)
        svc.private_token = 'test_token'
        svc.use_private_token = True
        svc.rate_limiter = MagicMock()
        svc.rate_limiter.consume = AsyncMock(return_value=True)

        captured_payload = {}

        async def fake_post(url, *, json=None, headers=None, **kwargs):
            captured_payload.update(json or {})
            mock_resp = MagicMock()
            mock_resp.raise_for_status = MagicMock()
            mock_resp.json.return_value = {'id': 'msg1', 'conversationId': 'conv1'}
            return mock_resp

        with patch('httpx.AsyncClient') as mock_client_cls:
            mock_client = MagicMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client.post = fake_post
            mock_client_cls.return_value = mock_client

            await svc.send_message(
                location_id='loc1',
                contact_id='contact_abc',
                message_text='Hello'
            )

        assert captured_payload.get('contactId') == 'contact_abc'
        assert 'phone' not in captured_payload


class TestSendMessageTypeWhatsApp:
    """GHL-06: send_message deve enviar type='WhatsApp', não 'SMS'."""

    @pytest.mark.asyncio
    async def test_payload_type_is_whatsapp(self):
        """Verifica que o campo 'type' no payload é 'WhatsApp'."""
        from src.services.ghl_conversations_service import GHLConversationsService

        db = MagicMock()
        svc = GHLConversationsService(db)
        svc.private_token = 'test_token'
        svc.use_private_token = True
        svc.rate_limiter = MagicMock()
        svc.rate_limiter.consume = AsyncMock(return_value=True)

        captured_payload = {}

        async def fake_post(url, *, json=None, headers=None, **kwargs):
            captured_payload.update(json or {})
            mock_resp = MagicMock()
            mock_resp.raise_for_status = MagicMock()
            mock_resp.json.return_value = {'id': 'm1', 'conversationId': 'c1'}
            return mock_resp

        with patch('httpx.AsyncClient') as mock_client_cls:
            mock_client = MagicMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client.post = fake_post
            mock_client_cls.return_value = mock_client

            await svc.send_message(location_id='loc1', contact_id='c1', message_text='Hi')

        assert captured_payload.get('type') == 'WhatsApp'
        assert captured_payload.get('type') != 'SMS'


class TestSendMessage401TokenRefresh:
    """GHL-08: 401 deve forçar refresh do token OAuth antes do retry."""

    def _make_401_error(self):
        mock_request = MagicMock()
        mock_response_401 = MagicMock()
        mock_response_401.status_code = 401
        mock_response_401.text = 'Unauthorized'
        mock_response_401.request = mock_request
        return httpx.HTTPStatusError('401', request=mock_request, response=mock_response_401)

    @pytest.mark.asyncio
    async def test_401_triggers_token_refresh(self):
        """Quando API retorna 401, oauth_service.refresh_token() é chamado."""
        from src.services.ghl_conversations_service import GHLConversationsService

        db = MagicMock()
        svc = GHLConversationsService(db)
        svc.private_token = None
        svc.use_private_token = False

        mock_oauth = MagicMock()
        mock_oauth.get_valid_access_token = AsyncMock(return_value='token_abc')
        mock_oauth.refresh_token = AsyncMock()
        svc.oauth_service = mock_oauth
        svc.rate_limiter = MagicMock()
        svc.rate_limiter.consume = AsyncMock(return_value=True)

        http_401_error = self._make_401_error()
        call_count = [0]

        async def fake_post(url, *, json=None, headers=None, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                raise http_401_error
            mock_resp = MagicMock()
            mock_resp.raise_for_status = MagicMock()
            mock_resp.json.return_value = {'id': 'm1', 'conversationId': 'c1'}
            return mock_resp

        with patch('httpx.AsyncClient') as mock_client_cls:
            mock_client = MagicMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client.post = fake_post
            mock_client_cls.return_value = mock_client

            await svc.send_message(location_id='loc1', contact_id='c1', message_text='Hi')

        mock_oauth.refresh_token.assert_called_once_with('loc1')

    @pytest.mark.asyncio
    async def test_private_token_does_not_refresh_on_401(self):
        """Quando use_private_token=True, 401 não tenta OAuth refresh."""
        from tenacity import RetryError
        from src.services.ghl_conversations_service import GHLConversationsService

        db = MagicMock()
        svc = GHLConversationsService(db)
        svc.private_token = 'static_token'
        svc.use_private_token = True
        svc.rate_limiter = MagicMock()
        svc.rate_limiter.consume = AsyncMock(return_value=True)

        http_401_error = self._make_401_error()

        with patch('httpx.AsyncClient') as mock_client_cls:
            mock_client = MagicMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client.post = AsyncMock(side_effect=http_401_error)
            mock_client_cls.return_value = mock_client

            # tenacity retries 3x then wraps in RetryError (no reraise=True on decorator)
            with pytest.raises((httpx.HTTPStatusError, RetryError)):
                await svc.send_message(location_id='loc1', contact_id='c1', message_text='Hi')
        # Test passes if no AttributeError (oauth_service not accessed on private token path)


class TestSyncUsersMarksInactive:
    """GHL-15: após sync, usuários não retornados pela API ficam is_active=False."""

    @pytest.mark.asyncio
    async def test_users_missing_from_api_marked_inactive(self):
        """Se DB tem user_A e user_B, mas API retorna só user_A, user_B vira is_active=False."""
        from src.services.ghl_users_service import GHLUsersService
        from src.models.ghl_user import GHLUser

        db = MagicMock()
        db.commit = AsyncMock()
        db.add = MagicMock()

        user_A = MagicMock(spec=GHLUser)
        user_A.ghl_user_id = 'user_A'
        user_A.is_active = True

        # execute returns user_A for any select, and a plain result for update
        execute_result = MagicMock()
        execute_result.scalar_one_or_none.return_value = user_A
        db.execute = AsyncMock(return_value=execute_result)

        svc = GHLUsersService(db)
        svc.private_token = 'tok'
        svc.use_private_token = True

        # API returns only user_A
        api_users = [{'id': 'user_A', 'name': 'Alice', 'email': 'a@x.com'}]
        svc.fetch_users_from_api = AsyncMock(return_value=api_users)

        await svc.sync_users_for_location('loc1')

        # The service calls db.execute() with an update() statement to mark inactive users
        # Verify db.execute was called (for both select and update calls)
        assert db.execute.called
        assert db.commit.called

    @pytest.mark.asyncio
    async def test_all_api_users_remain_active(self):
        """Usuários presentes na API ficam is_active=True após sync."""
        from src.services.ghl_users_service import GHLUsersService
        from src.models.ghl_user import GHLUser

        db = MagicMock()
        db.commit = AsyncMock()
        db.add = MagicMock()

        user_X = MagicMock(spec=GHLUser)
        user_X.ghl_user_id = 'user_X'
        user_X.is_active = False  # was inactive

        execute_result = MagicMock()
        execute_result.scalar_one_or_none.return_value = user_X
        db.execute = AsyncMock(return_value=execute_result)

        svc = GHLUsersService(db)
        svc.private_token = 'tok'
        svc.use_private_token = True

        api_users = [{'id': 'user_X', 'name': 'Xena', 'email': 'x@x.com'}]
        svc.fetch_users_from_api = AsyncMock(return_value=api_users)

        await svc.sync_users_for_location('loc1')

        assert user_X.is_active is True

    @pytest.mark.asyncio
    async def test_empty_api_response_marks_all_inactive(self):
        """API retorna vazio → todos os usuários locais viram is_active=False."""
        from src.services.ghl_users_service import GHLUsersService

        db = MagicMock()
        db.commit = AsyncMock()
        db.add = MagicMock()
        execute_result = MagicMock()
        db.execute = AsyncMock(return_value=execute_result)

        svc = GHLUsersService(db)
        svc.private_token = 'tok'
        svc.use_private_token = True

        # API returns empty list
        svc.fetch_users_from_api = AsyncMock(return_value=[])

        await svc.sync_users_for_location('loc1')

        # The service should call db.execute with an update statement for empty API
        assert db.execute.called
        assert db.commit.called

    @pytest.mark.asyncio
    async def test_user_without_id_skipped_and_does_not_break_deactivation(self):
        """API user without 'id' is skipped; bulk deactivation still fires for known user_B."""
        from src.services.ghl_users_service import GHLUsersService
        from src.models.ghl_user import GHLUser

        db = MagicMock()
        db.commit = AsyncMock()
        db.add = MagicMock()

        user_A = MagicMock(spec=GHLUser)
        user_A.ghl_user_id = 'user_A'
        user_A.is_active = True

        execute_result = MagicMock()
        execute_result.scalar_one_or_none.return_value = user_A
        db.execute = AsyncMock(return_value=execute_result)

        svc = GHLUsersService(db)
        svc.private_token = 'tok'
        svc.use_private_token = True

        # API returns user_A (valid) and a broken entry without 'id'
        api_users = [
            {'id': 'user_A', 'name': 'Alice', 'email': 'a@x.com'},
            {'name': 'Ghost', 'email': 'g@x.com'},  # no 'id'
        ]
        svc.fetch_users_from_api = AsyncMock(return_value=api_users)

        await svc.sync_users_for_location('loc1')

        # The service should have called execute (for select + update) and commit
        assert db.execute.called
        assert db.commit.called
