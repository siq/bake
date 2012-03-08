import optparse
import os
import sys
import textwrap
from ConfigParser import SafeConfigParser
from datetime import datetime
from operator import attrgetter
from traceback import format_exc

from bake.environment import Environment
from bake.path import path
from bake.process import Process
from bake.task import MultipleTasksError, Tasks, Task
from bake.util import import_object, import_source

BAKEFILES = ('bakefile', 'bakefile.py')
ENV_MODULES = 'BAKE_MODULES'

USAGE = 'Usage: %s [options] %s [param=value] ...'
DESCRIPTION = """
Useful information here.
"""

class OptionParser(optparse.OptionParser):
    options = (
        ('-c, --cache FILE', 'use specified file as build cache'),
        ('-C, --no-cache', 'ignore build cache'),
        ('-d, --dryrun', 'run tasks in dry-run mode'),
        ('-e, --env FILE', 'populate runtime environment with specified file'),
        ('-h, --help [TASK]', 'display help on specified task'),
        ('-i, --interactive', 'run tasks in interactive mode'),
        ('-l, --log FILE', 'log messages to specified file'),
        ('-m, --module MODULE', 'load tasks from specified module'),
        ('-n, --nosearch', 'do not search parent directories for bakefile'),
        ('-N, --nobakefile', 'do not use bakefile'),
        ('-p, --path PATH', 'run tasks under specified path'),
        ('-P, --pythonpath PATH', 'add specified path to python path'),
        ('-q, --quiet', 'only log error messages'),
        ('-t, --timestamps', 'include timestamps on all log messages'),
        ('-T, --timing', 'display timing information for each task'),
        ('-v, --verbose', 'log all messages'),
        ('-V, --version', 'display version information'),
    )

    def __init__(self):
        optparse.OptionParser.__init__(self, add_help_option=False)
        self.set_defaults(dryrun=False, help=False, interactive=False, nosearch=False,
            nobakefile=False, quiet=False, verbose=False, version=False, nocache=False,
            timing=False)

        self.add_option('-c', '--cache', dest='cache')
        self.add_option('-C', '--no-cache', action='store_true', dest='nocache')
        self.add_option('-d', '--dryrun', action='store_true', dest='dryrun')
        self.add_option('-e', '--env', action='append', dest='sources')
        self.add_option('-h', '--help', action='store_true', dest='help')
        self.add_option('-i', '--interactive', action='store_true', dest='interactive')
        self.add_option('-l', '--log', dest='logfile')
        self.add_option('-m', '--module', action='append', dest='modules')
        self.add_option('-n', '--nosearch', action='store_true', dest='nosearch')
        self.add_option('-N', '--nobaked', action='store_true', dest='nobaked')
        self.add_option('-p', '--path', dest='path')
        self.add_option('-P', '--pythonpath', action='append', dest='pythonpath')
        self.add_option('-q', '--quiet', action='store_true', dest='quiet')
        self.add_option('-t', '--timestamps', action='store_true', dest='timestamps')
        self.add_option('-T', '--timing', action='store_true', dest='timing')
        self.add_option('-v', '--verbose', action='store_true', dest='verbose')
        self.add_option('-V', '--version', action='store_true', dest='version')

    def error(self, msg):
        raise RuntimeError(msg)

    def generate_help(self, runtime):
        sections = [USAGE % (runtime.executable, '{task}'), DESCRIPTION.strip()]

        length = 0
        for option, description in self.options:
            length = max(length, len(option))
        for name in Tasks.by_name.iterkeys():
            length = max(length, len(name))

        template = '  %%-%ds    %%s' % length
        indent = ' ' * (length + 6)

        options = []
        for option, description in self.options:
            options.append(template % (option, description))

        sections.append('Options:\n%s' % '\n'.join(options))
        for source, tasks in sorted(Tasks.by_source.iteritems()):
            entries = []
            for name, task in sorted(tasks.iteritems()):
                description = self._format_text(task.description, indent)
                entries.append(template % (name, description))
            sections.append('Tasks from %s:\n%s' % (source, '\n'.join(entries)))

        return '\n\n'.join(sections)

    def generate_task_help(self, runtime, task):
        sections = [USAGE % (runtime.executable, task.name)]
        if task.notes:
            sections.append(self._format_text(task.notes))

        required = []
        optional = []

        length = 0
        for param in task.params:
            length = max(length, len(param.name))
            if param.required:
                required.append(param)
            else:
                optional.append(param)

        template = '  %%-%ds    %%s' % length
        indent = ' ' * (length + 6)

        if required:
            params = self._format_params(template, indent, required)
            sections.append('Required parameters:\n' + params)

        if optional:
            params = self._format_params(template, indent, optional)
            sections.append('Optional parameters:\n' + params)

        return '\n\n'.join(sections)

    def _format_params(self, template, indent, params):
        lines = []
        for param in sorted(params, key=attrgetter('name')):
            lines.append(template % (param.name,
                self._format_text(param.description, indent)))
        return '\n'.join(lines)

    def _format_text(self, text, indent='', width=70):
        if text:
            return textwrap.fill(text, width, initial_indent=indent,
                subsequent_indent=indent).strip()
        else:
            return ''

