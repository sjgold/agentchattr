"""yaml_mcp_settings, tested directly: byte-level preservation, refusals, backups, exact removal.

Every test works in a temporary directory standing in for HERMES_HOME; no real Hermes
configuration is read, listed or written.
"""
import contextlib
import dataclasses
import hashlib
import io
import os
from pathlib import Path
import re
import sys
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import yaml  # noqa: E402
import yaml_mcp_settings as ym  # noqa: E402
from yaml_mcp_settings import YamlSettingsError  # noqa: E402

TOKEN = 'tok_SECRET_feedfacecafebeef0123456789'
TOKEN2 = 'tok_SECRET_0000111122223333aaaabbbb'
URL = 'http://127.0.0.1:49961/mcp'
BAK_NAME = re.compile(r'config\.yaml\.agentchattr-uat-\d{8}T\d{6}Z-[0-9a-f]{6}\.bak')

ORIGINAL = (
    '# top comment\n'
    "model: 'hermes-3'   # single quoted\n"
    'name: "dq"\n'
    'plain: value\n'
    '\n'
    '\n'
    'defaults: &d\n'
    '  x: 1\n'
    'copy: *d\n'
    '\n'
    'mcp_servers:\n'
    '  # leading comment\n'
    '  agentchattr:\n'
    '    url: "http://127.0.0.1:8200/mcp"  # the real one\n'
    '    tags: [a, b]\n'
    "  other: {url: 'x'}   # flow child\n"
    '\n'
    '# terminal next\n'
    'terminal:\n'
    '  backend: local\n'
)


def entry_text(indent='  ', nl='\n', token=TOKEN):
    return nl.join([f'{indent}agentchattr-uat:', f'{indent}  url: "{URL}"', f'{indent}  headers:',
                    f'{indent}    Authorization: "Bearer {token}"']) + nl


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.home = Path(self.tmp.name) / 'hermes home'
        self.home.mkdir()
        self.config = self.home / 'config.yaml'
        patcher = patch.dict(os.environ, {'HERMES_HOME': str(self.home)})
        patcher.start()
        self.addCleanup(patcher.stop)
        self.logs = []

    def write(self, data):
        self.config.write_bytes(data.encode('utf-8') if isinstance(data, str) else data)

    def apply(self, token=TOKEN):
        return ym.apply(self.config, URL, token, log=self.logs.append)

    def remove(self, receipt=None):
        return ym.remove_exact(self.config, receipt=receipt, log=self.logs.append)

    def baks(self):
        return sorted(self.home.glob('*.bak'))

    def assertNoSecrets(self):
        self.assertNotIn('SECRET', '\n'.join(self.logs))
        for bak in self.baks():
            self.assertNotIn(b'SECRET', bak.read_bytes())

    def assertInsertOnly(self, before, after, inserted):
        """after is before with exactly `inserted` placed at a line boundary."""
        starts = [0] + [m.end() for m in re.finditer(r'\n', before)]
        ok = any(after == before[:i] + inserted + before[i:] for i in starts)
        self.assertTrue(ok, 'diff is not exactly the inserted entry lines')

    def assertRefused(self, content, fragment=None):
        self.write(content)
        before = self.config.read_bytes()
        with self.assertRaises(YamlSettingsError) as caught:
            self.apply()
        self.assertEqual(self.config.read_bytes(), before)
        self.assertEqual(self.baks(), [])
        self.assertNotIn('SECRET', str(caught.exception))
        if fragment:
            self.assertNotIn(fragment, str(caught.exception))
        return caught.exception


