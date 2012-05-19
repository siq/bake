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
            elif subject.isfile():
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

    def report(self, filepath):
        filepath = path(filepath)
        filepath.write_bytes('\n'.join(self.filepaths) + '\n')
