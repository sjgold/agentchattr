# Historical216ms tail selection is descriptive only, not a release criterion (Seth2026-10-26).
"""DESIGN only: admit_saved30 sentinel-only then30 nested DESIGN10 samples."""
from argparse import ArgumentParser
from contextlib import contextmanager
import hashlib
import json
import math
import os
from pathlib import Path
import statistics
import subprocess
import sys
import threading
import time
from unittest.mock import patch
import uuid

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT / 'src'))
import profile_artifact_authority_phases as authority
import measure_artifact_diagnostics as diagnostics
from artifact_measurement_support import MeasurementReceipt,interval,overlaps,instrument_valid


def minimal_observe(case,action):
    """No peers, lock proxies, component spans or within-call receipt writes."""
    boundary=case.service._boundary;writer=case.authority._persist_diagnostic_intent
    settle=case.authority._settle_diagnostic_intent;depth=0;phase=['A'];holds=[];writes=[]
    @contextmanager
    def observed_boundary():
        nonlocal depth
        outer=depth==0;depth+=1
        try:
            with boundary():
                start=time.perf_counter_ns()
                try:yield
                finally:
                    if outer:holds.append({**interval(start,time.perf_counter_ns()),'phase':phase[0]})
        finally:depth-=1
    def persist(intent):
        phase[0]='B';start=time.perf_counter_ns()
        try:return writer(intent)
        finally:writes.append({**interval(start,time.perf_counter_ns()),'phase':'B'});phase[0]='between'
    def settled(*args,**kwargs):phase[0]='C';return settle(*args,**kwargs)
    failure=None;value=None;start=time.perf_counter_ns()
    with patch.object(case.service,'_boundary',observed_boundary),patch.object(case.authority,'_persist_diagnostic_intent',persist),patch.object(case.authority,'_settle_diagnostic_intent',settled):
        try:value=action()
        except Exception as error:failure=type(error).__name__
    return {'holds':holds,'B_intervals':writes,'whole_call':interval(start,time.perf_counter_ns()),
        'exception_type':failure,'attribution_inclusive_summary':{},'attribution_top_level_spans':[]},value


class SetupFsyncObserver:
    """Outside measured code only. Sentinel keeps its captured native primitive."""
    def __init__(self):
        self.original=os.fsync;self.thread=threading.get_ident();self.count=0;self.maximum=None;self.last=None;self.heavy=[]
    def sync(self,descriptor):
        if threading.get_ident()!=self.thread:return self.original(descriptor)
        start=time.perf_counter_ns()
        try:return self.original(descriptor)
        finally:
            row=interval(start,time.perf_counter_ns());self.count+=1;self.last=row
            if self.maximum is None or row['seconds']>self.maximum['seconds']:self.maximum=row
            if row['seconds']>.100:self.heavy.append(row)
    def result(self):return {'count':self.count,'max':self.maximum,'last':self.last,'heavy_over_100ms':self.heavy}


def distribution(values):
    values=sorted(values)
    if not values:return None
    return {'n':len(values),'median':statistics.median(values),'p90':values[math.ceil(.9*len(values))-1],
        'p95':values[math.ceil(.95*len(values))-1],'max':values[-1],'min':values[0]}


def study_summary(rows,sentinel):
    output={}
    for arm in ('sentinel_only','nested_design10'):
        selected=[row for row in rows if row.get('arm')==arm and 'A_seconds' in row]
        phase_names=sorted({key for row in selected for key in row['attribution_inclusive_summary']})
        components={name:distribution([row['attribution_inclusive_summary'].get(name,{}).get('inclusive_seconds',0) for row in selected]) for name in phase_names}
        ordered=sorted(selected,key=lambda row:row['A_seconds'],reverse=True)
        tails=[row for row in ordered if row['A_seconds']>.216 or row in ordered[:3]]
        details=[]
        for row in tails:
            A=next(hold for hold in row['holds'] if hold['phase']=='A')
            overlay=[gap for gap in sentinel['gaps_over_100ms'] if overlaps(A,gap)]
            deltas={name:row['attribution_inclusive_summary'].get(name,{}).get('inclusive_seconds',0)-components[name]['median'] for name in phase_names}
            details.append({'sample':row['sample'],'A_seconds':row['A_seconds'],'sentinel_overlay':overlay,
                'setup_fsync':row['setup_fsync'],'ordering':row['ordering'],
                'component_deltas_from_arm_median_inclusive_not_additive':deltas,
                'top_level_spans':row['attribution_top_level_spans']})
        output[arm]={'A':distribution([row['A_seconds'] for row in selected]),'components_inclusive_not_additive':components,
            'tail_definition':'every A>0.216 plus slowest3, no sample discarded','tail_samples':details,
            'first_after_heavy_setup_fsync':distribution([row['A_seconds'] for row in selected if row['ordering']['first_after_new_heavy_setup_fsync']]),
            'other_samples':distribution([row['A_seconds'] for row in selected if not row['ordering']['first_after_new_heavy_setup_fsync']])}
    return output


