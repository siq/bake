from bake.task import *
from scheme import *

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