class Runtime(object):
    """The bake runtime."""

    flags = ('dryrun', 'interactive', 'nobakefile', 'nocache', 'nosearch',
        'quiet', 'timestamps', 'timing', 'verbose')

    def __init__(self, executable='bake', environment=None, stream=sys.stdout, logger=None, **params):
        self.context = []
        self.environment = Environment(environment or {})
        self.executable = executable
        self.logger = logger
        self.queue = []
        self.stream = stream

        self.cache = params.get('cache', None)
        self.dryrun = params.get('dryrun', False)
        self.interactive = params.get('interactive', False)
        self.logfile = params.get('logfile', None)
        self.nobakefile = params.get('nobakefile', False)
        self.nocache = params.get('nocache', False)
        self.nosearch = params.get('nosearch', False)
        self.path = params.get('path', None)
        self.quiet = params.get('quiet', False)
        self.timestamps = params.get('timestamps', False)
        self.timing = params.get('timing', False)
        self.verbose = params.get('verbose', False)

    def check(self, message, default=False):
        token = {True: 'y', False: 'n'}[default]
        if self.context:
            message = '[%s] %s' % (self.context[-1].name, message)

        message = '%s [%s] ' % (message, token)
        while True:
            response = raw_input(message) or token
            if response[0] == 'y':
                return True
            elif response[0] == 'n':
                return False

    def execute(self, task):
        self.context.append(task)
        try:
            self._reset_path()
            try:
                task.execute(self)
            except Exception:
                self.report('task raised uncaught exception', True, True)
                return False

            duration = ''
            if self.timing:
                duration = ' (%s)' % task.duration

            if task.status == task.COMPLETED:
                self.report('task completed%s' % duration)
                return True
            elif task.status == task.SKIPPED:
                self.report('task skipped', True)
                return True
            elif self.interactive:
                return self.check('task failed%s; continue?' % duration)
            else:
                self.report('task failed%s' % duration, True)
                return False
        finally:
            self.context.pop()

    def invoke(self, invocation):
        parser = OptionParser()
        try:
            options, arguments = parser.parse_args(invocation)
        except RuntimeError, exception:
            self.report(exception.args[0], True)
            return False

        if options.version:
            return self._display_version()

        for flag in self.flags:
            flagged = getattr(options, flag, False)
            if flagged:
                setattr(self, flag, True)

        if options.logfile:
            self.logfile = options.logfile

        for addition in (options.pythonpath or []):
            sys.path.insert(0, addition)
        sys.path.insert(0, '.')

        if options.path:
            self.path = options.path
        if self.path:
            if self._reset_path() is False:
                return False
        else:
            self.path = os.getcwd()

        modules = set(options.modules or [])
        if ENV_MODULES in os.environ:
            modules.update(os.environ[ENV_MODULES].split(' '))

        for module in modules:
            if self._load_target(module) is False:
                return False
        
        if not self.nobakefile:
            bakefile = self._find_bakefile(options.nosearch)
            if bakefile:
                if self._load_target(bakefile) is False:
                    return False

        if options.help:
            return self._display_help(parser, arguments)

        for source in (options.sources or []):
            if self._parse_source(source) is False:
                return False

        for argument in arguments:
            if '=' in argument:
                self.environment.parse_pair(argument)
            else:
                task = self._find_task(argument)
                if task and task is not True:
                    self.queue.append(task(self))
                elif task is False:
                    return False

        if not self.queue:
            self.report('no tasks specified')
            return True

        for task in self.queue:
            self.execute(task)

    def report(self, message, importance=None, exception=False, asis=False):
        if not message:
            return
        if (self.quiet and importance is not True) or (importance is False and not self.verbose):
            return

        if self.context and not asis:
            message = '[%s] %s' % (self.context[-1].name, message)
        if self.timestamps:
            message = '%s %s' % (datetime.now().strftime('%Y-%m-%dT%H:%M:%S'), message)
        if message[-1] != '\n':
            message += '\n'
        if exception:
            message += format_exc()

        self.stream.write(message)
        self.stream.flush()

    def shell(self, cmdline, data=None, environ=None, shell=False, timeout=None):
        process = Process(cmdline, environ, shell)
        process.run(self, data, timeout)
        return process

    def _display_help(self, parser, arguments):
        if not arguments:
            self.report(parser.generate_help(self))
            return

        task = self._find_task(arguments[0])
        if task and task is not True:
            self.report(parser.generate_task_help(self, task))
            return True
        else:
            return task

    def _display_version(self):
        self.report('bake 1.0.a1')

    def _find_bakefile(self, nosearch=False):
        path = self.path
        for bakefile in BAKEFILES:
            candidate = os.path.join(path, bakefile)
            if os.path.exists(candidate):
                return candidate

        if nosearch:
            return

        path = os.path.dirname(path)
        while True:
            for bakefile in BAKEFILES:
                candidate = os.path.join(path, bakefile)
                if os.path.exists(candidate):
                    return candidate

            up = os.path.dirname(path)
            if up != path:
                path = up
            else:
                break

    def _find_task(self, name):
        try:
            task = Tasks.get(name)
        except MultipleTasksError, exception:
            self.report('multiple tasks!!!', True)
            return False
        except KeyError:
            if self.interactive:
                return self.check('cannot find task %r; continue?' % name)
            else:
                self.report('cannot find task %r' % name, True)
                return False
        else:
            return task

    def _load_target(self, target):
        environment = None
        try:
            if target[-3:] == '.py':
                Tasks.current_source = path(target).relpath()
                try:
                    namespace = import_source(target)
                finally:
                    Tasks.current_source = None
                environment = namespace.get('environment')
            else:
                module = import_object(target)
                environment = getattr(module, 'environment', None)
        except Exception:
            if self.interactive:
                if not self.check('failed to load %r; continue?' % target):
                    return False
            else:
                self.report('failed to load %r' % target, True, True)
                return False

        if environment and isinstance(environment, dict):
            self.environment.merge(environment)

    def _parse_source(self, path):
        try:
            self.environment.parse(path)
        except RuntimeError, exception:
            if self.interactive:
                return self.check('%s; continue?' % exception.args[0])
            else:
                self.report(exception.args[0], True)
                return False
        except Exception, exception:
            if self.interactive:
                return self.check('failed to parse %s; continue?' % path)
            else:
                self.report('failed to parse %r' % path, True, True)
                return False

    def _reset_path(self):
        path = self.path
        if path != os.getcwd():
            try:
                os.chdir(path)
            except OSError, exception:
                if self.interactive:
                    return self.check('failed to change path to %r; continue?' % path)
                else:
                    self.report('failed to changed path to %r' % path, True)
                    return False

def run():
    runtime = Runtime(os.path.basename(sys.argv[0]))
    exitcode = 0
    if runtime.invoke(sys.argv[1:]) is False:
        runtime.report('aborted', True)
        exitcode = 1

    sys.exit(exitcode)