class PreservationTests(Base):
    def test_diff_is_exactly_the_inserted_entry_lines(self):
        self.write(ORIGINAL)
        self.apply()
        after = self.config.read_text('utf-8')
        self.assertInsertOnly(ORIGINAL, after, entry_text())
        # inserted at the end of the mcp_servers block, before the blank line and next comment
        self.assertIn('  other: {url: \'x\'}   # flow child\n  agentchattr-uat:', after)
        self.assertIn('Bearer ' + TOKEN + '"\n\n# terminal next\n', after)
        data = yaml.safe_load(after)
        self.assertEqual(data['mcp_servers']['agentchattr'], {'url': 'http://127.0.0.1:8200/mcp', 'tags': ['a', 'b']})
        self.assertNoSecrets()

    def test_refresh_replaces_only_our_entry(self):
        self.write(ORIGINAL)
        self.apply()
        self.apply(TOKEN2)
        after = self.config.read_text('utf-8')
        self.assertInsertOnly(ORIGINAL, after, entry_text(token=TOKEN2))
        self.assertNotIn(TOKEN, after)


class FileShapeTests(Base):
    def test_missing_file_in_existing_dir_is_created(self):
        receipt = self.apply()
        self.assertTrue(receipt.created_file)
        self.assertTrue(receipt.created_section)
        self.assertEqual(self.config.read_text('utf-8'), 'mcp_servers:\n' + entry_text())
        self.assertIsNone(receipt.backup_path)
        self.assertEqual(self.baks(), [])

    def test_missing_parent_dir_is_refused(self):
        target = self.home / 'nope' / 'config.yaml'
        with self.assertRaises(YamlSettingsError):
            ym.apply(target, URL, TOKEN, log=self.logs.append)
        self.assertFalse(target.parent.exists())

    def test_empty_file(self):
        self.write('')
        receipt = self.apply()
        self.assertEqual(self.config.read_text('utf-8'), 'mcp_servers:\n' + entry_text())
        self.assertEqual(receipt.backup_path.read_bytes(), b'')

    def test_comments_only_file(self):
        original = '# just a comment\n# and another\n'
        self.write(original)
        self.apply()
        after = self.config.read_text('utf-8')
        self.assertTrue(after.startswith(original))
        self.assertEqual(after, original + 'mcp_servers:\n' + entry_text())

    def test_no_mcp_servers_key(self):
        original = 'model: x  # c\nterminal:\n  backend: local\n'
        self.write(original)
        self.apply()
        after = self.config.read_text('utf-8')
        self.assertEqual(after, original + 'mcp_servers:\n' + entry_text())

    def test_empty_mcp_servers_followed_by_another_key(self):
        original = '# head\nmcp_servers:\nterminal:\n  backend: local\n'
        self.write(original)
        self.apply()
        after = self.config.read_text('utf-8')
        self.assertEqual(after, '# head\nmcp_servers:\n' + entry_text() + 'terminal:\n  backend: local\n')

    def test_empty_flow_mapping_with_trailing_comment(self):
        original = 'mcp_servers: {}  # keep me\nterminal:\n  backend: local\n'
        self.write(original)
        self.apply()
        after = self.config.read_text('utf-8')
        self.assertIn('# keep me', after)
        self.assertTrue(after.endswith('terminal:\n  backend: local\n'))
        data = yaml.safe_load(after)
        self.assertEqual(list(data['mcp_servers']), ['agentchattr-uat'])
        self.assertEqual(data['terminal'], {'backend': 'local'})

    def test_crlf_file_keeps_crlf_everywhere(self):
        original = 'a: 1\r\n# c\r\nmcp_servers:\r\n  x:\r\n    url: "u"\r\n\r\nz: 2\r\n'
        self.write(original)
        self.apply()
        raw = self.config.read_bytes()
        self.assertIsNone(re.search(rb'(?<!\r)\n', raw), 'stray LF in CRLF file')
        self.assertInsertOnly(original, raw.decode('utf-8'), entry_text(nl='\r\n'))

    def test_crlf_file_without_section(self):
        original = 'a: 1\r\n'
        self.write(original)
        self.apply()
        raw = self.config.read_bytes()
        self.assertIsNone(re.search(rb'(?<!\r)\n', raw))
        self.assertEqual(raw.decode('utf-8'), original + 'mcp_servers:\r\n' + entry_text(nl='\r\n'))

    def test_utf8_bom_is_kept_once(self):
        original = b'\xef\xbb\xbfa: 1\nmcp_servers:\n  x:\n    url: "u"\n'
        self.write(original)
        receipt = self.apply()
        raw = self.config.read_bytes()
        self.assertTrue(raw.startswith(b'\xef\xbb\xbf'))
        self.assertFalse(raw.startswith(b'\xef\xbb\xbf\xef\xbb\xbf'))
        self.assertEqual(raw.count(b'\xef\xbb\xbf'), 1)
        self.remove(dataclasses.replace(receipt))
        self.assertEqual(self.config.read_bytes(), original)

    def test_no_trailing_newline(self):
        original = 'mcp_servers:\n  x:\n    url: "u"'
        self.write(original)
        self.apply()
        after = self.config.read_text('utf-8')
        self.assertTrue(after.startswith(original + '\n'))
        self.assertEqual(after, original + '\n' + entry_text())
        self.write('a: 1')
        self.apply()
        self.assertEqual(self.config.read_text('utf-8'), 'a: 1\nmcp_servers:\n' + entry_text())

    def test_deep_last_entry_then_blank_line_and_next_key_comment(self):
        original = ('mcp_servers:\n  agentchattr:\n    url: "x"\n    headers:\n      A: b\n'
                    '\n# next key comment\nterminal:\n  backend: local\n')
        self.write(original)
        self.apply()
        after = self.config.read_text('utf-8')
        self.assertIn('      A: b\n  agentchattr-uat:', after)
        self.assertIn('Bearer ' + TOKEN + '"\n\n# next key comment\nterminal:', after)
        self.assertInsertOnly(original, after, entry_text())

    def test_every_shape_round_trips_to_the_original_bytes(self):
        shapes = {
            'full': ORIGINAL.encode(),
            'empty': b'',
            'comments': b'# only\n',
            'no-key': b'a: 1\n',
            'null-section': b'mcp_servers:\nterminal:\n  backend: local\n',
            'empty-flow': b'mcp_servers: {}  # c\nz: 1\n',
            'crlf': b'a: 1\r\nmcp_servers:\r\n  x:\r\n    url: "u"\r\n',
            'bom': b'\xef\xbb\xbfa: 1\n',
            'no-newline': b'a: 1',
            'deep': b'mcp_servers:\n  a:\n    h:\n      k: v\n\n# n\nt: 1\n',
        }
        for name, original in shapes.items():
            with self.subTest(shape=name):
                self.write(original)
                receipt = self.apply()
                self.assertEqual(self.remove(receipt).status, 'restored-exact')
                self.assertEqual(self.config.read_bytes(), original)
        self.assertNoSecrets()

    def test_unwritable_characters_are_refused_without_echoing_the_token(self):
        self.write('a: 1\n')
        with self.assertRaises(YamlSettingsError) as caught:
            ym.apply(self.config, URL, 'tok_SECRET_"bad', log=self.logs.append)
        self.assertNotIn('SECRET', str(caught.exception))
        self.assertEqual(self.config.read_bytes(), b'a: 1\n')


