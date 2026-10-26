"""Synthetic checkpoint orchestration tests. No latency/gate measurements.

Run: python tools/test_artifact_checkpoint_controls.py
Fixture/body/clock work is replaced by synthetic rows for orchestration only.
"""
import contextlib
import io
import json
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import measure_artifact_diagnostics as m
import profile_artifact_authority_phases as a


class CheckpointControlTests(unittest.TestCase):
    def test_incremental_receipts_errors_continue_and_design_has_no_import_or_verdict(self):
        root = ROOT / '.audit-tmp'
        before = set(root.glob('r2-*-design-*.json'))
        self.addCleanup(lambda: [p.unlink() for p in set(root.glob('r2-*-design-*.json'))-before])
        seen = []
        def probe(kind, checkpoint=None):
            if seen:
                self.assertTrue(any(json.loads(p.read_text(encoding='utf-8'))['samples']
                    for p in set(root.glob('r2-authority-phase-design-*.json'))-before))
            seen.append(kind)
            checkpoint({'caller':kind,'phase':'A','seconds':123})
            if len(seen)==1: raise AssertionError('synthetic failure after A')
            return {'caller':kind,'A_seconds':123,'C_probe_seconds':456}
        with patch.object(a,'probe',probe), patch.object(sys,'argv',['authority','--samples','10']), contextlib.redirect_stdout(io.StringIO()):
            a.historical_design(10)
        ar = json.loads(next(iter(set(root.glob('r2-*-design-*.json'))-before)).read_text(encoding='utf-8'))
        self.assertEqual((len(ar['samples']),len(ar['phase_observations'])),(90,90))
        self.assertEqual(ar['samples'][0]['error']['type'],'AssertionError')
        self.assertEqual(ar['samples'][-1]['caller'],'startup_terminal')
        middle = set(root.glob('r2-*-design-*.json'))
        calls=[]
        class Dummy:
            def __init__(self):
                self.root=root/'nonexistent-synthetic-fixture'
                self.artifacts=SimpleNamespace(_data={'version':2,'requests':{
                    str(i):{'state':'imported','audit':{}} for i in range(128)}},path=ROOT/'artifact_store.py',diagnostic_store=object())
                self.artifacts._data['requests']['candidate']={'state':'queued','audit':{}}
            def doCleanups(self): pass
        def setup(kind): return Dummy(),{'request_id':'candidate'},None,None,None
        def measure(case,store,audit,phase,checkpoint=None):
            calls.append(phase)
            checkpoint({'phase':phase,'hold':321,'peer_wait':654})
            if len(calls)==1:raise AssertionError('synthetic failure after hold')
            return {'phase':phase,'hold':321,'peer_wait':654,'exception_type':None,'normal_pass':False,'hard_pass':False}
        def structural(case,store,checkpoint=None):return measure(case,store,{},'structural_read',checkpoint)
        def action(case,owner,run,phase,limit,checkpoint=None):return measure(case,None,{},phase,checkpoint),({'quarantine_ids':['x']*8,'overflow_count':2},{'quarantine_ids':[],'overflow_count':0})
        with patch.object(a,'setup',setup),patch.object(m,'setup',lambda case,store,audits:(store,{})),patch.object(m,'measure',measure),patch.object(m,'structural_read',structural),patch.object(m,'measure_action',action),patch.object(m,'record',return_value={'counter':1}),patch.object(m,'import_gates',side_effect=AssertionError('DESIGN must not import')),contextlib.redirect_stdout(io.StringIO()):
            m.design_checkpoint(10)
        dr=json.loads(next(iter(set(root.glob('r2-*-design-*.json'))-middle)).read_text(encoding='utf-8'))
        self.assertEqual((len(dr['samples']),len(dr['phase_observations'])),(37,37))
        self.assertEqual(dr['samples'][0]['error']['type'],'AssertionError')
        self.assertEqual(dr['samples'][-1]['phase'],'structural_read')
        def no_verdict(value):
            if isinstance(value,dict):
                self.assertFalse({'normal_pass','hard_pass','margin_pass','pass'} & value.keys())
                for v in value.values(): no_verdict(v)
            elif isinstance(value,list):
                for v in value: no_verdict(v)
        for value in (ar,dr):
            no_verdict(value)
            for key in ('tool_sha256','source_sha256','product_pin','authoring_schema','r2_d1_d2_present','dirty_tree','fixture_and_support_sha256'):
                self.assertIn(key,value)

    def test_cleanup_error_does_not_replace_completed_result(self):
        rows=[]
        case=SimpleNamespace(doCleanups=lambda: (_ for _ in ()).throw(AssertionError('cleanup sentinel')))
        def completed():
            try: return {'A_seconds':123}
            finally:a.cleanup_probe(case,ROOT/'absent','synthetic',rows.append)
        self.assertEqual(completed(),{'A_seconds':123})
        self.assertEqual(rows[0]['phase'],'cleanup')
        self.assertEqual(rows[0]['error']['message'],'cleanup sentinel')

    def test_detected_provenance_uses_real_single_writer(self):
        value=a.checkpoint_provenance(__file__)
        self.assertTrue(value['r2_d1_d2_present'])
        self.assertFalse(value['fsync_mocked'])
        self.assertEqual(value['authoring_schema'],2)
        self.assertIn('sealed_result_io.py',value['fixture_and_support_sha256'])
        self.assertIn('tests/test_artifact_store.py',value['fixture_and_support_sha256'])

    def test_production_observation_times_actual_phases_without_an_outer_boundary(self):
        import threading
        case=SimpleNamespace(engine=SimpleNamespace(_lock=threading.RLock()),
            catalog=SimpleNamespace(_lock=threading.RLock()),artifacts=SimpleNamespace(_lock=threading.RLock()))
        @contextlib.contextmanager
        def boundary():
            with case.engine._lock,case.catalog._lock:yield
        service=SimpleNamespace(_boundary=boundary)
        def require_active(channel):
            with service._boundary():return channel
        service.require_active=require_active;case.service=service
        observed=[];peer_progress=threading.Event()
        original_require=service.require_active
        def progressed(channel):
            value=original_require(channel);peer_progress.set();return value
        service.require_active=progressed
        def writer(intent):
            observed.append(tuple(owner._lock._is_owned() for owner in (case.engine,case.catalog,case.artifacts)))
            self.assertTrue(peer_progress.wait(1))  # Synthetic control rendezvous only.
            return b'{}'
        case.authority=SimpleNamespace(_persist_diagnostic_intent=writer,_settle_diagnostic_intent=lambda *args:'settled',
            agents=SimpleNamespace(queue=SimpleNamespace(_lock=case.engine._lock)))
        def action():
            with case.authority.agents.queue._lock:pass  # Startup's cached engine-lock alias.
            with service._boundary():pass
            receipt=case.authority._persist_diagnostic_intent('synthetic')
            with service._boundary():return case.authority._settle_diagnostic_intent(receipt)
        row,value=a.production_observe(case,action)
        self.assertEqual(value,'settled');self.assertEqual(observed,[(False,False,False)])
        self.assertEqual([hold['phase'] for hold in row['holds']],['A','C'])
        self.assertEqual(len(row['B_seconds']),1);self.assertTrue(row['peer_waits'])
        self.assertEqual(row['peer_errors'],[])
        self.assertTrue(any(item['measured_thread'] and item['incidental_to_boundary'] for item in row['engine_holds']))
        def healthy():
            with service._boundary():return 'healthy'
        row,value=a.production_observe(case,healthy,healthy=True)
        self.assertEqual(value,'healthy');self.assertEqual(row['B_seconds'],[])
        self.assertEqual([hold['phase'] for hold in row['holds']],['A'])
        row,value=a.production_observe(case,lambda:'read',persist=False)
        self.assertEqual(value,'read');self.assertEqual(row['holds'],[])
        self.assertEqual(row['B_authority_owned'],[[False,False,False]])
        self.assertIn('whole_call',row);self.assertIn('A_plus_C_seconds',row)
        self.assertFalse(any(item['measured_thread'] for item in row['engine_holds']))

    def test_sentinel_thresholds_intervals_and_independent_error_lifecycle(self):
        import tempfile
        from artifact_measurement_support import MachineSentinel
        with tempfile.TemporaryDirectory(dir=ROOT/'.audit-tmp') as directory:
            notifications=[];sentinel=MachineSentinel(directory,lambda:notifications.append('gap'))
            sentinel.observe_cycle(0,100000000,10,20,{})
            sentinel.observe_cycle(100000000,200000001,20,30,{})
            state=sentinel.snapshot()
            self.assertEqual(state['cycles'],2);self.assertEqual(len(state['gaps_over_100ms']),1)
            self.assertEqual(state['gaps_over_100ms'][0]['start_monotonic_ns'],100000000)
            self.assertEqual(notifications,['gap']);sentinel.scratch.rmdir()
            def fails():raise OSError('synthetic sentinel IO fault')
            sentinel=MachineSentinel(directory,cycle=fails);sentinel.start();sentinel.close()
            state=sentinel.snapshot();self.assertFalse(state['running'])
            self.assertEqual(state['errors'][0]['type'],'OSError')
            import threading
            self.assertNotEqual(state['thread_id'],threading.get_ident())

    def test_temporal_policy_never_excludes_or_changes_original_miss(self):
        from artifact_measurement_support import classify_misses
        def span(start,end,limit=.216):return {'start_monotonic_ns':start,'end_monotonic_ns':end,'seconds':(end-start)/1e9,'limit_seconds':limit}
        rows=[{'caller':'overlap','pass':False,'gate_intervals':[span(100000000,700000000)]},
            {'caller':'no_overlap','pass':False,'gate_intervals':[span(900000000,1500000000)]},
            {'caller':'mixed','pass':False,'gate_intervals':[span(100000000,700000000),span(900000000,1500000000)]}]
        state={'gaps_over_100ms':[span(0,600000000)],'errors':[]}
        self.assertEqual(classify_misses(rows,state),['overlap'])
        self.assertTrue(all(row['pass'] is False for row in rows));self.assertEqual(len(rows),3)
        state['gaps_over_100ms']=[span(0,500000000)]
        self.assertEqual(classify_misses(rows,state),[])  # Strict >0.5 s.
        state['gaps_over_100ms']=[span(700000000,1300000000)]
        classify_misses(rows,state)
        self.assertEqual(rows[0]['miss_classifications'][0]['classification'],'unattributed-real-miss')

    def test_sentinel_gap_is_incrementally_journaled_then_embedded(self):
        import tempfile
        from artifact_measurement_support import MeasurementReceipt
        class FakeSentinel:
            def __init__(self,parent,notify):
                self.notify=notify;self.data={'gaps_over_100ms':[],'errors':[],'running':False,'cycles':1}
            def snapshot(self):return json.loads(json.dumps(self.data))
            def start(self):self.data['running']=True
            def close(self):self.data['running']=False
        with tempfile.TemporaryDirectory(dir=ROOT/'.audit-tmp') as directory:
            path=Path(directory)/'receipt.json';report={'samples':[],'phase_observations':[]}
            receipt=MeasurementReceipt(path,report,sentinel_factory=FakeSentinel)
            receipt.append('samples',{'sample':1,'pass':False})
            receipt.sentinel.data['gaps_over_100ms'].append({'seconds':.6,'start_monotonic_ns':1,'end_monotonic_ns':600000001})
            receipt.sentinel.notify()
            events=[json.loads(line) for line in receipt.journal.read_text(encoding='utf-8').splitlines()]
            self.assertEqual([event['type'] for event in events],['samples','gaps_over_100ms'])
            self.assertEqual(json.loads(path.read_text(encoding='utf-8'))['journal_counts']['samples'],1)
            receipt.close();final=json.loads(path.read_text(encoding='utf-8'))
            self.assertEqual(final['samples'],[{'sample':1,'pass':False}]);self.assertFalse(final['machine_sentinel']['running'])
            self.assertEqual(len(final['machine_sentinel']['gaps_over_100ms']),1)

    def test_profile_spans_are_inclusive_nested_and_main_thread_A_only(self):
        import threading
        from artifact_measurement_support import PhaseAttribution
        phase=['A'];profile=PhaseAttribution(phase)
        inner=profile.wrap('inner',lambda:7);outer=profile.wrap('outer',inner)
        with patch('artifact_measurement_support.time.perf_counter_ns',side_effect=[10,20,30,40]):
            self.assertEqual(outer(),7)
        self.assertEqual([(row['name'],row['depth']) for row in profile.rows],[('inner',1),('outer',0)])
        self.assertEqual([row['seconds'] for row in profile.rows],[1e-8,3e-8])
        phase[0]='B';outer();phase[0]='A'
        thread=threading.Thread(target=outer);thread.start();thread.join()
        self.assertEqual(len(profile.rows),2)

    def test_incidental_engine_lock_hold_is_observed_without_a_boundary(self):
        import threading
        from artifact_measurement_support import ObservedRLock
        original=threading.RLock();rows=[];observed=ObservedRLock(original,rows.append)
        with observed:
            self.assertTrue(observed._is_owned())
            with observed:pass
        self.assertFalse(original._is_owned());self.assertEqual(len(rows),1)
        try:
            with observed:raise ValueError('synthetic body failure')
        except ValueError:pass
        self.assertEqual(len(rows),2);self.assertFalse(original._is_owned())

    def test_real_mutating_peer_builders_use_independent_requests(self):
        # Functional fixture check only, no clocks, maximum fixture or gate samples.
        from tests.test_artifact_admission import ArtifactAdmissionTests
        for ordinal,expected in enumerate(('cancel','stop','independent_request')):
            with self.subTest(peer=expected):
                fixture=ArtifactAdmissionTests();fixture.setUp()
                try:
                    fixture.setup_authority()
                    kind,mutate=a.prepare_measurement_peer(fixture,fixture.instance,ordinal)
                    result=mutate()
                    self.assertEqual(kind,expected)
                    self.assertEqual(result['request_state'],'active' if ordinal==2 else 'cancelled')
                finally:fixture.doCleanups()

    def test_current_cli_rejects_unsentinelled_historical_measurement_modes(self):
        for module,arguments in ((a,['authority']), (m,['facade','--design-checkpoint'])):
            with self.subTest(arguments=arguments),patch.object(sys,'argv',arguments),contextlib.redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit) as caught:module.main()
                self.assertEqual(caught.exception.code,2)

    def test_actual_attribution_hooks_with_synthetic_clock_and_small_fixture(self):
        # This exercises hook signatures and unchanged product bytes, not timing.
        import itertools
        from tests.test_artifact_admission import ArtifactAdmissionTests
        case=ArtifactAdmissionTests();case.setUp()
        try:
            case.setup_authority();audit=case.prepare();consumer=case.claim(audit)
            first=case.sealed_fixture_record(audit,consumer,'# First')
            private=case.briefs.get_private(audit['brief_id'])
            box=a.ArtifactOutbox(case.root/'api_seat_runtime'/audit['producer']['launch_attempt'])
            box.save(first['payload'],private['_artifact_seal']['seal_secret'])
            second=case.sealed_fixture_record(audit,consumer,'# Different')
            ticks=itertools.count(1000000,1000)
            with patch('time.perf_counter_ns',side_effect=lambda:next(ticks)):
                row,value=a.production_observe(case,lambda:case.authority.admit_saved(second,case.instance),attribution=True)
            self.assertEqual(value['status'],'quarantined');self.assertIsNone(row['exception_type'])
            names={span['name'] for span in row['attribution_spans']}
            self.assertTrue({'validate_payload','context','producer','seal_verify','packet',
                'activation','authoring_persist','index_validation','json_encode','stream_write',
                'fsync','replace','outbox_find','capture'}<=names,names)
            self.assertTrue(any(hold['phase']=='C' for hold in row['holds']))
        finally:case.doCleanups()

    def test_real_sentinel_thread_uses_real_fsync_replace_outside_fixture(self):
        # A tiny IO lifecycle control, not a latency sample or gate.
        import tempfile,threading,os
        from artifact_measurement_support import MachineSentinel
        with tempfile.TemporaryDirectory(dir=ROOT/'.audit-tmp') as directory:
            sentinel=MachineSentinel(directory);completed=threading.Event();threads=[]
            original_cycle=sentinel.cycle;real_fsync=sentinel.fsync
            def sync(descriptor):threads.append(threading.get_ident());return real_fsync(descriptor)
            sentinel.fsync=sync
            def cycle():
                result=original_cycle();completed.set();return result
            sentinel.cycle=cycle;sentinel.start()
            try:
                self.assertTrue(completed.wait(2))
                self.assertEqual((sentinel.scratch/'pulse.json').read_bytes(),b'{"sentinel":1}\n')
            finally:sentinel.close()
            self.assertTrue(threads);self.assertTrue(all(t!=threading.get_ident() for t in threads))
            state=sentinel.snapshot();self.assertEqual(state['errors'],[]);self.assertGreaterEqual(state['cycles'],1)
            self.assertFalse(sentinel.scratch.exists())


if __name__ == '__main__':
    unittest.main()
