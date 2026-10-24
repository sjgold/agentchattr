"""Real archive/catalog/store units; no app factory, workers or provider claims."""
from copy import deepcopy
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch
import uuid
import zipfile

import archive
from agents import AgentTrigger
from channel_lifecycle import ChannelStore, ChannelConflict, ChannelUnavailable
from channel_service import ChannelService
from jobs import JobStore
from registry import RuntimeRegistry
from router import Router
from schedules import ScheduleStore
from session_engine import SessionEngine
from session_store import SessionStore
from store import MessageStore
from summaries import SummaryStore


class ChannelImportTests(unittest.TestCase):
    def setUp(self):
        scratch = Path(__file__).resolve().parents[1] / '.audit-tmp'
        temporary = tempfile.TemporaryDirectory(dir=scratch)
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.messages = MessageStore(str(self.root / 'messages.jsonl'))
        self.jobs = JobStore(str(self.root / 'jobs.json'))
        self.schedules = ScheduleStore(str(self.root / 'schedules.json'))
        self.summaries = SummaryStore(str(self.root / 'summaries.json'))
        self.sessions = SessionStore(str(self.root / 'sessions.json'))
        self.registry = RuntimeRegistry(str(self.root))
        self.trigger = AgentTrigger(self.registry, str(self.root))
        self.engine = SessionEngine(self.sessions, self.messages, self.trigger, self.registry)
        self.catalog = ChannelStore(self.root / 'channels.json')
        self.catalog.initialize(['general', 'review', 'peer'])
        self.settings = {'channels': ['general', 'review', 'peer']}
        self.saved = Mock()
        self.service = ChannelService(self.catalog, engine=self.engine, messages=self.messages,
            jobs=self.jobs, schedules=self.schedules, summaries=self.summaries, queue=self.trigger.queue,
            settings=self.settings, save_settings=self.saved, migrate_cursors=Mock(),
            router=Router([]), migrate_last_active=Mock())
        self.messages.bind_channel_policy(lambda: self.service)
        self.summaries.bind_channel_policy(lambda: self.service)
        self.engine.bind_channel_policy(lambda: self.service)
        self.engine._trigger.queue.bind_channel_policy(lambda: self.service)

    def zip_data(self, messages=(), jobs=None, summaries=None):
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, 'w') as zipped:
            zipped.writestr('manifest.json', json.dumps({'schema_version': archive.SCHEMA_VERSION, 'archive_id': uuid.uuid4().hex}))
            zipped.writestr('messages.jsonl', '\n'.join(json.dumps(row, ensure_ascii=False) for row in messages) + '\n')
            if jobs is not None:
                zipped.writestr('jobs.json', json.dumps(jobs, ensure_ascii=False))
            if summaries is not None:
                zipped.writestr('summaries.json', json.dumps(summaries, ensure_ascii=False))
        return buffer.getvalue()

    def import_data(self, messages=(), *, jobs=None, summaries=None, channels=None, max_channels=8):
        return archive.import_archive(self.zip_data(messages, jobs, summaries), self.messages, self.jobs,
            None, self.summaries, self.settings['channels'] if channels is None else channels,
            max_channels=max_channels, channel_policy=self.service)

    def test_archived_zip_row_remaps_strips_authority_and_never_wakes_queue(self):
        self.catalog.set_state('review', 'archived', expected_revision=0)
        observed = Mock()
        self.messages.on_message(observed)
        before_queue = self.trigger.queue.path.read_bytes() if self.trigger.queue.path.exists() else None
        report = self.import_data([{'uid': 'archived-source', 'channel': 'review', 'sender': 'operator',
            'text': 'Exact café\r\n@all', 'metadata': {'recipient_routing': {'forged': True}, 'seat_identity_id': 'forged'}}])
        self.assertTrue(report['ok'])
        saved = self.messages.get_snapshot(0)
        self.assertEqual(saved['channel'], 'general')
        self.assertEqual(saved['text'], 'Exact café\r\n@all')
        self.assertTrue(saved['metadata']['imported'])
        self.assertNotIn('recipient_routing', saved['metadata'])
        self.assertNotIn('seat_identity_id', saved['metadata'])
        self.assertTrue(any(row['from'] == 'review' and row['to'] == 'general'
            and row['reason'] == 'channel_retired' for row in report['channels']['remapped']))
        observed.assert_not_called()
        self.assertEqual(self.trigger.queue.path.read_bytes() if self.trigger.queue.path.exists() else None, before_queue)

    def test_new_valid_import_name_registers_catalog_and_settings_durably(self):
        result = self.service.resolve_import_channel('new-review', max_channels=8)
        self.assertEqual(result, {'channel': 'new-review', 'created': True, 'reason': None})
        self.assertEqual(ChannelStore(self.catalog.path).snapshot()['channels']['new-review'], 'active')
        self.assertIn('new-review', self.settings['channels'])
        self.saved.assert_called()

    def apply(self, op, channel):
        preview = self.service.preview(op, channel)
        return self.service.apply(op, channel, request_id=uuid.uuid4().hex,
            confirmation=channel, preview_token=preview['preview_token'])

    def effects(self):
        return ({str(path.relative_to(self.root)):path.read_bytes() for path in self.root.rglob('*.json')},
                self.messages._path.read_bytes() if self.messages._path.exists() else None,
                deepcopy(self.settings), self.messages._next_id, self.jobs._next_id)

    def row(self, uid, channel='review', **changes):
        return {'uid':uid, 'sender':'imported', 'channel':channel, 'text':'Literal ' + uid,
                'timestamp':100.25, 'time':'fixed-time', **changes}

    def remap_count(self, report, source, reason):
        return sum(row['count'] for row in report['channels']['remap_counts']
                   if row['from']==source and row['to']=='general' and row['reason']==reason)

    def test_strict_import_caps_precede_effects_and_normal_create_reopen_are_uncapped(self):
        for cap in (True, False, 0, -1, '8', 8.0, None):
            for call in (lambda:self.service.resolve_import_channel('new', max_channels=cap),
                         lambda:self.import_data([self.row('cap')], max_channels=cap)):
                before=self.effects()
                with self.subTest(cap=cap),self.assertRaises(ValueError):call()
                self.assertEqual(self.effects(),before)
        self.assertEqual(self.service.resolve_import_channel('full',max_channels=3),
                         {'channel':'general','created':False,'reason':'invalid_or_full'})
        self.apply('archive','review')
        self.assertTrue(self.service.resolve_import_channel('new',max_channels=3)['created'])
        self.apply('reopen','review')
        self.apply('create','uncapped')
        self.assertEqual(len(self.settings['channels']),5)

    def test_catalog_truth_ignores_stale_list_and_skips_remapped_summary(self):
        self.summaries.write('general','Keep original general summary','operator')
        before=self.summaries._path.read_bytes()
        self.apply('archive','review')
        stale=['general','review','ghost']
        report=self.import_data([self.row('stale','review'),self.row('new','new-channel')],channels=stale,
            summaries=[{'channel':'review','text':'Wrong general replacement','uid':'wrong-summary','updated_at':99999999999}])
        self.assertTrue(report['ok'])
        self.assertEqual(self.messages.get_snapshot(0)['channel'],'general')
        self.assertEqual(self.messages.get_snapshot(1)['channel'],'new-channel')
        self.assertNotIn('ghost',self.catalog.snapshot()['channels'])
        self.assertIn('new-channel',self.catalog.snapshot()['channels'])
        self.assertEqual(self.summaries._path.read_bytes(),before)
        self.assertEqual(report['sections']['summaries']['skipped'],1)
        self.assertEqual(self.remap_count(report,'review','channel_retired'),1)
        self.assertTrue(any('review' in warning for warning in report['warnings']))

    def test_grammar_retired_rows_and_aliases_never_resurrect_or_route(self):
        current=self.catalog.create('old',expected_revision=self.catalog.snapshot()['revision'])
        request=uuid.uuid4().hex
        self.catalog.begin('rename','old','owner',request_id=request,expected_revision=current['revision'])
        # Catalog lineage fixture only: no claim of configured cross-store rename migration.
        for step in ('messages','jobs','schedules','summaries','sessions','cursors','settings'):
            self.catalog.complete_step(request,step)
        self.catalog.finish(request)
        request=uuid.uuid4().hex
        self.catalog.begin('delete','owner',None,request_id=request,expected_revision=self.catalog.snapshot()['revision'])
        for step in ('todos','messages','settings'):self.catalog.complete_step(request,step)
        self.catalog.finish(request)
        for name in ('old','owner'):
            self.assertEqual(self.service.resolve_import_channel(name,max_channels=8),
                             {'channel':'general','created':False,'reason':'channel_retired'})
        for name in ('Upper','bad name','a_b','x'*21,'../file'):
            self.assertEqual(self.service.resolve_import_channel(name,max_channels=8),
                             {'channel':'general','created':False,'reason':'invalid_or_full'})
        valid='x'*20
        self.assertEqual(self.service.resolve_import_channel(valid,max_channels=8)['channel'],valid)
        report=self.import_data([self.row('old-row','old'),self.row('owner-row','owner')])
        self.assertEqual(self.remap_count(report,'old','channel_retired'),1)
        self.assertEqual(self.remap_count(report,'owner','channel_retired'),1)
        self.assertEqual(self.catalog.snapshot()['channels']['owner'],'retired')

    def test_initial_pending_or_corrupt_catalog_refuses_before_any_import_effect(self):
        original=self.catalog.path.read_bytes()
        self.catalog.begin('delete','review',None,request_id=uuid.uuid4().hex,expected_revision=0)
        before=self.effects()
        with self.assertRaises(ChannelConflict):self.import_data([self.row('blocked','general')])
        self.assertEqual(self.effects(),before)
        self.catalog.path.write_bytes(original)
        self.catalog.path.write_text('{broken',encoding='utf-8')
        before=self.effects()
        with self.assertRaises(ChannelUnavailable):self.import_data([self.row('unavailable','general')])
        self.assertEqual(self.effects(),before)

    def test_archive_at_interbatch_yield_preserves_first64_and_remaps_remaining_rows(self):
        rows=[self.row('batch-'+str(i)) for i in range(130)]
        transitioned=[]
        def between_batches(_):
            if not transitioned and len(self.messages.get_recent(1000))==64:
                self.assertFalse(self.engine._lock._is_owned())
                self.assertFalse(self.catalog._lock._is_owned())
                self.assertEqual(len(self.messages._path.read_text(encoding='utf-8').splitlines()),64)
                self.apply('archive','review');transitioned.append(True)
        with patch('archive.time.sleep',side_effect=between_batches):report=self.import_data(rows)
        self.assertEqual(transitioned,[True])
        saved=sorted(self.messages.get_recent(1000),key=lambda row:row['id'])
        self.assertEqual([row['channel'] for row in saved],['review']*64+['general']*66)
        self.assertEqual([row['uid'] for row in saved],[row['uid'] for row in rows])
        self.assertEqual(self.remap_count(report,'review','channel_retired'),66)

    def test_mid_import_intent_holds_old_channel_and_unseen_names_without_catalog_creation(self):
        rows=[self.row('initial-'+str(i)) for i in range(64)] + [self.row('held'),self.row('unseen','later-new'),self.row('peer','peer')]
        pending=[]
        def between_batches(_):
            if not pending and len(self.messages.get_recent(1000))==64:
                self.assertFalse(self.engine._lock._is_owned())
                self.catalog.begin('delete','review',None,request_id=uuid.uuid4().hex,
                                   expected_revision=self.catalog.snapshot()['revision'])
                pending.append(True)
        with patch('archive.time.sleep',side_effect=between_batches):report=self.import_data(rows)
        self.assertEqual(pending,[True])
        by_uid={row['uid']:row for row in self.messages.get_recent(1000)}
        self.assertEqual((by_uid['held']['channel'],by_uid['unseen']['channel'],by_uid['peer']['channel']),('general','general','peer'))
        self.assertEqual(self.remap_count(report,'review','channel_retired'),1)
        self.assertEqual(self.remap_count(report,'later-new','channel_repair_pending'),1)
        self.assertNotIn('later-new',self.catalog.snapshot()['channels'])

    def test_inactive_original_reply_and_breadcrumb_patches_are_skipped_without_history_rewrite(self):
        rows=[self.row('parent'),self.row('reply',reply_to_uid='parent'),
              self.row('breadcrumb',type='job_created',metadata={'job_id':42})]
        landed=[]
        def after_batch(_):
            if not landed and len(self.messages.get_recent(100))==3:
                landed.append(self.messages._path.read_bytes())
                self.apply('archive','review')
        job={'uid':'breadcrumb-job','id':42,'title':'Retained job','channel':'review','messages':[]}
        with patch('archive.time.sleep',side_effect=after_batch):report=self.import_data(rows,jobs=[job])
        self.assertEqual(len(landed),1)
        self.assertEqual(self.messages._path.read_bytes(),landed[0])
        self.assertNotIn('reply_to',self.messages.get_snapshot(1))
        self.assertEqual(self.messages.get_snapshot(2)['metadata']['job_id'],42)
        self.assertEqual(report['sections']['messages']['reply_links_skipped'],1)
        self.assertEqual(report['sections']['jobs']['breadcrumbs_skipped'],1)

    def test_partial_job_freezes_on_archive_and_reimport_after_reopen_does_not_complete_it(self):
        job={'uid':'partial-job','title':'Partial retained job','channel':'review','updated_at':42,
             'messages':[{'uid':'job-'+str(i),'sender':'imported','text':'row '+str(i)} for i in range(3)]}
        archived=[]
        def after_message(_):
            jobs=self.jobs.list_all()
            if not archived and jobs and len(jobs[0]['messages'])==1:
                self.assertFalse(self.engine._lock._is_owned())
                self.apply('archive','review');archived.append(True)
        with patch('archive.time.sleep',side_effect=after_message):report=self.import_data(jobs=[job])
        self.assertEqual(archived,[True])
        saved=self.jobs.list_all()[0]
        self.assertEqual(saved['channel'],'review')
        self.assertEqual([row['uid'] for row in saved['messages']],['job-0'])
        self.assertNotEqual(saved['updated_at'],42)
        self.assertEqual(report['sections']['jobs']['partial'],[{'job_id':saved['id'],'messages_imported':1,
            'messages_skipped':2,'reason':'channel_retired','reimport':'existing_job_uid_skipped'}])
        self.assertEqual(report['sections']['jobs']['messages_skipped'],2)
        self.apply('reopen','review')
        before=self.jobs._path.read_bytes()
        replay=self.import_data(jobs=[job])
        self.assertEqual(replay['sections']['jobs']['duplicates'],1)
        self.assertEqual(replay['sections']['jobs']['messages_created'],0)
        self.assertEqual(self.jobs._path.read_bytes(),before)
        self.assertEqual(len(self.jobs.list_all()),1)

    def test_active_job_and_summary_preserve_timestamps_and_job_metadata_cannot_forge_authority(self):
        report=self.import_data(jobs=[{'uid':'active-job','title':'Active','channel':'review','created_at':10,'updated_at':20,
            'messages':[{'uid':'job-active-row','sender':'operator','text':'literal','timestamp':15,'time':'fixed',
                         'metadata':{'recipient_routing':{'forged':True}}}]}],
            summaries=[{'uid':'active-summary','channel':'peer','text':'Summary literal','author':'imported','updated_at':30}])
        saved=self.jobs.list_all()[0]
        self.assertEqual((saved['created_at'],saved['updated_at']),(10,20))
        self.assertEqual(saved['messages'][0]['timestamp'],15)
        self.assertNotIn('recipient_routing',saved['messages'][0].get('metadata',{}))
        self.assertEqual(self.summaries.get('peer')['updated_at'],30)
        self.assertEqual(report['sections']['jobs']['messages_created'],1)

    def test_unconfigured_legacy_import_algorithm_remains_separate_and_unchanged(self):
        # Deliberately UNBOUND standalone storage; not evidence of a configured bypass.
        standalone=MessageStore(str(self.root/'standalone.jsonl'))
        legacy_name='legacy-channel-name-long'
        self.assertGreater(len(legacy_name),20)
        names=['general']
        report=archive.import_archive(self.zip_data([self.row('legacy',legacy_name)]),standalone,None,None,None,names)
        self.assertTrue(report['ok'])
        self.assertEqual(standalone.get_snapshot(0)['channel'],legacy_name)
        self.assertIn(legacy_name,names)
        self.assertNotIn(legacy_name,self.catalog.snapshot()['channels'])


if __name__ == '__main__':
    unittest.main()
