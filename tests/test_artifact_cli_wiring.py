"""Configured real watcher, owned temp service and explicit injection/HTTP doubles."""
from contextlib import redirect_stdout
import io
import json
from copy import deepcopy
import threading
import unittest
from unittest.mock import Mock, patch
from types import SimpleNamespace

import wrapper
from tests import test_artifact_workers as fixture

class ArtifactCliWiringTests(unittest.TestCase):
    def test_configured_watcher_uses_owned_preflight_and_never_mutable_chat_prompt(self):
        case = fixture.ArtifactWorkerTests()
        self.addCleanup(case.doCleanups)
        case.setUp()
        case.setup_authority()
        audit, consumer = case.claimed()
        record, owned = case.owned(audit)
        # Simulate a first dispatched poll: the fixture get_brief has activated
        # the request, while transport remains dispatched until injection ACK.
        client = case.queue_client(case.instance, consumer=consumer)
        stop = threading.Event()
        injected, statuses = [], []
        def inject(text):
            injected.append(text)
            stop.set()
            return True
        http = SimpleNamespace(fetch_brief=lambda brief:case.authority.get_brief(brief, case.instance),
            submit_saved=lambda saved:case.authority.admit_saved(saved, case.instance))
        with patch('queue_client.QueueClient', return_value=client), patch('artifact_worker.ArtifactHTTP', return_value=http), \
                patch.object(wrapper, '_fetch_role', side_effect=AssertionError('Mutable role')) as role, \
                patch.object(wrapper, '_fetch_active_rules', side_effect=AssertionError('Mutable rules')) as rules, \
                redirect_stdout(io.StringIO()):
            wrapper._queue_watcher(lambda:(case.instance['name'], case.root/'unused'), inject,
                server_port=18300, get_token_fn=lambda:'CONTROLLED', stop_event=stop,
                artifact_runtime=owned['runtime_path'], artifact_manifest=owned['manifest'],
                artifact_status=lambda *values:statuses.append(values))
        self.assertEqual(len(injected), 1)
        self.assertIn('chat_artifact_submit', injected[0])
        self.assertNotIn('chat_send', injected[0])
        role.assert_not_called()
        rules.assert_not_called()
        self.assertIn((audit['dispatch_id'], 'inject', None), statuses)
        self.assertEqual(client.inspect(audit['dispatch_id'])['state'], 'uncertain')

    def test_manager_projects_only_valid_optional_hold_metadata_and_clears_it(self):
        case = fixture.ArtifactWorkerTests()
        self.addCleanup(case.doCleanups)
        case.setUp()
        case.setup_authority()
        attempt = case.attempt
        original = json.loads(attempt['receipt'].read_text(encoding='utf-8'))
        self.assertNotIn('held_artifact', case.manager._inspect('team/cli'))
        held = {'dispatch_id':'a'*32, 'reason':'artifact_generation_uncertain'}
        for supplied, expected in ((held, held), ({**held, 'reason':'PRIVATE'}, None),
                                   ({**held, 'secret':'PRIVATE'}, None), (None, None)):
            attempt['receipt'].write_text(json.dumps({**original, 'held_artifact':supplied}), encoding='utf-8')
            value = case.manager._inspect('team/cli')
            self.assertEqual(value.get('held_artifact'), expected)
            if expected:
                value['held_artifact']['reason'] = 'MUTATED'
                self.assertEqual(case.manager._view(attempt)['held_artifact'], held)

if __name__ == '__main__':
    unittest.main()
