"""Reduced20 core ROOT reds. Missing new seams are infrastructure errors.
Bodies after a missing seam are unobserved until production exists; no live calls.
"""
from copy import deepcopy
import importlib
from pathlib import Path
import hashlib
import uuid
import unittest
from unittest.mock import patch

from tests import test_artifact_admission as admission_fixture


def accepted_source(case, *, text='Accepted café\r\n', state='complete'):
    case.sessions._load_templates(Path(__file__).resolve().parents[1]/'session_templates')
    session=case.sessions.create('planning','review',{'planner':case.instance['name'],'challenger':'human',
        'synthesiser':'human'},'operator',input_text='Frozen source',participant_bindings={
            'planner':{'kind':'agent','identity_id':case.instance['identity_id']},
            'challenger':{'kind':'human','identity_id':None},'synthesiser':{'kind':'agent','identity_id':None}})
    event={'brief_id':uuid.uuid4().hex,'run_id':session['run_id'],'turn_id':session['run_id']+':0:0',
        'attempt_id':uuid.uuid4().hex,'input_revision':session['input_revision'],
        'event_id':uuid.uuid4().hex,'kind':'final','sender':case.instance['name'],'content':text,'is_output':False}
    metadata={key:event[key] for key in ('brief_id','run_id','turn_id','attempt_id','input_revision','event_id','kind')}
    metadata.update(session_id=session['id'],routing_suppressed=True,session_output=False)
    row=case.messages.add_once('session-event:'+event['event_id'],event['sender'],text,
        msg_type='session_result',channel='review',metadata=metadata)
    event['projected_message_id']=row['id']
    session=case.sessions._event_update(session['id'],lambda value:value.update(admitted_events=[event],state=state))
    return session,row,event


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
            with self.assertRaises(importlib.import_module('artifact_operator').ArtifactOperatorError) as caught:resolve(self.session(case),case.authority)
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
            with self.assertRaises(importlib.import_module('artifact_operator').ArtifactOperatorError) as caught:resolve(session,case.authority)
        self.assertEqual(caught.exception.code,'no_author_available')
        self.assertEqual(caught.exception.cause,'unmanaged')
        self.assertEqual(caught.exception.examined_roles,2)

    def test_duplicate_active_identity_refuses_as_ambiguous(self):
        case=self.context();resolve=self.resolver();row=deepcopy(case.instance);row['state']='active'
        with patch.object(case.registry,'get_all',return_value={'one':row,'two':deepcopy(row)}):
            with self.assertRaises(importlib.import_module('artifact_operator').ArtifactOperatorError) as caught:resolve(self.session(case),case.authority)
        self.assertEqual(caught.exception.cause,'ambiguous')

    def test_public_status_prepared_without_queue_is_needs_recovery(self):
        case=self.context();audit,_=case.new_request()
        case.artifacts.reserve_request(audit,audit['request_id'])
        status=case.authority.request_status(audit['request_id'])
        self.assertTrue(status['needs_resume'])
        self.assertEqual(status['request']['state'],'prepared')
        self.assertIsNone(next((row for row in case.trigger.queue.records() if row['envelope']['dispatch_id']==audit['dispatch_id']),None))

    def test_terminal_status_is_not_needs_resume_and_does_not_repair(self):
        case=self.context();audit=case.prepare();case.claim(audit)
        cancelled=case.authority.cancel_request(audit['request_id'])
        self.assertEqual(cancelled['warning'],'transport_unconfirmed')
        before=case.files()
        with patch.object(case.authority,'_fence',side_effect=AssertionError('status must not repair')) as fence:
            result=case.authority.request_status(audit['request_id'])
        fence.assert_not_called()
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
        instance,_,_=case.launch_binding('api')
        audit,packet=case.new_request(instance=instance)
        revision=hashlib.sha256(b'Frozen source').hexdigest()
        source={'session_id':session['id'],'run_id':session['run_id'],'input_revision':revision,'state_at_request':session['state']}
        packet.update(scope_kind='run_accepted_messages',source_run=source,
            input={'text':'Frozen source','input_revision':revision,'source_document':None})
        request=uuid.uuid4().hex;ids=case.storage.request_ids(request)
        audit.update(request_id=request,**{key:ids[key] for key in ('lineage_id','attempt_id','dispatch_id','brief_id')})
        audit.update(source_run=source,scope=case.artifacts.put_packet(request,packet))
        case.authority.prepare_request(audit,packet,audit['request_id'])
        module=importlib.import_module('artifact_operator')
        operator=module.ArtifactOperator(authority=case.authority,sessions=case.sessions,messages=case.messages)
        intent={'request_id':audit['request_id'],'channel':'review',
            'session_id':session['id'],'run_id':session['run_id'],'instruction':audit['instruction']}
        old=case.manager.launch_provenance(instance)
        old_producer=case.manager.artifact_producer(instance)
        case.manager.stop('team','api')
        package=deepcopy(case.package);package['seats'][1]['model']='relaunched-model'
        case.manager.store.save(package)
        relaunched,_,_=case.launch_binding('api')
        current=case.manager.launch_provenance(relaunched)
        self.assertNotEqual(current['launch_attempt'],old['launch_attempt'])
        self.assertNotEqual(current['identity_id'],old['identity_id'])
        new_producer=case.manager.artifact_producer(relaunched)
        self.assertNotEqual(new_producer['launch_nonce'],old_producer['launch_nonce'])
        self.assertNotEqual(new_producer['fingerprint'],old_producer['fingerprint'])
        before=case.files()
        with patch.object(case.authority,'prepare_request',side_effect=AssertionError('must not prepare replay')),patch.object(
                module,'resolve_default_artifact_author',side_effect=AssertionError('must not resolve replay')),patch.object(
                case.manager,'launch_provenance',side_effect=AssertionError('must not inspect relaunched producer')):
            try:result=operator.create(intent)
            except module.ArtifactOperatorError as error:self.fail('Identical replay refused: '+error.code)
        self.assertEqual(result['request']['request_id'],audit['request_id'])
        self.assertEqual(result['request']['state'],'queued');self.assertEqual(case.files(),before)

    def test_reason_mapping_order_family_skip_and_inactive_duplicate(self):
        case=self.context();module=importlib.import_module('artifact_operator');resolve=module.resolve_default_artifact_author
        session=self.session(case)
        session['participant_bindings']['family']={'kind':'agent','identity_id':None}
        session['design_snapshot']['roles']=['human','family','first','second']
        session['participant_bindings']=dict(reversed(list(session['participant_bindings'].items())))
        mapping={'artifact_capability_missing':'not_supported','unmanaged_producer':'unmanaged',
            'producer_unavailable':'no_live_instance','capability_binding_changed':'binding_changed','runtime_unverified':'runtime_unverified'}
        for reason,cause in mapping.items():
            with self.subTest(reason=reason),patch.object(case.manager,'artifact_producer',return_value={'available':False,'reason':reason}):
                with self.assertRaises(module.ArtifactOperatorError) as caught:resolve(session,case.authority)
                self.assertEqual(caught.exception.cause,cause);self.assertEqual(caught.exception.examined_roles,2)
                self.assertEqual(caught.exception.author_name,case.instance['name'])
        inactive=deepcopy(case.instance);inactive['state']='inactive'
        rows=case.registry.get_all();rows['inactive-duplicate']=inactive
        with patch.object(case.registry,'get_all',return_value=rows):self.assertEqual(resolve(session,case.authority),case.instance['identity_id'])
        session['design_snapshot']['roles']=['human','family']
        with self.assertRaises(module.ArtifactOperatorError) as caught:resolve(session,case.authority)
        self.assertEqual((caught.exception.cause,caught.exception.examined_roles),('no_agent_role',0))

    def test_first_missing_bound_identity_then_second_live_author(self):
        case=self.context();other,_,_=case.launch_binding('api');session=self.session(case)
        session['participant_bindings']['first']['identity_id']='e'*32
        session['participant_bindings']['second']['identity_id']=other['identity_id']
        self.assertEqual(self.resolver()(session,case.authority),other['identity_id'])
        session['design_snapshot']['roles']=['first']
        with self.assertRaises(importlib.import_module('artifact_operator').ArtifactOperatorError) as caught:self.resolver()(session,case.authority)
        self.assertEqual(caught.exception.cause,'no_live_instance');self.assertEqual(caught.exception.examined_roles,1)

    def test_successful_create_replay_conflict_and_capture_stop_guard(self):
        case=self.context();session,row,event=accepted_source(case)
        module=importlib.import_module('artifact_operator')
        operator=module.ArtifactOperator(authority=case.authority,sessions=case.sessions,messages=case.messages)
        intent={'request_id':uuid.uuid4().hex,'channel':'review','session_id':session['id'],
            'run_id':session['run_id'],'instruction':'Write a report'}
        first=operator.create(intent);self.assertTrue(first.created)
        self.assertEqual(first['request']['label'],'queued');self.assertFalse(first['request']['source']['source_so_far'])
        replay=operator.create(intent);self.assertFalse(replay.created)
        with self.assertRaises(module.ArtifactOperatorError) as caught:operator.create({**intent,'instruction':'different'})
        self.assertEqual(caught.exception.code,'request_conflict');self.assertEqual(caught.exception.durability,'recorded')
        original=case.artifacts.put_packet
        def stop_after_packet(*args):
            result=original(*args);case.sessions.stop_run(session['id'],'Stop during capture');return result
        new_intent={**intent,'request_id':uuid.uuid4().hex}
        with patch.object(case.artifacts,'put_packet',stop_after_packet),self.assertRaises(module.ArtifactOperatorError) as caught:operator.create(new_intent)
        self.assertEqual(caught.exception.code,'source_unavailable')
        self.assertIsNone(case.artifacts.get_request(new_intent['request_id']))
        self.assertTrue(case.artifacts._object_path('packet',case.storage.request_ids(new_intent['request_id'])['packet_id']).exists())

    def test_summary_all_states_and_post_durable_cancel_failure(self):
        case=self.context();audit=case.prepare();module=importlib.import_module('artifact_operator')
        original=case.artifacts.get_request(audit['request_id'])
        expected={'prepared':'queued','queued':'queued','active':'working','fulfilled':'ready',
            'failed':'failed','cancelled':'failed','quarantined':'failed','imported':'failed'}
        for state,label in expected.items():
            row=deepcopy(original);row['state']=state
            value=module.summary(row)
            self.assertEqual(value['label'],label)
            self.assertEqual(set(value),{'request_id','channel','state','reason','label','author_name',
                'created_at','updated_at','version_id','source','needs_resume','warning'})
        row['version_id']='b'*32;self.assertEqual(module.summary(row)['label'],'ready')
        for state,reason in [('cancelled','operator_cancelled'),('cancelled','source_stopped'),('quarantined','invalid_response')]:
            rejected=deepcopy(original);rejected.update(state=state,reason=reason)
            self.assertEqual((module.summary(rejected)['label'],module.summary(rejected)['reason']),('failed',reason))
        self.assertEqual(module.summary(original,needs_resume=True)['label'],'unavailable')
        operator=module.ArtifactOperator(authority=case.authority,sessions=case.sessions,messages=case.messages)
        cancel=case.authority.cancel_request
        def failed_after_save(identifier):cancel(identifier);raise OSError('PRIVATE_FENCE_ERROR')
        with patch.object(case.authority,'cancel_request',failed_after_save),self.assertRaises(module.ArtifactOperatorError) as caught:operator.cancel(audit['request_id'])
        self.assertEqual(caught.exception.durability,'recorded');self.assertEqual(caught.exception.request['state'],'cancelled')
        self.assertNotIn('PRIVATE_FENCE_ERROR',str(caught.exception))

    def test_status_and_cancel_reads_are_serialized_and_create_guard_is_no_effect(self):
        case=self.context();session,_,_=accepted_source(case)
        module=importlib.import_module('artifact_operator')
        operator=module.ArtifactOperator(authority=case.authority,sessions=case.sessions,messages=case.messages)
        intent={'request_id':uuid.uuid4().hex,'channel':'review','session_id':session['id'],'run_id':session['run_id'],'instruction':'report'}
        before=case.files()
        with case.service._boundary(),self.assertRaises(module.ArtifactOperatorError) as caught:operator.create(intent)
        self.assertEqual(caught.exception.code,'boundary_held');self.assertEqual(case.files(),before)
        audit=case.prepare();read=case.artifacts.get_request;seen=[]
        def observed(identifier):
            seen.append((case.engine._lock._is_owned(),case.catalog._lock._is_owned()))
            return read(identifier)
        with patch.object(case.artifacts,'get_request',observed):
            operator.request_status(audit['request_id']);operator.cancel(audit['request_id'])
        self.assertTrue(seen);self.assertTrue(all(pair==(True,True) for pair in seen))

    def test_concurrent_saved_same_intent_wins_before_packet_staging(self):
        case=self.context();session,row,event=accepted_source(case)
        module=importlib.import_module('artifact_operator')
        operator=module.ArtifactOperator(authority=case.authority,sessions=case.sessions,messages=case.messages)
        intent={'request_id':uuid.uuid4().hex,'channel':'review','session_id':session['id'],
            'run_id':session['run_id'],'instruction':'same intent'}
        original=case.artifacts.put_packet;entered=[];winner=[]
        def concurrent(request,packet):
            if not entered:
                entered.append(True)
                extra=deepcopy(event);extra.update(event_id=uuid.uuid4().hex,content='Later accepted contribution')
                slots=[(phase,turn) for phase,data in enumerate(session['design_snapshot']['phases']) for turn,_ in enumerate(data['participants'])]
                phase,turn=slots[1];extra['turn_id']=session['run_id']+':'+str(phase)+':'+str(turn)
                meta={key:extra[key] for key in ('brief_id','run_id','turn_id','attempt_id','input_revision','event_id','kind')}
                meta.update(session_id=session['id'],routing_suppressed=True,session_output=False)
                added=case.messages.add_once('session-event:'+extra['event_id'],extra['sender'],extra['content'],
                    msg_type='session_result',channel='review',metadata=meta)
                extra['projected_message_id']=added['id']
                case.sessions._event_update(session['id'],lambda value:value['admitted_events'].append(extra))
                winner.append(operator.create(intent))
            return original(request,packet)
        with patch.object(case.artifacts,'put_packet',concurrent):
            try:result=operator.create(intent)
            except module.ArtifactOperatorError as error:self.fail('Stored identical winner must replay: '+error.code)
        self.assertEqual(len(winner),1);self.assertTrue(winner[0].created);self.assertFalse(result.created)
        self.assertEqual(result['request']['source']['message_count'],2)
        self.assertEqual(case.artifacts.get_request(intent['request_id'])['state'],'queued')

    def test_orphan_packet_conflict_has_distinct_recoverable_cause(self):
        case=self.context();session,_,_=accepted_source(case)
        module=importlib.import_module('artifact_operator');operator=module.ArtifactOperator(authority=case.authority,sessions=case.sessions,messages=case.messages)
        intent={'request_id':uuid.uuid4().hex,'channel':'review','session_id':session['id'],
            'run_id':session['run_id'],'instruction':'report'}
        with patch.object(case.authority,'prepare_request',side_effect=OSError('after packet staging')):
            with self.assertRaises(module.ArtifactOperatorError):operator.create(intent)
        self.assertIsNone(case.artifacts.get_request(intent['request_id']))
        original=module.capture_artifact_session_source
        def changed(*args,**kwargs):
            captured,packet=original(*args,**kwargs);packet['messages'][0]['text']+=' later';return captured,packet
        with patch.object(module,'capture_artifact_session_source',changed):
            with self.assertRaises(module.ArtifactOperatorError) as caught:operator.create(intent)
        self.assertEqual((caught.exception.code,caught.exception.cause),('request_conflict','packet_exists'))
        self.assertEqual(caught.exception.durability,'not_recorded')
        self.assertIn('new request_id',str(caught.exception))

    def test_producer_drift_and_access_loss_are_author_refusals(self):
        case=self.context();session,_,_=accepted_source(case)
        module=importlib.import_module('artifact_operator');operator=module.ArtifactOperator(authority=case.authority,sessions=case.sessions,messages=case.messages)
        intent={'request_id':uuid.uuid4().hex,'channel':'review','session_id':session['id'],
            'run_id':session['run_id'],'instruction':'report'}
        from artifact_service import _ArtifactProducerUnavailable,ArtifactAccessError
        for error in (_ArtifactProducerUnavailable('drift'),ArtifactAccessError('ended')):
            with patch.object(case.authority,'request_producer',side_effect=error):
                with self.assertRaises(module.ArtifactOperatorError) as caught:operator.create(intent)
            self.assertEqual((caught.exception.code,caught.exception.cause),('no_author_available','producer_unavailable'))

    def test_imported_matching_intent_replays_without_live_source_or_capability(self):
        from artifact_archive import portable_lineage
        case=self.context();session,_,_=accepted_source(case)
        module=importlib.import_module('artifact_operator')
        operator=module.ArtifactOperator(authority=case.authority,sessions=case.sessions,messages=case.messages)
        intent={'request_id':uuid.uuid4().hex,'channel':'review','session_id':session['id'],
            'run_id':session['run_id'],'instruction':'retained intent'}
        result=operator.create(intent);row=case.artifacts.get_request(intent['request_id'])
        snapshot=case.artifacts.export_metadata(row['audit']['lineage_id'])
        portable=portable_lineage(snapshot,archive_id='reduced-replay-fixture')
        packet_id=row['audit']['scope']['packet_id']
        objects={('packet',packet_id):case.artifacts._object_path('packet',packet_id).read_bytes()}
        target=self.context();prepared=target.artifacts.prepare_import_lineage(portable,objects)
        with target.service._boundary():target.artifacts.import_lineage(prepared,channel='review')
        reader=module.ArtifactOperator(authority=target.authority,sessions=target.sessions,messages=target.messages)
        self.assertIsNone(target.sessions.get(session['id']))
        with patch('runtime_protocol.SUPPORTED_CAPABILITIES',()),patch.object(module,'resolve_default_artifact_author',side_effect=AssertionError('read-only replay')):
            replay=reader.create(intent)
        self.assertFalse(replay.created);self.assertEqual(replay['request']['state'],'imported')
        self.assertFalse(replay['request']['needs_resume']);self.assertEqual(target.trigger.queue.records(),[])
