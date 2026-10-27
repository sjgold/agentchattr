"""json_mcp_settings, tested directly: byte-level preservation, refusals, backups, exact removal.

Every test works in a temporary directory standing in for the agy config directory; no real
Antigravity configuration is read, listed or written.
"""
import contextlib
import io
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import json_mcp_settings as jm  # noqa: E402
from json_mcp_settings import JsonSettingsError  # noqa: E402

TOKEN = 'tok_TOKENVAL_feedfacecafebeef0123456789'
TOKEN2 = 'tok_TOKENVAL_0000111122223333aaaabbbb'
URL = 'http://127.0.0.1:49961/mcp'
ENTRY = 'agentchattr-fork'
USER_SECRET = 'USERSECRET_do_not_echo'
BAK_NAME = re.compile(r'mcp_config\.json\.agentchattr-fork-\d{8}T\d{6}Z-[0-9a-f]{6}\.bak')

BASE_OBJ = {
    'theme': 'dark',
    'futureFeature': {'x': [1, 2, {'y': None}], 'z': 1.5},
    'mcpServers': {
        'agentchattr': {'serverURL': 'http://127.0.0.1:8200/mcp', 'disabled': False},
        'other': {'command': 'node', 'args': ['a', 'b']},
    },
    'zlast': [1, 2, 3],
}

PRETTY2 = (
    '{\n  "theme": "dark",\n  "mcpServers": {\n    "agentchattr": {\n'
    '      "serverURL": "http://127.0.0.1:8200/mcp"\n    }\n  }\n}\n'
)


def with_obj(**changes):
    obj = json.loads(json.dumps(BASE_OBJ))
    obj.update(changes)
    return obj


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.home = Path(self.tmp.name) / 'gemini config'
        self.home.mkdir()
        self.config = self.home / 'mcp_config.json'
        self.logs = []

    def write(self, data):
        self.config.write_bytes(data.encode('utf-8') if isinstance(data, str) else data)

    def apply(self, token=TOKEN, **kwargs):
        return jm.apply(self.config, URL, token, log=self.logs.append, **kwargs)

    def remove(self, receipt=None, **kwargs):
        return jm.remove_exact(self.config, receipt=receipt, log=self.logs.append, **kwargs)

    def baks(self):
        return sorted(self.home.glob('*.bak'))

    def tmps(self):
        return sorted(self.home.glob('*.tmp'))

    def assertNoSecrets(self):
        self.assertNotIn('TOKENVAL', '\n'.join(self.logs))
        for bak in self.baks():
            self.assertNotIn(b'TOKENVAL', bak.read_bytes())

    def assertInsertionOnly(self, before, after):
        """after is before with one contiguous run of bytes inserted and nothing else touched."""
        self.assertGreater(len(after), len(before))
        prefix = 0
        while prefix < len(before) and before[prefix] == after[prefix]:
            prefix += 1
        suffix = 0
        while suffix < len(before) - prefix and before[-1 - suffix] == after[-1 - suffix]:
            suffix += 1
        self.assertEqual(prefix + suffix, len(before), 'apply changed bytes other than the inserted member')

    def assertRefused(self, content, entry=ENTRY):
        self.write(content)
        before = self.config.read_bytes()
        with self.assertRaises(JsonSettingsError) as caught:
            self.apply(entry=entry)
        self.assertEqual(self.config.read_bytes(), before)
        self.assertEqual(self.baks(), [])
        self.assertEqual(self.tmps(), [])
        message = str(caught.exception)
        self.assertNotIn('TOKENVAL', message)
        self.assertNotIn(USER_SECRET, message)
        return caught.exception


def format_samples():
    """name -> bytes of a config that holds an agentchattr entry, an unknown key and more."""
    obj = BASE_OBJ
    single = with_obj(mcpServers={'agentchattr': {'serverURL': 'http://127.0.0.1:8200/mcp'}})
    pretty2 = json.dumps(obj, indent=2)
    pretty4 = json.dumps(obj, indent=4)
    tabs = json.dumps(obj, indent='\t')
    compact_spaced = json.dumps(obj)
    compact_tight = json.dumps(obj, separators=(',', ':'))
    return {
        '2-space newline': (pretty2 + '\n').encode(),
        '2-space no trailing newline': pretty2.encode(),
        '2-space extra trailing newlines': (pretty2 + '\n\n\n').encode(),
        '2-space leading blank lines': ('\n\n' + pretty2 + '\n').encode(),
        '4-space': (pretty4 + '\n').encode(),
        'tab': (tabs + '\n').encode(),
        'tab no trailing newline': tabs.encode(),
        'CRLF 2-space': (pretty2 + '\n').replace('\n', '\r\n').encode(),
        'CRLF 4-space no trailing newline': pretty4.replace('\n', '\r\n').encode(),
        'CRLF tab': (tabs + '\n').replace('\n', '\r\n').encode(),
        'compact spaced': compact_spaced.encode(),
        'compact spaced newline': (compact_spaced + '\n').encode(),
        'compact tight': compact_tight.encode(),
        'compact tight newline': (compact_tight + '\n').encode(),
        'compact tight single member': json.dumps(single, separators=(',', ':')).encode(),
        'compact spaced single member': json.dumps(single).encode(),
        'pretty single member': (json.dumps(single, indent=2) + '\n').encode(),
        'space before colon': b'{\n  "mcpServers" : {\n    "agentchattr" : {"serverURL" : "u"}\n  }\n}\n',
    }


