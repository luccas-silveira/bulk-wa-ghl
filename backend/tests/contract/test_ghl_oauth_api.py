# backend/tests/contract/test_ghl_oauth_api.py
import pytest
import time
from unittest.mock import patch, AsyncMock

from src.api.ghl_oauth import _generate_oauth_state, _verify_oauth_state


class TestCSRFStateFunctions:
    """GHL-03: CSRF state generation and verification"""

    def test_generated_state_is_valid(self):
        state = _generate_oauth_state()
        assert _verify_oauth_state(state) is True

    def test_tampered_state_is_invalid(self):
        state = _generate_oauth_state()
        tampered = state[:-5] + "AAAAA"
        assert _verify_oauth_state(tampered) is False

    def test_expired_state_is_invalid(self):
        with patch("src.api.ghl_oauth.time") as mock_time:
            mock_time.time.return_value = 1000.0
            state = _generate_oauth_state()
        # Fast-forward 6 minutes
        with patch("src.api.ghl_oauth.time") as mock_time:
            mock_time.time.return_value = 1000.0 + 360
            assert _verify_oauth_state(state) is False

    def test_empty_state_is_invalid(self):
        assert _verify_oauth_state("") is False

    def test_malformed_state_is_invalid(self):
        assert _verify_oauth_state("not.a.valid.state.format") is False

    def test_none_state_handled(self):
        assert _verify_oauth_state(None) is False
