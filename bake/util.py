import os
import sys
from inspect import getargspec
from tempfile import mkstemp
from textwrap import dedent
from traceback import format_tb

def call_with_supported_params(callable, **params):
    arguments = getargspec(callable)[0]
    for key in params.keys():
        if key not in arguments:
            del params[key]
    return callable(**params)

def execute_python_shell(code=None, ipython=False):
    arguments = [sys.executable, '-i']
    if ipython:
        try:
            import IPython
        except ImportError:
            pass
        else:
            arguments = ['ipython', '-i']

    if code:
        fileno, filename = mkstemp('.py', 'bake')
        os.write(fileno, dedent(code))
        os.close(fileno)
        arguments.append(filename)

    os.execvp(arguments[0], arguments)

def get_package_data(module, path):
    openfile = open(get_package_path(module, path))
    try:
        return openfile.read()
    finally:
        openfile.close()

def get_package_path(module, path):
    if isinstance(module, basestring):
        module = __import__(module, None, None, [module.split('.')[-1]])
    if not isinstance(module, list):
        module = module.__path__

    modulepath = module[0]
    for prefix in sys.path:
        if prefix in ('', '..'):
            prefix = os.getcwd()
        fullpath = os.path.abspath(os.path.join(prefix, modulepath))
        if os.path.exists(fullpath):
            break
    else:
        return None

    return os.path.join(fullpath, path)

def import_object(path):
    attr = None
    if ':' in path:
        path, attr = path.split(':')
        return getattr(__import__(path, None, None, [attr]), attr)

    try:
        return __import__(path, None, None, [path.split('.')[-1]])
    except ImportError:
        if '.' in path:
            path, attr = path.rsplit('.', 1)
            return getattr(__import__(path, None, None, [attr]), attr)
        else:
            raise

def import_source(path, namespace=None):
    namespace = namespace or {}
    container = {}

    openfile = open(path, 'r')
    try:
        exec openfile in namespace, container
        return container
    finally:
        openfile.close()

def propagate_traceback(exception):
    traceback = sys.exc_info()[2]
    if traceback is not None:
        traceback = ''.join(format_tb(traceback))
        if hasattr(exception, 'traceback'):
            exception.traceback += traceback
        else:
            exception.traceback = traceback
    return exception

def recursive_merge(original, addition):
    for key, value in addition.iteritems():
        if key in original:
            source = original[key]
            if isinstance(source, dict) and isinstance(value, dict):
                value = recursive_merge(source, value)
            original[key] = value
        else:
            original[key] = value
    return original

def topological_sort(graph):
    queue = []
    edges = graph.values()
    for node in graph.iterkeys():
        for edge in edges:
            if node in edge:
                break
        else:
            queue.append(node)

    result = []
    while queue:
        node = queue.pop(0)
        result.append(node)
        for target in graph[node].copy():
            graph[node].remove(target)
            for edge in graph.itervalues():
                if target in edge:
                    break
            else:
                queue.append(target)

    result.reverse()
    return result