class FormatTests(Base):
    def check_roundtrip(self, original):
        self.write(original)
        before = json.loads(original.decode('utf-8'))
        receipt = self.apply()
        after_bytes = self.config.read_bytes()
        after = json.loads(after_bytes.decode('utf-8'))
        self.assertInsertionOnly(original, after_bytes)
        self.assertEqual(list(after), list(before))
        self.assertEqual(list(after['mcpServers']), list(before['mcpServers']) + [ENTRY])
        for key in before:
            if key != 'mcpServers':
                self.assertEqual(after[key], before[key], key)
        for key in before['mcpServers']:
            self.assertEqual(after['mcpServers'][key], before['mcpServers'][key], key)
        self.assertEqual(after['mcpServers'][ENTRY]['serverURL'], URL)
        self.assertEqual(after['mcpServers'][ENTRY]['headers']['Authorization'], 'Bearer ' + TOKEN)
        self.assertFalse(receipt.created_file)
        self.assertFalse(receipt.created_section)
        self.assertEqual(receipt.backup_path.read_bytes(), original)
        result = self.remove(receipt)
        self.assertEqual(result.status, 'restored-exact')
        self.assertIs(result.matches_backup, True)
        self.assertEqual(self.config.read_bytes(), original)
        self.assertNoSecrets()
        return after_bytes

    def test_every_format_applies_and_removes_to_the_exact_original_bytes(self):
        for name, original in format_samples().items():
            with self.subTest(format=name):
                for stale in self.home.glob('*'):
                    stale.unlink()
                self.check_roundtrip(original)

    def test_indentation_style_is_copied_into_the_new_member(self):
        samples = format_samples()
        cases = {
            '2-space newline': b'\n    "' + ENTRY.encode() + b'": {\n      "serverURL"',
            '4-space': b'\n        "' + ENTRY.encode() + b'": {\n            "serverURL"',
            'tab': b'\n\t\t"' + ENTRY.encode() + b'": {\n\t\t\t"serverURL"',
        }
        for name, needle in cases.items():
            with self.subTest(format=name):
                for stale in self.home.glob('*'):
                    stale.unlink()
                self.write(samples[name])
                self.apply()
                self.assertIn(needle, self.config.read_bytes())

    def test_crlf_files_stay_crlf_throughout(self):
        for name in ('CRLF 2-space', 'CRLF 4-space no trailing newline', 'CRLF tab'):
            with self.subTest(format=name):
                for stale in self.home.glob('*'):
                    stale.unlink()
                self.write(format_samples()[name])
                self.apply()
                data = self.config.read_bytes()
                self.assertEqual(data.count(b'\n'), data.count(b'\r\n'))
                self.assertNotRegex(data, rb'\r(?!\n)')

    def test_compact_files_stay_on_one_line_with_their_separators(self):
        samples = format_samples()
        self.write(samples['compact tight'])
        self.apply()
        data = self.config.read_bytes()
        self.assertNotIn(b'\n', data)
        self.assertNotIn(b', ', data.replace(b'Bearer ' + TOKEN.encode(), b''))
        self.assertNotIn(b'": ', data)
        self.assertIn(b'"' + ENTRY.encode() + b'":{"serverURL":"' + URL.encode() + b'","headers":{"Authorization":"Bearer ', data)
        for stale in self.home.glob('*'):
            stale.unlink()
        self.write(samples['compact spaced'])
        self.apply()
        data = self.config.read_bytes()
        self.assertNotIn(b'\n', data)
        self.assertIn(b', "' + ENTRY.encode() + b'": {"serverURL": "' + URL.encode() + b'", "headers": {"Authorization": "Bearer ', data)

    def test_existing_agentchattr_entry_and_unknown_keys_are_untouched(self):
        original = (json.dumps(BASE_OBJ, indent=2) + '\n').encode()
        self.write(original)
        self.apply()
        text = self.config.read_text('utf-8')
        pairs = json.loads(text, object_pairs_hook=list)
        self.assertEqual([k for k, _ in pairs], list(BASE_OBJ))
        after = json.loads(text)
        self.assertEqual(after['mcpServers']['agentchattr'], BASE_OBJ['mcpServers']['agentchattr'])
        self.assertEqual(after['futureFeature'], BASE_OBJ['futureFeature'])
        self.assertEqual(after['zlast'], BASE_OBJ['zlast'])

    def test_empty_mcpservers_object(self):
        for name, original in {
            'pretty': b'{\n  "theme": "dark",\n  "mcpServers": {}\n}\n',
            'compact': b'{"mcpServers":{}}',
            'compact spaced': b'{"mcpServers": {}}\n',
            'tab': b'{\n\t"mcpServers": {}\n}\n',
            'crlf': b'{\r\n  "mcpServers": {}\r\n}\r\n',
        }.items():
            with self.subTest(format=name):
                for stale in self.home.glob('*'):
                    stale.unlink()
                self.write(original)
                receipt = self.apply()
                self.assertFalse(receipt.created_section)
                parsed = json.loads(self.config.read_text('utf-8'))
                self.assertEqual(list(parsed['mcpServers']), [ENTRY])
                result = self.remove(receipt)
                self.assertEqual(result.status, 'restored-exact')
                self.assertEqual(self.config.read_bytes(), original)

    def test_empty_mcpservers_pretty_layout_goes_on_new_lines(self):
        self.write(b'{\n  "mcpServers": {}\n}\n')
        self.apply()
        self.assertIn(b'{\n    "' + ENTRY.encode() + b'": {\n      "serverURL"', self.config.read_bytes())

    def test_missing_mcpservers_is_created_as_last_root_member(self):
        for name, original in {
            'pretty': b'{\n  "theme": "dark",\n  "zlast": [1]\n}\n',
            'tab': b'{\n\t"theme": "dark"\n}\n',
            'compact': b'{"theme":"dark"}',
            'crlf': b'{\r\n  "theme": "dark"\r\n}\r\n',
        }.items():
            with self.subTest(format=name):
                for stale in self.home.glob('*'):
                    stale.unlink()
                self.write(original)
                receipt = self.apply()
                self.assertTrue(receipt.created_section)
                self.assertFalse(receipt.created_file)
                after = json.loads(self.config.read_text('utf-8'))
                before = json.loads(original.decode())
                self.assertEqual(list(after), list(before) + ['mcpServers'])
                self.assertEqual(list(after['mcpServers']), [ENTRY])
                self.assertInsertionOnly(original, self.config.read_bytes())
                result = self.remove(receipt)
                self.assertEqual(result.status, 'restored-exact')
                self.assertEqual(self.config.read_bytes(), original)

    def test_empty_root_object(self):
        for original in (b'{}', b'{}\n', b'{\n}\n', b'  {}  \n', b'{ }'):
            with self.subTest(original=original):
                for stale in self.home.glob('*'):
                    stale.unlink()
                self.write(original)
                receipt = self.apply()
                self.assertTrue(receipt.created_section)
                after = json.loads(self.config.read_text('utf-8'))
                self.assertEqual(list(after), ['mcpServers'])
                self.assertEqual(list(after['mcpServers']), [ENTRY])
                result = self.remove(receipt)
                self.assertEqual(result.status, 'restored-exact')
                self.assertEqual(self.config.read_bytes(), original)

    def test_missing_file_in_existing_dir_is_created_then_deleted(self):
        self.assertFalse(self.config.exists())
        receipt = self.apply()
        self.assertTrue(receipt.created_file)
        self.assertTrue(receipt.created_section)
        self.assertIsNone(receipt.backup_path)
        self.assertIsNone(receipt.backup_sha256)
        data = self.config.read_bytes()
        self.assertTrue(data.endswith(b'\n'))
        parsed = json.loads(data.decode('utf-8'))
        self.assertEqual(parsed, {'mcpServers': {ENTRY: {'serverURL': URL, 'headers': {'Authorization': 'Bearer ' + TOKEN}}}})
        self.assertEqual(self.baks(), [])
        result = self.remove(receipt)
        self.assertEqual(result.status, 'deleted-created-file')
        self.assertIs(result.matches_backup, True)
        self.assertFalse(self.config.exists())
        self.assertEqual(self.tmps(), [])

    def test_missing_parent_dir_is_refused(self):
        target = Path(self.tmp.name) / 'nope' / 'mcp_config.json'
        with self.assertRaises(JsonSettingsError):
            jm.apply(target, URL, TOKEN, log=self.logs.append)
        self.assertFalse(target.parent.exists())

    def test_empty_token_adds_no_headers(self):
        self.write(PRETTY2)
        self.apply(token='')
        entry = json.loads(self.config.read_text('utf-8'))['mcpServers'][ENTRY]
        self.assertEqual(entry, {'serverURL': URL})

    def test_custom_entry_name_and_url_key(self):
        self.write(PRETTY2)
        receipt = jm.apply(self.config, URL, TOKEN, entry='my-entry', key='httpUrl', log=self.logs.append)
        entry = json.loads(self.config.read_text('utf-8'))['mcpServers']['my-entry']
        self.assertEqual(entry['httpUrl'], URL)
        self.assertNotIn('serverURL', entry)
        self.assertIn('.my-entry-', receipt.backup_path.name)
        result = jm.remove_exact(self.config, entry='my-entry', receipt=receipt, log=self.logs.append)
        self.assertEqual(result.status, 'restored-exact')
        self.assertEqual(self.config.read_bytes(), PRETTY2.encode())

    def test_non_text_url_or_token_is_refused_before_writing(self):
        self.write(PRETTY2)
        for url, token in ((None, TOKEN), (URL, None), (b'x', TOKEN), (URL, 5)):
            with self.subTest(url=url, token=token):
                with self.assertRaises(JsonSettingsError):
                    jm.apply(self.config, url, token, log=self.logs.append)
        self.assertEqual(self.config.read_bytes(), PRETTY2.encode())
        self.assertEqual(self.baks(), [])


