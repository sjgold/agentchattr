"""Reviewer-found parser edges, using genuine registry snapshots without workers."""
import tempfile
import unittest

from recipient_routing import resolve_recipients, scan_addresses
from registry import RuntimeRegistry


class RecipientParserEdgeTests(unittest.TestCase):
    def test_inline_triple_backticks_are_not_an_unclosed_fence(self):
        for text in ('```x``` @claude please', '```x```\n@claude'):
            with self.subTest(text=text):
                self.assertEqual(scan_addresses(text), {'tokens': ['claude'], 'ignored': []})

    def test_fence_ends_lazy_blockquote_continuation(self):
        self.assertEqual(scan_addresses('> quote\n```\ncode\n```\n@claude hi'),
                         {'tokens': ['claude'], 'ignored': []})

    def test_only_cr_lf_line_boundaries_introduce_blockquotes(self):
        for separator in ('\u2028', '\u2029', '\x85', '\v', '\f', '\x1c', '\x1d', '\x1e'):
            with self.subTest(separator=repr(separator)):
                self.assertEqual(scan_addresses('hello' + separator + '> @codex'),
                                 {'tokens': ['codex'], 'ignored': []})
        for separator in ('\n', '\r\n', '\r'):
            with self.subTest(separator=repr(separator)):
                self.assertEqual(scan_addresses('hello' + separator + '> @codex')['ignored'],
                                 [{'token': 'codex', 'reason': 'quote'}])

    def test_real_registry_odd_names_do_not_disable_other_audiences(self):
        with tempfile.TemporaryDirectory() as directory:
            registry = RuntimeRegistry(directory)
            registry.seed({'odd.name': {}, 'claude': {}})
            odd, claude = registry.register('odd.name'), registry.register('claude')
            snapshot = registry.get_all()
            online = set(snapshot)
            all_result = resolve_recipients('@all', [], snapshot, online)
            self.assertEqual([r['name'] for r in all_result['recipients']], ['claude', 'odd.name'])
            normal = resolve_recipients('@claude', [], snapshot, online)
            self.assertEqual(normal['recipients'][0]['identity_id'], claude['identity_id'])
            selected = resolve_recipients('', ['odd.name'], snapshot, online)
            self.assertEqual(selected['recipients'][0]['identity_id'], odd['identity_id'])
            self.assertEqual(selected['warnings'], [])
            stale = resolve_recipients('', ['stale.name'], snapshot, online)
            self.assertEqual(stale, {'mode': 'selected', 'tokens': ['stale.name'], 'ignored': [],
                                    'recipients': [], 'warnings': [
                                        {'kind': 'unavailable', 'token': 'stale.name', 'candidates': []}]})
            authored = resolve_recipients('@odd.name', ['claude'], snapshot, online)
            self.assertEqual(authored['recipients'], [])
            self.assertEqual(authored['warnings'][0]['kind'], 'unknown')
