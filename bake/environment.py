import os
import re
from pprint import pformat

from bake.util import import_object, import_source, recursive_merge

class ParameterParser(object):
    STRUCTURE_EXPR = re.compile(r'(?:\{[^{\[\]]*?\})|(?:\[[^{}\[]*?\])')

    @classmethod
    def parse(cls, value):
        if value[0] in ('{', '['):
            return cls._parse_structured_value(value)
        else:
            return cls._parse_simple_value(value)

    @classmethod
    def _parse_simple_value(cls, value):
        candidate = value.lower()
        if candidate == 'true':
            return True
        elif candidate == 'false':
            return False

        if '.' in value:
            try:
                return float(value)
            except (TypeError, ValueError):
                pass

        try:
            return int(value)
        except (TypeError, ValueError):
            return value

    @classmethod
    def _parse_structure(cls, text, structures):
        head, tail = text[0], text[-1]
        if head == '{' and tail == '}':
            tokens = text[1:-1]
            if tokens:
                try:
                    pairs = []
                    for pair in tokens.split(','):
                        key, value = pair.split(':')
                        if value in structures:
                            value = structures[value]
                        else:
                            value = cls._parse_simple_value(value)
                        pairs.append((key, value))
                    return dict(pairs)
                except Exception:
                    raise ValueError(value)
            else:
                return {}
        elif head == '[' and tail == ']':
            tokens = text[1:-1]
            if tokens:
                values = []
                for value in tokens.split(','):
                    if value in structures:
                        value = structures[value]
                    else:
                        value = cls._parse_simple_value(value)
                    values.append(value)
                return values
            else:
                return []
        else:
            raise ValueError(value)

    @classmethod
    def _parse_structured_value(cls, value):
        expr = cls.STRUCTURE_EXPR
        structures = {}

        def replace(match):
            token = '||%d||' % len(structures)
            structures[token] = cls._parse_structure(match.group(0), structures)
            return token

        while True:
            value, count = expr.subn(replace, value)
            if count == 0:
                return structures[value]

class Environment(dict):
    """A bake runtime environment."""

    Parsers = {}

    def __getitem__(self, key):
        if '.' not in key:
            try:
                return super(Environment, self).__getitem__(key)
            except KeyError:
                return None

        tokens = key.split('.')
        tail = tokens.pop()

        try:
            ref = super(Environment, self).__getitem__(tokens.pop(0))
        except KeyError:
            return None

        if not isinstance(ref, dict):
            raise ValueError(key)

        for token in tokens:
            if token in ref:
                ref = ref[token]
                if not isinstance(ref, dict):
                    raise ValueError(key)
            else:
                return None

        return ref.get(tail)

    def __setitem__(self, key, value):
        if '.' not in key:
            return super(Environment, self).__setitem__(key, value)

        tokens = key.split('.')
        tail = tokens.pop()

        head = tokens.pop(0)
        if head not in self:
            super(Environment, self).__setitem__(head, {})

        ref = self[head]
        if not isinstance(ref, dict):
            raise ValueError(key)

        for token in tokens:
            if token not in ref:
                ref[token] = {}
            ref = ref[token]
            if not isinstance(ref, dict):
                raise ValueError(key)

        ref[tail] = value

    def dump(self):
        return pformat(self)

    def merge(self, source):
        recursive_merge(self, source)

    def parse(self, path):
        if not os.path.exists(path):
            raise RuntimeError('cannot find %r' % path)

        extension = os.path.splitext(path)[-1].lower()
        if extension not in self.Parsers:
            try:
                source = self._parse_module(path)
                if source:
                    self.merge(source)
            except Exception:
                raise RuntimeError('cannot parse %r' % path)
            else:
                return

        parser = self.Parsers[extension]
        source = parser(path)
        if source:
            self.merge(source)

    def parse_pair(self, pair):
        key, value = pair.split('=', 1)
        self.merge({key: ParameterParser.parse(value)})

    @classmethod
    def register(cls, *extensions):
        def decorator(function):
            for extension in extensions:
                cls.Parsers[extension] = function
            return function
        return decorator

    def _parse_module(self, path):
        module = import_object(path)
        namespace = {}
        for attr in dir(module):
            if attr[0] != '_':
                namespace[attr] = getattr(module, attr)
        return namespace

@Environment.register('.cfg', '.cnf', '.ini')
def parse_inifile(path):
    from ConfigParser import SafeConfigParser
    parser = SafeConfigParser()

    openfile = open(path, 'r')
    try:
        parser.readfp(openfile)
    finally:
        openfile.close()

    namespace = {}
    for section in parser.sections():
        namespace[section] = {}
        for key, value in parser.items(section):
            namespace[section][key] = parse_value(value)
    return namespace

@Environment.register('.json')
def parse_json(path):
    import json
    openfile = open(path, 'r')
    try:
        return json.load(openfile)
    finally:
        openfile.close()

@Environment.register('.py')
def parse_pyfile(path):
    return import_source(path)

@Environment.register('.yaml')
def parse_yaml(path):
    import yaml
    openfile = open(path, 'r')
    try:
        return yaml.load(openfile.read())
    finally:
        openfile.close()
