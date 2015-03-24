import tarfile

from bake.path import path

class Collation(object):
    def __init__(self, root):
        if not isinstance(root, path):
            root = path(root)

        self.root = root.abspath()
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
                self.directories.append(str(subject))
            elif subject.isfile() or subject.islink():
                self.files[str(subject)] = subject.read_hexhash('sha1')

    def prune(self, other):
        for filepath, hash in self.files.items():
            if other.files.get(filepath) == hash:
                del self.files[filepath]

        filepaths = self.files.keys()
        directories = []

        for directory in self.directories:
            for filepath in filepaths:
                if filepath.startswith(directory):
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
        finally:
            openfile.close()

    def _transform_filepath(self, filepath, transforms):
        for prefix, repl in transforms.iteritems():
            if filepath.startswith(prefix):
                return filepath.replace(prefix, repl)
        return filepath
