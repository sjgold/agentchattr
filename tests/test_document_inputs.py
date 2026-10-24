"""Pure byte/snapshot validation; source strings are never imported or executed."""
import hashlib
import importlib
import json
import unittest


class DocumentInputTests(unittest.TestCase):
    def setUp(self):
        self.documents = importlib.import_module('document_inputs')

    def test_exact_utf8_snapshot_preserves_crlf_bom_and_unicode(self):
        name = 'Source.PY'
        text = '\ufeffcafé\r\n日本語 😀 e\u0301\nlast\rline'
        content = text.encode('utf-8')
        digest = hashlib.sha256(content).hexdigest()
        identity = hashlib.sha256(json.dumps({'name': name, 'content_sha256': digest},
            sort_keys=True, ensure_ascii=True, separators=(',', ':'), allow_nan=False).encode('utf-8')).hexdigest()
        self.assertEqual(self.documents.preview_document(name, content), {
            'version': 1, 'kind': 'file', 'source_id': 'file:' + identity, 'name': name,
            'encoding': 'utf-8', 'byte_length': len(content), 'content_sha256': digest, 'text': text})

    def test_snapshot_validation_rejects_hash_tamper_and_returns_detached_copy(self):
        original = self.documents.preview_document('review.txt', b'Exact\r\nsource')
        validated = self.documents.validate_document_snapshot(original)
        self.assertEqual(validated, original)
        self.assertIsNot(validated, original)
        validated['text'] = 'local edit'
        self.assertEqual(original['text'], 'Exact\r\nsource')
        changed = {**original, 'content_sha256': '0' * 64}
        with self.assertRaises(self.documents.DocumentInputError):
            self.documents.validate_document_snapshot(changed)

    def canonical(self, name, text):
        content = text.encode('utf-8')
        digest = hashlib.sha256(content).hexdigest()
        identity_bytes = json.dumps({'name': name, 'content_sha256': digest},
            sort_keys=True, ensure_ascii=True, separators=(',', ':'), allow_nan=False).encode('utf-8')
        return {'version': 1, 'kind': 'file', 'source_id': 'file:' + hashlib.sha256(identity_bytes).hexdigest(),
                'name': name, 'encoding': 'utf-8', 'byte_length': len(content), 'content_sha256': digest, 'text': text}

    def test_empty_and_advisory_extensions_are_valid_literal_sources(self):
        empty = self.documents.preview_document('empty.txt', b'')
        self.assertEqual(empty, self.canonical('empty.txt', ''))
        self.assertEqual(self.documents.validate_document_snapshot(empty), empty)
        for name in ('source.rs', 'source.go', 'query.sql', 'events.log', 'Source.PY', 'module.mjs',
                     'Makefile', 'LICENSE', 'unusual.extension', ' leading.txt'):
            with self.subTest(name=name):
                self.assertEqual(self.documents.preview_document(name, b'raw\r\ntext'), self.canonical(name, 'raw\r\ntext'))

    def test_exact_byte_size_limit_including_bom_and_too_large_error_hierarchy(self):
        limit = self.documents.MAX_DOCUMENT_BYTES
        self.assertEqual(limit, importlib.import_module('review_brief').MAX_INPUT_BYTES)
        self.assertEqual(limit, 512 * 1024)
        self.assertTrue(issubclass(self.documents.DocumentTooLarge, self.documents.DocumentInputError))
        self.assertTrue(issubclass(self.documents.DocumentInputError, ValueError))
        for content in (b'x' * limit, b'\xef\xbb\xbf' + b'x' * (limit - 3), '😀'.encode('utf-8') * (limit // 4)):
            with self.subTest(prefix=content[:4]):
                snapshot = self.documents.preview_document('boundary.txt', content)
                self.assertEqual(snapshot['byte_length'], limit)
                self.assertEqual(snapshot['text'].encode('utf-8'), content)
                self.assertEqual(self.documents.validate_document_snapshot(snapshot), snapshot)
                with self.assertRaises(self.documents.DocumentTooLarge):
                    self.documents.preview_document('boundary.txt', content + b'x')
                oversized = self.canonical('boundary.txt', content.decode('utf-8') + 'x')
                with self.assertRaises(self.documents.DocumentTooLarge):
                    self.documents.validate_document_snapshot(oversized)

    def test_preview_requires_exact_bytes_without_coercion(self):
        class DerivedBytes(bytes):
            pass
        for content in ('source', bytearray(b'source'), memoryview(b'source'), DerivedBytes(b'source'),
                        None, True, 1, ['source'], {'text': 'source'}):
            with self.subTest(content_type=type(content).__name__), self.assertRaises(self.documents.DocumentInputError):
                self.documents.preview_document('source.txt', content)

    def test_invalid_utf8_reports_zero_based_byte_offset_without_source_or_bytes_echo(self):
        prefix = 'PRIVATE_SOURCE_é😀'.encode('utf-8')
        for suffix in (b'\xff', b'\xc0\xaf', b'\xed\xa0\x80', b'\xf0\x9f\x98', b'\xe2(\xa1'):
            with self.subTest(suffix=suffix), self.assertRaises(self.documents.DocumentInputError) as caught:
                self.documents.preview_document('input.txt', prefix + suffix)
            message = str(caught.exception)
            self.assertRegex(message, r'(?i)(?:byte(?:\s+offset)?|offset)\D*' + str(len(prefix)) + r'\b')
            self.assertNotIn('PRIVATE_SOURCE', message)
            self.assertNotIn('é', message)
            self.assertNotIn('😀', message)
            self.assertNotRegex(message, r'(?i)0x(?:ff|c0|ed|f0|e2)|\\x(?:ff|c0|ed|f0|e2)')

    def test_forbidden_controls_report_codepoint_and_utf8_byte_offset(self):
        prefix = 'SECRET😀é'  # 6 ASCII + 4 astral + 2 accent bytes, distinct from character offset.
        self.assertEqual(len(prefix.encode('utf-8')), 12)
        for code in [value for value in range(32) if value not in (9, 10, 13)] + [127]:
            with self.subTest(code=code), self.assertRaises(self.documents.DocumentInputError) as caught:
                self.documents.preview_document('source.py', (prefix + chr(code) + 'TAIL').encode('utf-8'))
            message = str(caught.exception)
            self.assertIn('U+' + format(code, '04X'), message)
            self.assertRegex(message, r'(?i)(?:byte(?:\s+offset)?|offset)\D*12\b')
            self.assertNotIn('SECRET', message)
            self.assertNotIn('TAIL', message)
        allowed = '\tfirst\r\nsecond\nthird\r'
        self.assertEqual(self.documents.preview_document('allowed.txt', allowed.encode('utf-8'))['text'], allowed)

    def test_names_reject_paths_controls_format_characters_and_invalid_types(self):
        names = ['', ' ', '\u00a0', '.', '..', '../source.py', 'a/b.py', 'a\\b.py', 'C:source.py',
                 'trailing.', 'trailing ', 'tab\tname', 'line\nname', 'nul\x00name', 'del\x7fname',
                 'zero\u200bwidth', 'join\u200der', 'bidi\u202e.py', 'line\u2028separator', 'para\u2029separator',
                 'surrogate\ud800', None, True, 7, b'name.py', [], {}]
        for name in names:
            with self.subTest(name=repr(name)), self.assertRaises(self.documents.DocumentInputError):
                self.documents.preview_document(name, b'valid')

    def test_name_codepoint_and_utf8_limits_preserve_accepted_spelling(self):
        for name in ('x' * 255, '😀' * 255, 'é' * 253 + '.X', '日本語 e\u0301.PY'):
            with self.subTest(name_length=len(name)):
                snapshot = self.documents.preview_document(name, b'valid')
                self.assertEqual(snapshot['name'], name)
                self.assertEqual(snapshot, self.canonical(name, 'valid'))
        for name in ('x' * 256, '😀' * 256, '😀' * 257):
            with self.subTest(name_length=len(name)), self.assertRaises(self.documents.DocumentInputError):
                self.documents.preview_document(name, b'valid')

    def test_identity_depends_on_exact_bytes_and_name_and_recomputed_changes_are_allowed(self):
        original = self.documents.preview_document('café.py', b'line\r\n')
        self.assertEqual(original, self.documents.preview_document('café.py', b'line\r\n'))
        renamed = self.documents.preview_document('Café.py', b'line\r\n')
        changed = self.documents.preview_document('café.py', b'line\n')
        self.assertEqual(original['content_sha256'], renamed['content_sha256'])
        self.assertNotEqual(original['source_id'], renamed['source_id'])
        self.assertNotEqual(original['content_sha256'], changed['content_sha256'])
        self.assertNotEqual(original['source_id'], changed['source_id'])
        # Validator certifies self-consistency, not a previous preview or native-file provenance.
        independently_changed = self.canonical('entirely-new.rs', 'new café\r\nsource')
        self.assertEqual(self.documents.validate_document_snapshot(independently_changed), independently_changed)

    def test_snapshot_schema_literal_types_and_each_tampered_field_fail_closed(self):
        original = self.canonical('source.txt', 'Exact café\r\nsource')
        self.assertEqual(self.documents.validate_document_snapshot(original), original)
        mutations = {'version': [True, 1.0, '1', 0, 2], 'kind': ['paste', None, True],
                     'encoding': ['UTF-8', 'utf-16', None], 'name': ['renamed.txt', '../bad'],
                     'byte_length': [True, float(original['byte_length']), str(original['byte_length']), -1, 0],
                     'content_sha256': ['0' * 64, original['content_sha256'].upper(), None],
                     'source_id': ['file:' + '0' * 64, 'path:source.txt', None], 'text': ['edited', b'bytes', None]}
        for field, values in mutations.items():
            for value in values:
                with self.subTest(field=field, value=repr(value)), self.assertRaises(self.documents.DocumentInputError):
                    self.documents.validate_document_snapshot({**original, field: value})
        for field in original:
            missing = dict(original)
            del missing[field]
            with self.subTest(missing=field), self.assertRaises(self.documents.DocumentInputError):
                self.documents.validate_document_snapshot(missing)
        for bad in ({**original, 'path': '/forged'}, None, [], 'snapshot', True):
            with self.subTest(shape=type(bad).__name__), self.assertRaises(self.documents.DocumentInputError):
                self.documents.validate_document_snapshot(bad)
        self.assertEqual(original, self.canonical('source.txt', 'Exact café\r\nsource'))

    def test_source_language_and_html_syntax_remain_inert_literal_plaintext(self):
        text = ('@all\r\n$(touch SHOULD_NOT_RUN)\n<script>globalThis.SHOULD_NOT_RUN=true</script>\n'
                '```python\n__import__("os").system("SHOULD_NOT_RUN")\n```\n'
                'import fs from "node:fs"; export default "literal";\n')
        for name in ('source.py', 'source.mjs', 'source.html'):
            with self.subTest(name=name):
                snapshot = self.documents.preview_document(name, text.encode('utf-8'))
                self.assertEqual(snapshot, self.canonical(name, text))
                self.assertEqual(self.documents.validate_document_snapshot(snapshot)['text'], text)


if __name__ == '__main__':
    unittest.main()