class AnchorAndRefusalTests(Base):
    def test_anchors_and_aliases_elsewhere_are_allowed_and_kept(self):
        original = 'defaults: &d\n  x: 1\ncopy: *d\nmcp_servers:\n  a:\n    url: "u"\n'
        self.write(original)
        self.apply()
        after = self.config.read_text('utf-8')
        self.assertInsertOnly(original, after, entry_text())
        self.assertIn('&d', after)
        self.assertIn('*d', after)
        self.assertEqual(yaml.safe_load(after)['copy'], {'x': 1})

    def test_refusals_leave_the_file_byte_identical(self):
        cases = {
            'alias on mcp_servers': 'base: &b\n  a:\n    url: x\nmcp_servers: *b\n',
            'anchor on mcp_servers': 'mcp_servers: &m\n  a:\n    url: x\n',
            'merge key inside mcp_servers': 'base: &b\n  url: x\nmcp_servers:\n  <<: *b\n',
            'top-level merge key': 'base: &b\n  url: x\n<<: *b\nmcp_servers:\n  a:\n    url: x\n',
            'non-empty flow mapping': 'mcp_servers: {a: {url: x}}\n',
            'list root': '- a\n- b\n',
            'scalar root': 'hello\n',
            'two documents': 'a: 1\n---\nb: 2\n',
            'mcp_servers is a scalar': 'mcp_servers: nope\n',
            'mcp_servers is a list': 'mcp_servers:\n  - a\n',
        }
        for name, content in cases.items():
            with self.subTest(case=name):
                self.assertRefused(content)

    def test_invalid_yaml_error_does_not_quote_the_file(self):
        error = self.assertRefused('key: [SECRETCONTENT\nother: }\n', fragment='SECRETCONTENT')
        self.assertNotIn('other', str(error))

    def test_mixed_line_endings_are_refused(self):
        self.assertRefused('a: 1\r\nb: 2\nc: 3\r\n')

    def test_non_utf8_bytes_are_refused(self):
        self.assertRefused(b'a: \xff\xfe\x00bad\n')


