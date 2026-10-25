"""Root-owned pre-change fingerprint vector and real-source static closure."""
import ast
import importlib
from pathlib import Path
import unittest

from runtime_ownership import new_launch_identity


ROOT = Path(__file__).resolve().parents[1]


class RuntimeProtocolManifestTests(unittest.TestCase):
    def test_legacy_ownership_fingerprint_matches_prechange_literal(self):
        # Captured at85179c0 BEFORE protocol code; independently stdlib-derived.
        effective = {'seat': {'adapter': 'cli', 'name': 'Golden author'},
            'provider': {'command': 'python', 'cwd': '.'},
            'server': {'host': '127.0.0.1', 'port': 12345, 'data_dir': './data'},
            'mcp': {'http_port': 12346, 'sse_port': 12347}, 'config_resource': None}
        identity = new_launch_identity(ROOT, effective, 'golden/author', '1' * 32, '2' * 32)
        self.assertEqual(identity['fingerprint'],
            'bce6783ec65b26921583bf847bc9a226f63cbe0289da81a75efe25da91e9155f')

    def test_fixed_sets_cover_real_adapter_repo_import_closures(self):
        protocol = importlib.import_module('runtime_protocol')
        modules = {path.stem: path.name for path in ROOT.glob('*.py')}
        for adapter, entries in (('cli', ('wrapper.py', 'cli_worker.py')),
                                 ('openai-compatible', ('wrapper.py', 'wrapper_api.py'))):
            with self.subTest(adapter=adapter):
                listed = set(protocol.SOURCE_FILES[adapter])
                self.assertIn('runtime_protocol.py', listed)
                for filename in listed:
                    self.assertEqual(Path(filename).name, filename)
                    self.assertTrue((ROOT / filename).is_file(), 'Missing manifest file: ' + filename)
                seen, pending = set(), list(entries)
                while pending:
                    filename = pending.pop()
                    if filename in seen:
                        continue
                    seen.add(filename)
                    tree = ast.parse((ROOT / filename).read_text(encoding='utf-8'))
                    for node in ast.walk(tree):
                        imports = ([part.name for part in node.names] if isinstance(node, ast.Import)
                            else [node.module] if isinstance(node, ast.ImportFrom) and node.module else [])
                        for name in imports:
                            local = modules.get(name.split('.')[0])
                            if local is not None and local not in seen:
                                pending.append(local)
                missing = sorted(seen - listed)
                self.assertFalse(missing, 'Missing repo modules: ' + ', '.join(missing)
                    + '; extend the fixed set before enabling artifact-v1')


if __name__ == '__main__':
    unittest.main()
