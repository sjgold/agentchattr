"""Root-owned driver review regressions on real temporary stores and ZIPs."""
import asyncio
from contextlib import ExitStack
import io
import json
import threading
import unittest
from unittest.mock import patch

import archive
import artifact_archive as codec
from artifact_store import ArtifactConflict, ArtifactUnavailable
from channel_lifecycle import ChannelConflict, ChannelInactive
from tests import test_artifact_archive_driver as fixture


class ArtifactArchiveDriverReviewTests(unittest.TestCase):
    setUp=fixture.ArtifactArchiveDriverTests.setUp
    packet=fixture.ArtifactArchiveDriverTests.packet
    audit=fixture.ArtifactArchiveDriverTests.audit
    portable=fixture.ArtifactArchiveDriverTests.portable
    source_graph=fixture.ArtifactArchiveDriverTests.source_graph
    export=fixture.ArtifactArchiveDriverTests.export
    target_history=fixture.ArtifactArchiveDriverTests.target_history
    restore=fixture.ArtifactArchiveDriverTests.restore
    repack=staticmethod(fixture.ArtifactArchiveDriverTests.repack)

    def data(self, count=1):
        self.source_graph(attempts=False)
        for i in range(count):self.messages.add('operator','history '+str(i),channel='review',uid='review-'+str(i))
        return self.export()

    def test_repair_started_after_first_history_batch_is_409_with_exact_partial_counts(self):
        data=self.data(65);history=self.target_history();append=history[0]._append_imported_batch
        def begin_after_commit(rows):
            saved=append(rows)
            if len(saved)==64:
                self.catalog.begin('rename','review','new-review',request_id='a'*32,
                    expected_revision=self.catalog.snapshot()['revision'])
            return saved
        with patch.object(history[0],'_append_imported_batch',side_effect=begin_after_commit):
            result=self.restore(data,history=history)
        self.assertFalse(result['ok']);self.assertTrue(result['partial'])
        self.assertEqual(result['sections']['messages']['created'],64)
        self.assertEqual(len(history[0].get_recent(100)),64)
        self.assertEqual(result['sections']['artifacts']['section_error']['code'],'artifact_archive_repair_pending')
        self.assertEqual(self.target.export_lineage_ids(),())

    def test_channel_inactive_at_artifact_commit_is_a_lineage_skip(self):
        data=self.data()
        with patch.object(self.target,'import_lineage',side_effect=ChannelInactive('private detail')):
            result=self.restore(data)
        self.assertTrue(result['ok']);self.assertFalse(result['partial'])
        row=result['sections']['artifacts']
        self.assertEqual(row['channel_unavailable_lineages'],1)
        self.assertEqual(row['details'][0]['reason'],'channel_unavailable')
        self.assertIsNone(row['section_error'])
        self.assertNotIn('private detail',json.dumps(result))

    def test_changed_import_classification_is_a_safe_whole_lineage_skip(self):
        data=self.data()
        with patch.object(self.target,'classify_import_lineage',side_effect=ArtifactConflict('prepare again')):
            result=self.restore(data)
        self.assertTrue(result['ok']);self.assertFalse(result['partial'])
        row=result['sections']['artifacts']
        self.assertEqual(row['details'][0]['reason'],'classification_changed')
        self.assertEqual(row['skipped_lineages'],1)
        self.assertIsNone(row['section_error'])
        self.assertEqual(self.target.export_lineage_ids(),())

    def test_history_row_faults_keep_report_and_never_blame_artifact_section(self):
        for kind in (TypeError,KeyError,AttributeError,RuntimeError):
            with self.subTest(kind=kind.__name__):
                data=self.data();history=fixture.make_stores(self.root/kind.__name__)
                for owner in history:
                    if hasattr(owner,'bind_channel_policy'):owner.bind_channel_policy(lambda:self.service)
                blob=self.repack(data,lambda members:members.update({'summaries.json':b'[{"channel":"review"}]'}))
                with patch.object(history[3],'get',side_effect=kind('private detail')):
                    result=self.restore(blob,history=history)
                self.assertFalse(result['ok']);self.assertTrue(result['partial'])
                self.assertGreaterEqual(result['sections']['messages']['created'],1)
                self.assertIsNone(result['sections']['artifacts']['section_error'])
                self.assertEqual(result['sections']['artifacts']['created_lineages'],0)
                expected='history_import_failed' if kind is RuntimeError else 'history_import_invalid'
                self.assertEqual(result['history_error']['code'],expected)
                self.assertNotIn('private detail',json.dumps(result))

    def test_held_owner_after_history_commit_is_fatal_storage_with_report(self):
        data=self.data()
        with patch.object(self.target,'prepare_import_lineage',side_effect=ArtifactUnavailable('private')):
            result=self.restore(data)
        self.assertFalse(result['ok']);self.assertTrue(result['partial'])
        self.assertEqual(result['sections']['messages']['created'],1)
        self.assertEqual(result['sections']['artifacts']['section_error']['code'],'artifact_archive_storage_unavailable')


    def test_export_version_failure_is_fixed_and_explicit(self):
        self.source_graph(attempts=False)
        with self.assertRaises(ValueError) as caught:
            archive.build_export(self.messages,None,None,None,app_version='x'*129,artifact_store=self.source)
        self.assertEqual(caught.exception.code,'artifact_archive_export_version_invalid')
        self.assertNotIn('x'*129,str(caught.exception))

    def test_lineage_limit_is_early_with_no_metadata_or_body_reads(self):
        from types import SimpleNamespace
        def forbidden(*args,**kwargs):raise AssertionError('No metadata or body reads for early lineage bound')
        owner=SimpleNamespace(export_lineage_ids=lambda:tuple(str(i) for i in range(1025)),
            export_metadata=forbidden,read_archive_object=forbidden)
        with self.assertRaises(archive.ArtifactArchiveLimit) as caught:
            archive.build_export(self.messages,None,None,None,artifact_store=owner)
        error=caught.exception
        self.assertEqual((error.bound,error.actual),('lineages',1025))
        self.assertEqual((error.history_bytes,error.artifact_bytes,error.container_overhead_bytes),(0,0,0))
        self.assertEqual(error.dominant_section,'history')

    def test_actual_export_handler_uses_thread_without_blocking_loop(self):
        import app
        entered,release=threading.Event(),threading.Event();main=threading.get_ident();seen=[]
        self.data()
        real=archive.build_export
        def blocked(*args,**kwargs):
            seen.append(threading.get_ident());entered.set()
            if not release.wait(2):raise AssertionError('event loop could not release export worker')
            return real(*args,**kwargs)
        async def exercise():
            task=asyncio.create_task(app.export_history())
            try:
                self.assertTrue(await asyncio.to_thread(entered.wait,1))
                self.assertNotEqual(seen,[main]);release.set()
                return await task
            finally:release.set()
        with ExitStack() as stack:
            for key,value in dict(store=self.messages,jobs=self.jobs,rules=None,summaries=self.summaries,
                                  artifacts=self.source,config={'server':{'version':'test'}}).items():
                stack.enter_context(patch.object(app,key,value))
            stack.enter_context(patch.object(archive,'build_export',side_effect=blocked))
            response=asyncio.run(exercise())
        self.assertEqual(response.status_code,200)
        self.assertTrue(self.restore(response.body)['ok'])

    def test_mid_export_unavailable_is_fixed_503(self):
        import app
        self.source_graph(attempts=False)
        with patch.object(app,'store',self.messages),patch.object(app,'jobs',self.jobs), \
                patch.object(app,'rules',None),patch.object(app,'summaries',self.summaries), \
                patch.object(app,'artifacts',self.source),patch.object(self.source,'read_archive_object',
                side_effect=ArtifactUnavailable('private path')):
            response=asyncio.run(app.export_history())
        self.assertEqual(response.status_code,503)
        self.assertEqual(json.loads(response.body)['code'],'artifact_archive_storage_unavailable')
        self.assertNotIn('private path',response.body.decode())

    def test_unknown_skip_reason_fails_to_fixed_invalid_lineage(self):
        report=archive._artifact_report();section=report['sections']['artifacts']
        for reason in ('duplicate','uid_collision','invalid_lineage','object_conflict','channel_unavailable',
                       'classification_changed','unexpected_private_reason'):
            archive._artifact_skip(section,0,reason)
        self.assertEqual(section['skipped_lineages'],7)
        self.assertEqual(section['details'][-1]['reason'],'invalid_lineage')


    def test_actual_import_handler_returns_history_partial_report_and_status(self):
        import app
        from fastapi import UploadFile
        data=self.data();history=self.target_history()
        blob=self.repack(data,lambda members:members.update({'summaries.json':b'[{"channel":"review"}]'}))
        with ExitStack() as stack:
            for key,value in dict(store=history[0],jobs=history[1],rules=None,summaries=history[3],
                    artifacts=self.target,room_settings=self.settings,ws_clients=set()).items():
                stack.enter_context(patch.object(app,key,value))
            stack.enter_context(patch.object(app,'_channels',return_value=self.service))
            stack.enter_context(patch.object(history[3],'get',side_effect=AttributeError('private detail')))
            response=asyncio.run(app.import_history(UploadFile(filename='input.zip',file=io.BytesIO(blob))))
        self.assertEqual(response.status_code,400)
        report=json.loads(response.body)
        self.assertTrue(report['partial']);self.assertEqual(report['sections']['messages']['created'],1)
        self.assertEqual(report['history_error']['code'],'history_import_invalid')
        self.assertIsNone(report['sections']['artifacts']['section_error'])
        self.assertNotIn('private detail',response.body.decode())

    def test_history_conflict_storage_and_unexpected_failures_use_fixed_codes(self):
        from channel_lifecycle import ChannelUnavailable
        for kind,code,status in ((ChannelConflict,'history_import_conflict',409),
                (ChannelInactive,'history_import_conflict',409),(OSError,'history_import_storage_unavailable',503),
                (ChannelUnavailable,'history_import_storage_unavailable',503),(IndexError,'history_import_failed',500)):
            with self.subTest(kind=kind.__name__):
                report=archive._artifact_report();report['sections']['messages']={'created':2}
                actual=archive._history_failure(report,kind('private'))
                self.assertEqual((actual['history_error']['code'],actual['history_error']['http_status']),(code,status))
                self.assertTrue(actual['partial']);self.assertIsNone(actual['sections']['artifacts']['section_error'])
                self.assertNotIn('private',json.dumps(actual))

    def test_export_import_reexport_reimport_preserves_first_origin_and_unversioned_rows(self):
        from artifact_store import ArtifactStore
        self.source_graph();first=self.export()
        self.assertTrue(self.restore(first)['ok'])
        original={row['audit']['request_id']:row['import_source'] for row in self.target.export_metadata(self.target.export_lineage_ids()[0])['requests']}
        second=archive.build_export(*self.target_history(),app_version='reexport',artifact_store=self.target)
        third=ArtifactStore(self.root/'third');third.bind_channel_policy(lambda:self.service)
        report=self.restore(second,owner=third)
        self.assertTrue(report['ok']);self.assertFalse(report['partial'])
        metadata=third.export_metadata(third.export_lineage_ids()[0])
        self.assertEqual({row['audit']['request_id']:row['import_source'] for row in metadata['requests']},original)
        self.assertEqual(sum(row['version_id'] is None for row in metadata['requests']),2)
        repeated=self.restore(second,owner=third)
        self.assertEqual(repeated['sections']['artifacts']['duplicate_lineages'],1)
        self.assertNotIn('history_error',repeated)

    def test_hostile_zips_through_driver_refuse_without_history_mutation(self):
        import warnings
        import zipfile
        data=self.data()
        with zipfile.ZipFile(io.BytesIO(data)) as zf:members={name:zf.read(name) for name in zf.namelist()}
        bad=[]
        bad.append(('schema',self.repack(data,lambda rows:rows.update({'manifest.json':
            json.dumps({**json.loads(rows['manifest.json']),'schema_version':1}).encode()})),
            'artifact_archive_schema_mismatch'))
        buffer=io.BytesIO()
        with zipfile.ZipFile(buffer,'w') as zf:
            for name,raw in members.items():zf.writestr(name,raw)
            with warnings.catch_warnings(record=True) as seen:
                warnings.simplefilter('always');zf.writestr('messages.jsonl',b'')
            self.assertTrue(seen)
        bad.append(('duplicate',buffer.getvalue(),'artifact_archive_invalid_section'))
        buffer=io.BytesIO()
        with zipfile.ZipFile(buffer,'w',zipfile.ZIP_DEFLATED) as zf:
            for name,raw in members.items():zf.writestr(name,b'x'*2000000 if name=='messages.jsonl' else raw)
        bad.append(('ratio',buffer.getvalue(),'artifact_archive_limit'))
        stored=self.repack(data,lambda rows:None)
        with zipfile.ZipFile(io.BytesIO(stored)) as zf:info=zf.getinfo('messages.jsonl')
        position=info.header_offset+30+len(info.filename.encode())+len(info.extra)
        corrupt=bytearray(stored);corrupt[position]^=1
        bad.append(('crc',bytes(corrupt),'artifact_archive_invalid_section'))
        # Keep the central directory but remove the tail of the actual stored history member.
        short=stored[:position+1]+stored[position+info.compress_size:]
        bad.append(('truncated',short,'artifact_archive_invalid_section'))
        for name,blob,code in bad:
            with self.subTest(name=name):
                history=fixture.make_stores(self.root/('hostile-'+name))
                for owner in history:
                    if hasattr(owner,'bind_channel_policy'):owner.bind_channel_policy(lambda:self.service)
                result=self.restore(blob,history=history)
                self.assertFalse(result['ok']);self.assertFalse(result.get('partial',False))
                self.assertEqual(result['sections']['artifacts']['section_error']['code'],code)
                self.assertEqual(history[0].get_recent(100),[])
                self.assertEqual(self.target.export_lineage_ids(),())

    def test_small_manifest_boundaries_and_legacy_primitives_through_driver(self):
        import zipfile
        data=self.data()
        for schema in (0,-1,1.0,True):
            with self.subTest(schema=schema):
                buffer=io.BytesIO()
                with zipfile.ZipFile(buffer,'w') as zf:
                    zf.writestr('manifest.json',json.dumps({'schema_version':schema}))
                result=self.restore(buffer.getvalue())
                self.assertTrue(result['ok']);self.assertNotIn('history_error',result)
                self.assertNotIn('artifacts',result['sections'])
        def exact(rows):
            raw=rows['manifest.json'];rows['manifest.json']=raw+b' '*(65536-len(raw))
        exact_data=self.repack(data,exact)
        self.assertTrue(self.restore(exact_data)['ok'])
        # A duplicate-key small manifest without artifact members stays the old parser path.
        buffer=io.BytesIO()
        with zipfile.ZipFile(buffer,'w') as zf:zf.writestr('manifest.json',b'{"schema_version":2,"schema_version":1}')
        result=self.restore(buffer.getvalue());self.assertTrue(result['ok'])
        self.assertEqual(result['archive']['schema_version'],1)

    def test_actual_export_accepts_exact_raw_and_exact_zip_bounds(self):
        from types import SimpleNamespace
        import random
        import zipfile
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
        # Freeze UUID/time so only the owned history text changes the byte totals.
        with patch.object(archive.uuid,'uuid4',return_value='fixed-export'), \
                patch.object(archive.time,'strftime',return_value='2026-10-25T00:00:00Z'):
            baseline=archive.build_export(history,None,None,None,artifact_store=self.source)
            with zipfile.ZipFile(io.BytesIO(baseline)) as zf:base=sum(info.file_size for info in zf.infolist())
            length=codec.MAX_ARCHIVE_BYTES-base
            rng=random.Random(81);block=''.join(rng.choices('abcdefghijklmnopqrstuvwxyz0123456789',k=16000))
            row['text']=(block*(length//len(block)+1))[:length]
            raw_exact=archive.build_export(history,None,None,None,artifact_store=self.source)
            with zipfile.ZipFile(io.BytesIO(raw_exact)) as zf:
                self.assertEqual(sum(info.file_size for info in zf.infolist()),codec.MAX_ARCHIVE_BYTES)
            self.assertLess(len(raw_exact),codec.MAX_ARCHIVE_BYTES)
            row['text']='x'*length
            with self.assertRaises(archive.ArtifactArchiveLimit) as caught:
                archive.build_export(history,None,None,None,artifact_store=self.source)
            self.assertEqual(caught.exception.bound,'zip')
            row['text']=row['text'][:length-(caught.exception.actual-codec.MAX_ARCHIVE_BYTES)]
            zip_exact=archive.build_export(history,None,None,None,artifact_store=self.source)
        self.assertEqual(len(zip_exact),codec.MAX_ARCHIVE_BYTES)
        with zipfile.ZipFile(io.BytesIO(zip_exact)) as zf:
            self.assertLess(sum(info.file_size for info in zf.infolist()),codec.MAX_ARCHIVE_BYTES)
            codec.preflight(zf,zip_size=len(zip_exact))


    def test_real_odd_history_job_rows_preserve_prior_messages_and_created_job(self):
        data=self.data()
        for conversation in (5,[None]):
            with self.subTest(conversation=conversation):
                history=fixture.make_stores(self.root/('odd-'+str(conversation)))
                for owner in history:
                    if hasattr(owner,'bind_channel_policy'):owner.bind_channel_policy(lambda:self.service)
                blob=self.repack(data,lambda rows:rows.update({'jobs.json':json.dumps([
                    {'uid':'odd-job','channel':'review','title':'Odd conversation','messages':conversation}]).encode()}))
                result=self.restore(blob,history=history)
                self.assertFalse(result['ok']);self.assertTrue(result['partial'])
                self.assertEqual(result['history_error']['code'],'history_import_invalid')
                self.assertEqual(result['sections']['messages']['created'],1)
                self.assertEqual(result['sections']['jobs']['created'],1)
                self.assertEqual(len(history[1].list_all()),1)
                self.assertEqual(len(history[0].get_recent(100)),1)
                self.assertIsNone(result['sections']['artifacts']['section_error'])


if __name__=='__main__':unittest.main()