def main():
    parser=ArgumentParser(description=__doc__);parser.add_argument('--samples',type=int,default=30);args=parser.parse_args()
    if args.samples<30:parser.error('At least30 fresh samples in EACH arm required')
    product_hashes={name:hashlib.sha256((ROOT / 'src' / name if name.endswith('.py') and '/' not in name else ROOT / name).read_bytes()).hexdigest() for name in ('artifact_store.py','artifact_service.py','api_seats.py','mcp_bridge.py')}
    authority.verify_frozen_product(product_hashes)
    report={'kind':'DESIGN two-arm admit_saved tail attribution, NOT acceptance','samples':[],'phase_observations':[],
        'source_sha256':product_hashes,'product_pin':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        'samples_per_arm':args.samples,'fixed_order':['sentinel_only','nested_design10'],'warmup_discarded':0,'resampling':'none',
        'heavy_setup_fsync_threshold_seconds':.100,'acceptance_claim':False,
        'arm1':'sentinel plus minimal outermost A/C/B timers; no peer/proxy/component wrappers',
        'arm2':'nested DESIGN10 spans plus passive peer and lock proxy; no mutating peer',
        'cache_disclosure':'warm owner caches after identical fresh129-request/2MiB/1000-ref/512KiB setup',
        'span_aggregation':'all nested calls contribute to per-label count/total/max; all top-level intervals retained; nested sums are not additive'}
    report.update(authority.checkpoint_provenance(__file__))
    path=ROOT/'.audit-tmp'/('d4-admit-tail-two-arms-'+uuid.uuid4().hex+'.json')
    receipt=MeasurementReceipt(path,report);previous_B=None;seen_heavy=None;last_heavy=None;ordinal=0
    print(json.dumps({'receipt':str(path),'source_sha256':product_hashes,'tool_sha256':report['tool_sha256']}),flush=True)
    try:
        for arm in report['fixed_order']:
            for sample in range(1,args.samples+1):
                ordinal+=1;case=None;row=None
                try:
                    tracker=SetupFsyncObserver()
                    with patch.object(os,'fsync',tracker.sync):
                        case,audit,instance,record,box=authority.setup('admit_saved')
                        audits=[row['audit'] for row in case.artifacts._data['requests'].values() if row['state']=='imported'][:127]+[audit]
                        diagnostics.setup(case,store=case.artifacts,audits=audits)
                    setup_io=tracker.result()
                    if tracker.heavy:last_heavy=tracker.heavy[-1]
                    new_heavy=last_heavy is not None and last_heavy['end_monotonic_ns']!=seen_heavy
                    if last_heavy:seen_heavy=last_heavy['end_monotonic_ns']
                    action=lambda:case.authority.admit_saved(record,instance)
                    if arm=='sentinel_only':row,value=minimal_observe(case,action)
                    else:
                        row,value=authority.production_observe(case,action,attribution=True)
                        spans=row.pop('attribution_spans');row['attribution_top_level_spans']=[span for span in spans if span['depth']==0]
                    row={key:value for key,value in row.items() if key not in ('pass','hard_pass','margin_pass','gate_intervals')}
                    if row['exception_type'] is not None or not isinstance(value,dict) or value.get('status')!='quarantined':raise AssertionError('Study did not reach conflicting-saved diagnostic')
                    A=next(hold for hold in row['holds'] if hold['phase']=='A')
                    row.update(arm=arm,sample=sample,ordinal=ordinal,A_seconds=A['seconds'],setup_fsync=setup_io,
                        fixture_identity=case.root.name,authoring_requests=len(case.artifacts._data['requests']),
                        ordering={'first_after_fresh_setup':True,'first_after_new_heavy_setup_fsync':new_heavy,
                            'last_heavy_setup_fsync':last_heavy,'seconds_since_last_setup_fsync':(A['start_monotonic_ns']-tracker.last['end_monotonic_ns'])/1e9 if tracker.last else None,
                            'previous_measured_B':previous_B,'previous_B_is_not_a_native_fsync_observation':True})
                    if row['B_intervals']:previous_B=row['B_intervals'][-1]
                    receipt.append('samples',row)
                    print(json.dumps({'arm':arm,'sample':sample,'A_seconds':row['A_seconds'],'setup_fsync_max':tracker.maximum['seconds'],'first_after_heavy':new_heavy}),flush=True)
                except Exception as error:
                    receipt.append('samples',{**(row or {}),'arm':arm,'sample':sample,'ordinal':ordinal,'error':type(error).__name__,'message':str(error)})
                finally:
                    if case is not None:authority.cleanup_probe(case,case.root,arm,lambda failure:receipt.append('samples',{**failure,'arm':arm,'sample':sample}))
    finally:receipt.close()
    report['instrument_valid']=instrument_valid(report['machine_sentinel']);report['summary']=study_summary(report['samples'],report['machine_sentinel'])
    report['measurement_complete']=len(report['samples'])==args.samples*2 and not any('error' in row for row in report['samples'])
    receipt.save();print(json.dumps({'receipt':str(path),'complete':report['measurement_complete'],'instrument_valid':report['instrument_valid']}),flush=True)
    return 0 if report['measurement_complete'] and report['instrument_valid'] else 1


if __name__=='__main__':raise SystemExit(main())
