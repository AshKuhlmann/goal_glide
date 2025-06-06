class GoalNotFoundError(ValueError):
    pass


class GoalAlreadyArchivedError(ValueError):
    pass


class GoalNotArchivedError(ValueError):
    pass


class EmptyThoughtError(ValueError):
    pass


class GoalDoesNotExistError(ValueError):
    pass
