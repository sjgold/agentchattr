"""Harness-only clocks, machine-stall sentinel, receipt and lock observations."""
from contextlib import contextmanager
from collections import deque
import json
import os
from pathlib import Path
import threading
import time
import uuid


def interval(start_ns, end_ns):
    return {'start_monotonic_ns': start_ns, 'end_monotonic_ns': end_ns,
            'seconds': (end_ns-start_ns)/1e9}


def overlaps(left, right):
    return left['start_monotonic_ns'] < right['end_monotonic_ns'] and right['start_monotonic_ns'] < left['end_monotonic_ns']


class MachineSentinel:
    """Independent real-IO thread. Callbacks run without the sentinel state lock."""
    def __init__(self, scratch_parent, notify=lambda:None, *, clock=time.perf_counter_ns,
                 sleep=time.sleep, wall=time.time_ns, cycle=None):
        self.scratch=Path(scratch_parent)/('stall-sentinel-'+uuid.uuid4().hex)
        self.scratch.mkdir(parents=True)
        self.notify=notify;self.clock=clock;self.sleep=sleep;self.wall=wall
        self.stop=threading.Event();self.started=threading.Event();self.lock=threading.Lock()
        self.thread=threading.Thread(target=self._run,name='D4-machine-stall-sentinel')
        self.state={'kind':'independent sleep5ms + tiny real fsync/replace sentinel',
            'scratch':str(self.scratch),'cycles':0,'gaps_over_100ms':[], 'errors':[],
            'max_gap_seconds':0,'running':False,'thread_id':None,'sleep_seconds':.005,
            'gap_record_threshold_seconds':.100,'machine_attribution_threshold_seconds':.500}
        # Capture primitives before any measured-thread wrappers are installed.
        self.open=Path.open;self.replace=Path.replace;self.fsync=os.fsync
        self.cycle=cycle or self._io_cycle
    def snapshot(self):
        with self.lock:return json.loads(json.dumps(self.state))
    def _io_cycle(self):
        stages={}
        start=self.clock();self.sleep(.005);now=self.clock();stages['sleep_seconds']=(now-start)/1e9
        target=self.scratch/'pulse.json';temporary=self.scratch/'pulse.tmp'
        start=now
        with self.open(temporary,'wb') as stream:
            stream.write(b'{"sentinel":1}\n');stream.flush()
            sync=self.clock();self.fsync(stream.fileno());stages['fsync_seconds']=(self.clock()-sync)/1e9
        stages['write_flush_close_seconds']=(self.clock()-start)/1e9-stages['fsync_seconds']
        start=self.clock();self.replace(temporary,target);stages['replace_seconds']=(self.clock()-start)/1e9
        return stages
    def observe_cycle(self,start,end,wall_start,wall_end,stages):
        row={**interval(start,end),'start_utc_ns':wall_start,'end_utc_ns':wall_end,**stages}
        with self.lock:
            self.state['cycles']+=1;self.state['last_cycle_end_monotonic_ns']=end
            self.state['max_gap_seconds']=max(self.state['max_gap_seconds'],row['seconds'])
            if row['seconds']>.100:self.state['gaps_over_100ms'].append(row)
        if row['seconds']>.100:self.notify()
    def _run(self):
        with self.lock:self.state.update(running=True,thread_id=threading.get_ident(),started_monotonic_ns=self.clock())
        self.started.set()
        previous=self.clock();previous_wall=self.wall()
        while not self.stop.is_set():
            start=previous;wall_start=previous_wall;work_start=self.clock()
            try:stages=self.cycle()
            except Exception as error:
                with self.lock:self.state['errors'].append({'type':type(error).__name__,'message':str(error),'monotonic_ns':self.clock()})
                self.notify();break
            end=self.clock();wall_end=self.wall()
            stages['between_cycle_seconds']=(work_start-start)/1e9
            previous=end;previous_wall=wall_end
            self.observe_cycle(start,end,wall_start,wall_end,stages)
        with self.lock:self.state.update(running=False,ended_monotonic_ns=self.clock())
        self.notify()
    def start(self):
        self.thread.start()
        if not self.started.wait(5):raise RuntimeError('Machine sentinel did not start')
        return self
    def observe_through(self,end_ns,timeout=30):
        """Outside measured code only; include a possibly still-running stall cycle."""
        deadline=time.monotonic()+timeout
        while time.monotonic()<deadline:
            state=self.snapshot()
            if state.get('last_cycle_end_monotonic_ns',0)>=end_ns:return True
            if state['errors'] or not state['running']:return False
            time.sleep(.001)
        return False
    def close(self):
        self.stop.set();self.thread.join(timeout=30)
        if self.thread.is_alive():raise RuntimeError('Machine sentinel did not finish; measurement invalid')
        # Only our two private scratch files are removed; the recorded path is retained.
        (self.scratch/'pulse.tmp').unlink(missing_ok=True)
        (self.scratch/'pulse.json').unlink(missing_ok=True)
        self.scratch.rmdir()