class RepeatedApplyRemoveTests(Base):
    def merged(self, first, latest):
        return dataclasses.replace(first, written_sha256=latest.written_sha256)

    def test_three_cycles_restore_exact_bytes_and_add_one_backup_each(self):
        self.write(ORIGINAL)
        original = self.config.read_bytes()
        for cycle in range(1, 4):
            first = self.apply()
            latest = self.apply(TOKEN2)
            self.assertIsNone(latest.backup_path)          # refresh never takes a second backup
            result = self.remove(self.merged(first, latest))
            self.assertEqual(result.status, 'restored-exact')
            self.assertTrue(result.matches_backup)
            self.assertEqual(self.config.read_bytes(), original)
            self.assertEqual(len(self.baks()), cycle)
            self.assertNoSecrets()
        for bak in self.baks():
            self.assertTrue(BAK_NAME.fullmatch(bak.name), bak.name)
            self.assertEqual(bak.read_bytes(), original)

    def test_remove_without_receipt_removes_only_our_entry(self):
        for original in (ORIGINAL, 'mcp_servers:\nz: 1\n', 'a: 1\n', 'mcp_servers:\n  x:\n    url: "u"'):
            with self.subTest(original=original[:20]):
                self.write(original)
                self.apply()
                result = self.remove(None)
                self.assertEqual(result.status, 'removed-entry')
                self.assertIsNone(result.matches_backup)
                after = yaml.safe_load(self.config.read_text('utf-8')) or {}
                before = yaml.safe_load(original) or {}
                if after.get('mcp_servers') in (None, {}):
                    after.pop('mcp_servers', None)
                    before = {k: v for k, v in before.items() if not (k == 'mcp_servers' and v in (None, {}))}
                self.assertEqual(after, before)
                self.assertNotIn('agentchattr-uat', self.config.read_text('utf-8'))

    def test_remove_when_absent(self):
        self.write(ORIGINAL)
        result = self.remove(None)
        self.assertEqual(result.status, 'absent')
        self.assertEqual(self.config.read_bytes(), ORIGINAL.encode())
        self.config.unlink()
        self.assertEqual(self.remove(None).status, 'absent')

    def test_created_file_is_deleted_on_exact_removal(self):
        receipt = self.apply()
        self.assertEqual(self.remove(receipt).status, 'deleted-created-file')
        self.assertFalse(self.config.exists())


class ConcurrentEditTests(Base):
    def test_user_edit_after_apply_keeps_the_edit_and_drops_our_entry(self):
        self.write(ORIGINAL)
        receipt = self.apply()
        edited = self.config.read_text('utf-8').replace("model: 'hermes-3'", "model: 'hermes-4'")
        self.config.write_bytes(edited.encode('utf-8'))
        result = self.remove(receipt)
        self.assertEqual(result.status, 'removed-entry')
        self.assertIs(result.matches_backup, False)
        self.assertEqual(result.differing_keys, ['model'])
        text = self.config.read_text('utf-8')
        self.assertNotIn('agentchattr-uat', text)
        self.assertIn("model: 'hermes-4'", text)
        self.assertEqual(text, ORIGINAL.replace("'hermes-3'", "'hermes-4'"))
        joined = '\n'.join(self.logs) + ' '.join(result.differing_keys)
        self.assertNotIn('hermes-4', joined)
        self.assertNoSecrets()


