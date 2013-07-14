from scheme import *

from bake.path import path
from bake.process import Process
from bake.task import *

class Repository(object):
    """A git repository."""

    def __init__(self, root, runtime=None, binary='git'):
        if not isinstance(root, path):
            root = path(root)

        self.binary = binary
        self.root = root.expanduser().abspath()
        self.runtime = runtime

    @property
    def tags(self):
        return self.execute(['tag']).stdout.strip().split('\n')

    def checkout(self, commit):
        self.execute(['checkout', commit])

    def clone(self, url):
        self.execute(['clone', url, str(self.root)], False, True)

    def create_tag(self, tag, message):
        self.execute(['tag', '-a', tag, '-m', '"%s"' % message])

    def execute(self, tokens, cwd=True, passthrough=False, root=None, passive=False):
        root = root or self.root
        if cwd:
            cwd = str(root)
        else:
            cwd = None

        process = Process([self.binary] + tokens)
        if passthrough and self.runtime and self.runtime.verbose:
            process.merge_output = True
            process.passthrough = True

        returncode = process(runtime=self.runtime, cwd=cwd)
        if passive or returncode == 0:
            return process
        else:
            raise RuntimeError(process.stderr or '')

    def get_current_branch(self):
        process = self.execute(['rev-parse', '--abbrev-ref', 'HEAD'])
        return process.stdout.strip()

    def get_current_hash(self):
        process = self.execute(['log', '-1', '--pretty=format:%H'])
        return process.stdout.strip()

    def get_file(self, filename, commit='HEAD'):
        filename = '%s:%s' % (commit, filename)
        return self.execute(['show', filename]).stdout

    def get_status(self):
        process = self.execute(['status', '-s'], passive=True)
        if process.returncode == 0:
            return process.stdout

    def is_repository(self):
        return (self.root / '.git').exists()

    def is_on_master(self):
        return (self.get_current_branch() == 'master')

    def pull(self, fastforward_only=True, passthrough=True):
        tokens = ['pull']
        if fastforward_only:
            tokens.append('--ff-only')

        process = self.execute(tokens, passthrough=passthrough)
        if not passthrough:
            return process.stdout

class GitTask(Task):
    parameters = {
        'binary': Text(description='path to git binary', default='git'),
    }

class GitClone(GitTask):
    name = 'git.clone'
    description = 'clones a git repository'
    parameters = {
        'path': Text(description='path to destination directory'),
        'url': Text(description='url of git repository', required=True),
    }

    def run(self, runtime):
        options = [self['binary'], 'clone', self['url']]
        if self['path']:
            options.append(self['path'])
        runtime.shell(options)
