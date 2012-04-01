from bake.path import Path, path
from bake.task import *
from scheme import Boolean, Text

try:
    import sphinx
except ImportError:
    sphinx = None

class SphinxTask(Task):
    supported = bool(sphinx)
    parameters = {
        'binary': Text(description='path to sphinx binary', default='sphinx-build'),
        'cachedir': Path(description='path to cache directory for doctrees'),
        'outdir': Path(description='path to output directory for generated docs'),
        'sourcedir': Path(description='path to source directory', default=path('docs')),
        'nocache': Boolean(description='do not use cached environment', default=False),
    }

    def _collate_options(self, options=None):
        sourcedir = self['sourcedir']
        if not sourcedir.exists():
            raise TaskError("source directory '%s' does not exist" % sourcedir)

        if not self['cachedir']:
            self['cachedir'] = sourcedir / '_doctrees'
        if not self['outdir']:
            self['outdir'] = sourcedir / 'html'

        options = options or []
        options += ['-d %s' % self['cachedir'], str(sourcedir), str(self['outdir'])]
        return options

class BuildHtml(SphinxTask):
    name = 'sphinx.html'
    description = 'build html documentation using sphinx'

    def run(self, runtime):
        options = self._collate_options([self['binary'], '-b html'])
        runtime.shell(' '.join(options))

class CleanDocs(SphinxTask):
    name = 'sphinx.clean'
    description = 'cleans (deletes) generated documentation'

    def run(self, runtime):
        self._collate_options()
        self['outdir'].rmtree()
        self['cachedir'].rmtree()
