"""Explicit fresh choices after pre-brief failure; process/readiness doubles only."""
from copy import deepcopy
import unittest
import uuid

from turn_events import EventConflict
from tests import test_participant_replacement_store as fixture


class ReplacementPreparationSupersedeTests(unittest.TestCase):
    def setUp(self):
        self.f = fixture.ParticipantReplacementStoreTests()
        self.f.setUp()
        self.addCleanup(self.f.doCleanups)

    def failed(self, state='preparation_failed'):
        staged = self.f.stage()
        def fail(value):
            value['pending_replacement']['status'] = state
            value['replacement_requests'][self.f.intent['request_id']]['status'] = state
        self.f.sessions._event_update(self.f.run['id'], fail)
        return staged['pending_replacement']

    def new_choice(self):
        package = deepcopy(self.f.fixture.package)
        seat = deepcopy(package['seats'][0])
        seat.update(id='backup', name='Backup API', model='backup-model')
        package['seats'].append(seat)
        self.f.fixture.store.save(package)
        source, _ = self.f.fixture.ready('backup')
        return dict(self.f.intent, request_id=uuid.uuid4().hex,
                    target_provenance=self.f.fixture.manager.launch_provenance(source))

    def test_terminal_prebrief_failure_accepts_explicit_fresh_choice_with_new_ids_and_old_audits(self):
        first = self.failed()
        choice = self.new_choice()
        before = self.f.sessions.get(self.f.run['id'])
        spawn_count = self.f.fixture.spawn.call_count
        result = self.f.sessions.replace_participant(self.f.run['id'], **choice)
        self.assertEqual(result['pending_replacement']['request_id'], choice['request_id'])
        for key in ('new_attempt_id', 'new_brief_id', 'new_dispatch_id'):
            self.assertNotEqual(result['pending_replacement'][key], first[key])
        old = result['replacement_requests'][self.f.intent['request_id']]
        self.assertEqual(old['status'], 'superseded_preparation')
        self.assertEqual(old['superseded_by'], choice['request_id'])
        self.assertEqual(result['superseded_attempts'][0], before['superseded_attempts'][0])
        self.assertEqual(result['admitted_events'], before['admitted_events'])
        self.assertEqual(result['cast'], before['cast'])
        self.assertEqual(self.f.fixture.spawn.call_count, spawn_count)
        for process in self.f.fixture.processes:
            process.terminate.assert_not_called()
            process.wait.assert_not_called()

    def test_active_pending_or_changed_same_request_still_rejects_without_mutation(self):
        self.f.stage()
        for state in ('preparing_contexts', 'starting', 'waiting', 'dispatching'):
            self.f.sessions._event_update(self.f.run['id'], lambda value: value['pending_replacement'].update(status=state))
            disk = self.f.sessions._path.read_bytes()
            with self.assertRaises(EventConflict):
                self.f.stage(request_id=uuid.uuid4().hex)
            self.assertEqual(self.f.sessions._path.read_bytes(), disk)
        self.f.sessions._event_update(self.f.run['id'], lambda value: value['pending_replacement'].update(status='blocked'))
        with self.assertRaises(EventConflict):
            self.f.stage(reason='Changed same-request intent')

    def persisted_brief_denies(self, sealed):
        pending = self.failed()
        context, _ = self.f.clone(pending)
        envelope = self.f.sessions.briefs.get(self.f.run['active_invocation']['brief_id'], operator=True)
        envelope.update(brief_id=pending['new_brief_id'], attempt_id=pending['new_attempt_id'],
                        expected_agent=context['name'], expected_identity_id=context['identity_id'])
        owner = None
        if sealed:
            instance = self.f.fixture.registry.get_instance(context['name'])
            owner = self.f.fixture.manager.result_owner(instance, pending['new_dispatch_id'])
        self.f.sessions.briefs.put(envelope, result_owner=owner)
        disk = self.f.sessions._path.read_bytes()
        brief = self.f.sessions.briefs._path(pending['new_brief_id']).read_bytes()
        with self.assertRaises(EventConflict):
            self.f.stage(request_id=uuid.uuid4().hex)
        self.assertEqual(self.f.sessions._path.read_bytes(), disk)
        self.assertEqual(self.f.sessions.briefs._path(pending['new_brief_id']).read_bytes(), brief)

    def test_any_unsealed_immutable_brief_closes_preparation_supersession(self):
        self.persisted_brief_denies(False)

    def test_api_sealed_authority_also_closes_preparation_supersession(self):
        self.persisted_brief_denies(True)
