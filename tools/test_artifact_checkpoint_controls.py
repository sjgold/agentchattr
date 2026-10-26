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
            a.main()
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
        observed=[]
        def writer(intent):
            observed.append(tuple(owner._lock._is_owned() for owner in (case.engine,case.catalog,case.artifacts)))
            return b'{}'
        case.authority=SimpleNamespace(_persist_diagnostic_intent=writer,_settle_diagnostic_intent=lambda *args:'settled')
        def action():
            with service._boundary():pass
            receipt=case.authority._persist_diagnostic_intent('synthetic')
            with service._boundary():return case.authority._settle_diagnostic_intent(receipt)
        row,value=a.production_observe(case,action)
        self.assertEqual(value,'settled');self.assertEqual(observed,[(False,False,False)])
        self.assertEqual([hold['phase'] for hold in row['holds']],['A','C'])
        self.assertEqual(len(row['B_seconds']),1);self.assertTrue(row['peer_waits'])
        self.assertEqual(row['peer_errors'],[])
        def healthy():
            with service._boundary():return 'healthy'
        row,value=a.production_observe(case,healthy,healthy=True)
        self.assertEqual(value,'healthy');self.assertEqual(row['B_seconds'],[])
        self.assertEqual([hold['phase'] for hold in row['holds']],['A'])
        row,value=a.production_observe(case,lambda:'read',persist=False)
        self.assertEqual(value,'read');self.assertEqual(row['holds'],[])
        self.assertEqual(row['B_authority_owned'],[[False,False,False]])


if __name__ == '__main__':
    unittest.main()
