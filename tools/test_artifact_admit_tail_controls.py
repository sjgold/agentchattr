"""Synthetic controls for the two-arm DESIGN observer, not timing evidence."""
from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace
import sys
import threading
import unittest
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import profile_artifact_admit_tail as tail


class TailControls(unittest.TestCase):
    def test_minimal_observer_has_no_proxy_no_peer_no_component_spans(self):
        engine=threading.RLock();catalog=threading.RLock();authoring=threading.RLock()
        case=SimpleNamespace(engine=SimpleNamespace(_lock=engine),catalog=SimpleNamespace(_lock=catalog),artifacts=SimpleNamespace(_lock=authoring))
        @contextmanager
        def boundary():
            with engine,catalog:yield
        case.service=SimpleNamespace(_boundary=boundary)
        observed=[]
        def persist(intent):
            observed.append((engine._is_owned(),catalog._is_owned(),authoring._is_owned()))
            self.assertIs(case.engine._lock,engine);return 'receipt'
        case.authority=SimpleNamespace(_persist_diagnostic_intent=persist,_settle_diagnostic_intent=lambda *args:'result')
        def action():
            with case.service._boundary():pass
            receipt=case.authority._persist_diagnostic_intent('intent')
            with case.service._boundary():return case.authority._settle_diagnostic_intent(receipt)
        with patch('threading.Thread',side_effect=AssertionError('Minimal observer spawned peer')):
            row,value=tail.minimal_observe(case,action)
        self.assertEqual(value,'result');self.assertEqual(observed,[(False,False,False)])
        self.assertEqual([x['phase'] for x in row['holds']],['A','C'])
        self.assertEqual(row['attribution_inclusive_summary'],{});self.assertEqual(row['attribution_top_level_spans'],[])
        self.assertIs(case.engine._lock,engine)

    def test_setup_io_observer_threshold_and_thread_isolation(self):
        tracker=tail.SetupFsyncObserver();tracker.original=lambda descriptor:None
        with patch('time.perf_counter_ns',side_effect=[0,100000001]):tracker.sync(0)
        self.assertEqual(tracker.count,1);self.assertEqual(len(tracker.heavy),1)
        thread=threading.Thread(target=lambda:tracker.sync(0));thread.start();thread.join()
        self.assertEqual(tracker.count,1)
        self.assertEqual(tracker.result()['last']['seconds'],.100000001)

    def test_distribution_tail_selection_and_empty_heavy_group_disclosure(self):
        rows=[]
        for arm in ('sentinel_only','nested_design10'):
            for n,value in enumerate((.1,.15,.25),1):
                rows.append({'arm':arm,'sample':n,'A_seconds':value,'holds':[{'phase':'A','start_monotonic_ns':n*1000000000,'end_monotonic_ns':n*1000000000+int(value*1e9)}],
                    'attribution_inclusive_summary':{},'attribution_top_level_spans':[], 'setup_fsync':{},
                    'ordering':{'first_after_new_heavy_setup_fsync':False}})
        result=tail.study_summary(rows,{'gaps_over_100ms':[]})
        self.assertEqual(result['sentinel_only']['A']['median'],.15)
        self.assertEqual(len(result['nested_design10']['tail_samples']),3)
        self.assertIsNone(result['sentinel_only']['first_after_heavy_setup_fsync'])

    def test_both_arms_require_at_least30_samples(self):
        with patch.object(sys,'argv',['tail','--samples','1']):
            with self.assertRaises(SystemExit) as caught:tail.main()
            self.assertEqual(caught.exception.code,2)


if __name__=='__main__':unittest.main()
