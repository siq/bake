import optparse
import os
import sys
import textwrap
from ConfigParser import SafeConfigParser

from bake.environment import Environment
from bake.task import MultipleTasksError, Tasks, Task
from bake.util import import_source

BAKEFILES = ('bakefile', 'bakefile.py')
ENV_MODULES = 'BAKE_MODULES'

USAGE = 'Usage: bake [options] %s [param=value] ...'
DESCRIPTION = """
Useful information here.
"""

class OptionParser(optparse.OptionParser):
    options = (
        ('-d, --dryrun', 'run task(s) in dryrun mode'),
        ('-e, --env', 'contribute specified file to runtime environment'),
        ('-h, --help', 'display help on specified task'),
        ('-i, --interactive', 'run task(s) in interactive mode'),
        ('-m, --module', 'load tasks from specified module'),
        ('-n, --nosearch', 'do not search parent directories for bakefile'),
        ('-N, --nobakefile', 'do not load bakefile'),
        ('-p, --path', 'run task(s) under specified path'),
        ('-P, --pythonpath', 'add specified path to python path'),
        ('-q, --quiet', 'only display error messages'),
        ('-v, --verbose', 'display all log messages'),
    )

    def __init__(self):
        optparse.OptionParser.__init__(self, add_help_option=False)
        self.set_defaults(dryrun=False, help=False, interactive=False, nosearch=False,
            nobakefile=False, quiet=False, verbose=False)

        self.add_option('-d', '--dryrun', action='store_true', dest='dryrun')
        self.add_option('-e', '--env', action='append', dest='sources')
        self.add_option('-h', '--help', action='store_true', dest='help')
        self.add_option('-i', '--interactive', action='store_true', dest='interactive')
        self.add_option('-m', '--module', action='append', dest='modules')
        self.add_option('-n', '--nosearch', action='store_true', dest='nosearch')
        self.add_option('-N', '--nobaked', action='store_true', dest='nobaked')
        self.add_option('-p', '--path', dest='path')
        self.add_option('-P', '--pythonpath', action='append', dest='pythonpath')
        self.add_option('-q', '--quiet', action='store_true', dest='quiet')
        self.add_option('-v', '--verbose', action='store_true', dest='verbose')

    def error(self, msg):
        raise RuntimeError(msg)

    def generate_help(self):
        sections = [USAGE % '{task}', DESCRIPTION.strip()]

        length = 0
        for option, description in self.options:
            length = max(length, len(option))
        for name in Tasks.by_name.iterkeys():
            length = max(length, len(name))

        template = '  %%-%ds  %%s' % length
        indent = ' ' * (length + 4)

        options = []
        for option, description in self.options:
            options.append(template % (option, description))

        sections.append('Options:\n%s' % '\n'.join(options))
        for module, tasks in sorted(Tasks.by_module.iteritems()):
            entries = []
            for name, task in sorted(tasks.iteritems()):
                description = self._format_text(task.description, indent)
                entries.append(template % (name, description))
            sections.append('Tasks from %s:\n%s' % (module, '\n'.join(entries)))

        return '\n\n'.join(sections)

    def generate_task_help(self, task):
        sections = [USAGE % task.fullname]
        if task.notes:
            sections.append(self._format_text(task.notes))

        required = task.required_params
        optional = task.optional_params

        length = 0
        for container in (required, optional):
            for param in container.iterkeys():
                length = max(length, len(param))

        template = '  %%-%ds  %%s' % length
        indent = ' ' * (length + 4)

        if required:
            params = self._format_params(template, indent, required)
            sections.append('Required parameters:\n' + params)

        if optional:
            params = self._format_params(template, indent, optional)
            sections.append('Optional parameters:\n' + params)

        return '\n\n'.join(sections)

    def _format_params(self, template, indent, params):
        lines = []
        for param, description in sorted(params.iteritems()):
            lines.append(template % (param, self._format_text(description, indent)))
        return '\n'.join(lines)

    def _format_text(self, text, indent='', width=70):
        if text:
            return textwrap.fill(text, width, initial_indent=indent,
                subsequent_indent=indent).strip()
        else:
            return ''
            
