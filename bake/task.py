from datetime import datetime
from textwrap import dedent
from types import FunctionType

from scheme import Structure, Text

from bake.environment import *
from bake.exceptions import *
from bake.util import call_with_supported_params, propagate_traceback

__all__ = ('Task', 'TaskError', 'parameter', 'requires', 'task')

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
            raise UnknownTaskError('no task named %r' % name)

class TaskMeta(type):
    def __new__(metatype, name, bases, namespace):
        task = type.__new__(metatype, name, bases, namespace)
        if not task.supported:
            return task

        parameters = {}
        for base in reversed(bases):
            inherited = getattr(base, 'parameters', None)
            if inherited:
                parameters.update(inherited)

        if task.parameters:
            parameters.update(task.parameters)

        task.parameters = parameters
        if task.name is None:
            return task

        task.configuration = {}
        for name, parameter in parameters.iteritems():
            parameter.name = '%s.%s' % (task.name, name)
            task.configuration[parameter.name] = parameter

        task.fullname = task.__name__
        if task.__module__ != '__main__':
            task.fullname = '%s.%s' % (task.__module__, task.__name__)

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

    configuration = None
    description = None
    implementation = None
    name = None
    notes = None
    parameters = None
    requires = []
    source = None
    supports_dryrun = False
    supports_interactive = False

    def __init__(self, runtime, independent=False):
        self.dependencies = set()
        self.environment = None
        self.exception = None
        self.finished = None
        self.independent = independent
        self.runtime = runtime
        self.started = None
        self.status = self.PENDING

    def __repr__(self):
        return '%s(status=%r)' % (type(self).__name__, self.status)

    def __getitem__(self, name):
        if not self.environment:
            raise RuntimeError()
        if name[:len(self.name)] != self.name:
            name = '%s.%s' % (self.name, name)
        return self.environment.find(name)

    def __setitem__(self, name, value):
        if not self.environment:
            raise RuntimeError()
        if name[:len(self.name)] != self.name:
            name = '%s.%s' % (self.name, name)
        self.environment.set(name, value)

    @property
    def duration(self):
        return '%0.03fs' % (self.finished - self.started).total_seconds()

    def execute(self, environment=None):
        runtime = self.runtime
        try:
            self.environment = self._prepare_environment(runtime, environment)
        except RequiredParameterError, exception:
            runtime.error('task requires parameter %r' % exception.args[0])
            self.status = self.FAILED
            return False

        if runtime.interactive and not self.supports_interactive:
            if not runtime.check('execute task?', True):
                self.status = self.SKIPPED

        if runtime.dryrun and not self.supports_dryrun:
            self.status = self.COMPLETED

        if self.status == self.PENDING:
            self._execute_task(runtime)

        duration = ''
        if runtime.timing:
            duration = ' (%s)' % self.duration
        
        if self.status == self.COMPLETED:
            runtime.report('task completed%s' % duration)
            return True
        elif self.status == self.SKIPPED:
            runtime.report('task skipped')
            return True
        elif runtime.interactive:
            return runtime.check('task failed%s; continue?' % duration)
        else:
            runtime.error('task failed%s' % duration)
            return False

    def finalize(self, runtime):
        pass

    def prepare(self, runtime):
        pass

    def _execute_task(self, runtime):
        self.started = datetime.now()
        try:
            self.prepare(runtime)
            call_with_supported_params(self.implementation or self.run,
                runtime=runtime, environment=self.environment)
            self.finalize(runtime)
        except RequiredParameterError, exception:
            runtime.error('task requires parameter %r' % exception.args[0])
            self.status = self.FAILED
        except TaskError, exception:
            runtime.error(exception.args[0])
            self.status = self.FAILED
        except Exception, exception:
            runtime.error('task raised exception', True)
            self.status = self.FAILED
        else:
            self.status = self.COMPLETED
        finally:
            self.finished = datetime.now()

    def _prepare_environment(self, runtime, environment):
        environment = environment or runtime.environment
        if not self.configuration:
            return environment

        overlay = Environment()
        for name, parameter in self.configuration.iteritems():
            if runtime.strict:
                value = environment.get(name)
            else:
                value = environment.find(name)
            if value is not None:
                overlay.set(name, parameter.process(value, serialized=True))
                runtime.info('%s = %r' % (name, value))
            elif parameter.default is not None:
                overlay.set(name, parameter.get_default())
            elif parameter.required:
                raise RequiredParameterError(name)

        return environment.overlay(overlay)

def parameter(name, field=None):
    if not field:
        field = Text(nonnull=True)

    def decorator(function):
        try:
            function.parameters[name] = field
        except AttributeError:
            function.parameters = {name: field}
        return function
    return decorator

def requires(*args):
    def decorator(function):
        try:
            function.requires.update(args)
        except AttributeError:
            function.requires = set(args)
        return function
    return decorator

def task(name=None, description=None, supports_dryrun=False, supports_interactive=False):
    def decorator(function):
        return type(function.__name__, (Task,), {
            '__doc__': function.__doc__ or '',
            'name': name or function.__name__,
            'description': description,
            'implementation': staticmethod(function),
            'supports_dryrun': supports_dryrun,
            'supports_interactive': supports_interactive,
            'parameters': getattr(function, 'parameters', None),
            'requires': getattr(function, 'requires', []),
        })
    return decorator
