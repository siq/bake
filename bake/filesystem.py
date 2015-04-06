import tarfile

from bake.path import path

class Collation(object):
    def __init__(self, root, runtime=None):
        if not isinstance(root, path):
            root = path(root)

        self.root = root.abspath()
        if runtime: # added for debugging purposes
            self.runtime = runtime
        else:
            self.runtime = None
        self.collate()

    @property
    def filepaths(self):
        return list(sorted(self.files.keys()))

    def collate(self):
        self.directories = [str(self.root)]
        self.files = {}

        for subject in self.root.walk():
            subject = subject.abspath()
            if subject.isdir():
                if self.runtime:
                    self.runtime.report('filesystem Collation.collate: %s is a dir, adding to directories' % subject)
                self.directories.append(str(subject))
            elif subject.isfile():
                if self.runtime:
                    self.runtime.report('filesystem Collation.collate: %s is a file, adding to files with hash %s' % (subject, subject.read_hexhash('sha1')))
                self.files[str(subject)] = subject.read_hexhash('sha1')

    def prune(self, other):
        for filepath, hash in self.files.items():
            if other.files.get(filepath) == hash:
                del self.files[filepath]
        
        for directory in self.directories:
            if self.runtime:
                self.runtime.report('checking for %s in the other collation' % directory)
        
            if directory in other.directories:
                if self.runtime:
                    self.runtime.report('removing %s from this collations directories list' % directory)
                del self.directories[self.directories.index(directory)]
            else:
                if self.runtime:
                    self.runtime.report('not removing %s from this collations directories list' % directory)

        filepaths = self.files.keys()
        directories = []
        for directory in self.directories:
            for filepath in filepaths:
                if filepath.startswith(directory) or path(directory).islink():
                    directories.append(directory)
                    break
    
        self.directories = directories
        return self

    def report(self, filepath, transforms=None):
        reportpath = path(filepath)
        for filepath in self.filepaths:
            if transforms:
                filepath = self._transform_filepath(filepath, transforms)
            reportpath.write_text(filepath + '\n', append=True)

    def tar(self, filename, transforms=None, compression='bz2'):
        openfile = tarfile.open(filename, 'w:' + compression)
        try:
            for filepath in self.filepaths:
                arcname = filepath
                if transforms: 
                    arcname = self._transform_filepath(filepath, transforms)
                openfile.add(filepath, arcname, recursive=False)
            for directory in self.directories:
                docontinue = False
                for filepath in self.filepaths:
                    if filepath.startswith(directory):
                        docontinue = True
                        break
                if docontinue:
                    continue
                arcname = directory
                if transforms:
                    arcname = self._transform_filepath(directory, transforms)
                openfile.add(directory, arcname, recursive=False)
                
        finally:
            openfile.close()

    def _transform_filepath(self, filepath, transforms):
        for prefix, repl in transforms.iteritems():
            if filepath.startswith(prefix):
                return filepath.replace(prefix, repl)
        return filepath
