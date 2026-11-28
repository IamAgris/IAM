"""Shared workspace errors (avoids circular imports between modules)."""


class WorkspaceError(PermissionError):
    """Raised when a workspace operation is outside policy or capability."""
