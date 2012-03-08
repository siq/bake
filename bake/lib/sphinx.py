from bake.path import path
from bake.task import *

try:
    import sphinx
except ImportError:
    sphinx = None

class BuildDocs(Task):
    supported = bool(sphinx)
    params = [
        param('sphinx.sourcedir', 'path to source directory for docs', default='docs'),
        param('sphinx.outdir', 'path to output directory for generated docs'),
        param('sphinx.cachedir', 'path to cache directory for doctrees'),
        param('sphinx.script', 'path to sphinx-build script', default='sphinx-build'),
    ]

    def _collate_options(self, environment, options=None):
        sourcedir = path(environment['sphinx.sourcedir'])
        if not sourcedir.exists():
            raise TaskError("source directory '%s' does not exist" % sourcedir)

        if not environment['sphinx.outdir']:
            environment['sphinx.outdir'] = sourcedir / 'html'
        if not environment['sphinx.cachedir']:
            environment['sphinx.cachedir'] = sourcedir / '_doctrees'

        options = options or []
        options.append('-d %s' % environment['sphinx.cachedir'])
        options.append('%s %s' % (sourcedir, environment['sphinx.outdir']))
        return options

class BuildHtml(BuildDocs):
    name = 'sphinx:html'
    description = 'build html documentation using sphinx'
    params = [
        param('sphinx.nocache', 'do not use cached environment', default=False),
    ]

    def run(self, runtime, environment):
        options = self._collate_options(environment, ['-b html'])
        if environment['sphinx.nocache']:
            options.insert(0, '-E')

        invocation = '%s %s' % (environment['sphinx.script'], ' '.join(options))
        runtime.shell(invocation)

class CleanDocs(BuildDocs):
    name = 'sphinx:clean'
    description = 'cleans (deletes) generated documentation'
    
    def run(self, runtime, environment):
        self._collate_options(environment)
        path(environment['sphinx.outdir']).rmtree()
        path(environment['sphinx.cachedir']).rmtree()