class RefusalTests(Base):
    CASES = {
        'invalid json': ('{"k": "%s", oops}' % USER_SECRET).encode(),
        'trailing comma': ('{"k": "%s",}' % USER_SECRET).encode(),
        'comment': ('{"k": "%s" /* c */}' % USER_SECRET).encode(),
        'truncated': ('{"k": "%s"' % USER_SECRET).encode(),
        'trailing garbage': ('{"k": "%s"} x' % USER_SECRET).encode(),
        'root array': ('["%s"]' % USER_SECRET).encode(),
        'root string': ('"%s"' % USER_SECRET).encode(),
        'root number': b'42',
        'root null': b'null',
        'root true': b'true',
        'mcpServers array': ('{"mcpServers": ["%s"]}' % USER_SECRET).encode(),
        'mcpServers string': ('{"mcpServers": "%s"}' % USER_SECRET).encode(),
        'mcpServers null': b'{"mcpServers": null}',
        'mcpServers number': b'{"mcpServers": 3}',
        'our entry array': ('{"mcpServers": {"%s": ["%s"]}}' % (ENTRY, USER_SECRET)).encode(),
        'our entry string': ('{"mcpServers": {"%s": "%s"}}' % (ENTRY, USER_SECRET)).encode(),
        'our entry null': ('{"mcpServers": {"%s": null, "x": "%s"}}' % (ENTRY, USER_SECRET)).encode(),
        'our entry number': ('{"mcpServers": {"%s": 1, "x": "%s"}}' % (ENTRY, USER_SECRET)).encode(),
        'duplicate top-level key': ('{"a": "%s", "a": 2}' % USER_SECRET).encode(),
        'duplicate mcpServers key': ('{"mcpServers": {}, "mcpServers": {}, "x": "%s"}' % USER_SECRET).encode(),
        'duplicate nested key': ('{"mcpServers": {"x": {"k": 1, "k": "%s"}}}' % USER_SECRET).encode(),
        'duplicate our entry': ('{"mcpServers": {"%s": {}, "%s": {}, "x": "%s"}}' % (ENTRY, ENTRY, USER_SECRET)).encode(),
        'NaN': ('{"a": NaN, "s": "%s"}' % USER_SECRET).encode(),
        'Infinity': ('{"a": Infinity, "s": "%s"}' % USER_SECRET).encode(),
        '-Infinity': ('{"a": -Infinity, "s": "%s"}' % USER_SECRET).encode(),
        '1e999': ('{"a": 1e999, "s": "%s"}' % USER_SECRET).encode(),
        '-1e999': ('{"a": -1e999, "s": "%s"}' % USER_SECRET).encode(),
        'utf-8 BOM': b'\xef\xbb\xbf{"s": "' + USER_SECRET.encode() + b'"}',
        'non-UTF-8 bytes': b'{"s": "\xff\xfe ' + USER_SECRET.encode() + b'"}',
        'UTF-16 text': ('{"s": "%s"}' % USER_SECRET).encode('utf-16'),
        'mixed CRLF and LF': ('{\r\n"a": 1,\n"s": "%s"\r\n}' % USER_SECRET).encode(),
        'bare CR': ('{"a": 1,\r"s": "%s"}' % USER_SECRET).encode(),
        'bare CR with CRLF': ('{\r\n"a": 1,\r"s": "%s"\r\n}' % USER_SECRET).encode(),
        'empty file': b'',
        'whitespace only': b'  \n\n',
    }

    def test_refusals_leave_the_file_byte_identical_and_make_no_backup(self):
        for name, content in self.CASES.items():
            with self.subTest(case=name):
                self.assertRefused(content)
                self.assertEqual(self.logs, [])

    def test_removal_refuses_the_same_shapes_without_touching_the_file(self):
        for name, content in self.CASES.items():
            with self.subTest(case=name):
                self.write(content)
                with self.assertRaises(JsonSettingsError) as caught:
                    self.remove()
                self.assertEqual(self.config.read_bytes(), content)
                self.assertNotIn(USER_SECRET, str(caught.exception))
                self.assertEqual(self.baks(), [])

    def test_invalid_json_error_names_only_a_line_number(self):
        error = self.assertRefused(b'{\n"a": 1,\n"b": oops "' + USER_SECRET.encode() + b'"\n}')
        self.assertIn('line 3', str(error))
        self.assertNotIn('oops', str(error))

    def test_error_messages_carry_no_token_even_when_the_user_file_holds_it(self):
        self.assertRefused(('{"mcpServers": {"%s": {"h": "%s"}, "%s": 1}}' % ('x', TOKEN, ENTRY)).encode())

    def test_reserved_and_bad_entry_names_are_refused_before_any_write(self):
        self.write(PRETTY2)
        for name in ('agentchattr', 'AgentChattr', 'AGENTCHATTR', 'agentChattr', '', ' ', 'bad name', 'a/b',
                     '-lead', '.lead', '_lead', 'x' * 65, 'quo"te', 'new\nline', 'ü', None.__class__, 5, ['a']):
            with self.subTest(name=name):
                with self.assertRaises(JsonSettingsError):
                    self.apply(entry=name)
                with self.assertRaises(JsonSettingsError):
                    self.remove(entry=name)
        self.assertEqual(self.config.read_bytes(), PRETTY2.encode())
        self.assertEqual(self.baks(), [])

    def test_valid_entry_names(self):
        self.assertEqual(jm.entry_name(), 'agentchattr-fork')
        self.assertEqual(jm.entry_name(None), 'agentchattr-fork')
        for name in ('agentchattr-fork', 'a', 'a.b_c-1', 'agentchattr2', 'x' * 64, '9lives'):
            with self.subTest(name=name):
                self.assertEqual(jm.entry_name(name), name)

    def test_bad_url_keys_are_refused(self):
        self.write(PRETTY2)
        for key in ('headers', '', ' ', '1bad', 'a-b', 'a b', 'a.b', 'x' * 65, 'quo"te', 5, None.__class__):
            with self.subTest(key=key):
                with self.assertRaises(JsonSettingsError):
                    self.apply(key=key)
        self.assertEqual(self.config.read_bytes(), PRETTY2.encode())
        self.assertEqual(self.baks(), [])

    def test_valid_url_keys(self):
        self.assertEqual(jm.url_key(), 'serverURL')
        self.assertEqual(jm.url_key(None), 'serverURL')
        for key in ('url', 'serverURL', 'httpUrl', '_u', 'a1_b2'):
            with self.subTest(key=key):
                self.assertEqual(jm.url_key(key), key)

    def test_a_valid_file_with_non_ascii_content_is_accepted(self):
        original = ('{"note": "caf\u00e9 \u2603 \U0001F600", "mcpServers": {}}\n').encode('utf-8')
        self.write(original)
        receipt = self.apply()
        self.assertEqual(json.loads(self.config.read_text('utf-8'))['note'], 'caf\u00e9 \u2603 \U0001F600')
        self.remove(receipt)
        self.assertEqual(self.config.read_bytes(), original)

    def test_strings_with_escapes_and_braces_do_not_confuse_the_scanner(self):
        original = (
            '{\n  "a": "}{\\"\\\\",\n  "mcpServers": {\n    "agentchattr": {"serverURL": "x}\\"]{"},\n'
            '    "q\\"}": [1, {"k": "}"}]\n  },\n  "z": "\\\\"\n}\n'
        ).encode()
        self.write(original)
        receipt = self.apply()
        after = json.loads(self.config.read_text('utf-8'))
        self.assertEqual(list(after['mcpServers']), ['agentchattr', 'q"}', ENTRY])
        self.assertEqual(after['z'], '\\')
        self.remove(receipt)
        self.assertEqual(self.config.read_bytes(), original)


class BackupTests(Base):
    def test_backup_holds_the_exact_prior_bytes_and_never_the_token(self):
        original = (json.dumps(BASE_OBJ, indent=2) + '\n').encode()
        self.write(original)
        receipt = self.apply()
        baks = self.baks()
        self.assertEqual(len(baks), 1)
        self.assertEqual(baks[0], receipt.backup_path)
        self.assertRegex(baks[0].name, BAK_NAME)
        self.assertEqual(baks[0].read_bytes(), original)
        self.assertEqual(receipt.backup_sha256, __import__('hashlib').sha256(original).hexdigest())
        self.assertNotIn(b'TOKENVAL', baks[0].read_bytes())
        self.assertNoSecrets()

    def test_backup_name_uses_the_entry_name(self):
        self.write(PRETTY2)
        receipt = jm.apply(self.config, URL, TOKEN, entry='other.entry_1', log=self.logs.append)
        self.assertRegex(receipt.backup_path.name, r'mcp_config\.json\.other\.entry_1-\d{8}T\d{6}Z-[0-9a-f]{6}\.bak')

    def test_two_backups_never_collide(self):
        self.write(PRETTY2)
        first = self.apply()
        self.remove(first)
        second = self.apply()
        self.assertNotEqual(first.backup_path, second.backup_path)
        self.assertEqual(len(self.baks()), 2)

    def test_refresh_makes_no_second_backup(self):
        self.write(PRETTY2)
        first = self.apply()
        self.assertEqual(len(self.baks()), 1)
        second = self.apply(token=TOKEN2)
        self.assertEqual(len(self.baks()), 1)
        self.assertIsNone(second.backup_path)
        self.assertIsNone(second.backup_sha256)
        self.assertFalse(second.created_file)
        self.assertEqual(first.backup_path.read_bytes(), PRETTY2.encode())
        self.assertNoSecrets()

    def test_no_backup_for_a_new_file(self):
        receipt = self.apply()
        self.assertIsNone(receipt.backup_path)
        self.assertEqual(self.baks(), [])

    def test_stale_entry_from_a_killed_run_gets_no_backup_and_removes_as_removed_entry(self):
        self.write(PRETTY2)
        self.apply(token='stale_TOKENVAL_old')
        for bak in self.baks():
            bak.unlink()                                # the earlier run's receipt and backup are gone
        stale_bytes = self.config.read_bytes()
        receipt = self.apply()
        self.assertEqual(self.baks(), [])
        self.assertIsNone(receipt.backup_path)
        self.assertFalse(receipt.created_file)
        self.assertEqual(self.config.read_bytes(), stale_bytes.replace(b'stale_TOKENVAL_old', TOKEN.encode()))
        result = self.remove(receipt)
        self.assertEqual(result.status, 'removed-entry')
        self.assertIsNone(result.matches_backup)
        self.assertEqual(result.differing_keys, [])
        self.assertEqual(self.config.read_bytes(), PRETTY2.encode())

    def test_backup_is_not_made_when_a_refusal_happens(self):
        self.write(b'[1]')
        with self.assertRaises(JsonSettingsError):
            self.apply()
        self.assertEqual(self.baks(), [])


