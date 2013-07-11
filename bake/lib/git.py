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

    def get_file(self, filename, commit='HEAD'):
        filename = '%s:%s' % (commit, filename)
        return self.execute(['show', filename]).stdout

    def create_tag(self, tag, message):
        self.execute(['tag', '-a', tag, '-m', '"%s"' % message])

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