class IntervalAggregate:
    """Bounded fast-path detail; every >100ms row and every mutation survives."""
    def __init__(self,edge=3):
        self.edge=edge;self.count=0;self.maximum=None;self.first=[];self.last=deque(maxlen=edge);self.slow=[]
    def append(self,row):
        row={**row,'sequence':self.count};self.count+=1
        if len(self.first)<self.edge:self.first.append(row)
        self.last.append(row)
        if self.maximum is None or row['seconds']>self.maximum['seconds']:self.maximum=row
        if row['seconds']>.100 or row.get('mutation'):self.slow.append(row)
    def details(self):
        values=self.first+list(self.last)+self.slow+([self.maximum] if self.maximum else [])
        return sorted({row['sequence']:row for row in values}.values(),key=lambda row:row['sequence'])
    def summary(self):
        return {'count':self.count,'max_seconds':self.maximum['seconds'] if self.maximum else None,
            'retained_detail_count':len(self.details()),'edge_count':self.edge,
            'policy':'first/last3, maximum, every >100ms and every mutation; no comparator exceedance omitted'}


class MeasurementReceipt:
    """Incremental journal plus progress header; final JSON embeds every row.

    Avoid repeatedly serializing a growing multi-MiB history while timing. The
    journal is part of the receipt, not a replacement or discarded sample set.
    """
    def __init__(self,path,report,*,sentinel_factory=MachineSentinel):
        self.path=Path(path);self.path.parent.mkdir(parents=True,exist_ok=True)
        self.journal=self.path.with_suffix('.events.jsonl');self.report=report
        self.lock=threading.RLock();self.sentinel=None;self.closed=False
        self.native_open=Path.open;self.native_replace=Path.replace;self.native_fsync=os.fsync
        self.written={'samples':0,'phase_observations':0,'gaps_over_100ms':0,'errors':0}
        self.sentinel=sentinel_factory(self.path.parent,self.save)
        self.save();self.sentinel.start();self.save()
    def save(self):
        with self.lock:
            snapshot=self.sentinel.snapshot() if self.sentinel is not None else {}
            self.report['machine_sentinel']=snapshot
            with self.journal.open('a',encoding='utf-8') as stream:
                for key,values in [('samples',self.report.get('samples',[])),
                    ('phase_observations',self.report.get('phase_observations',[])),
                    ('gaps_over_100ms',snapshot.get('gaps_over_100ms',[])),('errors',snapshot.get('errors',[]))]:
                    for value in values[self.written[key]:]:stream.write(json.dumps({'type':key,'value':value})+'\n')
                    self.written[key]=len(values)
                stream.flush()
            self.report['incremental_journal']=str(self.journal)
            if self.closed:payload=self.report
            else:
                payload={key:value for key,value in self.report.items() if key not in ('samples','phase_observations')}
                payload['samples']=[];payload['phase_observations']=[]
                payload['receipt_in_progress']=True;payload['journal_counts']=dict(self.written)
                payload['machine_sentinel']={key:value for key,value in snapshot.items() if key not in ('gaps_over_100ms','errors')}
            temporary=self.path.with_suffix('.progress.tmp')
            with self.native_open(temporary,'w',encoding='utf-8') as stream:
                stream.write(json.dumps(payload,indent=2));stream.flush()
            self.native_replace(temporary,self.path)
    def append(self,key,row):
        with self.lock:self.report.setdefault(key,[]).append(row);self.save()
    def close(self):
        if self.closed:return
        try:self.sentinel.close()
        finally:
            with self.native_open(self.journal,'ab') as stream:stream.flush();self.native_fsync(stream.fileno())
            self.closed=True;self.save()


