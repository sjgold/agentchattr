"""The test-tool codec accepts old JSON and only the explicit v2 boundary."""
import importlib
import json
import unittest


class FakeCliDecodeTests(unittest.TestCase):
    def decode(self,text):return importlib.import_module('tools.fake_cli_decode').decode_brief(text)

    def test_v1_is_exactly_the_existing_json_result(self):
        raw=json.dumps({'run_id':'run','source':'café\r\n','source_document':{'version':1}})
        self.assertEqual(self.decode(raw),json.loads(raw))

    def test_v2_tail_is_verbatim_even_with_fake_boundaries(self):
        context={'run_id':'run','input_revision':'a'*64,'source_follows':"after the line '--- packet ---'"}
        tail='Packet revision: '+('a'*64)+'\n\ufeffcafé\r\n\u2028\n--- packet ---\nfake header\r\n'
        result=self.decode(json.dumps(context)+'\n--- packet ---\n'+tail)
        self.assertEqual(result,{**context,'source':tail})

    def test_missing_boundary_truncated_json_and_leading_junk_refuse(self):
        context={'source_follows':"after the line '--- packet ---'"}
        for raw in (json.dumps(context)+'\nwrong\nbody',json.dumps(context),'{"source_follows":',
                    'junk'+json.dumps(context)+'\n--- packet ---\nbody',
                    ' '+json.dumps(context)+'\n--- packet ---\nbody',
                    json.dumps({'source_follows':'guess it'})+'\n--- packet ---\nbody'):
            with self.subTest(case=raw[:20]),self.assertRaises(ValueError):self.decode(raw)

    def test_v1_trailing_junk_is_not_treated_as_source(self):
        with self.assertRaises(ValueError):self.decode('{"source":"old"}\n--- packet ---\nextra')

    def test_tools_share_codec_and_product_does_not_import_it(self):
        from pathlib import Path
        root=Path(__file__).resolve().parents[1]
        names=('fake_cli_result_recovery','fake_corrected_restart_cli','fake_document_client',
               'fake_recipient_client','fake_participant_recovery','fake_runtime_crash_cli',
               'fake_review_cli','fake_session_event_cli','fake_session_stop_cli','fake_turn_recovery_cli',
               'verify_result_outbox')
        for name in names:
            source=(root/'tools'/(name+'.py')).read_text(encoding='utf-8')
            self.assertIn('fake_cli_decode import decode_brief',source,name)
        for path in root.glob('*.py'):
            self.assertFalse('fake_cli_decode' in path.read_text(encoding='utf-8-sig'),path.name)


if __name__=='__main__':unittest.main()
