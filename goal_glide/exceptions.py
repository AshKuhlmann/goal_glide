class GoalNotFoundError(ValueError):
    pass


class GoalAlreadyArchivedError(ValueError):
    pass


class GoalNotArchivedError(ValueError):
    pass


class InvalidTagError(ValueError):
    pass
