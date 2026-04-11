"""Unit tests for Campaign state machine (CAMP-05, PERS-28)."""
import pytest
from src.models.campaign import Campaign
from src.exceptions import InvalidTransitionError


class TestValidTransitions:
    def test_draft_to_scheduled(self):
        c = Campaign(status='draft')
        c.transition_to('scheduled')
        assert c.status == 'scheduled'

    def test_draft_to_executing(self):
        c = Campaign(status='draft')
        c.transition_to('executing')
        assert c.status == 'executing'

    def test_draft_to_failed(self):
        c = Campaign(status='draft')
        c.transition_to('failed')
        assert c.status == 'failed'

    def test_executing_to_paused(self):
        c = Campaign(status='executing')
        c.transition_to('paused')
        assert c.status == 'paused'

    def test_executing_to_completed(self):
        c = Campaign(status='executing')
        c.transition_to('completed')
        assert c.status == 'completed'

    def test_executing_to_failed(self):
        c = Campaign(status='executing')
        c.transition_to('failed')
        assert c.status == 'failed'

    def test_paused_to_executing(self):
        c = Campaign(status='paused')
        c.transition_to('executing')
        assert c.status == 'executing'

    def test_paused_to_completed(self):
        """Resume with nothing left to do should complete directly from paused."""
        c = Campaign(status='paused')
        c.transition_to('completed')
        assert c.status == 'completed'

    def test_paused_to_failed(self):
        """Resume that encounters a fatal error should be allowed to fail from paused."""
        c = Campaign(status='paused')
        c.transition_to('failed')
        assert c.status == 'failed'

    def test_scheduled_to_cancelled(self):
        c = Campaign(status='scheduled')
        c.transition_to('cancelled')
        assert c.status == 'cancelled'

    def test_scheduled_to_failed(self):
        c = Campaign(status='scheduled')
        c.transition_to('failed')
        assert c.status == 'failed'

    def test_scheduled_to_executing(self):
        c = Campaign(status='scheduled')
        c.transition_to('executing')
        assert c.status == 'executing'


class TestInvalidTransitions:
    def test_completed_is_terminal(self):
        c = Campaign(status='completed')
        with pytest.raises(InvalidTransitionError):
            c.transition_to('executing')

    def test_failed_is_terminal(self):
        c = Campaign(status='failed')
        with pytest.raises(InvalidTransitionError):
            c.transition_to('executing')

    def test_cancelled_is_terminal(self):
        c = Campaign(status='cancelled')
        with pytest.raises(InvalidTransitionError):
            c.transition_to('executing')

    def test_draft_to_completed_not_allowed(self):
        c = Campaign(status='draft')
        with pytest.raises(InvalidTransitionError):
            c.transition_to('completed')

    def test_paused_to_scheduled_not_allowed(self):
        c = Campaign(status='paused')
        with pytest.raises(InvalidTransitionError):
            c.transition_to('scheduled')

    def test_error_includes_from_state(self):
        c = Campaign(status='completed')
        with pytest.raises(InvalidTransitionError, match="completed"):
            c.transition_to('paused')

    def test_error_includes_to_state(self):
        c = Campaign(status='completed')
        with pytest.raises(InvalidTransitionError, match="paused"):
            c.transition_to('paused')


class TestValidateStatus:
    def test_unknown_status_raises_value_error(self):
        with pytest.raises(ValueError, match="Invalid campaign status"):
            Campaign(status='unknown_status')

    def test_all_valid_statuses_accepted(self):
        for s in ('draft', 'scheduled', 'executing', 'paused', 'completed', 'failed', 'cancelled'):
            c = Campaign(status=s)
            assert c.status == s

    def test_assigning_invalid_status_raises(self):
        c = Campaign(status='draft')
        with pytest.raises(ValueError, match="Invalid campaign status"):
            c.status = 'typo_status'