def classify_misses(rows, sentinel):
    """Annotate every failed interval. This never changes pass or schedules repeats."""
    stalls=[gap for gap in sentinel['gaps_over_100ms'] if gap['seconds']>.500]
    for row in rows:
        misses=[]
        for observation in row.get('gate_intervals',[]):
            if observation['seconds']<=observation['limit_seconds']:continue
            matching=[gap for gap in stalls if overlaps(observation,gap)]
            misses.append({'interval':observation,'classification':'machine-attributed' if matching else 'unattributed-real-miss',
                'overlapping_sentinel_stalls':[{**gap,
                    'overlap_nanoseconds':min(observation['end_monotonic_ns'],gap['end_monotonic_ns'])-max(observation['start_monotonic_ns'],gap['start_monotonic_ns']),
                    'miss_start_offset_within_stall_ns':observation['start_monotonic_ns']-gap['start_monotonic_ns'],
                    'miss_end_offset_within_stall_ns':observation['end_monotonic_ns']-gap['start_monotonic_ns']} for gap in matching]})
        row['miss_classifications']=misses
        row['repeat_eligible_under_policy']=bool(misses) and all(m['classification']=='machine-attributed' for m in misses)
        # Error or ownership/retry failure cannot become eligible through an unrelated stall.
        retries=row.get('replace_retries',0)
        retry_count=sum(retries.values()) if isinstance(retries,dict) else retries
        ownership=any(any(value) for value in row.get('B_authority_owned',[]))
        if row.get('error') or row.get('exception_unexpected') or row.get('peer_errors') or row.get('instrument_errors') or row.get('functional_failure') or retry_count or ownership:
            row['repeat_eligible_under_policy']=False
    return sorted({row.get('caller',row.get('phase')) for row in rows if row.get('repeat_eligible_under_policy')})


def instrument_valid(state):
    return not state.get('errors') and state.get('cycles',0)>0 and state.get('running') is False


def row_class(row):
    if row.get('caller')=='facade_reads':return row.get('phase','setup_error')
    return row.get('caller',row.get('phase'))


