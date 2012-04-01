class BakeError(Exception):
    """A bake error."""

class RequiredParameterError(BakeError):
    """A required parameter was not specified."""

class TaskError(BakeError):
    """A task error."""

class MultipleTasksError(TaskError):
    """Multiple tasks with the same name exist."""

class UnknownTaskError(TaskError):
    """An unknown task was requested."""