class RefreshTests(Base):
    OLD = (
        '{\n  "mcpServers": {\n    "agentchattr-fork": {\n      "serverURL": "http://127.0.0.1:49961/mcp",\n'
        '      "headers": {\n        "Authorization": "Bearer OLD"\n      }\n    },\n'
        '    "other": {"command": "x"}\n  },\n  "k": 1\n}\n'
    )

    def test_refresh_replaces_the_value_in_place_when_other_members_follow(self):
        self.write(self.OLD)
        receipt = self.apply()
        self.assertEqual(self.config.read_text('utf-8'), self.OLD.replace('Bearer OLD', 'Bearer ' + TOKEN))
        self.assertEqual(list(json.loads(self.config.read_text('utf-8'))['mcpServers']), [ENTRY, 'other'])
        self.assertIsNone(receipt.backup_path)
        self.assertFalse(receipt.created_section)

    def test_second_apply_with_a_new_token_changes_only_the_token(self):
        original = (json.dumps(BASE_OBJ, indent=2) + '\n').encode()
        self.write(original)
        self.apply()
        first = self.config.read_bytes()
        self.apply(token=TOKEN2)
        second = self.config.read_bytes()
        self.assertEqual(second, first.replace(TOKEN.encode(), TOKEN2.encode()))
        self.assertNotIn(TOKEN.encode(), second)
        self.assertEqual(list(json.loads(second)['mcpServers']), ['agentchattr', 'other', ENTRY])

    def test_refresh_with_a_new_url(self):
        self.write(self.OLD)
        jm.apply(self.config, 'http://127.0.0.1:1/mcp', 'T', log=self.logs.append)
        data = json.loads(self.config.read_text('utf-8'))['mcpServers'][ENTRY]
        self.assertEqual(data, {'serverURL': 'http://127.0.0.1:1/mcp', 'headers': {'Authorization': 'Bearer T'}})

    def test_refresh_keeps_a_one_line_entry_on_one_line(self):
        original = '{"mcpServers": {"agentchattr-fork": {"serverURL": "old"}, "z": 1}, "k": 2}'
        self.write(original)
        self.apply()
        text = self.config.read_text('utf-8')
        self.assertNotIn('\n', text)
        self.assertEqual(list(json.loads(text)['mcpServers']), [ENTRY, 'z'])
        self.assertTrue(text.endswith('}, "z": 1}, "k": 2}'))

    def test_refresh_can_drop_headers_when_the_token_is_empty(self):
        self.write(self.OLD)
        self.apply(token='')
        self.assertEqual(json.loads(self.config.read_text('utf-8'))['mcpServers'][ENTRY], {'serverURL': URL})


class RemoveTests(Base):
    def test_unchanged_since_write_restores_the_backup_bytes(self):
        original = (json.dumps(BASE_OBJ, indent=4) + '\n').encode()
        self.write(original)
        receipt = self.apply()
        result = self.remove(receipt)
        self.assertEqual(result.status, 'restored-exact')
        self.assertIs(result.matches_backup, True)
        self.assertEqual(result.differing_keys, [])
        self.assertEqual(self.config.read_bytes(), original)
        self.assertEqual(self.tmps(), [])

    def test_edited_elsewhere_since_write_removes_only_our_member(self):
        self.write(PRETTY2)
        receipt = self.apply()
        edited = self.config.read_bytes().replace(b'"theme": "dark"', b'"theme": "light"')
        self.config.write_bytes(edited)
        result = self.remove(receipt)
        self.assertEqual(result.status, 'removed-entry')
        self.assertIs(result.matches_backup, False)
        self.assertEqual(result.differing_keys, ['theme'])
        self.assertEqual(self.config.read_bytes(), PRETTY2.replace('"dark"', '"light"').encode())
        self.assertNotIn(b'TOKENVAL', self.config.read_bytes())

    def test_member_added_after_ours_is_kept(self):
        self.write(PRETTY2)
        receipt = self.apply()
        tail = b'\n  }\n}\n'
        data = self.config.read_bytes()
        self.assertEqual(data.count(tail), 1)
        self.config.write_bytes(data.replace(tail, b',\n    "added": {"command": "x"}' + tail))
        result = self.remove(receipt)
        self.assertEqual(result.status, 'removed-entry')
        self.assertIs(result.matches_backup, False)
        self.assertEqual(result.differing_keys, ['mcpServers.added'])
        expected = PRETTY2.replace('\n    }\n  }\n}\n', '\n    },\n    "added": {"command": "x"}\n  }\n}\n')
        self.assertEqual(self.config.read_text('utf-8'), expected)

    def test_member_added_before_ours_is_kept(self):
        self.write(PRETTY2)
        receipt = self.apply()
        data = self.config.read_text('utf-8')
        data = data.replace('  "mcpServers": {\n', '  "mcpServers": {\n    "first": {},\n', 1)
        self.config.write_text(data, 'utf-8', newline='')
        result = self.remove(receipt)
        self.assertEqual(result.status, 'removed-entry')
        after = json.loads(self.config.read_text('utf-8'))
        self.assertEqual(list(after['mcpServers']), ['first', 'agentchattr'])

    def test_our_entry_first_of_several_members(self):
        original = ('{\n  "mcpServers": {\n    "agentchattr-fork": {"serverURL": "u"},\n'
                    '    "other": {"command": "x"}\n  }\n}\n')
        self.write(original)
        result = self.remove()
        self.assertEqual(result.status, 'removed-entry')
        self.assertIsNone(result.matches_backup)
        self.assertEqual(self.config.read_text('utf-8'), '{\n  "mcpServers": {\n    "other": {"command": "x"}\n  }\n}\n')

    def test_our_entry_in_the_middle_of_several_members(self):
        original = ('{"mcpServers": {"a": 1, "agentchattr-fork": {"serverURL": "u"}, "c": [2]}, "k": 0}\n')
        self.write(original)
        result = self.remove()
        self.assertEqual(result.status, 'removed-entry')
        self.assertEqual(self.config.read_text('utf-8'), '{"mcpServers": {"a": 1, "c": [2]}, "k": 0}\n')

    def test_our_entry_the_only_member_leaves_an_empty_mcpservers(self):
        self.write('{\n  "theme": "dark",\n  "mcpServers": {\n    "agentchattr-fork": {"serverURL": "u"}\n  }\n}\n')
        result = self.remove()
        self.assertEqual(result.status, 'removed-entry')
        self.assertEqual(json.loads(self.config.read_text('utf-8')), {'theme': 'dark', 'mcpServers': {}})

    def test_backup_missing_falls_back_to_removing_the_entry(self):
        self.write(PRETTY2)
        receipt = self.apply()
        receipt.backup_path.unlink()
        result = self.remove(receipt)
        self.assertEqual(result.status, 'removed-entry')
        self.assertIs(result.matches_backup, False)
        self.assertEqual(result.differing_keys, ['<backup missing or changed>'])
        self.assertEqual(self.config.read_bytes(), PRETTY2.encode())

    def test_backup_tampered_falls_back_to_removing_the_entry(self):
        self.write(PRETTY2)
        receipt = self.apply()
        receipt.backup_path.write_bytes(b'{"tampered": true}')
        result = self.remove(receipt)
        self.assertEqual(result.status, 'removed-entry')
        self.assertIs(result.matches_backup, False)
        self.assertEqual(result.differing_keys, ['<backup missing or changed>'])
        self.assertEqual(self.config.read_bytes(), PRETTY2.encode())
        self.assertEqual(receipt.backup_path.read_bytes(), b'{"tampered": true}')   # not ours to repair

    def test_created_section_edited_since_removes_mcpservers_too(self):
        original = b'{\n  "theme": "dark"\n}\n'
        self.write(original)
        receipt = self.apply()
        self.assertTrue(receipt.created_section)
        self.config.write_bytes(self.config.read_bytes().replace(b'"dark"', b'"light"'))
        result = self.remove(receipt)
        self.assertEqual(result.status, 'removed-entry')
        self.assertEqual(self.config.read_bytes(), b'{\n  "theme": "light"\n}\n')

    def test_created_section_kept_when_the_user_added_a_sibling_server(self):
        self.write(b'{\n  "theme": "dark"\n}\n')
        receipt = self.apply()
        data = self.config.read_text('utf-8')
        data = data.replace('  "mcpServers": {\n', '  "mcpServers": {\n    "mine": {},\n', 1)
        self.config.write_text(data, 'utf-8', newline='')
        result = self.remove(receipt)
        self.assertEqual(result.status, 'removed-entry')
        after = json.loads(self.config.read_text('utf-8'))
        self.assertEqual(after, {'theme': 'dark', 'mcpServers': {'mine': {}}})

    def test_file_we_created_then_edited_is_not_deleted(self):
        receipt = self.apply()
        self.assertTrue(receipt.created_file)
        self.config.write_bytes(self.config.read_bytes() + b'\n')
        result = self.remove(receipt)
        self.assertEqual(result.status, 'removed-entry')
        self.assertIsNone(result.matches_backup)
        self.assertTrue(self.config.exists())
        self.assertEqual(json.loads(self.config.read_text('utf-8')), {})

    def test_no_receipt_removes_the_entry(self):
        self.write(PRETTY2)
        self.apply()
        result = self.remove()
        self.assertEqual(result.status, 'removed-entry')
        self.assertIsNone(result.matches_backup)
        self.assertEqual(result.differing_keys, [])
        self.assertEqual(self.config.read_bytes(), PRETTY2.encode())

    def test_no_receipt_removes_a_crlf_entry_exactly(self):
        original = (json.dumps(BASE_OBJ, indent=2) + '\n').replace('\n', '\r\n').encode()
        self.write(original)
        self.apply()
        self.remove()
        self.assertEqual(self.config.read_bytes(), original)

    def test_entry_absent_is_a_no_op(self):
        self.write(PRETTY2)
        result = self.remove()
        self.assertEqual(result.status, 'absent')
        self.assertIsNone(result.matches_backup)
        self.assertEqual(result.differing_keys, [])
        self.assertEqual(self.config.read_bytes(), PRETTY2.encode())
        self.assertEqual(self.logs, [])

    def test_mcpservers_absent_is_a_no_op(self):
        self.write(b'{"theme": "dark"}')
        self.assertEqual(self.remove().status, 'absent')
        self.assertEqual(self.config.read_bytes(), b'{"theme": "dark"}')

    def test_file_absent_is_a_no_op(self):
        result = self.remove()
        self.assertEqual(result.status, 'absent')
        self.assertFalse(self.config.exists())

    def test_removal_never_touches_the_users_own_agentchattr_entry(self):
        original = (json.dumps(BASE_OBJ, indent=2) + '\n').encode()
        self.write(original)
        receipt = self.apply()
        self.config.write_bytes(self.config.read_bytes().replace(b'"dark"', b'"light"'))
        self.remove(receipt)
        after = json.loads(self.config.read_text('utf-8'))
        self.assertEqual(after['mcpServers']['agentchattr'], BASE_OBJ['mcpServers']['agentchattr'])
        self.assertEqual(list(after['mcpServers']), ['agentchattr', 'other'])


