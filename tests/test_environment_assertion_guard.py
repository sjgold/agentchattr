"""A failing assertion must never format the real environment container."""
import ast
from pathlib import Path
import unittest


def environment_container(node):
    if isinstance(node, ast.Attribute) and isinstance(node.value,ast.Name):
        return node.value.id=='os' and node.attr=='environ'
    return (isinstance(node,ast.Call) and isinstance(node.func,ast.Name)
            and node.func.id=='dict' and any(environment_container(arg) for arg in node.args))


class EnvironmentAssertionGuardTests(unittest.TestCase):
    def test_no_environment_container_in_assertion_diagnostics(self):
        hits=[]
        for path in Path(__file__).parent.glob('test_*.py'):
            for node in ast.walk(ast.parse(path.read_text(encoding='utf-8-sig'))):
                if (isinstance(node,ast.Call) and isinstance(node.func,ast.Attribute)
                        and node.func.attr in {'assertIn','assertNotIn','assertEqual','assertNotEqual'}
                        and any(environment_container(arg) for arg in node.args)):
                    hits.append(path.name+':'+str(node.lineno))
        self.assertEqual(hits,[], 'Use fake-only environments and boolean assertions: '+', '.join(hits))
