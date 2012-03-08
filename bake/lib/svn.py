from bake.path import path
from bake.task import *

class SubversionTask(Task):
    params = [
        param('svn.binary', 'path to svn binary', default='svn'),
        param('svn.revision', 'subversion revision'),
        param('svn.password', 'password for svn operation'),
        param('svn.username', 'username for svn operation'),
    ]

    def _collate_options(self, environment):
        options = []
        if environment['svn.revision']:
            options.append('-r %s' % environment['svn.revision'])
        if environment['svn.username']:
            options.append('--username "%s"' % environment['svn.username'])
        if environment['svn.password']:
            options.append('--password "%s"' % environment['svn.password'])
        return options

class SubversionCheckout(SubversionTask):
    name = 'svn:checkout'
    description = 'checks out a subversion repo'
    params = [
        param('svn.path', 'path to destination directory'),
        param('svn.url', 'url to subversion repo', required=True),
    ]

    def run(self, runtime, environment):
        options = [environment['svn.binary'], 'co'] + self._collate_options(environment)
        options.append(environment['svn.url'])

        if environment['svn.path']:
            options.append(environment['svn.path'])

        runtime.shell(options)

class SubversionExport(SubversionTask):
    name = 'svn:export'
    description = 'exports a subversion repo'
    params = [
        param('svn.path', 'path to destination directory'),
        param('svn.url', 'url to subversion repo', required=True),
    ]

    def run(self, runtime, environment):
        options = [environment['svn.binary'], 'export'] + self._collate_options(environment)
        options.append(environment['svn.url'])

        if environment['svn.path']:
            options.append(environment['svn.path'])

        runtime.shell(options)

class SubversionUpdate(SubversionTask):
    name = 'svn:update'
    description = 'updates a subversion checkout'
    params = [
        param('svn.path', 'path to destination directory'),
    ]

    def run(self, runtime, environment):
        options = [environment['svn.binary'], 'up'] + self._collate_options(environment)
        if environment['svn.path']:
            options.append(environment['svn.path'])

        runtime.shell(options)
