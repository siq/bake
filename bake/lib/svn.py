from bake.path import path
from bake.task import *
from scheme import *

class SubversionTask(Task):
    parameters = {
        'binary': Text(description='path to svn binary', default='svn'),
        'revision': Text(description='revision'),
        'username': Text(description='username for authentication'),
        'password': Text(description='password for authentication'),
        'noauthcache': Boolean(description='do not cache authentication', default=False),
    }

    def _collate_options(self):
        options = []
        if self['noauthcache']:
            options.append('--no-auth-cache')
        if self['revision']:
            options.append('-r %s' % self['revision'])
        if self['username']:
            options.append('--username "%s"' % self['username'])
        if self['password']:
            options.append('--password "%s"' % self['password'])
        return options

class SubversionCheckout(SubversionTask):
    name = 'svn.checkout'
    description = 'checks out a subversion repository'
    parameters = {
        'path': Text(description='path to destination directory'),
        'url': Text(description='url of subversion repository', required=True),
    }

    def run(self, runtime):
        options = [self['binary'], 'co'] + self._collate_options() + [self['url']]
        if self['path']:
            options.append(self['path'])
        runtime.shell(options)

class SubversionExport(SubversionTask):
    name = 'svn.export'
    description = 'exports a subversion repository'
    parameters = {
        'path': Text(description='path to destination directory'),
        'url': Text(description='url of subversion repository', required=True),
    }

    def run(self, runtime):
        options = [self['binary'], 'export'] + self._collate_options() + [self['url']]
        if self['path']:
            options.append(self['path'])
        runtime.shell(options)