class VerifyOnlyOneKeyChangedTests(unittest.TestCase):
    BEFORE = 'a: SECRETVAL1\nmcp_servers:\n  s1:\n    url: SECRETVAL2\n'

    def test_returns_the_changed_path(self):
        after = self.BEFORE + '  agentchattr-uat:\n    url: u\n'
        self.assertEqual(ym.verify_only_one_key_changed(self.BEFORE, after), ['mcp_servers.agentchattr-uat'])

    def test_raises_when_another_server_changes(self):
        after = self.BEFORE.replace('SECRETVAL2', 'SECRETVAL3') + '  agentchattr-uat:\n    url: u\n'
        with self.assertRaises(YamlSettingsError) as caught:
            ym.verify_only_one_key_changed(self.BEFORE, after)
        self.assertIn('mcp_servers.s1', str(caught.exception))
        self.assertNotIn('SECRETVAL', str(caught.exception))

    def test_raises_when_a_top_level_key_changes(self):
        after = self.BEFORE.replace('a: SECRETVAL1', 'a: SECRETVAL9') + '  agentchattr-uat:\n    url: u\n'
        with self.assertRaises(YamlSettingsError) as caught:
            ym.verify_only_one_key_changed(self.BEFORE, after)
        self.assertIn('a', str(caught.exception))
        self.assertNotIn('SECRETVAL', str(caught.exception))

    def test_raises_when_a_top_level_key_is_added(self):
        with self.assertRaises(YamlSettingsError) as caught:
            ym.verify_only_one_key_changed(self.BEFORE, self.BEFORE + 'extra: SECRETVAL4\n')
        self.assertIn('extra', str(caught.exception))
        self.assertNotIn('SECRETVAL', str(caught.exception))


class BackupTests(Base):
    def test_name_bytes_and_log_line(self):
        self.write(ORIGINAL)
        original = self.config.read_bytes()
        receipt = self.apply()
        self.assertTrue(BAK_NAME.fullmatch(receipt.backup_path.name), receipt.backup_path.name)
        self.assertEqual(receipt.backup_path.parent, self.home)
        self.assertEqual(receipt.backup_path.read_bytes(), original)
        digest = hashlib.sha256(original).hexdigest()
        self.assertEqual(receipt.backup_sha256, digest)
        line = next(l for l in self.logs if 'Backed up' in l)
        self.assertIn(receipt.backup_path.name, line)
        self.assertIn(digest, line)
        self.assertNoSecrets()

    def test_no_backup_for_a_new_file(self):
        receipt = self.apply()
        self.assertIsNone(receipt.backup_path)
        self.assertIsNone(receipt.backup_sha256)
        self.assertEqual(self.baks(), [])

    def test_tampered_backup_falls_back_to_removing_only_our_entry(self):
        # Reviewer must-fix 2: a bad backup must not leave the token behind.
        self.write(ORIGINAL)
        receipt = self.apply()
        receipt.backup_path.write_bytes(b'tampered: true\n')
        result = self.remove(receipt)
        self.assertEqual(result.status, 'removed-entry')
        self.assertFalse(result.matches_backup)
        self.assertNotIn(TOKEN.encode(), self.config.read_bytes())
        self.assertEqual(yaml.safe_load(self.config.read_text('utf-8')), yaml.safe_load(ORIGINAL))

    def test_missing_backup_falls_back_to_removing_only_our_entry(self):
        self.write(ORIGINAL)
        receipt = self.apply()
        receipt.backup_path.unlink()
        result = self.remove(receipt)
        self.assertEqual(result.status, 'removed-entry')
        self.assertFalse(result.matches_backup)
        self.assertNotIn(TOKEN.encode(), self.config.read_bytes())


