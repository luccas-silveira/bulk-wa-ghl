"""Domain exceptions for bulk-wa-ghl."""


class InvalidTransitionError(Exception):
    """Raised when a campaign status transition is not allowed."""

    def __init__(self, from_status: str, to_status: str, allowed: set) -> None:
        if allowed:
            msg = (
                f"Cannot transition from '{from_status}' to '{to_status}'. "
                f"Allowed: {sorted(allowed)}"
            )
        else:
            msg = (
                f"Cannot transition from '{from_status}' to '{to_status}'. "
                f"'{from_status}' is a terminal state — no transitions allowed."
            )
        super().__init__(msg)
        self.from_status = from_status
        self.to_status = to_status
        self.allowed = allowed