class RepeatedCycleTests(Base):
    def test_apply_refresh_remove_three_times_returns_the_exact_original(self):
        samples = {name: data for name, data in format_samples().items()}
        samples['missing mcpServers'] = b'{\n  "theme": "dark"\n}\n'
        samples['empty root'] = b'{}\n'
        samples['empty mcpServers'] = b'{\n  "mcpServers": {}\n}\n'
        for name, original in samples.items():
            with self.subTest(format=name):
                for stale in self.home.glob('*'):
                    stale.unlink()
                self.write(original)
                for cycle in range(3):
                    receipt = self.apply(token=TOKEN)
                    self.apply(token=TOKEN2)                      # refresh
                    self.assertNotIn(TOKEN.encode(), self.config.read_bytes())
                    result = self.remove(receipt)
                    self.assertEqual(result.status, 'removed-entry', (name, cycle))
                    self.assertIs(result.matches_backup, True, (name, cycle))
                    self.assertEqual(self.config.read_bytes(), original, (name, cycle))
                self.assertEqual(self.tmps(), [])

    def test_plain_apply_remove_three_times_restores_exactly(self):
        original = (json.dumps(BASE_OBJ, indent=2) + '\n').encode()
        self.write(original)
        for cycle in range(3):
            receipt = self.apply()
            self.assertEqual(self.remove(receipt).status, 'restored-exact')
            self.assertEqual(self.config.read_bytes(), original, cycle)
        self.assertEqual(len(self.baks()), 3)
        self.assertNoSecrets()

    def test_created_file_cycles(self):
        for cycle in range(3):
            receipt = self.apply()
            self.assertEqual(self.remove(receipt).status, 'deleted-created-file')
            self.assertFalse(self.config.exists(), cycle)