class ConcurrentWriterTests(Base):
    def test_apply_redoes_its_plan_when_the_file_changes_before_replace(self):
        # Reviewer must-fix 4: Hermes may write config.yaml while we prepare ours.
        self.write(ORIGINAL)
        real = ym._atomic_write
        calls = []

        def racing(path, data, expect):
            if not calls:
                Path(path).write_bytes(ORIGINAL.replace('model:', 'model_new: 1\nmodel:').encode('utf-8'))
            calls.append(1)
            return real(path, data, expect)
        with patch.object(ym, '_atomic_write', side_effect=racing):
            self.apply()
        data = yaml.safe_load(self.config.read_text('utf-8'))
        self.assertEqual(data['model_new'], 1)                 # the concurrent edit survived
        self.assertIn('agentchattr-uat', data['mcp_servers'])
        self.assertEqual(len(calls), 2)

    def test_apply_refuses_when_the_file_keeps_changing(self):
        self.write(ORIGINAL)
        real = ym._atomic_write
        counter = iter(range(100))

        def always_racing(path, data, expect):
            Path(path).write_bytes((ORIGINAL + f'x{next(counter)}: 1\n').encode('utf-8'))
            return real(path, data, expect)
        with patch.object(ym, '_atomic_write', side_effect=always_racing):
            with self.assertRaises(YamlSettingsError):
                self.apply()
        self.assertNotIn(TOKEN.encode(), self.config.read_bytes())


class HandEditedEntryTests(Base):
    def test_refresh_checks_its_own_deletion_of_an_existing_entry(self):
        # Reviewer must-fix 5: the delete of an existing entry is verified on its own.
        self.write(ORIGINAL)
        with patch.object(ym, '_without_entry', side_effect=lambda text, layout: (text.replace('model:', 'modelx:'), (0, 0, 0))):
            with self.assertRaises(YamlSettingsError):
                ym.apply(self.config, URL, TOKEN, log=lambda *_: None)
                ym.apply(self.config, URL, TOKEN2, log=lambda *_: None)


class UnicodeLineBreakTests(Base):
    def test_unicode_line_separators_are_refused(self):
        for char in ('\u0085', ' ', ' '):
            with self.subTest(char=repr(char)):
                self.write('model: x' + char + 'y\n')
                before = self.config.read_bytes()
                with self.assertRaises(YamlSettingsError):
                    ym.apply(self.config, URL, TOKEN, log=lambda *_: None)
                self.assertEqual(self.config.read_bytes(), before)


class ResolveSettingsPathTests(Base):
    def test_hermes_home_forms_expand(self):
        self.assertEqual(ym.resolve_settings_path('$HERMES_HOME/config.yaml'), self.home / 'config.yaml')
        self.assertEqual(ym.resolve_settings_path('${HERMES_HOME}/config.yaml'), self.home / 'config.yaml')

    def test_tilde_expands(self):
        home = Path(self.tmp.name) / 'userhome'
        with patch.dict(os.environ, {'HOME': str(home), 'USERPROFILE': str(home)}):
            self.assertEqual(ym.resolve_settings_path('~/c.yaml'), home / 'c.yaml')

    def test_unset_variable_raises(self):
        os.environ.pop('HERMES_HOME', None)
        with self.assertRaises(YamlSettingsError):
            ym.resolve_settings_path('$HERMES_HOME/config.yaml')
        with self.assertRaises(YamlSettingsError):
            ym.resolve_settings_path('${HERMES_HOME}/config.yaml')

    def test_variable_set_to_empty_is_refused(self):
        # Reviewer must-fix 6: HERMES_HOME="" would otherwise give a root-level /config.yaml.
        for empty in ('', '   '):
            with self.subTest(value=repr(empty)), patch.dict(os.environ, {'HERMES_HOME': empty}):
                with self.assertRaises(YamlSettingsError):
                    ym.resolve_settings_path('$HERMES_HOME/config.yaml')
                with self.assertRaises(YamlSettingsError):
                    ym.resolve_settings_path('${HERMES_HOME}/config.yaml')

    def test_empty_raises(self):
        for raw in ('', '   ', None):
            with self.assertRaises(YamlSettingsError):
                ym.resolve_settings_path(raw)

    def test_relative_path_joins_project_dir(self):
        project = Path(self.tmp.name) / 'project'
        self.assertEqual(ym.resolve_settings_path('sub/config.yaml', project), project / 'sub' / 'config.yaml')


