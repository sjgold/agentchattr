"""Configured archive driver/store units; no launched workers or providers."""
from contextlib import ExitStack
import asyncio
from copy import deepcopy
import hashlib
import io
import json
import unittest
from unittest.mock import patch
import zipfile
from types import SimpleNamespace

import archive
import artifact_archive as codec
from artifact_store import ArtifactUnavailable
from tests import test_artifact_imported_store as fixture
from tests.test_archive_feature import make_stores

_TARGET_OWNER=object()


class ArtifactArchiveDriverTests(unittest.TestCase):
    setUp=fixture.ArtifactImportedStoreTests.setUp
    packet=fixture.ArtifactImportedStoreTests.packet
    audit=fixture.ArtifactImportedStoreTests.audit
    portable=fixture.ArtifactImportedStoreTests.portable
    source_graph=fixture.ArtifactImportedStoreTests.source_graph

    def export(self):
        return archive.build_export(self.messages,self.jobs,None,self.summaries,
                                    app_version='driver-test',artifact_store=self.source)

    def target_history(self):
        values=make_stores(self.root/'restored-history')
        for owner in values:
            if hasattr(owner,'bind_channel_policy'):owner.bind_channel_policy(lambda:self.service)
        return values

    def restore(self,data,*,history=None,owner=_TARGET_OWNER,max_channels=8):
        history=history or self.target_history()
        return archive.import_archive(data,*history,list(self.settings['channels']),channel_policy=self.service,
            max_channels=max_channels,artifact_store=self.target if owner is _TARGET_OWNER else owner)

    @staticmethod
    def repack(data,mutate):
        with zipfile.ZipFile(io.BytesIO(data)) as zf:members={name:zf.read(name) for name in zf.namelist()}
        mutate(members);buffer=io.BytesIO()
        with zipfile.ZipFile(buffer,'w',zipfile.ZIP_STORED) as zf:
            for name,raw in members.items():zf.writestr(name,raw)
        return buffer.getvalue()

    def test_schema2_export_preserves_exact_objects_and_reads_outside_engine_boundary(self):
        graph,audit,version=self.source_graph()
        calls=[];read=self.source.read_archive_object
        def observed(*args,**kwargs):
            self.assertFalse(self.engine._lock._is_owned());self.assertFalse(self.catalog._lock._is_owned())
            calls.append(args[:2]);return read(*args,**kwargs)
        with patch.object(self.source,'read_archive_object',side_effect=observed):data=self.export()
        self.assertEqual(len(calls),4)
        with zipfile.ZipFile(io.BytesIO(data)) as zf:
            section=codec.preflight(zf,zip_size=len(data))
            self.assertEqual(section['manifest']['schema_version'],2)
            self.assertEqual(section['manifest']['artifacts']['requests'],3)
            self.assertEqual(codec.read_lineage_objects(zf,section['index']['lineages'][0]),graph[1])
            self.assertNotIn('launch_nonce',zf.read(codec.INDEX_MEMBER).decode('utf-8'))

    def test_round_trip_real_history_and_artifact_store_is_terminal_and_idempotent(self):
        graph,audit,version=self.source_graph()
        self.messages.add('operator','History retained with the authored deliverable',channel='review',uid='history-one')
        data=self.export();history=self.target_history()
        report=self.restore(data,history=history)
        self.assertTrue(report['ok']);self.assertFalse(report['partial'])
        section=report['sections']['artifacts']
        self.assertEqual((section['created_lineages'],section['created_versions'],section['created_requests']),(1,1,3))
        self.assertEqual(section['orphans'],{'objects':0,'bytes':0})
        self.assertEqual(len(history[0].get_recent(100)),1)
        self.assertEqual(self.target.get_version(version['id'])['markdown'].encode('utf-8'),graph[1][('version',version['id'])])
        self.assertEqual(self.target.pending('review'),[])
        self.assertFalse((self.target.root/'artifact_briefs'/'requests').exists())
        again=self.restore(data,history=history)
        self.assertTrue(again['ok']);self.assertFalse(again['partial'])
        self.assertEqual(again['sections']['artifacts']['duplicate_lineages'],1)
        self.assertEqual(again['sections']['artifacts']['status'],'complete')
        self.assertEqual(again['sections']['artifacts']['created_lineages'],0)
        self.assertEqual(len(history[0].get_recent(100)),1)

    def test_explicit_none_export_refuses_instead_of_silent_legacy_fallback(self):
        with self.assertRaises(codec.ArtifactSectionError) as caught:
            archive.build_export(self.messages,self.jobs,None,self.summaries,artifact_store=None)
        self.assertEqual(caught.exception.code,'artifact_archive_owner_unavailable')

    def test_actual_configured_export_none_and_held_owner_are_fixed_503(self):
        import app
        self.source_graph(attempts=False)
        self.source.path.write_bytes(b'HELD_INDEX')
        for owner,code in ((None,'artifact_archive_owner_unavailable'),
                           (self.source,'artifact_archive_storage_unavailable')):
            with self.subTest(code=code),patch.object(app,'artifacts',owner), \
                    patch.object(app,'config',{'server':{'version':'fixture'}}):
                response=asyncio.run(app.export_history())
                self.assertEqual(response.status_code,503)
                self.assertEqual(json.loads(response.body)['code'],code)

    def test_structural_missing_owner_held_owner_and_repair_refuse_before_history(self):
        graph,_,_=self.source_graph(attempts=False)
        self.messages.add('operator','must not land',channel='review',uid='no-partial')
        data=self.export()
        for fault in ('structure','missing_owner','held','repair'):
            with self.subTest(fault=fault):
                history=make_stores(self.root/('empty-'+fault))
                for owner in history:
                    if hasattr(owner,'bind_channel_policy'):owner.bind_channel_policy(lambda:self.service)
                target=type(self.target)(self.root/('artifacts-'+fault));target.bind_channel_policy(lambda:self.service)
                blob=data
                if fault=='structure':blob=self.repack(data,lambda members:members.update({'../unsafe':b'x'}))
                elif fault=='held':target.path.parent.mkdir(parents=True);target.path.write_bytes(b'BROKEN')
                elif fault=='repair':
                    import uuid
                    self.catalog.begin('rename','review','reserved',request_id=uuid.uuid4().hex,
                                       expected_revision=self.catalog.snapshot()['revision'])
                before={p.relative_to(self.root).as_posix():p.read_bytes() for p in self.root.rglob('*') if p.is_file()}
                report=self.restore(blob,history=history,owner=None if fault=='missing_owner' else target)
                self.assertFalse(report['ok']);self.assertFalse(report['partial'])
                expected={'structure':'artifact_archive_invalid_section','missing_owner':'artifact_archive_owner_unavailable',
                          'held':'artifact_archive_storage_unavailable','repair':'artifact_archive_repair_pending'}[fault]
                self.assertEqual(report['sections']['artifacts']['section_error']['code'],expected)
                self.assertEqual(report['sections']['artifacts']['status'],'rejected')
                self.assertEqual(len(history[0].get_recent(100)),0)
                self.assertEqual({p.relative_to(self.root).as_posix():p.read_bytes() for p in self.root.rglob('*') if p.is_file()},before)

    def test_bad_lineage_body_skips_only_it_and_keeps_top_partial_false(self):
        graph,_,version=self.source_graph(attempts=False)
        self.messages.add('operator','history succeeds',channel='review',uid='history-success')
        data=self.repack(self.export(),lambda members:members.update({codec.member_name('version',version['id']):b'WRONG'}))
        history=self.target_history();report=self.restore(data,history=history)
        self.assertTrue(report['ok']);self.assertFalse(report['partial'])
        self.assertEqual(report['sections']['messages']['created'],1)
        section=report['sections']['artifacts']
        self.assertEqual((section['status'],section['invalid_lineages'],section['skipped_lineages']),('partial',1,1))
        self.assertEqual(section['details'],[{'ordinal':0,'reason':'invalid_lineage','collision_kinds':[],'channel_reason':None}])
        self.assertEqual(section['orphans'],{'objects':0,'bytes':0})
        self.assertEqual(self.target.export_lineage_ids(),())

    def test_later_index_failure_keeps_exact_committed_counts_and_orphan_receipt(self):
        self.source_graph(attempts=False);self.source_graph(attempts=False)
        self.messages.add('operator','committed first',channel='review',uid='before-storage-fault')
        data=self.export();original=self.target.import_lineage;calls=[]
        def fail_second(plan,**kwargs):
            calls.append(plan)
            if len(calls)==2:raise ArtifactUnavailable('controlled final index failure')
            return original(plan,**kwargs)
        with patch.object(self.target,'import_lineage',side_effect=fail_second):report=self.restore(data)
        self.assertFalse(report['ok']);self.assertTrue(report['partial'])
        section=report['sections']['artifacts']
        self.assertEqual((section['status'],section['created_lineages'],section['created_versions'],section['created_requests']),
                         ('failed',1,1,1))
        self.assertEqual(section['section_error']['code'],'artifact_archive_storage_unavailable')
        self.assertEqual(report['sections']['messages']['created'],1)
        self.assertEqual(section['orphans'],{'objects':2,'bytes':sum(row[2] for row in calls[1].created_objects)})
        self.assertEqual(len(self.target.export_lineage_ids()),1)

    def test_object_conflict_and_capacity_skips_report_only_this_invocation_orphans(self):
        for reason in ('object_conflict','channel_unavailable'):
            with self.subTest(reason=reason):
                case=fixture.ArtifactImportedStoreTests();self.addCleanup(case.doCleanups);case.setUp()
                graph,_,version=case.source_graph(attempts=False)
                if reason=='object_conflict':
                    path=case.target._object_path('version',version['id']);path.parent.mkdir(parents=True,exist_ok=True)
                    path.write_bytes(b'# Pre-existing orphan remains unchanged')
                else:case.source.rename_channel('review','unseen')
                data=archive.build_export(case.messages,case.jobs,None,case.summaries,artifact_store=case.source)
                report=archive.import_archive(data,case.messages,case.jobs,None,case.summaries,
                    list(case.settings['channels']),channel_policy=case.service,artifact_store=case.target,max_channels=3)
                self.assertTrue(report['ok']);self.assertFalse(report['partial'])
                section=report['sections']['artifacts']
                self.assertEqual(section['details'][0]['reason'],reason)
                self.assertEqual(section['details'][0]['collision_kinds'],[])
                self.assertEqual(section['status'],'partial')
                self.assertEqual(section['orphans']['objects'],1 if reason=='object_conflict' else 2)
                self.assertEqual(case.target.export_lineage_ids(),())
                self.assertNotIn('unseen',case.catalog.snapshot()['channels'])

    def test_actual_import_handler_returns_full_fixed_section_errors(self):
        import app
        from fastapi import UploadFile
        self.source_graph(attempts=False);data=self.export()
        cases=[('owner',data,None,'artifact_archive_owner_unavailable',503),
               ('structure',self.repack(data,lambda members:members.update({'../unsafe':b'x'})),self.target,
                'artifact_archive_invalid_section',400),
               ('limit',self.repack(data,lambda members:members.update({'manifest.json':b' '*65537})),self.target,
                'artifact_archive_limit',413),
               ('repair',data,self.target,'artifact_archive_repair_pending',409)]
        for name,blob,owner,code,status in cases:
            with self.subTest(name=name),ExitStack() as stack:
                if name=='repair':
                    import uuid
                    self.catalog.begin('rename','review','reserved',request_id=uuid.uuid4().hex,
                                       expected_revision=self.catalog.snapshot()['revision'])
                for key,value in dict(store=self.messages,jobs=self.jobs,rules=None,summaries=self.summaries,
                    artifacts=owner,room_settings=self.settings,ws_clients=set()).items():stack.enter_context(patch.object(app,key,value))
                stack.enter_context(patch.object(app,'_channels',return_value=self.service))
                response=asyncio.run(app.import_history(UploadFile(filename='input.zip',file=io.BytesIO(blob))))
                self.assertEqual(response.status_code,status)
                body=json.loads(response.body)
                self.assertFalse(body['ok']);self.assertFalse(body['partial'])
                self.assertEqual(body['sections']['artifacts']['section_error']['code'],code)

    def test_structural_preflight_wins_before_catalog_read(self):
        self.source_graph(attempts=False)
        data=self.repack(self.export(),lambda members:members.update({'../unsafe':b'x'}))
        self.catalog.path.write_bytes(b'BROKEN_CATALOG')
        report=self.restore(data)
        self.assertFalse(report['ok']);self.assertFalse(report['partial'])
        self.assertEqual(report['sections']['artifacts']['section_error']['code'],'artifact_archive_invalid_section')
        self.assertEqual(self.catalog.path.read_bytes(),b'BROKEN_CATALOG')

    def test_history_archive_io_before_writes_and_staging_io_after_history_are_distinct(self):
        self.source_graph(attempts=False)
        self.messages.add('operator','durable history',channel='review',uid='io-history')
        data=self.export();history=self.target_history();read=codec._bounded_read
        def fail_history(zf,info,maximum):
            if info.filename=='messages.jsonl':raise OSError('PRIVATE_ARCHIVE_IO')
            return read(zf,info,maximum)
        with patch.object(codec,'_bounded_read',side_effect=fail_history):report=self.restore(data,history=history)
        self.assertFalse(report['ok']);self.assertFalse(report['partial'])
        self.assertEqual(report['sections']['artifacts']['status'],'failed')
        self.assertEqual(report['sections']['artifacts']['section_error']['code'],'artifact_archive_storage_unavailable')
        self.assertEqual(len(history[0].get_recent(100)),0)
        put=self.target._put_bytes
        def fail_stage(path,raw):
            if path.suffix=='.md':raise OSError('PRIVATE_STAGING_IO')
            return put(path,raw)
        with patch.object(self.target,'_put_bytes',side_effect=fail_stage):report=self.restore(data,history=history)
        self.assertFalse(report['ok']);self.assertTrue(report['partial'])
        self.assertEqual(report['sections']['messages']['created'],1)
        self.assertIsNone(report['sections']['artifacts']['orphans'])
        self.assertEqual(self.target.export_lineage_ids(),())
        self.assertNotIn('PRIVATE_',json.dumps(report))

    def test_measured_uncompressed_export_limit_and_history_tie_projection(self):
        # Controlled immutable owner observations; the writer/bytes/compressor
        # are real, while no fifty-MiB store file or provider is needed.
        from tests.test_artifact_import_benchmark import graph as make_graph
        snapshots={};objects={}
        raw=b'x'*524288
        for _ in range(100):
            portable,blobs=make_graph(1)
            version=portable['versions'][0];version.update(sha256=hashlib.sha256(raw).hexdigest(),byte_length=len(raw))
            blobs[('version',version['version_id'])]=raw
            value=self.source._import_metadata(portable)
            snapshots[portable['lineage_id']]={'lineage':value['lineages'][portable['lineage_id']],
                'requests':list(value['requests'].values()),'versions':list(value['versions'].values())}
            objects.update(blobs)
        calls=[]
        def read(kind,key,*,sha256,byte_length):
            body=objects[(kind,key)];self.assertEqual((hashlib.sha256(body).hexdigest(),len(body)),(sha256,byte_length))
            calls.append((kind,key));return body
        owner=SimpleNamespace(export_lineage_ids=lambda:tuple(snapshots),
            export_metadata=lambda key:deepcopy(snapshots[key]),read_archive_object=read)
        with self.assertRaises(archive.ArtifactArchiveLimit) as caught:
            archive.build_export(self.messages,None,None,None,artifact_store=owner)
        error=caught.exception
        self.assertEqual((error.bound,error.unit,error.limit,error.dominant_section),('uncompressed','bytes',52428800,'artifacts'))
        self.assertEqual(len(calls),200)
        index=codec.portable_index(snapshots.values(),archive_id='measure')
        from sealed_result_io import canonical_utf8
        self.assertEqual(error.artifact_bytes,len(canonical_utf8(index))+sum(len(body) for body in objects.values()))
        self.assertEqual(error.actual,error.total_bytes)
        self.assertGreater(error.actual,error.limit)
        tie=archive.ArtifactArchiveLimit('uncompressed',20,history_bytes=10,artifact_bytes=10)
        self.assertEqual(tie.projection()['dominant_section'],'history')

    def test_measured_zip_limit_counts_real_compressed_sections_and_container(self):
        import artifact_store
        import uuid
        packet={'version':1,'channel':'review','scope_kind':'selected_channel_messages',
                'source_run':None,'input':None,'messages':[]}
        audit=self.audit(artifact_store,self.source,packet=packet)
        audit.update(requester='o',instruction='i',format='m',created_at=1)
        audit['producer'].update(name='p',identity_id=uuid.uuid4().hex,requested_model_reason='r')
        self.source.reserve_request(audit,audit['request_id'])
        row={'id':0,'sender':'o','text':'','uid':'one','channel':'review'}
        history=SimpleNamespace(get_recent=lambda count:[dict(row)])
        baseline=archive.build_export(history,None,None,None,artifact_store=self.source)
        with zipfile.ZipFile(io.BytesIO(baseline)) as zf:
            baseline_raw=sum(info.file_size for info in zf.infolist())
        row['text']='x'*(codec.MAX_ARCHIVE_BYTES-baseline_raw)
        owned=[];close=zipfile.ZipFile.close
        def observed(zf):
            stream=zf.fp;writing=zf.mode=='w' and stream is not None
            close(zf)
            if writing:owned.append(stream.getvalue())
        with patch.object(zipfile.ZipFile,'close',observed),self.assertRaises(archive.ArtifactArchiveLimit) as caught:
            archive.build_export(history,None,None,None,artifact_store=self.source)
        error=caught.exception
        self.assertEqual((error.bound,error.dominant_section),('zip','history'))
        blob=max(owned,key=len)
        with zipfile.ZipFile(io.BytesIO(blob)) as zf:
            infos=zf.infolist()
            self.assertEqual(sum(info.file_size for info in infos),codec.MAX_ARCHIVE_BYTES)
            self.assertEqual(zf.getinfo('messages.jsonl').compress_type,zipfile.ZIP_STORED)
            compressed_history=sum(info.compress_size for info in infos if info.filename in codec.HISTORY_MEMBERS)
            compressed_artifacts=sum(info.compress_size for info in infos if info.filename not in codec.HISTORY_MEMBERS)
        self.assertEqual((error.history_bytes,error.artifact_bytes),(compressed_history,compressed_artifacts))
        self.assertEqual(error.container_overhead_bytes,len(blob)-compressed_history-compressed_artifacts)
        self.assertEqual(error.actual,len(blob));self.assertEqual(error.total_bytes,len(blob))
        self.assertGreater(error.actual,error.limit)

    def test_measured_index_member_and_lineage_export_bounds_use_owned_data(self):
        from tests.test_artifact_import_benchmark import graph as make_graph
        import artifact_store
        import uuid
        for bound in ('index','members','lineages'):
            with self.subTest(bound=bound):
                if bound=='index':
                    graph=make_graph(128,exact_bytes=4194304)
                    candidate=next(row for row in graph[0]['requests'] if len(row['instruction'])<32768)
                    candidate['instruction']+='x'
                    graphs=[graph];expected_actual=4194305
                elif bound=='members':
                    portable,objects=make_graph(2045)
                    request=deepcopy(portable['requests'][-1]);request['request_id']=uuid.uuid4().hex
                    ids=artifact_store.request_ids(request['request_id'])
                    request['scope']['packet_id']=ids['packet_id']
                    request['import_source'].update(original_state='failed',original_reason='generation_failed')
                    last=portable['versions'][-1]
                    request['expected_parent']={'version_id':last['version_id'],'sequence':last['sequence'],'sha256':last['sha256']}
                    portable['requests'].append(request)
                    objects[('packet',ids['packet_id'])]=next(raw for key,raw in objects.items() if key[0]=='packet')
                    graphs=[(portable,objects)];expected_actual=4097
                else:graphs=[make_graph(1) for _ in range(1025)];expected_actual=1025
                snapshots={};bodies={}
                for portable,objects in graphs:
                    metadata=self.source._import_metadata(portable)
                    key=portable['lineage_id']
                    snapshots[key]={'lineage':metadata['lineages'][key],
                        'requests':list(metadata['requests'].values()),'versions':list(metadata['versions'].values())}
                    bodies.update(objects)
                def read(kind,key,*,sha256,byte_length):
                    raw=bodies[(kind,key)]
                    self.assertEqual((hashlib.sha256(raw).hexdigest(),len(raw)),(sha256,byte_length))
                    return raw
                owner=SimpleNamespace(export_lineage_ids=lambda:tuple(snapshots),
                    export_metadata=lambda key:deepcopy(snapshots[key]),read_archive_object=read)
                with self.assertRaises(archive.ArtifactArchiveLimit) as caught:
                    archive.build_export(self.messages,None,None,None,artifact_store=owner)
                error=caught.exception
                self.assertEqual((error.bound,error.actual),(bound,expected_actual))
                self.assertEqual(error.total_bytes,error.history_bytes+error.artifact_bytes)
                self.assertEqual(error.container_overhead_bytes,0)
                self.assertEqual(error.dominant_section,'history' if bound=='lineages' else 'artifacts')


if __name__=='__main__':unittest.main()
