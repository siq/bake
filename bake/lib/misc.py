from bake.task import *

class DumpEnvironment(Task):
    name = 'bake:env'
    description = 'dumps the runtime environment'

    def run(self, runtime, environment):
        runtime.report(environment.dump(), True)