class HermesRunningTests(unittest.TestCase):
    def run_with(self, platform, output=None, error=None):
        def fake(*args, **kwargs):
            if error:
                raise error
            return SimpleNamespace(stdout=output)
        with patch.object(ym.sys, 'platform', platform), patch.object(ym.subprocess, 'run', side_effect=fake) as run:
            result = ym.hermes_running()
        return result, run

    def test_windows_tasklist(self):
        csv = '"System","4","Services","0","100 K"\n"hermes.exe","123","Console","1","50,000 K"\n'
        result, run = self.run_with('win32', csv)
        self.assertIs(result, True)
        command = run.call_args.args[0]
        # Reviewer must-fix 7: the System32 tasklist by full path, never a PATH lookup.
        self.assertTrue(command[0].lower().endswith(os.path.join('system32', 'tasklist.exe')), command[0])
        self.assertTrue(os.path.isabs(command[0]))
        self.assertEqual(command[1:], ['/FO', 'CSV', '/NH'])
        self.assertEqual(run.call_count, 1)

    def test_undecodable_bytes_and_value_errors_give_none_or_a_result_not_an_exception(self):
        result, _ = self.run_with('win32', b'"hermes.exe","1","Console","1","1 K"\n"\xff\xfe.exe","2"\n')
        self.assertIs(result, True)
        result, _ = self.run_with('win32', error=ValueError('bad'))
        self.assertIsNone(result)

    def test_windows_without_hermes(self):
        result, run = self.run_with('win32', '"System","4","Services","0","100 K"\n"python.exe","9","Console","1","1 K"\n')
        self.assertIs(result, False)
        argv = [a.lower() for a in run.call_args.args[0]]
        self.assertNotIn('/v', argv)
        self.assertNotIn('/svc', argv)
        self.assertTrue(argv[0].endswith(os.path.join('system32', 'tasklist.exe')), argv[0])
        self.assertEqual(argv[1:], ['/fo', 'csv', '/nh'])

    def test_windows_oserror_is_none(self):
        result, _ = self.run_with('win32', error=OSError('no tasklist'))
        self.assertIsNone(result)

    def test_posix_ps_lists_image_names_only(self):
        result, run = self.run_with('linux', 'init\n/usr/bin/hermes\n')
        self.assertIs(result, True)
        self.assertEqual(run.call_args.args[0], ['ps', '-A', '-o', 'comm='])
        result, _ = self.run_with('linux', 'init\nbash\n')
        self.assertIs(result, False)
        result, _ = self.run_with('linux', error=OSError('no ps'))
        self.assertIsNone(result)


class WrapperStopHookTests(Base):
    def setUp(self):
        super().setUp()
        import wrapper
        self.wrapper = wrapper
        wrapper._reset_yaml_state()
        self.addCleanup(wrapper._reset_yaml_state)

    def test_failed_removal_warns_without_the_token_and_does_not_raise(self):
        self.write(ORIGINAL)
        self.wrapper._apply_yaml_mcp_settings('$HERMES_HOME/config.yaml', ROOT, URL, TOKEN)
        self.assertEqual(len(self.wrapper._YAML_RECEIPTS), 1)
        self.config.write_bytes(b'broken: [unclosed\n')
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            results = self.wrapper._remove_yaml_mcp_entries()
        self.assertEqual(results, [])
        self.assertIn('Warning', out.getvalue())
        self.assertNotIn('SECRET', out.getvalue())
        self.assertEqual(self.config.read_bytes(), b'broken: [unclosed\n')


if __name__ == '__main__':
    unittest.main()
