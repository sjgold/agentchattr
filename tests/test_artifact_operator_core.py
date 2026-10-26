"""Reduced20 core ROOT reds. Missing new seams are infrastructure errors.
Bodies after a missing seam are unobserved until production exists; no live calls.
"""
from copy import deepcopy
import importlib
from pathlib import Path
import hashlib
import unittest
from unittest.mock import patch

from tests import test_artifact_admission as admission_fixture


class ArtifactOperatorCoreTests(unittest.TestCase):
    def context(self):
        case=admission_fixture.ArtifactAdmissionTests();case.setUp();case.setup_authority()
        self.addCleanup(case.doCleanups)
        return case

    def resolver(self):
        return importlib.import_module('artifact_operator').resolve_default_artifact_author

    def session(self,case):
        return {'design_snapshot':{'roles':['human','first','second']},
            'participant_bindings':{'human':{'kind':'human','identity_id':None},
                'first':{'kind':'agent','identity_id':case.instance['identity_id']},
                'second':{'kind':'agent','identity_id':'f'*32}}}

    def test_default_author_uses_binding_identity_and_returns_only_identity(self):
        case=self.context();session=self.session(case)
        session['cast']={'first':'WRONG-NAME-MUST-NOT-CHOOSE'}
        self.assertEqual(self.resolver()(session,case.authority),case.instance['identity_id'])

    def test_capability_off_refuses_before_any_manager_lookup(self):
        case=self.context();resolve=self.resolver()
        with patch('runtime_protocol.SUPPORTED_CAPABILITIES',()),patch.object(case.manager,'artifact_producer') as lookup:
            with self.assertRaises(Exception) as caught:resolve(self.session(case),case.authority)
        self.assertEqual(caught.exception.code,'no_author_available')
        self.assertEqual(caught.exception.cause,'capability_off')
        self.assertEqual(str(caught.exception),'Artifact authoring is not enabled.')
        lookup.assert_not_called()

    def test_resolver_manager_io_does_not_own_engine_catalog_boundary(self):
        case=self.context();resolve=self.resolver();seen=[];original=case.manager.artifact_producer
        def observed(instance):
            seen.append((case.engine._lock._is_owned(),case.catalog._lock._is_owned()))
            return original(instance)
        with patch.object(case.manager,'artifact_producer',observed):identity=resolve(self.session(case),case.authority)
        self.assertEqual(identity,case.instance['identity_id']);self.assertTrue(seen)
        self.assertTrue(all(value==(False,False) for value in seen))

    def test_first_candidate_cause_and_examined_count_are_deterministic(self):
        case=self.context();resolve=self.resolver();session=self.session(case)
        with patch.object(case.manager,'artifact_producer',return_value={'available':False,'reason':'unmanaged_producer'}):
            with self.assertRaises(Exception) as caught:resolve(session,case.authority)
        self.assertEqual(caught.exception.code,'no_author_available')
        self.assertEqual(caught.exception.cause,'unmanaged')
        self.assertEqual(caught.exception.examined_roles,2)

    def test_duplicate_active_identity_refuses_as_ambiguous(self):
        case=self.context();resolve=self.resolver();row=deepcopy(case.instance);row['state']='active'
        with patch.object(case.registry,'get_all',return_value={'one':row,'two':deepcopy(row)}):
            with self.assertRaises(Exception) as caught:resolve(self.session(case),case.authority)
        self.assertEqual(caught.exception.cause,'ambiguous')

    def test_public_status_prepared_without_queue_is_needs_recovery(self):
        case=self.context();audit,_=case.new_request()
        case.artifacts.reserve_request(audit,audit['request_id'])
        status=case.authority.request_status(audit['request_id'])
        self.assertTrue(status['needs_resume'])
        self.assertEqual(status['request']['state'],'prepared')
        self.assertIsNone(next((row for row in case.trigger.queue.records() if row['envelope']['dispatch_id']==audit['dispatch_id']),None))

    def test_terminal_status_is_not_needs_resume_and_does_not_repair(self):
        case=self.context();audit=case.prepare();case.authority.cancel_request(audit['request_id'])
        before=case.files()
        result=case.authority.request_status(audit['request_id'])
        self.assertFalse(result['needs_resume']);self.assertEqual(result['request']['state'],'cancelled')
        self.assertEqual(case.files(),before)

    def test_imported_status_is_read_only_without_needs_resume(self):
        case=self.context()
        from tests.test_artifact_import_benchmark import graph
        portable,objects=graph(1)
        prepared=case.artifacts.prepare_import_lineage(portable,objects)
        with case.service._boundary():case.artifacts.import_lineage(prepared,channel='review')
        request=portable['requests'][0]['request_id'];before=case.files()
        result=case.authority.request_status(request)
        self.assertEqual(result['request']['state'],'imported');self.assertFalse(result['needs_resume'])
        self.assertEqual(case.files(),before)

    def test_replay_uses_stored_intent_before_prepare_or_resolver(self):
        case=self.context()
        case.sessions._load_templates(Path(__file__).resolve().parents[1]/'session_templates')
        session=case.sessions.create('planning','review',{'planner':'planner','challenger':'challenger',
            'synthesiser':'synthesiser'},'operator',input_text='Frozen source')
        audit,packet=case.new_request()
        revision=hashlib.sha256(b'Frozen source').hexdigest()
        source={'session_id':session['id'],'run_id':session['run_id'],'input_revision':revision,'state_at_request':session['state']}
        packet.update(scope_kind='run_accepted_messages',source_run=source,
            input={'text':'Frozen source','input_revision':revision,'source_document':None})
        audit.update(source_run=source,scope=case.artifacts.put_packet(audit['request_id'],packet))
        case.authority.prepare_request(audit,packet,audit['request_id'])
        module=importlib.import_module('artifact_operator')
        operator=module.ArtifactOperator(authority=case.authority,sessions=case.sessions,messages=case.messages)
        intent={'request_id':audit['request_id'],'channel':'review',
            'session_id':session['id'],'run_id':session['run_id'],'instruction':audit['instruction']}
        before=case.files()
        with patch.object(case.authority,'prepare_request',side_effect=AssertionError('must not prepare replay')),patch.object(
                module,'resolve_default_artifact_author',side_effect=AssertionError('must not resolve replay')),patch.object(
                case.manager,'launch_provenance',side_effect=AssertionError('must not inspect relaunched producer')):
            result=operator.create(intent)
        self.assertEqual(result['request']['request_id'],audit['request_id'])
        self.assertEqual(result['request']['state'],'queued');self.assertEqual(case.files(),before)
