import os

def collate_data_files(rootpath, extensions=None):
    if isinstance(extensions, basestring):
        extensions = extensions.split(' ')

    def filter(filename):
        if not extensions:
            return True
        for extension in extensions:
            if filename.endswith(extension):
                return True

    data_files = []
    for root, dirs, files in os.walk(rootpath):
        candidates = []
        for filename in files:
            if filter(filename):
                candidates.append(os.path.join(root, filename))
        if candidates:
            data_files.append((root, candidates))
    return data_files

def enumerate_packages(rootpath):
    packages = []
    for root, dirs, files in os.walk(rootpath):
        if '__init__.py' in files:
            packages.append(root.replace('/', '.'))
    return packages