def verify_machine_repeats(original,repeats):
    """Return paired evidence; never mutate either run or claim D4 acceptance."""
    originals=original['samples'];pairs=[]
    for name in sorted({row_class(row) for row in originals if not row.get('pass',False)}):
        failed=[row for row in originals if row_class(row)==name and not row.get('pass',False)]
        repeat=repeats.get(name);reasons=[]
        if not failed or not all(row.get('repeat_eligible_under_policy') for row in failed):reasons.append('Original class has an ineligible miss')
        if not instrument_valid(original.get('machine_sentinel',{})):reasons.append('Original instrument invalid')
        if repeat is None:reasons.append('Complete class repeat absent');rows=[]
        else:
            rows=repeat['samples']
            for key in ('product_pin','source_sha256','tool_sha256','fixture_and_support_sha256'):
                if not original.get(key) or original.get(key)!=repeat.get(key):reasons.append('Different provenance: '+key)
            if not instrument_valid(repeat.get('machine_sentinel',{})):reasons.append('Repeat instrument invalid')
            if len(rows)<10 or any(row_class(row)!=name for row in rows):reasons.append('Not a complete10+ sample class repeat')
            identities=[row.get('fixture_identity') for row in rows]
            if not all(identities) or len(set(identities))!=len(rows):reasons.append('Fresh unique fixtures not evidenced')
            if any(not row.get('pass',False) or any(span['seconds']>span['limit_seconds'] for span in row.get('gate_intervals',[])) for row in rows):reasons.append('Repeat has misses or failures')
            old_end=max((row.get('whole_call',{}).get('end_monotonic_ns',0) for row in originals),default=0)
            if not old_end or any(row.get('whole_call',{}).get('start_monotonic_ns',0)<=old_end for row in rows):reasons.append('Repeat is not temporally fresh')
            stalls=[gap for gap in repeat.get('machine_sentinel',{}).get('gaps_over_100ms',[]) if gap['seconds']>.5]
            if any(overlaps(row.get('whole_call',{}),gap) for row in rows if row.get('whole_call') for gap in stalls):reasons.append('Repeat overlaps sentinel stall>0.5s')
        pairs.append({'class':name,'original_samples':len([row for row in originals if row_class(row)==name]),
            'original_misses':len(failed),'original_pass_fields_unchanged':[row.get('pass') for row in failed],
            'repeat_samples':len(rows),
            'original_max_interval_seconds':max((span['seconds'] for row in originals if row_class(row)==name for span in row.get('gate_intervals',[])),default=None),
            'repeat_max_interval_seconds':max((span['seconds'] for row in rows for span in row.get('gate_intervals',[])),default=None),
            'policy_satisfied':not reasons,'refusals':reasons})
    return {'pairs':pairs,'machine_attributed_repeat_policy_satisfied':bool(pairs) and all(p['policy_satisfied'] for p in pairs),
            'acceptance_claim':False}


def last_attempt_stop_reason(row,sentinel):
    if row.get('pass',False):return None
    classify_misses([row],sentinel)
    retries=row.get('replace_retries',0)
    retries=sum(retries.values()) if isinstance(retries,dict) else retries
    if row.get('error') or row.get('instrument_errors') or row.get('functional_failure') or row.get('peer_errors') or row.get('exception_unexpected') or retries or any(any(x) for x in row.get('B_authority_owned',[])):
        return 'instrument-functional-or-fault failure; escalate, no new complete gate'
    if row['repeat_eligible_under_policy']:return None
    return 'unattributed-real-miss; last complete attempt escalated'


class ObservedRLock:
    """Forwarding harness proxy, measures every outermost acquired hold by thread."""
    def __init__(self, original, observe):
        self.original=original;self.observe=observe;self.local=threading.local()
    def acquire(self,*args,**kwargs):
        acquired=self.original.acquire(*args,**kwargs)
        if acquired:
            depth=getattr(self.local,'depth',0)
            if depth==0:self.local.start=time.perf_counter_ns()
            self.local.depth=depth+1
        return acquired
    def release(self):
        depth=self.local.depth
        row=interval(self.local.start,time.perf_counter_ns()) if depth==1 else None
        self.local.depth=depth-1;self.original.release()
        if row is not None:self.observe({**row,'thread_id':threading.get_ident()})
    def __enter__(self):self.acquire();return self
    def __exit__(self,*args):self.release()
    def _is_owned(self):return self.original._is_owned()


class PhaseAttribution:
    """Inclusive timed spans, measured thread only. Nested spans are not additive."""
    def __init__(self,phase):
        self.phase=phase;self.thread=threading.get_ident();self.rows=[];self.depth=0
    def wrap(self,label,method):
        def wrapped(*args,**kwargs):
            if threading.get_ident()!=self.thread or self.phase[0]!='A':return method(*args,**kwargs)
            start=time.perf_counter_ns();depth=self.depth;self.depth+=1
            try:return method(*args,**kwargs)
            finally:
                self.rows.append({'name':label,'depth':depth,**interval(start,time.perf_counter_ns())});self.depth-=1
        return wrapped


class ProfiledStream:
    def __init__(self,stream,profile):self.stream=stream;self.profile=profile
    def __getattr__(self,name):return getattr(self.stream,name)
    def __enter__(self):self.stream.__enter__();return self
    def __exit__(self,*args):return self.stream.__exit__(*args)
    def write(self,value):return self.profile.wrap('stream_write',self.stream.write)(value)
