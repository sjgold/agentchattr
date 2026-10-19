"""Ticket #4 (PF-2/3): safe, atomic provider-config writes.

Baseline bug: _write_json_mcp_settings() swallows a malformed existing
settings file (`except Exception: pass`) and silently overwrites it with a
fresh config, destroying whatever was there. A root value that parses but
isn't a mapping (a list, a string) isn't rejected either — it blows up with
an unrelated AttributeError/TypeError deeper in the merge instead of a clean
ValueError, and nothing stops the write from touching the file before that
point in some shapes. There is also no backup before the destination is
replaced, so a crash mid-write can lose the original content outright.

These tests pin the ticket #4 contract for the (not yet implemented)
`_replace_config_bytes` atomic-write path: malformed/non-map existing config
raises ValueError and leaves the file byte-for-byte untouched; a valid merge
preserves unrelated keys and leaves behind a unique sibling backup holding
the exact pre-write bytes; and a failure in the backup/replace step
propagates OSError while leaving the destination unchanged.
"""
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from wrapper import _write_json_mcp_settings  # noqa: E402


class ConfigPreservationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.target = Path(self.tmp.name) / "settings.json"

    def _write(self, content: str) -> bytes:
        raw = content.encode("utf-8")
        self.target.write_bytes(raw)
        return raw

    def _snapshot_dir(self) -> set[str]:
        return {p.name for p in self.target.parent.iterdir()}

    # -- malformed / non-map existing content ----------------------------

    def test_malformed_json_raises_valueerror_and_preserves_bytes(self):
        original = self._write("{not valid json!!")
        with self.assertRaises(ValueError):
            _write_json_mcp_settings(self.target, "http://127.0.0.1:8200/mcp",
                                     transport="http")
        self.assertEqual(self.target.read_bytes(), original)

    def test_root_non_map_raises_valueerror_and_preserves_bytes(self):
        original = self._write(json.dumps([1, 2, 3]))
        with self.assertRaises(ValueError):
            _write_json_mcp_settings(self.target, "http://127.0.0.1:8200/mcp",
                                     transport="http")
        self.assertEqual(self.target.read_bytes(), original)

    def test_nested_mcpServers_non_map_raises_valueerror_and_preserves_bytes(self):
        original = self._write(json.dumps({"mcpServers": "not-a-mapping"}))
        with self.assertRaises(ValueError):
            _write_json_mcp_settings(self.target, "http://127.0.0.1:8200/mcp",
                                     transport="http")
        self.assertEqual(self.target.read_bytes(), original)

    # -- valid merge: preserve unrelated data + unique backups ----------

    def test_valid_merge_preserves_unrelated_data(self):
        self._write(json.dumps({
            "mcpServers": {"some-other-server": {"type": "http", "url": "http://elsewhere"}},
            "unrelatedTopLevelKey": {"keep": "me"},
        }))
        _write_json_mcp_settings(self.target, "http://127.0.0.1:8200/mcp",
                                 transport="http", http_key="url")
        data = json.loads(self.target.read_text("utf-8"))
        self.assertIn("some-other-server", data["mcpServers"])
        self.assertIn("agentchattr", data["mcpServers"])
        self.assertEqual(data.get("unrelatedTopLevelKey"), {"keep": "me"})

    def test_valid_merge_creates_sibling_backup_with_exact_original_bytes(self):
        original = self._write(json.dumps({
            "mcpServers": {"some-other-server": {"type": "http", "url": "http://elsewhere"}},
        }))
        before = self._snapshot_dir()
        _write_json_mcp_settings(self.target, "http://127.0.0.1:8200/mcp",
                                 transport="http", http_key="url")
        after = self._snapshot_dir()
        new_files = after - before
        self.assertTrue(new_files, "expected a sibling backup file to be created")
        backup_path = self.target.parent / next(iter(new_files))
        self.assertEqual(backup_path.read_bytes(), original)

    def test_repeated_writes_create_unique_backups(self):
        first_original = self._write(json.dumps({"mcpServers": {}}))
        before = self._snapshot_dir()
        _write_json_mcp_settings(self.target, "http://127.0.0.1:8200/mcp",
                                 transport="http", http_key="url")
        after_first = self._snapshot_dir()
        first_backups = after_first - before

        second_original = self.target.read_bytes()
        _write_json_mcp_settings(self.target, "http://127.0.0.1:9999/mcp",
                                 transport="http", http_key="url")
        after_second = self._snapshot_dir()
        second_backups = after_second - after_first

        self.assertTrue(first_backups, "expected a backup on the first write")
        self.assertTrue(second_backups, "expected a distinct backup on the second write")
        self.assertTrue(first_backups.isdisjoint(second_backups),
                         "backups must not collide between writes")

        second_backup_path = self.target.parent / next(iter(second_backups))
        self.assertEqual(second_backup_path.read_bytes(), second_original)
        self.assertNotEqual(second_original, first_original)

    # -- backup/replace failure must not touch the destination -----------

    def test_replace_failure_preserves_destination_and_propagates_oserror(self):
        original = self._write(json.dumps({"mcpServers": {}}))
        with patch("wrapper.os.replace", side_effect=OSError("disk full")):
            with self.assertRaises(OSError):
                _write_json_mcp_settings(self.target, "http://127.0.0.1:8200/mcp",
                                         transport="http", http_key="url")
        self.assertEqual(self.target.read_bytes(), original)

    def test_backup_failure_preserves_destination_and_propagates_oserror(self):
        original = self._write(json.dumps({"mcpServers": {}}))
        with patch("wrapper.shutil.copy2", side_effect=OSError("backup failed")):
            with self.assertRaises(OSError):
                _write_json_mcp_settings(self.target, "http://127.0.0.1:8200/mcp",
                                         transport="http", http_key="url")
        self.assertEqual(self.target.read_bytes(), original)


if __name__ == "__main__":
    unittest.main()