class ConcurrentWriterTests(Base):
    def test_apply_redoes_its_plan_when_the_file_changes_before_replace(self):
        original = PRETTY2
        self.write(original)
        real = jm._atomic_write
        calls = []

        def racing(path, data, expect):
            if not calls:
                Path(path).write_bytes(original.replace('"theme": "dark"', '"theme": "dark", "added": 1').encode())
            calls.append(1)
            return real(path, data, expect)
        with patch.object(jm, '_atomic_write', side_effect=racing):
            receipt = self.apply()
        data = json.loads(self.config.read_text('utf-8'))
        self.assertEqual(data['added'], 1)                       # the concurrent edit survived
        self.assertIn(ENTRY, data['mcpServers'])
        self.assertEqual(len(calls), 2)
        self.assertEqual(self.tmps(), [])
        self.assertEqual(len(self.baks()), 1)                    # the first attempt's backup was removed
        self.assertEqual(receipt.backup_path.read_bytes(), original.replace('"theme": "dark"', '"theme": "dark", "added": 1').encode())
        self.assertNoSecrets()

    def test_apply_redoes_its_plan_when_a_missing_file_appears(self):
        real = jm._atomic_write
        calls = []

        def racing(path, data, expect):
            if not calls:
                Path(path).write_bytes(b'{"theme": "dark"}\n')
            calls.append(1)
            return real(path, data, expect)
        with patch.object(jm, '_atomic_write', side_effect=racing):
            receipt = self.apply()
        self.assertEqual(len(calls), 2)
        self.assertFalse(receipt.created_file)
        data = json.loads(self.config.read_text('utf-8'))
        self.assertEqual(data['theme'], 'dark')
        self.assertIn(ENTRY, data['mcpServers'])
        self.assertEqual(receipt.backup_path.read_bytes(), b'{"theme": "dark"}\n')

    def test_apply_refuses_when_the_file_keeps_changing(self):
        self.write(PRETTY2)
        real = jm._atomic_write
        counter = iter(range(100))

        def always_racing(path, data, expect):
            Path(path).write_bytes(PRETTY2.replace('"dark"', f'"dark{next(counter)}"').encode())
            return real(path, data, expect)
        with patch.object(jm, '_atomic_write', side_effect=always_racing):
            with self.assertRaises(JsonSettingsError) as caught:
                self.apply()
        self.assertNotIn(TOKEN.encode(), self.config.read_bytes())
        self.assertNotIn('TOKENVAL', str(caught.exception))
        self.assertEqual(self.baks(), [])                        # our temporary backups were removed
        self.assertEqual(self.tmps(), [])
        self.assertEqual(json.loads(self.config.read_text('utf-8'))['theme'], 'dark1')   # the writer's last bytes
        self.assertEqual(self.logs, [])

    def test_apply_refuses_when_current_bytes_always_differs_from_the_plan(self):
        self.write(PRETTY2)
        original_read = jm._current_bytes
        state = {'n': 0}

        def shifting(path):
            data = original_read(path)
            state['n'] += 1
            return data if state['n'] % 2 else (data or b'') + b' '
        with patch.object(jm, '_current_bytes', side_effect=shifting):
            with self.assertRaises(JsonSettingsError):
                self.apply()
        self.assertEqual(self.config.read_bytes(), PRETTY2.encode())
        self.assertEqual(self.baks(), [])
        self.assertEqual(self.tmps(), [])

    def test_remove_redoes_its_plan_when_the_file_changes_before_replace(self):
        self.write(PRETTY2)
        receipt = self.apply()
        real = jm._atomic_write
        calls = []

        def racing(path, data, expect):
            if not calls:
                current = Path(path).read_bytes()
                Path(path).write_bytes(current.replace(b'"dark"', b'"light"'))
            calls.append(1)
            return real(path, data, expect)
        with patch.object(jm, '_atomic_write', side_effect=racing):
            result = self.remove(receipt)
        self.assertEqual(len(calls), 2)
        self.assertEqual(result.status, 'removed-entry')
        self.assertEqual(self.config.read_bytes(), PRETTY2.replace('"dark"', '"light"').encode())
        self.assertEqual(self.tmps(), [])

    def test_remove_refuses_when_the_file_keeps_changing(self):
        self.write(PRETTY2)
        receipt = self.apply()
        real = jm._atomic_write
        counter = iter(range(100))

        def always_racing(path, data, expect):
            next(counter)
            Path(path).write_bytes(Path(path).read_bytes() + b' ')
            return real(path, data, expect)
        with patch.object(jm, '_atomic_write', side_effect=always_racing):
            with self.assertRaises(JsonSettingsError):
                self.remove(receipt)
        self.assertIn(ENTRY.encode(), self.config.read_bytes())  # untouched by us
        self.assertEqual(self.tmps(), [])

    def test_atomic_write_checks_the_expected_bytes_and_cleans_up(self):
        self.write(b'{}')
        with self.assertRaises(jm._ChangedUnderUs):
            jm._atomic_write(self.config, b'{"a": 1}', b'something else')
        self.assertEqual(self.config.read_bytes(), b'{}')
        self.assertEqual(self.tmps(), [])
        jm._atomic_write(self.config, b'{"a": 1}', b'{}')
        self.assertEqual(self.config.read_bytes(), b'{"a": 1}')
        self.assertEqual(self.tmps(), [])
        missing = self.home / 'new.json'
        jm._atomic_write(missing, b'{}', None)
        self.assertEqual(missing.read_bytes(), b'{}')
        with self.assertRaises(jm._ChangedUnderUs):
            jm._atomic_write(missing, b'{}', None)
        self.assertEqual(self.tmps(), [])

    def test_atomic_write_retries_a_transient_permission_error(self):
        self.write(b'{}')
        real = os.replace
        calls = []

        def flaky(source, target):
            calls.append(1)
            if len(calls) < 3:
                raise PermissionError('busy')
            return real(source, target)
        with patch.object(jm.os, 'replace', side_effect=flaky), patch.object(jm.time, 'sleep'):
            jm._atomic_write(self.config, b'{"a": 1}', b'{}')
        self.assertEqual(len(calls), 3)
        self.assertEqual(self.config.read_bytes(), b'{"a": 1}')
        self.assertEqual(self.tmps(), [])

    def test_atomic_write_gives_up_on_a_persistent_permission_error(self):
        self.write(b'{}')
        with patch.object(jm.os, 'replace', side_effect=PermissionError('busy')), patch.object(jm.time, 'sleep'):
            with self.assertRaises(PermissionError):
                jm._atomic_write(self.config, b'{"a": 1}', b'{}')
        self.assertEqual(self.config.read_bytes(), b'{}')
        self.assertEqual(self.tmps(), [])


class VerifyOnlyOneKeyChangedTests(unittest.TestCase):
    def verify(self, before, after, entry=ENTRY):
        return jm.verify_only_one_key_changed(before, after, entry=entry)

    def test_accepts_adding_our_entry(self):
        changed = self.verify('{"a": 1, "mcpServers": {"x": 1}}', '{"a": 1, "mcpServers": {"x": 1, "%s": {}}}' % ENTRY)
        self.assertEqual(changed, ['mcpServers.%s' % ENTRY])

    def test_accepts_replacing_or_removing_our_entry(self):
        before = '{"mcpServers": {"x": 1, "%s": {"a": 1}}}' % ENTRY
        self.assertEqual(self.verify(before, '{"mcpServers": {"x": 1, "%s": {"a": 2}}}' % ENTRY), ['mcpServers.%s' % ENTRY])
        self.assertEqual(self.verify(before, '{"mcpServers": {"x": 1}}'), ['mcpServers.%s' % ENTRY])

    def test_accepts_creating_and_removing_mcpservers_that_holds_only_ours(self):
        with_section = '{"a": 1, "mcpServers": {"%s": {}}}' % ENTRY
        self.assertEqual(self.verify('{"a": 1}', with_section), ['mcpServers'])
        self.assertEqual(self.verify(with_section, '{"a": 1}'), ['mcpServers'])

    def test_accepts_an_unchanged_document(self):
        self.assertEqual(self.verify('{"a": 1}', '{"a":   1}'), [])

    def test_rejects_other_key_changes(self):
        cases = [
            ('{"a": 1, "mcpServers": {}}', '{"a": 2, "mcpServers": {"%s": {}}}' % ENTRY),
            ('{"a": 1}', '{"a": 1, "b": 2, "mcpServers": {"%s": {}}}' % ENTRY),
            ('{"a": 1, "b": 2}', '{"a": 1}'),
            ('{"mcpServers": {"x": 1}}', '{"mcpServers": {"x": 2, "%s": {}}}' % ENTRY),
            ('{"mcpServers": {"x": 1}}', '{"mcpServers": {"%s": {}}}' % ENTRY),
            ('{"mcpServers": {"x": 1, "%s": {}}}' % ENTRY, '{"mcpServers": {"x": 1, "y": 2}}'),
            ('{"a": {"b": 1}}', '{"a": {"b": 2}, "mcpServers": {"%s": {}}}' % ENTRY),
            ('{"mcpServers": {"x": {"k": 1}}}', '{"mcpServers": {"x": {"k": 1, "j": 2}, "%s": {}}}' % ENTRY),
        ]
        for before, after in cases:
            with self.subTest(before=before, after=after):
                with self.assertRaises(JsonSettingsError):
                    self.verify(before, after)

    def test_rejects_key_reordering(self):
        cases = [
            ('{"a": 1, "b": 2}', '{"b": 2, "a": 1}'),
            ('{"mcpServers": {"x": 1, "y": 2}}', '{"mcpServers": {"y": 2, "x": 1, "%s": {}}}' % ENTRY),
            ('{"a": {"p": 1, "q": 2}}', '{"a": {"q": 2, "p": 1}}'),
        ]
        for before, after in cases:
            with self.subTest(before=before, after=after):
                with self.assertRaises(JsonSettingsError):
                    self.verify(before, after)

    def test_rejects_an_empty_mcpservers_that_moves_while_gaining_our_entry(self):
        # _without() drops an empty mcpServers before comparing, so its position is pinned separately.
        with self.assertRaises(JsonSettingsError):
            self.verify('{"a": 1, "mcpServers": {}}', '{"mcpServers": {"%s": {}}, "a": 1}' % ENTRY)

    def test_rejects_type_changes(self):
        for left, right in (('1', '1.0'), ('1', 'true'), ('1.0', 'true'), ('0', 'false'), ('1.0', '1'),
                            ('true', '1'), ('"1"', '1'), ('null', '0'), ('[]', '{}'), ('[1]', '[1.0]'), ('[true]', '[1]')):
            with self.subTest(left=left, right=right):
                with self.assertRaises(JsonSettingsError):
                    self.verify('{"a": %s}' % left, '{"a": %s}' % right)
                with self.assertRaises(JsonSettingsError):
                    self.verify('{"a": %s}' % left, '{"a": %s, "mcpServers": {"%s": {}}}' % (right, ENTRY))

    def test_error_message_names_the_key_path_only(self):
        with self.assertRaises(JsonSettingsError) as caught:
            self.verify('{"a": "%s"}' % USER_SECRET, '{"a": "other"}')
        self.assertIn('a', str(caught.exception))
        self.assertNotIn(USER_SECRET, str(caught.exception))
        self.assertNotIn('other', str(caught.exception))

    def test_non_object_roots_are_rejected(self):
        with self.assertRaises(JsonSettingsError):
            self.verify('[1]', '{"a": 1}')
        with self.assertRaises(JsonSettingsError):
            self.verify('{"a": 1}', '[1]')

    def test_invalid_input_is_refused(self):
        with self.assertRaises(JsonSettingsError):
            self.verify('{"a": 1', '{"a": 1}')
        with self.assertRaises(JsonSettingsError):
            self.verify('{"a": 1}', '{"a": 1, "a": 2}')


