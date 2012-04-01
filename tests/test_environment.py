from unittest2 import TestCase
from bake.environment import *

class TestEnvironment(TestCase):
    def test_path_handling(self):
        e = Environment()
        for path, value in [('a', 1), ('b.c', 2), ('e.f.g', 3), ('h.i.j.k', 4)]:
            self.assertFalse(e.has(path))
            self.assertIsNone(e.get(path))
            e.set(path, value)
            self.assertTrue(e.has(path))
            self.assertEqual(e.get(path), value)

    def test_pair_parsing(self):
        e = Environment()
        pairs = [
            ('a', '1', 1),
            ('b.c', '[1,2]', [1, 2]),
            ('d.e.f', '{a:1,b:true,c:test}', {'a': 1, 'b': True, 'c': 'test'}),
        ]
        for path, serialized, unserialized in pairs:
            e.parse_pair('%s=%s' % (path, serialized))
            self.assertEqual(e.get(path), unserialized)

class TestEnvironmentStack(TestCase):
    def test_path_handling(self):
        e1 = Environment({'a': {'b': 2, 'c': 3}})
        e2 = Environment({'a': {'b': 4, 'd': 5}})
        es = EnvironmentStack(e1, e2)

