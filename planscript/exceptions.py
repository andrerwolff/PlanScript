class ParseError(Exception):
    pass

class ValidationError(Exception):
    pass


class SchedulingError(Exception):
    """The project cannot produce the requested schedule."""
    pass

class BudgetingError(Exception):
    pass