class LogTests(Base):
    def test_token_is_never_printed_and_lines_carry_path_and_sha256(self):
        self.write(PRETTY2)
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            receipt = jm.apply(self.config, URL, TOKEN)
            jm.apply(self.config, URL, TOKEN2)
            jm.remove_exact(self.config, receipt=receipt)
        text = out.getvalue()
        self.assertNotIn('TOKENVAL', text)
        lines = text.splitlines()
        self.assertEqual(len(lines), 4)                          # backed up, added, refreshed, removed
        for line in lines:
            self.assertRegex(line, r'sha256 [0-9a-f]{64}')
        self.assertIn(str(receipt.backup_path), lines[0])
        self.assertIn(receipt.backup_sha256, lines[0])
        self.assertIn('Added', lines[1])
        self.assertIn(str(self.config), lines[1])
        self.assertIn(receipt.written_sha256, lines[1])
        self.assertIn('Refreshed', lines[2])
        self.assertIn(str(self.config), lines[2])
        self.assertIn('Removed', lines[3])
        self.assertIn(self.config.name, lines[3])

    def test_restore_and_delete_lines_carry_sha256_and_no_token(self):
        self.write(PRETTY2)
        receipt = self.apply()
        self.remove(receipt)
        receipt = self.apply()                                   # a second backup
        self.config.unlink()
        self.assertEqual(self.remove(receipt).status, 'absent')
        fresh = self.home / 'fresh'
        fresh.mkdir()
        created = jm.apply(fresh / 'mcp_config.json', URL, TOKEN, log=self.logs.append)
        jm.remove_exact(fresh / 'mcp_config.json', receipt=created, log=self.logs.append)
        text = '\n'.join(self.logs)
        self.assertNotIn('TOKENVAL', text)
        self.assertRegex(text, r'Restored mcp_config\.json from backup \(sha256 [0-9a-f]{64}\)')
        self.assertIn('created for this run; sha256 matched', text)
        self.assertIn(str(fresh / 'mcp_config.json'), text)

    def test_removal_log_reports_the_backup_comparison(self):
        self.write(PRETTY2)
        receipt = self.apply()
        self.config.write_bytes(self.config.read_bytes().replace(b'"dark"', b'"light"'))
        self.logs.clear()
        self.remove(receipt)
        self.assertIn('differs from backup at theme', self.logs[-1])
        self.assertNotIn('TOKENVAL', self.logs[-1])

    def test_refusal_and_failure_output_carries_no_token(self):
        self.write(('{"x": "%s", "x": 1}' % TOKEN).encode())
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            with self.assertRaises(JsonSettingsError) as caught:
                jm.apply(self.config, URL, TOKEN)
        self.assertNotIn('TOKENVAL', out.getvalue())
        self.assertNotIn('TOKENVAL', str(caught.exception))
        self.assertNotIn('TOKENVAL', repr(caught.exception))


class ResolveSettingsPathTests(Base):
    def test_variable_forms_expand(self):
        with patch.dict(os.environ, {'AGY_TEST_HOME': str(self.home)}):
            self.assertEqual(jm.resolve_settings_path('$AGY_TEST_HOME/mcp_config.json'), self.config)
            self.assertEqual(jm.resolve_settings_path('${AGY_TEST_HOME}/mcp_config.json'), self.config)
            if os.name == 'nt':
                self.assertEqual(jm.resolve_settings_path('%AGY_TEST_HOME%/mcp_config.json'), self.config)

    def test_tilde_expands(self):
        home = Path(self.tmp.name) / 'userhome'
        with patch.dict(os.environ, {'HOME': str(home), 'USERPROFILE': str(home)}):
            self.assertEqual(jm.resolve_settings_path('~/.gemini/config/mcp_config.json'),
                             home / '.gemini' / 'config' / 'mcp_config.json')

    def test_unset_variable_raises(self):
        os.environ.pop('AGY_TEST_UNSET', None)
        for raw in ('$AGY_TEST_UNSET/mcp_config.json', '${AGY_TEST_UNSET}/mcp_config.json', '%AGY_TEST_UNSET%/mcp_config.json'):
            with self.subTest(raw=raw):
                with self.assertRaises(JsonSettingsError):
                    jm.resolve_settings_path(raw)

    def test_variable_set_to_empty_is_refused(self):
        for empty in ('', '   '):
            with self.subTest(value=repr(empty)), patch.dict(os.environ, {'AGY_TEST_HOME': empty}):
                with self.assertRaises(JsonSettingsError):
                    jm.resolve_settings_path('$AGY_TEST_HOME/mcp_config.json')
                with self.assertRaises(JsonSettingsError):
                    jm.resolve_settings_path('${AGY_TEST_HOME}/mcp_config.json')

    def test_empty_raises(self):
        for raw in ('', '   ', None, 5):
            with self.subTest(raw=raw):
                with self.assertRaises(JsonSettingsError):
                    jm.resolve_settings_path(raw)

    def test_relative_path_joins_project_dir(self):
        project = Path(self.tmp.name) / 'project'
        self.assertEqual(jm.resolve_settings_path('sub/mcp_config.json', project), project / 'sub' / 'mcp_config.json')

    def test_absolute_path_ignores_project_dir(self):
        project = Path(self.tmp.name) / 'project'
        self.assertEqual(jm.resolve_settings_path(str(self.config), project), self.config)


