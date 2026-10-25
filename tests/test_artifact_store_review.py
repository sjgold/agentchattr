"""Root-owned regressions for independently reproduced store findings."""
from copy import deepcopy
import hashlib
import json
import unittest
from unittest.mock import patch
import uuid

import artifact_store
from tests import test_artifact_store as fixture


class ArtifactStoreReviewTests(unittest.TestCase):
    def setUp(self):
        self.case = fixture.ArtifactStoreTests()
        self.addCleanup(self.case.doCleanups)
        self.case.setUp()
        self.module, self.store = self.case.owner()

    def test_malformed_packet_channels_refuse_with_validation_and_no_effects(self):
        for packet in (None, {}, [], 'x', {'channel': 5}, {'channel': 'NOT VALID'}):
            with self.subTest(packet=packet):
                before = self.case.files(self.store)
                with self.assertRaises(artifact_store.ArtifactValidationError):
                    self.store.put_packet(uuid.uuid4().hex, packet)
                self.assertEqual(self.case.files(self.store), before)

    def test_pagination_reports_only_rows_remaining_after_this_page(self):
        audits = [self.case.queued(self.module, self.store) for _ in range(3)]
        self.assertFalse(self.store.list_lineages(offset=1)['truncated'])
        self.assertFalse(self.store.list_lineages(offset=2, limit=1)['truncated'])
        self.assertTrue(self.store.list_lineages(offset=1, limit=1)['truncated'])
        self.assertFalse(self.store.list_lineages(offset=9)['truncated'])
        audit = audits[0]
        for number in range(3):
            version = self.case.commit(self.store, audit, f'# Version {number}')
            if number < 2:
                audit = self.case.queued(self.module, self.store, lineage_id=version['lineage_id'],
                    parent={'version_id': version['id'], 'sequence': version['sequence'], 'sha256': version['sha256']})
        self.assertFalse(self.store.list_versions(version['lineage_id'], offset=1)['truncated'])

    def test_invalid_producer_text_is_hash_only_diagnostic_with_exact_dedupe(self):
        audit = self.case.queued(self.module, self.store)
        for text in ('bad\x00text', 'bad\ud800text', 'bad\udffftext'):
            with self.subTest(text=repr(text)):
                raw = text.encode('utf-8', errors='surrogatepass')
                row = self.store.quarantine_submission(audit['request_id'], audit['attempt_id'],
                    audit['dispatch_id'], reason='invalid_content', content=text, now=100)
                self.assertEqual(row['sha256'], hashlib.sha256(raw).hexdigest())
                self.assertEqual(row['byte_count'], len(raw))
                self.assertTrue(row['not_retained'])
                self.assertIsNone(row['body_object_id'])
                before = self.store.path.read_bytes()
                self.assertEqual(self.store.quarantine_submission(audit['request_id'], audit['attempt_id'],
                    audit['dispatch_id'], reason='invalid_content', content=text, now=999), row)
                self.assertEqual(self.store.path.read_bytes(), before)
        self.assertEqual(self.store.get_request(audit['request_id'])['state'], 'queued')

    def test_unknown_packets_and_unreserved_missing_packet_are_not_corruption(self):
        for _ in range(500):
            with self.assertRaises(artifact_store.ArtifactUnavailable):
                self.store.get_packet(uuid.uuid4().hex)
        self.assertEqual(self.store.diagnostics()['count'], 0)
        self.assertEqual(len(self.store._object_errors), 0)  # Root-owned bounded-cache observation.
        audit = self.case.audit(self.module, self.store)
        packet = self.store._object_path('packet', audit['scope']['packet_id'])
        packet.unlink()  # Deliberate fixture corruption, before reserve.
        with self.assertRaises(artifact_store.ArtifactUnavailable):
            self.store.reserve_request(audit, audit['request_id'])
        self.assertEqual(self.store.diagnostics()['count'], 0)
        self.store.put_packet(audit['request_id'], self.case.packet())
        self.store.reserve_request(audit, audit['request_id'])
        packet.unlink()
        with self.assertRaises(artifact_store.ArtifactUnavailable):
            self.store.get_packet(audit['scope']['packet_id'])
        self.assertEqual(self.store.diagnostics()['rows'][0]['object_kind'], 'packet')

    def test_full_dispatch_group_uses_its_summary_even_when_global_details_full(self):
        row = self.store.quarantine_submission(None, uuid.uuid4().hex, uuid.uuid4().hex,
            reason='unmatched_saved_result', content=None, now=100)
        value = json.loads(self.store.path.read_text(encoding='utf-8'))
        value['diagnostics'] = {}
        # Root-owned valid full-index fixture, no patched limits or public setup claim.
        dispatches = [uuid.uuid4().hex for _ in range(128)]
        for dispatch in dispatches:
            for number in range(8):
                detail = deepcopy(row)
                detail.update(dispatch_id=dispatch, attempt_id=uuid.uuid4().hex)
                key = {k: detail[k] for k in ('request_id', 'attempt_id', 'dispatch_id',
                    'reason', 'sha256', 'byte_count', 'actor_identity_id')}
                detail['id'] = self.store._diagnostic_id(key)
                value['diagnostics'][detail['id']] = detail
        self.store.path.write_text(json.dumps(value), encoding='utf-8')
        restored = artifact_store.ArtifactStore(self.case.root)
        summary = restored.quarantine_submission(None, uuid.uuid4().hex, dispatches[0],
            reason='unmatched_saved_result', content=None, now=200)
        self.assertEqual(summary['kind'], 'dispatch_overflow')
        self.assertEqual(summary['dispatch_id'], dispatches[0])
        self.assertEqual(restored.diagnostics()['detailed_count'], 1024)

    def test_version_replay_refuses_missing_read_result_with_owned_error(self):
        audit = self.case.queued(self.module, self.store)
        self.case.commit(self.store, audit)
        with patch.object(self.store, 'get_version', return_value=None):
            with self.assertRaises(artifact_store.ArtifactUnavailable):
                self.case.commit(self.store, audit)

    def test_referenced_corruption_observations_are_bounded_without_holding_store(self):
        audit = self.case.queued(self.module, self.store)
        value = json.loads(self.store.path.read_text(encoding='utf-8'))
        template = deepcopy(value['requests'][audit['request_id']])
        lineage = deepcopy(value['lineages'][audit['lineage_id']])
        packet_ids = []
        for _ in range(257):
            request_id = uuid.uuid4().hex
            ids = artifact_store.request_ids(request_id)
            row = deepcopy(template)
            row['audit'].update({key: ids[key] for key in ('lineage_id', 'attempt_id', 'dispatch_id', 'brief_id')},
                                request_id=request_id)
            row['audit']['scope']['packet_id'] = ids['packet_id']
            value['requests'][request_id] = row
            owner = deepcopy(lineage)
            owner.update(id=ids['lineage_id'], pending_request_id=request_id)
            value['lineages'][ids['lineage_id']] = owner
            packet_ids.append(ids['packet_id'])
        self.store.path.write_text(json.dumps(value), encoding='utf-8')
        restored = artifact_store.ArtifactStore(self.case.root)
        for packet_id in packet_ids:
            with self.assertRaises(artifact_store.ArtifactUnavailable):
                restored.get_packet(packet_id)
        self.assertEqual(len(restored._object_errors), 256)
        self.assertEqual(restored.diagnostics()['count'], 256)
        self.assertNotIn(('packet', packet_ids[0]), restored._object_errors)
        self.assertEqual(restored.list_lineages()['count'], 258)


if __name__ == '__main__':
    unittest.main()
