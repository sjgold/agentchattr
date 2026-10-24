"""Pure recipient policy contracts; dictionary snapshots imply no process readiness."""

import importlib
import copy
import time
import unittest


class RecipientResolutionTests(unittest.TestCase):
    def setUp(self):
        self.routing = importlib.import_module('recipient_routing')
        self.instances = {
            name: {'name': name, 'base': name, 'identity_id': 'id-' + name,
                   'state': 'active'}
            for name in ('claude', 'codex')
        }
        self.online = {'claude', 'codex'}

    def test_explicit_overrides_selection_and_unknown_only_never_falls_back(self):
        self.assertEqual(self.routing.resolve_recipients(
            '@CLAUDE @unknown', ['codex'], self.instances, self.online), {
                'mode': 'explicit', 'tokens': ['claude', 'unknown'], 'ignored': [],
                'recipients': [{'name': 'claude', 'identity_id': 'id-claude', 'online': True}],
                'warnings': [{'kind': 'unknown', 'token': 'unknown', 'candidates': []}],
            })
        self.assertEqual(self.routing.resolve_recipients(
            '@unknown', ['codex'], self.instances, self.online), {
                'mode': 'explicit', 'tokens': ['unknown'], 'ignored': [],
                'recipients': [],
                'warnings': [{'kind': 'unknown', 'token': 'unknown', 'candidates': []}],
            })

    def test_quote_code_and_fence_addresses_are_ignored_with_diagnostics(self):
        text = '"@CLAUDE" `@codex`\n\n```text\n@unknown\n```\n@claude'
        self.assertEqual(self.routing.scan_addresses(text), {
            'tokens': ['claude'],
            'ignored': [{'token': 'claude', 'reason': 'quote'},
                        {'token': 'codex', 'reason': 'code'},
                        {'token': 'unknown', 'reason': 'fence'}],
        })

    def resolve(self, text='', selected=None, instances=None, online=None):
        return self.routing.resolve_recipients(
            text, [] if selected is None else selected,
            self.instances if instances is None else instances,
            self.online if online is None else online)

    def test_selected_normalization_none_and_ignored_only_modes(self):
        self.assertEqual(self.resolve('', ['@CoDeX', 'codex', 'CLAUDE']), {
            'mode': 'selected', 'tokens': ['codex', 'claude'], 'ignored': [],
            'recipients': [
                {'name': 'codex', 'identity_id': 'id-codex', 'online': True},
                {'name': 'claude', 'identity_id': 'id-claude', 'online': True}],
            'warnings': []})
        self.assertEqual(self.resolve('plain text'), {
            'mode': 'none', 'tokens': [], 'ignored': [], 'recipients': [], 'warnings': []})
        result = self.resolve('"@claude"', ['codex'])
        self.assertEqual(result, {
            'mode': 'selected', 'tokens': ['codex'],
            'ignored': [{'token': 'claude', 'reason': 'quote'}],
            'recipients': [{'name': 'codex', 'identity_id': 'id-codex', 'online': True}],
            'warnings': []})

    def test_all_both_order_and_identity_deduplication(self):
        self.instances['alias'] = dict(self.instances['claude'], name='alias')
        self.online.add('alias')
        result = self.resolve('@codex @all @both @claude @ALL')
        self.assertEqual(result['tokens'], ['codex', 'all', 'both', 'claude'])
        self.assertEqual(result['recipients'], [
            {'name': 'codex', 'identity_id': 'id-codex', 'online': True},
            {'name': 'alias', 'identity_id': 'id-claude', 'online': True}])
        self.assertEqual(result['warnings'], [])

    def test_exact_names_win_unique_family_and_ambiguity(self):
        seats = {
            'claude-1': dict(self.instances['claude'], name='claude-1'),
            'claude-2': dict(self.instances['claude'], name='claude-2', identity_id='other'),
        }
        result = self.resolve('@claude @claude-2', instances=seats, online=set(seats))
        self.assertEqual(result['warnings'], [
            {'kind': 'ambiguous', 'token': 'claude', 'candidates': ['claude-1', 'claude-2']}])
        self.assertEqual(result['recipients'], [
            {'name': 'claude-2', 'identity_id': 'other', 'online': True}])
        seats['claude-2']['state'] = 'pending'
        self.assertEqual(self.resolve('@claude', instances=seats, online=set(seats))['recipients'], [
            {'name': 'claude-1', 'identity_id': 'id-claude', 'online': True}])
        seats['claude'] = dict(self.instances['claude'], identity_id='exact')
        self.assertEqual(self.resolve('@claude', instances=seats, online=set(seats))['recipients'][0]['identity_id'], 'exact')

    def test_pending_offline_empty_all_and_stale_selected_diagnostics(self):
        self.instances['claude']['state'] = 'pending'
        result = self.resolve('@claude @codex @all @both', online=set())
        self.assertEqual(result['recipients'], [
            {'name': 'codex', 'identity_id': 'id-codex', 'online': False}])
        self.assertEqual(result['warnings'], [
            {'kind': 'unavailable', 'token': 'claude', 'candidates': []},
            {'kind': 'offline', 'token': 'codex', 'candidates': []},
            {'kind': 'unavailable', 'token': 'all', 'candidates': []},
            {'kind': 'unavailable', 'token': 'both', 'candidates': []}])
        self.assertEqual(self.resolve('', ['stale'], instances={}, online=set()), {
            'mode': 'selected', 'tokens': ['stale'], 'ignored': [], 'recipients': [],
            'warnings': [{'kind': 'unavailable', 'token': 'stale', 'candidates': []}]})
        only_pending = {'claude-1': dict(self.instances['claude'], name='claude-1')}
        self.assertEqual(self.resolve('@claude', instances=only_pending)['warnings'], [
            {'kind': 'unavailable', 'token': 'claude', 'candidates': []}])

    def test_full_identifier_unicode_suffix_and_email_boundaries(self):
        text = 'a@claude x.@codex a+@codex a%@codex a-@codex a_@codex (@CLAUDE), @codex. @claude-tail @claude- @claudeé'
        self.assertEqual(self.routing.scan_addresses(text), {
            'tokens': ['claude', 'codex', 'claude-tail', 'claude-', 'claudeé'], 'ignored': []})
        result = self.resolve('@claudeé @claude-tail @claude-')
        self.assertEqual(result['recipients'], [])
        self.assertEqual(result['warnings'], [
            {'kind': 'unknown', 'token': token, 'candidates': []}
            for token in ('claudeé', 'claude-tail', 'claude-')])

    def test_balanced_double_quotes_unmatched_and_apostrophes(self):
        examples = [
            ('"@claude" “@codex”', [], ['claude', 'codex']),
            ('"@claude', ['claude'], []),
            ('“@claude"', ['claude'], []),
            ('"@claude\n\n@codex"', ['claude', 'codex'], []),
            ("agents' notes @claude's draft and 'tis '@codex'", ['claude', 'codex'], []),
        ]
        for text, tokens, ignored in examples:
            with self.subTest(text=text):
                self.assertEqual(self.routing.scan_addresses(text), {
                    'tokens': tokens,
                    'ignored': [{'token': token, 'reason': 'quote'} for token in ignored]})

    def test_lazy_blockquotes_blank_line_and_mask_precedence(self):
        self.assertEqual(self.routing.scan_addresses(
            '  > @claude\nlazy @codex\n\n@claude\n\n> `@codex`'), {
                'tokens': ['claude'],
                'ignored': [{'token': 'claude', 'reason': 'quote'},
                            {'token': 'codex', 'reason': 'quote'},
                            {'token': 'codex', 'reason': 'code'}]})

    def test_fence_open_close_rules_and_unclosed_fence(self):
        text = '   ~~~~lang\n@claude\n~~~\n@codex\n~~~~  \n@claude\n\n```\n@codex'
        self.assertEqual(self.routing.scan_addresses(text), {
            'tokens': ['claude'],
            'ignored': [{'token': 'claude', 'reason': 'fence'},
                        {'token': 'codex', 'reason': 'fence'}]})
        self.assertEqual(self.routing.scan_addresses('    ~~~\n@claude')['tokens'], ['claude'])

    def test_inline_equal_runs_unmatched_and_paragraph_reset(self):
        for text, tokens, ignored in [
            ('`` @claude ` @codex `` @claude', ['claude'], ['claude', 'codex']),
            ('` @claude `` @codex', ['claude', 'codex'], []),
            ('` @claude\n\n@codex `', ['claude', 'codex'], []),
        ]:
            with self.subTest(text=text):
                self.assertEqual(self.routing.scan_addresses(text), {
                    'tokens': tokens,
                    'ignored': [{'token': token, 'reason': 'code'} for token in ignored]})

    def test_repeated_diagnostics_are_deduplicated_by_token_and_reason(self):
        result = self.resolve('@MISSING @missing "@codex @CODEX" `@codex` `@codex`', ['claude'])
        self.assertEqual(result, {
            'mode': 'explicit', 'tokens': ['missing'],
            'ignored': [{'token': 'codex', 'reason': 'quote'}, {'token': 'codex', 'reason': 'code'}],
            'recipients': [], 'warnings': [{'kind': 'unknown', 'token': 'missing', 'candidates': []}]})

    def test_results_are_detached_and_inputs_never_mutated(self):
        self.instances['claude']['extra'] = {'secret': ['private']}
        selected = ['CLAUDE']
        originals = copy.deepcopy((self.instances, self.online, selected))
        expected = self.resolve('', selected)
        result = self.resolve('', selected)
        result['tokens'].append('codex')
        result['recipients'][0]['identity_id'] = 'changed'
        result['recipients'].append({'bad': []})
        result['warnings'].append({'bad': []})
        self.assertEqual((self.instances, self.online, selected), originals)
        self.assertEqual(self.resolve('', selected), expected)
        ignored = self.routing.scan_addresses('"@claude"')
        ignored['ignored'][0]['token'] = 'changed'
        self.assertEqual(self.routing.scan_addresses('"@claude"')['ignored'][0]['token'], 'claude')

    def test_malformed_registry_and_case_collisions_fail_closed(self):
        bad = [None, [], {'claude': None}]
        for field in ('name', 'base', 'identity_id', 'state'):
            for value in (None, 1, [], ''):
                seat = dict(self.instances['claude'])
                seat[field] = value
                bad.append({'claude': seat})
            seat = dict(self.instances['claude'])
            del seat[field]
            bad.append({'claude': seat})
        bad.extend([
            {'wrong': self.instances['claude']},
            {**self.instances, 'CLAUDE': dict(self.instances['claude'], name='CLAUDE')},
        ])
        for snapshot in bad:
            with self.subTest(snapshot=snapshot), self.assertRaises(ValueError):
                self.routing.resolve_recipients('@claude', [], snapshot, self.online)
        for online in ([], {}, {'claude', 1}):
            with self.subTest(online=online), self.assertRaises(ValueError):
                self.resolve('@claude', online=online)

    def test_invalid_text_selections_and_generic_errors(self):
        sentinel = 'DO_NOT_ECHO_PRIVATE'
        invalid_text = [None, 3, [], sentinel + '\x00', sentinel + '\ud800']
        for text in invalid_text:
            for function in (self.routing.scan_addresses, lambda value: self.resolve(value)):
                with self.subTest(text=repr(text)), self.assertRaises(ValueError) as caught:
                    function(text)
                self.assertNotIn(sentinel, str(caught.exception))
        for selected in (None, (), 'claude', [None], [True], [''], ['@@claude'],
                         ['bad name'], [sentinel + '\x00'], [sentinel + '\ud800']):
            with self.subTest(selected=repr(selected)), self.assertRaises(ValueError) as caught:
                self.routing.resolve_recipients('', selected, self.instances, self.online)
            self.assertNotIn(sentinel, str(caught.exception))

    def test_utf8_text_and_aggregate_selection_byte_limits(self):
        limit = importlib.import_module('turn_events').MAX_EVENT_BYTES
        self.assertEqual(self.routing.scan_addresses('é' * (limit // 2)), {'tokens': [], 'ignored': []})
        with self.assertRaises(ValueError):
            self.routing.scan_addresses('é' * (limit // 2) + 'x')
        self.assertEqual(self.resolve('', ['a' * limit], instances={}, online=set())['mode'], 'selected')
        with self.assertRaises(ValueError):
            self.resolve('', ['a' * limit, 'b'], instances={}, online=set())
        with self.assertRaises(ValueError):
            self.resolve('', ['a'] * (limit + 1), instances={}, online=set())

    def test_long_diagnostics_are_bounded_without_routing_known_prefix(self):
        prefix = 'x' * 127
        long_token = prefix + 'trailing'
        self.instances[prefix] = {'name': prefix, 'base': prefix, 'identity_id': 'long-prefix', 'state': 'active'}
        self.online.add(prefix)
        text = '@' + long_token + ' "@' + long_token + '" `@' + long_token + '`'
        unchanged = text[:]
        diagnostic = prefix + '\u2026'
        self.assertEqual(self.resolve(text), {
            'mode': 'explicit', 'tokens': [diagnostic],
            'ignored': [{'token': diagnostic, 'reason': 'quote'}, {'token': diagnostic, 'reason': 'code'}],
            'recipients': [], 'warnings': [{'kind': 'unknown', 'token': diagnostic, 'candidates': []}]})
        self.assertEqual(len(diagnostic), 128)
        self.assertEqual(text, unchanged)

    def test_pathological_200kib_scanning_is_bounded(self):
        # Two seconds permits Windows scheduling noise; this is a generous complexity guard.
        text = ('`"@@@@' * 40960)[:200 * 1024]
        started = time.perf_counter()
        result = self.routing.scan_addresses(text)
        elapsed = time.perf_counter() - started
        self.assertEqual(set(result), {'tokens', 'ignored'})
        self.assertEqual(result['tokens'], [])
        self.assertEqual(result['ignored'], [])
        self.assertLess(elapsed, 2.0)


if __name__ == '__main__':
    unittest.main()
