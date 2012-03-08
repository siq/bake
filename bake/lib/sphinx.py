import os

from bake.task import Task, param
from bake.util import shell

try:
    import sphinx
except ImportError:
    sphinx = None

class BuildDocs(Task):
    supported = bool(sphinx)

    def _collate_options(self, environment, options=None):
        sourcedir = environment['sphinx.sourcedir']
        if not environment['sphinx.outdir']:
            environment['sphinx.outdir'] = os.path.join(sourcedir, 'html')
        if not environment['sphinx.cachedir']:
            environment['sphinx.cachedir'] = os.path.join(sourcedir, '_doctrees')

        options = options or []
        if environment['sphinx.nocache']:
            options.append('-E')

        options.append('-d %s' % environment['sphinx.cachedir'])
        options.append('%s %s' % (sourcedir, environment['sphinx.outdir']))
        return options

class BuildHtml(BuildDocs):
    name = 'sphinx:html'
    description = 'build html documentation using sphinx'
    params = [
        param('sphinx.sourcedir', 'path to source directory for docs', default='docs'),
        param('sphinx.outdir', 'path to output directory for generated html'),
        param('sphinx.cachedir', 'path to cache directory for doctrees'),
        param('sphinx.nocache', 'do not use cached environment', default=False),
        param('sphinx.script', 'path to sphinx-build script', default='sphinx-build'),
    ]

    def run(self, runtime, environment):
        options = self._collate_options(environment, ['-b html'])
        invocation = '%s %s' % (environment['sphinx.script'], ' '.join(options))

        shell(invocation)
