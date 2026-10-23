"""Operator choice previews contain public profile summaries and no mutations."""
import json
import unittest
from unittest.mock import patch

from tests import test_participant_replacement_store as fixture


class ParticipantRecoveryOptionsTests(unittest.TestCase):
    def test_choices_are_readonly_sanitized_and_bound_to_exact_checkpoint(self):
        f = fixture.ParticipantReplacementStoreTests()
        f.setUp()
        self.addCleanup(f.doCleanups)
        files = {path: path.read_bytes() for path in f.fixture.root.rglob('*') if path.is_file()}
        with patch.object(f.fixture.manager, '_inspect', side_effect=AssertionError('Preview cannot release contexts')):
            view = f.engine.participant_recovery_options(f.run['id'])
        self.assertEqual(view['checkpoint_id'], f.intent['checkpoint_id'])
        self.assertEqual(view['attempt_id'], f.intent['attempt_id'])
        self.assertEqual(view['role'], 'editor')
        self.assertEqual(view['current']['identity_id'], f.old['identity_id'])
        source = next(item for item in view['choices'] if item['identity_id'] == f.source['identity_id'])
        self.assertEqual(source['fingerprint'], f.provenance['fingerprint'])
        self.assertEqual(source['model'], f.provenance['effective']['seat']['model'])
        for forbidden in ('effective', 'launch_nonce', 'secret_ref', 'api_key_env', 'data_dir', 'token', 'cwd'):
            self.assertNotIn('"' + forbidden + '"', json.dumps(view))
        self.assertEqual(files, {path: path.read_bytes() for path in f.fixture.root.rglob('*') if path.is_file()})