class AgyRunningTests(unittest.TestCase):
    def run_with(self, platform, output=None, error=None, **kwargs):
        def fake(*args, **kw):
            if error:
                raise error
            return SimpleNamespace(stdout=output)
        kwargs.setdefault('install_root', os.path.join(os.sep, 'fake', 'agy', 'bin'))
        with patch.object(jm.sys, 'platform', platform), patch.object(jm.subprocess, 'run', side_effect=fake) as run, \
                patch.object(jm, '_windows_executable_paths', return_value=[]):   # never touch real processes
            result = jm.agy_running(**kwargs)
        return result, run

    def test_windows_tasklist(self):
        csv = '"System","4","Services","0","100 K"\n"agy.exe","123","Console","1","50,000 K"\n'
        result, run = self.run_with('win32', csv)
        self.assertIs(result, True)
        command = run.call_args.args[0]
        self.assertTrue(command[0].lower().endswith(os.path.join('system32', 'tasklist.exe')), command[0])
        self.assertTrue(os.path.isabs(command[0]))
        self.assertEqual(command[1:], ['/FO', 'CSV', '/NH'])
        self.assertEqual(run.call_count, 1)
        self.assertTrue(run.call_args.kwargs.get('timeout'))
        self.assertTrue(run.call_args.kwargs.get('capture_output'))

    def test_windows_without_agy(self):
        result, run = self.run_with('win32', '"System","4","Services","0","100 K"\n"python.exe","9","Console","1","1 K"\n')
        self.assertIs(result, False)
        argv = [a.lower() for a in run.call_args.args[0]]
        self.assertNotIn('/v', argv)
        self.assertNotIn('/svc', argv)
        self.assertTrue(argv[0].endswith(os.path.join('system32', 'tasklist.exe')), argv[0])
        self.assertEqual(argv[1:], ['/fo', 'csv', '/nh'])

    def test_windows_match_is_case_insensitive_and_by_image_name_only(self):
        result, _ = self.run_with('win32', '"AGY.EXE","1","Console","1","1 K"\n')
        self.assertIs(result, True)
        for output in ('"notagy.exe","1","Console","1","1 K"\n', '"agy.exe.bak","1","Console","1","1 K"\n',
                       '"node.exe","1","agy.exe","1","1 K"\n', '"python.exe","1","Console","1","agy 1 K"\n'):
            with self.subTest(output=output):
                result, _ = self.run_with('win32', output)
                self.assertIs(result, False)

    def test_custom_image_names(self):
        csv = '"node.exe","1","Console","1","1 K"\n'
        self.assertIs(self.run_with('win32', csv)[0], False)
        self.assertIs(self.run_with('win32', csv, image_names=('node.exe',))[0], True)
        self.assertIs(self.run_with('win32', csv, image_names=('NODE.EXE',))[0], True)

    def test_windows_oserror_timeout_and_empty_output_are_none(self):
        self.assertIsNone(self.run_with('win32', error=OSError('no tasklist'))[0])
        self.assertIsNone(self.run_with('win32', error=subprocess.TimeoutExpired('tasklist', 15))[0])
        self.assertIsNone(self.run_with('win32', error=subprocess.SubprocessError('boom'))[0])
        self.assertIsNone(self.run_with('win32', '')[0])
        self.assertIsNone(self.run_with('win32', b'')[0])
        self.assertIsNone(self.run_with('win32', None)[0])
        self.assertIsNone(self.run_with('win32', 'INFO: no tasks\n')[0])

    def test_undecodable_bytes_and_value_errors_give_none_or_a_result_not_an_exception(self):
        result, _ = self.run_with('win32', b'"agy.exe","1","Console","1","1 K"\n"\xff\xfe.exe","2"\n')
        self.assertIs(result, True)
        result, _ = self.run_with('win32', b'"\xff\xfe.exe","2"\n')
        self.assertIs(result, False)
        result, _ = self.run_with('win32', error=ValueError('bad'))
        self.assertIsNone(result)

    def test_posix_ps_lists_image_names_only(self):
        result, run = self.run_with('linux', 'init\n/usr/local/bin/agy\n')
        self.assertIs(result, True)
        self.assertEqual(run.call_args.args[0], ['ps', '-A', '-o', 'comm='])
        self.assertEqual(run.call_count, 1)
        self.assertTrue(run.call_args.kwargs.get('timeout'))
        self.assertIs(self.run_with('linux', 'init\nbash\n')[0], False)
        self.assertIs(self.run_with('linux', 'init\n/opt/agy-tools/helper\nagyx\n')[0], False)
        self.assertIs(self.run_with('darwin', '  AGY  \n')[0], True)

    def test_posix_failures_are_none(self):
        self.assertIsNone(self.run_with('linux', error=OSError('no ps'))[0])
        self.assertIsNone(self.run_with('linux', error=subprocess.TimeoutExpired('ps', 15))[0])
        self.assertIsNone(self.run_with('linux', '')[0])
        self.assertIsNone(self.run_with('linux', '\n  \n')[0])
        self.assertIsNone(self.run_with('linux', b'')[0])

    def test_posix_undecodable_bytes_are_replaced(self):
        result, _ = self.run_with('linux', b'init\n\xff\xfe\nagy\n')
        self.assertIs(result, True)
        result, _ = self.run_with('linux', b'init\n\xff\xfe\n')
        self.assertIs(result, False)

    def test_system_root_is_used_for_the_tasklist_path(self):
        with patch.dict(os.environ, {'SystemRoot': r'D:\WinRoot'}):
            result, run = self.run_with('win32', '"agy.exe","1","Console","1","1 K"\n')
        self.assertIs(result, True)
        self.assertEqual(run.call_args.args[0][0], os.path.join(r'D:\WinRoot', 'System32', 'tasklist.exe'))


class AgyRunningByPathTests(unittest.TestCase):
    """Executable-path detection, with fake process lists only (no real process access)."""

    def setUp(self):
        self.root = os.path.join(tempfile.gettempdir(), 'fake-localappdata', 'agy', 'bin')

    def running(self, *processes, **kwargs):
        kwargs.setdefault('install_root', self.root)
        return jm.agy_running(lister=lambda: list(processes), **kwargs)

    def test_renamed_executable_under_the_root_is_detected(self):
        self.assertIs(self.running(('svchost.exe', None), ('agy-cli.exe', os.path.join(self.root, 'agy-cli.exe'))), True)
        self.assertIs(self.running(('x.exe', os.path.join(self.root, 'nested', 'x.exe'))), True)

    def test_other_paths_are_not_detected(self):
        self.assertIs(self.running(('node.exe', os.path.join(os.sep, 'tools', 'node.exe')), ('svchost.exe', None)), False)

    def test_sibling_prefix_is_not_under_the_root(self):
        self.assertIs(self.running(('x.exe', self.root + '2' + os.sep + 'x.exe'),
                                   ('y.exe', os.path.dirname(self.root) + os.sep + 'binary.exe')), False)

    @unittest.skipUnless(sys.platform == 'win32', 'normcase folds case and slashes only on Windows')
    def test_case_and_slash_variants_are_detected(self):
        variant = os.path.join(self.root.upper(), 'x.exe').replace('\\', '/')
        self.assertIs(self.running(('x.exe', variant)), True)
        self.assertIs(self.running(('x.exe', os.path.join(self.root, '.', 'sub', '..', 'x.exe'))), True)
        self.assertIs(jm.agy_running(lister=lambda: [('x.exe', os.path.join(self.root, 'x.exe'))],
                                     install_root=self.root.replace('\\', '/') + '/'), True)

    def test_image_name_match_still_counts_without_a_path(self):
        self.assertIs(self.running(('AGY.EXE', None)), True)

    def test_lister_failure_is_none(self):
        for error in (OSError('denied'), ValueError('empty'), subprocess.TimeoutExpired('tasklist', 15)):
            def broken(error=error):
                raise error
            with self.subTest(error=type(error).__name__):
                self.assertIsNone(jm.agy_running(lister=broken, install_root=self.root))

    def test_empty_list_is_none(self):
        self.assertIsNone(self.running())

    def test_no_known_install_root_is_none_unless_a_name_matches(self):
        with patch.object(jm, '_default_install_root', return_value=None):
            self.assertIsNone(jm.agy_running(lister=lambda: [('node.exe', os.path.join(os.sep, 'n.exe'))]))
            self.assertIs(jm.agy_running(lister=lambda: [('agy.exe', None)]), True)

    def test_default_root_is_localappdata_agy_bin(self):
        with patch.object(jm.sys, 'platform', 'win32'), patch.dict(os.environ, {'LOCALAPPDATA': self.root}):
            self.assertEqual(jm._default_install_root(), os.path.join(self.root, 'agy', 'bin'))
        with patch.object(jm.sys, 'platform', 'win32'), patch.dict(os.environ, {'LOCALAPPDATA': ''}):
            self.assertIsNone(jm._default_install_root())
        with patch.object(jm.sys, 'platform', 'linux'):
            self.assertIsNone(jm._default_install_root())

    def test_windows_default_lister_combines_tasklist_names_and_ctypes_paths(self):
        exe = os.path.join(self.root, 'renamed.exe')
        with patch.object(jm.sys, 'platform', 'win32'), \
                patch.object(jm.subprocess, 'run', return_value=SimpleNamespace(stdout='"System","4"\n')), \
                patch.object(jm, '_windows_executable_paths', return_value=[exe]) as paths:
            self.assertIs(jm.agy_running(install_root=self.root), True)
        paths.assert_called_once_with()

    def test_ctypes_failure_gives_none(self):
        with patch.object(jm.sys, 'platform', 'win32'), \
                patch.object(jm.subprocess, 'run', return_value=SimpleNamespace(stdout='"System","4"\n')), \
                patch.object(jm, '_windows_executable_paths', side_effect=OSError('EnumProcesses failed')):
            self.assertIsNone(jm.agy_running(install_root=self.root))


if __name__ == '__main__':
    unittest.main()
