from datetime import datetime
from textwrap import dedent

from bake.util import propagate_traceback

class MultipleTasksError(Exception):
    pass

class Tasks(object):
    by_fullname = {}
    by_name = {}
    by_module = {}

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
        task = type.__new__(metatype, name, bases, namespace)
        if task.name is None:
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

        task.module = task.__module__
        if task.module in Tasks.by_module:
            Tasks.by_module[task.module][task.name] = task
        else:
            Tasks.by_module[task.module] = {task.name: task}

        docstring = task.__doc__
        if docstring and not task.notes:
            task.notes = dedent(docstring.strip())

        return task

class Task(object):
    """A bake task."""

    __metaclass__ = TaskMeta

    COMPLETED = 'completed'
    FAILED = 'failed'
    PENDING = 'pending'
    
    name = None
    module = None
    fullname = None
    description = None
    notes = None
    implementation = None

    supports_dryrun = False
    supports_interactive = False
    required_params = {}
    optional_params = {}

    def __init__(self, runtime):
        self.exception = None
        self.finished = None
        self.runtime = runtime
        self.started = None
        self.status = self.PENDING

    def execute(self):
        self.started = datetime.now()

        implementation = self.implementation or self.run
        try:
            implementation(self.runtime, self.runtime.environment)
        except Exception, exception:
            self.exception = propagate_traceback(exception)
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

class DumpEnvironment(Task):
    name = 'dump-environment'
    description = 'dumps the runtime environment'

    required_params = {
        'bundle': 'this is a test of the emergency line wrapping system, because in the end of this line should be properly wrapped',
        'indent': 'more'
    }

    optional_params = {
        'fff': 'rrr'
    }


    
    def run(self, runtime, environment):
        runtime.report(environment.dump(), asis=True)

@task()
def dump(runtime, environment):
    "testing"
    runtime.report(environment.dump(), asis=True)
