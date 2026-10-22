"""A persisted preparation intent can recover a missing context backlink."""
import unittest
from unittest.mock import patch
import uuid


class PreparedBacklinkTests(unittest.TestCase):
    def test_same_context_request_repairs_missing_backlink_without_reassignment_or_spawn(self):
        from tests.test_prepared_contexts import PreparedContextTests
        fixture = PreparedContextTests()
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        save = fixture.sessions._save
        calls = []
        def fail_backlink():
            calls.append(True)
            if len(calls) == 2:
                raise OSError('fixture failure after context preparation, before backlink')
            return save()
        request_id = uuid.uuid4().hex
        with patch.object(fixture.sessions, '_save', side_effect=fail_backlink):
            with self.assertRaises(OSError):
                fixture.engine.prepare_contexts(fixture.child_id, request_id)
        current = fixture.current()
        self.assertFalse(current['preparation_contexts'])
        history = current['reassigned_contexts_history']
        process_count = len(fixture.processes)
        repaired = fixture.engine.prepare_contexts(fixture.child_id, request_id)
        self.assertEqual(repaired['preparation_contexts']['reviewer']['state'], 'ready')
        self.assertEqual(repaired['reassigned_contexts_history'], history)
        self.assertEqual(len(fixture.processes), process_count)
        self.assertEqual(repaired['input_snapshot'], fixture.child['input_snapshot'])


if __name__ == '__main__':
    unittest.main()
