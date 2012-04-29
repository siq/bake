from __future__ import absolute_import

from bake.path import Path, path
from bake.task import *
from scheme import Boolean, Text

try:
    import alembic
except ImportError:
    alembic = None
else:
    from alembic import command

class AlembicTask(Task):
    supported = bool(alembic)
    parameters = {
        'path': Path(description='path to migrations directory', required=True),
        'url': Text(description='sqlalchemy url', required=True),
    }

    @property
    def config(self):
        from alembic.config import Config
        config = Config()
        config.set_main_option('script_location', str(self['path']))
        config.set_main_option('sqlalchemy.url', self['url'])
        return config

class CreateRevision(AlembicTask):
    name = 'alembic.revision'
    description = 'create an alembic revision'
    parameters = {
        'autogenerate': Boolean(description='autogenerate revision', default=False),
        'title': Text(description='short title for revision'),
    }

    def run(self, runtime):
        command.revision(self.config, message=self['title'], autogenerate=self['autogenerate'])

class Downgrade(AlembicTask):
    name = 'alembic.downgrade'
    description = 'downgrade to an earlier version of the schema'
    parameters = {
        'revision': Text(description='revision to upgrade to', default='head'),
        'sql': Boolean(description='generate sql instead of upgrading database', default=False),
    }

    def run(self, runtime):
        command.downgrade(self.config, revision=self['revision'], sql=self['sql'])

class Initialize(AlembicTask):
    name = 'alembic.init'
    description = 'initialize an alembic migrations directory'
    
    def run(self, runtime):
        command.init(self.config, str(self['path']))

class ShowBranches(AlembicTask):
    name = 'alembic.branches'
    description = 'show un-spliced branch points'

    def run(self, runtime):
        command.branches(self.config)

class ShowCurrent(AlembicTask):
    name = 'alembic.current'
    description = 'show current revision'

    def run(self, runtime):
        command.current(self.config)

class ShowHistory(AlembicTask):
    name = 'alembic.history'
    description = 'show changeset history'

    def run(self, runtime):
        command.history(self.config)

class Upgrade(AlembicTask):
    name = 'alembic.upgrade'
    description = 'upgrade to a later version of the schema'
    parameters = {
        'revision': Text(description='revision to upgrade to', default='head'),
        'sql': Boolean(description='generate sql instead of upgrading database', default=False),
    }

    def run(self, runtime):
        command.upgrade(self.config, revision=self['revision'], sql=self['sql'])

