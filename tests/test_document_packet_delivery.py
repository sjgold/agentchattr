"""Final delivery boundaries: canonical storage, literal shared display, old bytes."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from types import SimpleNamespace
import mcp_bridge
import review_brief
from document_inputs import preview_document
from document_packets import render_delivery
from tests.test_document_packets import packet_fixture
from tests.test_review_brief import design


def envelope(kind):
    options={'source_file':packet_fixture()} if kind=='packet' else ({'source_file':preview_document('legacy.txt','legacy café\r\n'.encode('utf-8'))} if kind=='file' else {'input_text':'legacy café\r\n'})
    frozen=review_brief.freeze_inputs(design(),**options);frozen['run_id']='a'*32
    with patch('review_brief.uuid.uuid4',return_value=SimpleNamespace(hex='b'*32)):
        return review_brief.build_brief({**frozen,'id':4,'channel':'review'},0,0,'cli-seat','cli-id')


def tool_delivery(value):
    with tempfile.TemporaryDirectory() as tmp:
        store=review_brief.BriefStore(tmp);store.put(value)
        with patch.object(mcp_bridge,'review_briefs',store),patch.object(mcp_bridge,'_authenticated_instance',return_value={'name':'cli-seat','identity_id':'cli-id'}):
            return mcp_bridge.chat_review_brief(value['brief_id'])


class PacketDeliveryTests(unittest.TestCase):
    def test_cli_prefix_is_one_json_context_then_literal_delivery(self):
        value=envelope('packet');raw=tool_delivery(value)
        context,end=json.JSONDecoder().raw_decode(raw)
        self.assertEqual(context['input_revision'],value['input_revision'])
        for key in ('brief_id','run_id','turn_id','attempt_id'):self.assertEqual(context[key],value[key])
        self.assertEqual(context['source_follows'],"after the line '--- packet ---'")
        self.assertNotIn('source',context)
        self.assertTrue(raw[end:].startswith('\n--- packet ---\n'))
        tail=raw[end+len('\n--- packet ---\n'):]
        self.assertEqual(tail,render_delivery(packet_fixture()))
        self.assertNotIn(packet_fixture()['text'],raw)

    def test_api_model_message_equals_cli_literal_tail_and_content_occurs_once(self):
        value=envelope('packet');shown=render_delivery(packet_fixture())
        messages=review_brief.brief_messages(value,[],'cli-seat')
        self.assertEqual(messages[1]['content'],shown)
        raw=tool_delivery(value);context,end=json.JSONDecoder().raw_decode(raw)
        self.assertEqual(raw[end+len('\n--- packet ---\n'):],messages[1]['content'])
        for row in json.loads(packet_fixture()['text'])['files']:
            self.assertEqual(raw.count(row['text']),1)
            self.assertEqual(messages[1]['content'].count(row['text']),1)
        self.assertNotIn(packet_fixture()['text'],messages[1]['content'])

    def test_v1_file_and_paste_cli_bytes_remain_identical(self):
        for kind in ('file','paste'):
            value=envelope(kind)
            self.assertEqual(tool_delivery(value).encode('utf-8'),json.dumps(value,ensure_ascii=False).encode('utf-8'))

    def test_v1_file_and_paste_api_bytes_keep_prechange_digest(self):
        expected={'file':'4ee9e26342784c7089908659b7ff33eb1ac3530e207fbccf40e440588c9f3bd8','paste':'4d7824e85357758ed767a43347e475d13dcaf2ca4210dade2b446f9014b2fd9c'}
        for kind in ('file','paste'):
            payload=json.dumps(review_brief.brief_messages(envelope(kind),[],'cli-seat'),ensure_ascii=False).encode('utf-8')
            self.assertEqual(hashlib.sha256(payload).hexdigest(),expected[kind])

    def test_http_internal_delivery_remains_canonical_and_validated(self):
        value=envelope('packet')
        with tempfile.TemporaryDirectory() as tmp:
            store=review_brief.BriefStore(tmp);store.put(value)
            delivered=store.get_delivery(value['brief_id'],{'name':'cli-seat','identity_id':'cli-id'})
            self.assertEqual(delivered['source'],packet_fixture()['text'])
            self.assertEqual(delivered['input_revision'],packet_fixture()['content_sha256'])


if __name__=='__main__':unittest.main()
