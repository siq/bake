from datetime import datetime
from textwrap import dedent

from bake.util import call_with_supported_params, propagate_traceback

__all__ = ('Task', 'TaskError', 'param', 'task')

class param(object):
    """A task parameter."""

    def __init__(self, name, description=None, required=False, default=None):
        self.default = default
        self.description = description
        self.name = name
        self.required = required

class TaskError(Exception):
    pass

class MultipleTasksError(Exception):
    pass

class Tasks(object):
    by_fullname = {}
    by_name = {}
    by_source = {}
    current_source = None

    @classmethod
    def get(cls, name):
        task = cls.by_fullname.get(name)
        if task:
            return task

        candidate = cls.by_name.get(name)
        if isinstance(candidate, set):
            raise MultipleTasksError(candidate)
        elif candidate:
            return candidate
        else:
            raise KeyError(name)

class TaskMeta(type):
    def __new__(metatype, name, bases, namespace):
        declared_params = namespace.pop('params', [])
        task = type.__new__(metatype, name, bases, namespace)

        params = {}
        for base in reversed(bases):
            inherited_params = getattr(base, 'params', None)
            if inherited_params:
                for param in inherited_params:
                    params[param.name] = param

        for param in declared_params:
            params[param.name] = param

        task.params = params.values()
        if task.name is None or not task.supported:
            return task

        task.fullname = task.name
        if task.__module__ != '__main__':
            task.fullname = '%s.%s' % (task.__module__, task.name)

        Tasks.by_fullname[task.fullname] = task
        if task.name in Tasks.by_name:
            value = Tasks.by_name[task.name]
            if isinstance(value, set):
                value.add(task)
            else:
                Tasks.by_name[task.name] = set([value, task])
        else:
            Tasks.by_name[task.name] = task

        source = Tasks.current_source
        if source is None:
            source = task.__module__
        if source in Tasks.by_source:
            Tasks.by_source[source][task.name] = task
        else:
            Tasks.by_source[source] = {task.name: task}

        docstring = task.__doc__
        if docstring and not task.notes:
            task.notes = dedent(docstring.strip())

        return task

class Task(object):
    """A bake task."""

    __metaclass__ = TaskMeta
    supported = True

    COMPLETED = 'completed'
    FAILED = 'failed'
    PENDING = 'pending'
    SKIPPED = 'skipped'

    description = None
    fullname = None
    implementation = None
    name = None
    notes = None
    params = []
    requires = []
    source = None
    supports_dryrun = False
    supports_interactive = False

    def __init__(self, runtime):
        self.exception = None
        self.finished = None
        self.runtime = runtime
        self.started = None
        self.status = self.PENDING

    @property
    def duration(self):
        return '%0.03fs' % (self.finished - self.started).total_seconds()

    def execute(self, runtime):
        environment = runtime.environment
        for param in self.params:
            try:
                value = environment[param.name]
            except ValueError:
                runtime.report('task cannot run due to malformed value for %r' % param.name, True)
                self.status = self.FAILED
                return

            if value is None:
                if param.default is not None:
                    environment[param.name] = param.default
                elif param.required:
                    runtime.report('task requires parameter %r' % param.name, True)
                    self.status = self.FAILED
                    return

        implementation = self.implementation or self.run
        if runtime.dryrun and not self.supports_dryrun:
            self.status = self.COMPLETED
            return
        if runtime.interactive and not self.supports_interactive:
            if not runtime.check('execute task?', True):
                self.status = self.SKIPPED
                return

        self.started = datetime.now()
        try:
            call_with_supported_params(implementation, runtime=runtime, environment=environment)
        except TaskError, exception:
            runtime.report(exception.args[0], True)
            self.status = self.FAILED
        except Exception, exception:
            runtime.report('task raised exception', True, True)
            self.status = self.FAILED
        else:
            self.status = self.COMPLETED

        self.finished = datetime.now()

    def run(self, runtime, environment):
        raise NotImplementedError()

def task(name=None, description=None, supports_dryrun=False, supports_interactive=False):
    def decorator(function):
        return type(function.__name__, (Task,), {
            '__doc__': function.__doc__ or '',
            'name': name or function.__name__.lower().replace('_', '-').strip('-'),
            'description': description,
            'implementation': staticmethod(function),
            'supports_dryrun': supports_dryrun,
            'supports_interactive': supports_interactive,
        })
    return decorator
