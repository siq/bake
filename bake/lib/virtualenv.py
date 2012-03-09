from bake.path import path
from bake.task import *

try:
    import virtualenv
except ImportError:
    virtualenv = None

class VirtualEnvTask(Task):
    supported = bool(virtualenv)

class CreateVirtualEnv(VirtualEnvTask):
    name = 'virtualenv:create'
    description = 'creates a virtual environment'
    params = [
        param('virtualenv.dir', 'path to destination directory', required=True),
        param('virtualenv.nositepackages', '--no-site-packages', default=False),
        param('virtualenv.script', 'path to virtualenv script', default='virtualenv'),
    ]

    def run(self, runtime, environment):
        options = [environment['virtualenv.script']]
        if environment['virtualenv.nositepackages']:
            options.append('--no-site-packages')

        options.append(environment['virtualenv.dir'])
        runtime.shell(options)
