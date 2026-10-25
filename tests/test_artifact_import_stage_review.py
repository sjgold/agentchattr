"""Root-owned classification-before-staging and graph validation regressions."""
from copy import deepcopy
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
import threading
from pathlib import Path
import unittest
from unittest.mock import patch
import uuid

import artifact_store as module
from channel_lifecycle import ChannelInactive, DELETE_STEPS
from tests import test_artifact_imported_store as fixture


class ArtifactImportStageReviewTests(unittest.TestCase):
    setUp = fixture.ArtifactImportedStoreTests.setUp
    packet = fixture.ArtifactImportedStoreTests.packet
    audit = fixture.ArtifactImportedStoreTests.audit
    portable = fixture.ArtifactImportedStoreTests.portable
    source_graph = fixture.ArtifactImportedStoreTests.source_graph
    files = staticmethod(fixture.ArtifactImportedStoreTests.files)

    def prepare(self, owner, graph):
        return owner.prepare_import_lineage(*graph)

    def test_indexed_missing_object_is_never_filled_with_conflicting_archive_bytes(self):
        graph, audit, version = self.source_graph(attempts=False)
        path = self.source.root/'artifacts'/'objects'/(version['id']+'.md')
        path.unlink()  # Existing local metadata still owns this missing object.
        changed, objects = deepcopy(graph[0]), dict(graph[1])
        raw = b'# Foreign bytes must not repair local corruption\r\n'
        changed['versions'][0].update(sha256=hashlib.sha256(raw).hexdigest(), byte_length=len(raw))
        objects[('version', version['id'])] = raw
        before = self.files(self.source)
        with self.assertRaises(module.ArtifactImportCollision) as caught:
            self.prepare(self.source, (changed, objects))
        self.assertEqual(caught.exception.reason, 'uid_collision')
        self.assertEqual(set(caught.exception.collision_kinds), {'lineage','request','version','packet','dispatch'})
        self.assertEqual(self.files(self.source), before)
        self.assertFalse(path.exists())

    def test_known_live_request_derived_version_path_is_never_staged(self):
        graph, audit, version = self.source_graph(attempts=False)
        self.target.put_packet(audit['request_id'], self.source.get_packet(audit['scope']['packet_id']))
        self.target.reserve_request(audit, audit['request_id'])
        before = self.files(self.target)
        prepared = self.prepare(self.target, graph)
        with self.service._boundary():
            result = self.target.classify_import_lineage(prepared)
        self.assertEqual(result['reason'], 'uid_collision')
        self.assertEqual(set(result['collision_kinds']), {'lineage','request','packet','dispatch'})
        self.assertEqual(self.files(self.target), before)
        self.target.set_attempt_state(audit['request_id'], audit['attempt_id'], 'prepared',
                                      {'state':'queued','reason':'queued'})
        saved = self.target.commit_version(audit['request_id'],audit['attempt_id'],audit['dispatch_id'],
            '# The live author remains free to write different content',
            {'confirmed_model':None,'confirmation_reason':'cli_model_unverified'})
        self.assertEqual(saved['sequence'],1)

    def test_unversioned_attempt_parent_must_reference_its_own_lineage_version(self):
        graph, _, _ = self.source_graph()
        for bad in ('id','sha256','sequence'):
            with self.subTest(field=bad):
                portable = deepcopy(graph[0])
                request = next(row for row in portable['requests']
                               if row['import_source']['original_state']=='failed')
                request['expected_parent'][bad if bad!='id' else 'version_id'] = (
                    2 if bad=='sequence' else 'f'*(64 if bad=='sha256' else 32))
                with self.assertRaises(module.ArtifactValidationError):
                    self.prepare(self.target,(portable,graph[1]))
                self.assertFalse(self.target.path.exists())

    def test_all_existing_ids_in_different_local_lineage_are_collision_not_duplicate(self):
        graph, audit, _ = self.source_graph(attempts=False)
        prepared=self.prepare(self.target,graph)
        with self.service._boundary():self.target.import_lineage(prepared,channel='review')
        other=self.audit(module,self.target)
        self.target.reserve_request(other,other['request_id'])
        self.target.set_attempt_state(other['request_id'],other['attempt_id'],'prepared',
                                      {'state':'failed','reason':'generation_failed'})
        portable=deepcopy(graph[0]);portable['lineage_id']=other['lineage_id']
        before=self.files(self.target)
        prepared=self.prepare(self.target,(portable,graph[1]))
        with self.service._boundary():result=self.target.classify_import_lineage(prepared)
        self.assertEqual(result['reason'],'uid_collision')
        self.assertEqual(set(result['collision_kinds']),{'lineage','request','version','packet','dispatch'})
        self.assertEqual(self.files(self.target),before)

    def test_portable_packet_chain_and_hostile_type_matrix_refuses_before_staging(self):
        graph,audit,version=self.source_graph(attempts=False)
        parent={'version_id':version['id'],'sequence':1,'sha256':version['sha256']}
        next_audit=self.audit(module,self.source,lineage_id=audit['lineage_id'],parent=parent)
        self.source.reserve_request(next_audit,next_audit['request_id'])
        self.source.set_attempt_state(next_audit['request_id'],next_audit['attempt_id'],'prepared',
                                      {'state':'queued','reason':'queued'})
        self.source.commit_version(next_audit['request_id'],next_audit['attempt_id'],next_audit['dispatch_id'],
            '# Second',{'confirmed_model':None,'confirmation_reason':'cli_model_unverified'})
        graph=self.portable(self.source,audit['lineage_id'])
        cases=('packet_hash','scope_kind','scope_digest','input_revision','packet_channel','source_run',
            'parent','sequence_gap','head','version_order','orphan_version','two_versions_one_request',
            'derived_version','dispatch_extra','bad_origin','origin_version','bool_sequence','float_sequence',
            'bytearray','string_body','duplicate_request','deep_nesting','non_dict')
        for bad in cases:
            with self.subTest(case=bad):
                portable,objects=deepcopy(graph[0]),dict(graph[1])
                request=portable['requests'][0];scope=request['scope'];first=portable['versions'][0]
                if bad=='packet_hash':objects[('packet',scope['packet_id'])]+=b' '
                elif bad=='scope_kind':scope['kind']='run_accepted_messages'
                elif bad=='scope_digest':scope['message_refs'][0]['sha256']='f'*64
                elif bad=='input_revision':scope['input_revision']='f'*64
                elif bad=='packet_channel':request['original_channel']='peer'
                elif bad=='source_run':request['source_run']={'session_id':1,'run_id':'a'*32,
                    'input_revision':'f'*64,'state_at_request':'stopped'}
                elif bad=='parent':portable['versions'][1]['parent_version_id']='f'*32
                elif bad=='sequence_gap':first['sequence']=3
                elif bad=='head':portable['head_version_id']=first['version_id']
                elif bad=='version_order':portable['versions'].reverse()
                elif bad=='orphan_version':first['request_id']='f'*32
                elif bad=='two_versions_one_request':portable['versions'][1]['request_id']=first['request_id']
                elif bad=='derived_version':first['version_id']='f'*32
                elif bad=='dispatch_extra':request['dispatch_id']='f'*32
                elif bad=='bad_origin':request['import_source']['archive_id']='../path'
                elif bad=='origin_version':request['import_source']['original_state']='failed'
                elif bad=='bool_sequence':first['sequence']=True
                elif bad=='float_sequence':first['sequence']=1.0
                elif bad in ('bytearray','string_body'):
                    key=('packet',scope['packet_id'])
                    objects[key]=bytearray(objects[key]) if bad=='bytearray' else objects[key].decode('utf-8')
                elif bad=='duplicate_request':portable['requests'].append(deepcopy(request))
                elif bad=='deep_nesting':
                    nested=[]
                    for _ in range(1500):nested=[nested]
                    request['instruction']=nested
                else:portable=None
                with self.assertRaises(module.ArtifactValidationError):self.prepare(self.target,(portable,objects))
                self.assertFalse(self.target.path.exists())
                self.assertEqual(self.files(self.target),{})

    def test_stale_owner_and_body_free_classification_have_no_external_effects(self):
        graph,audit,_=self.source_graph(attempts=False)
        outside={p.relative_to(self.root).as_posix():p.read_bytes() for p in self.root.rglob('*')
                 if p.is_file() and not p.is_relative_to(self.target.root)}
        prepared=self.prepare(self.target,graph)
        stale=module.ArtifactStore(self.target.root);stale.bind_channel_policy(lambda:self.service)
        original=Path.open
        def no_body(path,*args,**kwargs):
            if path.suffix=='.md' or path.parent.name=='packets':raise AssertionError('classification read body')
            return original(path,*args,**kwargs)
        with patch.object(Path,'open',no_body),self.service._boundary():
            self.assertIsNone(self.target.classify_import_lineage(prepared))
        with self.service._boundary():self.target.import_lineage(prepared,channel='peer')
        before=self.files(self.target)
        with self.assertRaises(module.ArtifactUnavailable),self.service._boundary():
            stale.import_lineage(prepared,channel='review')
        self.assertEqual(self.files(self.target),before)
        self.assertEqual(outside,{p.relative_to(self.root).as_posix():p.read_bytes() for p in self.root.rglob('*')
            if p.is_file() and not p.is_relative_to(self.target.root)})
        self.assertEqual(self.target.get_request(audit['request_id'])['channel'],'peer')
        self.assertEqual(self.target.get_request(audit['request_id'])['audit']['original_channel'],'review')
        self.assertFalse((self.target.root/'artifact_briefs'/'requests').exists())
        self.assertFalse((self.target.root/'queue').exists())

    def test_subset_of_longer_local_history_is_duplicate_but_lineage_only_overlap_is_not(self):
        graph,audit,version=self.source_graph()
        pending=next(row for row in graph[0]['requests'] if row['import_source']['original_state']=='prepared')
        ids=module.request_ids(pending['request_id'])
        self.source.set_attempt_state(pending['request_id'],ids['attempt_id'],'prepared',
                                      {'state':'queued','reason':'queued'})
        self.source.commit_version(pending['request_id'],ids['attempt_id'],ids['dispatch_id'],'# Later local version',
            {'confirmed_model':None,'confirmation_reason':'cli_model_unverified'})
        before=self.files(self.source)
        prepared=self.prepare(self.source,graph)
        with self.service._boundary():result=self.source.import_lineage(prepared,channel='review')
        self.assertEqual((result['reason'],result['collision_kinds']),('duplicate',[]))
        self.assertEqual(self.files(self.source),before)
        other,_,_=self.source_graph(attempts=False)
        portable=deepcopy(other[0]);portable['lineage_id']=audit['lineage_id']
        before=self.files(self.target)
        # Seed only the old lineage into target, then reject a different chain
        # which shares that lineage id but no request/version/packet ids.
        prepared=self.prepare(self.target,graph)
        with self.service._boundary():self.target.import_lineage(prepared,channel='review')
        before=self.files(self.target)
        prepared=self.prepare(self.target,(portable,other[1]))
        with self.service._boundary():result=self.target.classify_import_lineage(prepared)
        self.assertEqual((result['reason'],result['collision_kinds']),('uid_collision',['lineage']))
        self.assertEqual(self.files(self.target),before)

    def test_local_reserve_racing_stage_is_explicit_and_low_level_settlement_progresses(self):
        graph,audit,version=self.source_graph(attempts=False)
        entered,release=threading.Event(),threading.Event()
        original=self.target._put_bytes;preparer=[]
        def stage(path,raw):
            if threading.get_ident()==preparer[0] and path.suffix=='.md':
                entered.set()
                if not release.wait(5):raise AssertionError('stage gate timed out')
            return original(path,raw)
        def prepare():
            preparer.append(threading.get_ident())
            return self.prepare(self.target,graph)
        with patch.object(self.target,'_put_bytes',stage),ThreadPoolExecutor(1) as pool:
            future=pool.submit(prepare)
            try:
                self.assertTrue(entered.wait(5))
                self.target.put_packet(audit['request_id'],self.source.get_packet(audit['scope']['packet_id']))
                self.target.reserve_request(audit,audit['request_id'])
                self.target.set_attempt_state(audit['request_id'],audit['attempt_id'],'prepared',
                    {'state':'queued','reason':'queued'})
            finally:release.set()
            prepared=future.result(timeout=5)
        with self.service._boundary():result=self.target.import_lineage(prepared,channel='review')
        self.assertEqual(result['reason'],'uid_collision')
        with self.assertRaises(module.ArtifactConflict):
            self.target.commit_version(audit['request_id'],audit['attempt_id'],audit['dispatch_id'],'# Local bytes',
                {'confirmed_model':None,'confirmation_reason':'cli_model_unverified'})
        self.assertTrue(any(row['kind']=='orphan_version' and row['id']==version['id']
                            for row in self.target.diagnostics()['rows']))
        self.target.set_attempt_state(audit['request_id'],audit['attempt_id'],'queued',
            {'state':'cancelled','reason':'operator_cancelled'})
        self.assertEqual(self.target.pending('review'),[])

    def test_inactive_missing_reserved_repair_channels_refuse_and_real_remap_is_explicit(self):
        for state in ('missing','archived','retired','reserved','repair','invalid'):
            with self.subTest(state=state):
                case=fixture.ArtifactImportedStoreTests();self.addCleanup(case.doCleanups);case.setUp()
                graph,audit,_=case.source_graph(attempts=False)
                prepared=case.target.prepare_import_lineage(*graph)
                channel='review'
                if state=='missing':channel='missing'
                elif state=='invalid':channel='Upper'
                elif state=='archived':case.catalog.set_state('review','archived',expected_revision=case.catalog.snapshot()['revision'])
                elif state=='retired':
                    operation=uuid.uuid4().hex
                    case.catalog.begin('delete','review',None,request_id=operation,expected_revision=case.catalog.snapshot()['revision'])
                    for step in DELETE_STEPS:case.catalog.complete_step(operation,step)
                    case.catalog.finish(operation)
                else:
                    case.catalog.begin('rename','review','reserved',request_id=uuid.uuid4().hex,
                                       expected_revision=case.catalog.snapshot()['revision'])
                    if state=='reserved':channel='reserved'
                before=self.files(case.target)
                with self.assertRaises(module.ArtifactValidationError if state=='invalid' else ChannelInactive):
                    case.target.import_lineage(prepared,channel=channel)
                self.assertEqual(self.files(case.target),before)
                if state=='retired':
                    with case.service._boundary():
                        remap=case.service.resolve_import_channel('review',max_channels=8)
                        case.target.import_lineage(prepared,channel=remap['channel'])
                    self.assertEqual(remap['reason'],'channel_retired')
                    self.assertEqual(case.target.get_request(audit['request_id'])['channel'],'general')


if __name__=='__main__':unittest.main()
