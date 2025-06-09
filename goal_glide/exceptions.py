
class GoalGlideError(Exception):
    """Base exception for all application-specific errors."""

    pass


class GoalNotFoundError(GoalGlideError):
    """Raised when a goal with the given ID is not found."""

    pass


class GoalAlreadyArchivedError(GoalGlideError):
    """Raised when attempting to archive an already-archived goal."""

    pass


class GoalNotArchivedError(GoalGlideError):
    """Raised when attempting to restore a goal that is not archived."""

    pass


class InvalidTagError(GoalGlideError):
    """Raised when a tag format is invalid."""

    pass
