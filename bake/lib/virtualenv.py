#from __future__ import absolute_import

from bake.path import *
from bake.task import *
from scheme import *

try:
    import virtualenv
except ImportError:
    virtualenv = None

class VirtualEnvTask(Task):
    supported = bool(virtualenv)

class CreateVirtualEnv(VirtualEnvTask):
    name = 'virtualenv.create'
    description = 'creates a virtual environment'
    parameters = {
        'distribute': Boolean(description='use distribute', default=True),
        'executable': Text(description='path to virtualenv script', default='virtualenv'),
        'isolated': Boolean(description='isolate from site packages', default=False),
        'path': Path(description='path to destination directory', required=True),
    }

    def run(self, runtime):
        options = [self['executable']]
        if self['distribute']:
            options.append('--distribute')
        if self['isolated']:
            options.append('--no-site-packages')

        options.append(self['path'])
        runtime.shell(options)
