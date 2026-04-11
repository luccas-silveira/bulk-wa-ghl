"""Unit tests for domain exceptions."""
import pytest
from src.exceptions import InvalidTransitionError


class TestInvalidTransitionError:
    def test_message_includes_from_status(self):
        err = InvalidTransitionError("executing", "draft", set())
        assert "executing" in str(err)

    def test_message_includes_to_status(self):
        err = InvalidTransitionError("executing", "draft", set())
        assert "draft" in str(err)

    def test_message_includes_allowed_when_set(self):
        err = InvalidTransitionError("paused", "scheduled", {"executing"})
        assert "executing" in str(err)

    def test_terminal_state_message_when_no_allowed(self):
        err = InvalidTransitionError("completed", "executing", set())
        assert "terminal" in str(err).lower()

    def test_is_exception_subclass(self):
        err = InvalidTransitionError("paused", "scheduled", {"executing"})
        assert isinstance(err, Exception)

    def test_attributes_stored(self):
        err = InvalidTransitionError("paused", "draft", {"executing"})
        assert err.from_status == "paused"
        assert err.to_status == "draft"
        assert err.allowed == {"executing"}