class Runtime(object):
    """The bake runtime."""

    flags = ('dryrun', 'interactive', 'quiet', 'verbose')
    prefix = '[bake]'

    def __init__(self, environment=None, stream=sys.stdout, path=None, dryrun=False,
        interactive=False, quiet=False, verbose=False):

        self.dryrun = dryrun
        self.environment = Environment(environment or {})
        self.interactive = interactive
        self.path = path
        self.queue = []
        self.quiet = quiet
        self.stream = stream
        self.verbose = verbose

    def check(self, message, default=False):
        token = {True: 'y', False: 'n'}[default]
        message = '%s %s [%s] ' % (self.prefix, message, token)

        while True:
            response = raw_input(message) or token
            if response[0] == 'y':
                return True
            elif response[0] == 'n':
                return False

    def execute(self, task):
        self._reset_path()
        try:
            task.execute()
        except Exception:
            raise

        if task.status == task.COMPLETED:
            self.report('%s completed' % task.fullname)
            return True
        elif self.interactive:
            return self.check('%s failed; continue?' % task.fullname)
        else:
            self.report('%s failed' % task.fullname)
            return False

    def invoke(self, invocation):
        parser = OptionParser()
        try:
            options, arguments = parser.parse_args(invocation)
        except RuntimeError, exception:
            self.report(exception.args[0])
            return False

        for flag in self.flags:
            flagged = getattr(options, flag)
            if flagged:
                setattr(self, flag, True)

        if options.path:
            self.path = options.path
        if self.path:
            if self._reset_path() is False:
                return False
        else:
            self.path = os.getcwd()

        for addition in (options.pythonpath or []):
            sys.path.insert(0, addition)

        modules = set(options.modules or [])
        if ENV_MODULES in os.environ:
            modules.update(os.environ[ENV_MODULES].split(' '))
            
        for module in modules:
            if self._load_module(module) is False:
                return False

        if not options.nobakefile:
            bakefile = self._find_bakefile(options.nosearch)
            if bakefile:
                if self._load_bakefile(bakefile) is False:
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

    def report(self, message, *args, **params):
        message = message % args
        if not params.get('asis', False):
            message = '%s %s' % (self.prefix, message)
        if message[-1] != '\n':
            message += '\n'
        if self.stream:
            self.stream.write(message)
            self.stream.flush()

    def _display_help(self, parser, arguments):
        if not arguments:
            self.report(parser.generate_help(), asis=True)
            return

        task = self._find_task(arguments[0])
        if task and task is not True:
            self.report(parser.generate_task_help(task), asis=True)
            return True
        else:
            return task

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
            self.report('multiple tasks!!!')
            return False
        except KeyError:
            if self.interactive:
                return self.check('cannot find task %r; continue?' % name)
            else:
                self.report('cannot find task %r' % name)
                return False
        else:
            return task

    def _load_bakefile(self, path):
        try:
            source = import_source(path)
        except Exception, exception:
            if self.interactive:
                return self.check('failed to load %r; continue?' % path)
            else:
                self.report('failed to load %r' % path)
                return False

    def _load_module(self, module):
        try:
            __import__(module)
        except ImportError:
            if self.interactive:
                if not self.check('failed to load %r; continue?' % module):
                    return False
            else:
                self.report('failed to load %r' % module)
                return False

    def _parse_source(self, path):
        try:
            self.environment.parse(path)
        except RuntimeError, exception:
            if self.interactive:
                return self.check('%s; continue?' % exception.args[0])
            else:
                self.report(exception.args[0])
                return False
        except Exception, exception:
            if self.interactive:
                return self.check('failed to parse %s; continue?' % path)
            else:
                self.report('failed to parse %s' % path)
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
                    self.report('failed to changed path to %r; aborting' % path)
                    return False

def run():
    runtime = Runtime()
    if runtime.invoke(sys.argv[1:]) is False:
        runtime.report('aborted')
        sys.exit(1)
    else:
        sys.exit(0)
