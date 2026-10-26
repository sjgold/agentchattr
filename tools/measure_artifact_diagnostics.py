"""R2 reachable heavy/summary MEASUREMENT, separate from unit reds.

Run --check-plan before implementation for arithmetic only. Actual measurements
require the reviewed R2 diagnostic owner, real fsync and >=10 fresh samples.
This harness does not implement R2 and is not a unit test or a passing gate.
--full-gate includes structural reads and guarded4MiB imports with diagnostics
full/held. Heavy-path clearance also requires20percent margin (max<=0.216s).
"""
from argparse import ArgumentParser
from contextlib import ExitStack
import hashlib
import json
from pathlib import Path
import sys
import threading
import time
from unittest.mock import patch
import uuid

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import artifact_store as storage
from tests.test_artifact_store import ArtifactStoreTests

STAMP = 1.2345678901234567e-100


def body(ordinal, size):
    prefix = f'row{ordinal:04d}\n'.encode('ascii')
    assert len(prefix) == 8 and size >= 8
    return prefix + b'x' * (size - len(prefix))


def setup(case):
    _, store = case.owner('measurement')
    diagnostics = store.diagnostic_store
    audits = [case.queued(storage, store, request_id=f'{index + 1:032x}') for index in range(128)]
    ledger = {'version': 1, 'diagnostics': {}, 'dispatch_overflow': {}, 'store_overflow': None}
    for ordinal in range(1023):
        audit = audits[ordinal // 8]
        raw = body(ordinal, 15360 if ordinal == 1022 else 7680)
        key = {'request_id': audit['request_id'], 'attempt_id': audit['attempt_id'],
               'dispatch_id': audit['dispatch_id'], 'reason': 'invalid_response',
               'sha256': hashlib.sha256(raw).hexdigest(), 'byte_count': len(raw),
               'actor_identity_id': 'a' * 32}
        canonical = json.dumps(key, sort_keys=True, ensure_ascii=False,
                               separators=(',', ':'), allow_nan=False)
        identifier = uuid.uuid5(uuid.NAMESPACE_URL, canonical).hex
        assert identifier == store._diagnostic_id(key)
        diagnostics._put_bytes(diagnostics._object_path('quarantine', identifier), raw)
        ledger['diagnostics'][identifier] = {'id': identifier, 'kind': 'quarantine', **key,
            'received_at': STAMP, 'updated_at': STAMP, 'not_retained': False,
            'body_object_id': identifier, 'attached_request_id': audit['request_id']}
    # Fixture seed, not a claimed naturally reached transaction history. All128
    # groups do have actual reserved requests and all bodies match their hashes.
    diagnostics._persist_diagnostics(ledger)
    files, byte_count = diagnostics._body_inventory()
    assert len(files) == 1023 and byte_count == 7864320
    return store, audits[-1]


def record(store, audit, text):
    return store.quarantine_submission(audit['request_id'], audit['attempt_id'], audit['dispatch_id'],
        reason='invalid_response', content=text, actor_identity_id='a' * 32, now=STAMP)


def measure(case, store, audit, phase):
    entered = threading.Event()
    waits = []
    failures = []
    retries = [0]
    def peer():
        entered.wait()
        started = time.perf_counter()
        try:
            case.service.require_active('review')
        except Exception as exc:
            failures.append(type(exc).__name__)
        waits.append(time.perf_counter() - started)
    original = Path.replace
    def counted_replace(source, target):
        try:
            return original(source, target)
        except PermissionError:
            if Path(target) == store.diagnostic_store.path:
                retries[0] += 1
            raise
    thread = threading.Thread(target=peer, daemon=True)
    thread.start()
    exception = None
    result = None
    with patch.object(Path, 'replace', counted_replace):
        with case.service._boundary():
            started = time.perf_counter()
            entered.set()
            try:
                text = body(1023, 524288).decode('ascii') if phase == 'heavy' else 'distinct summary key two'
                result = record(store, audit, text)
            except Exception as exc:
                exception = type(exc).__name__
            hold = time.perf_counter() - started
    thread.join(timeout=30)
    if thread.is_alive():
        raise RuntimeError('Measurement peer did not complete')
    files, size = store.diagnostic_store._body_inventory()
    if exception is None:
        assert len(files) == 1024 and size == 8388608
        assert result['kind'] == ('quarantine' if phase == 'heavy' else 'dispatch_overflow')
        if phase == 'summary':
            assert result['counter'] == 2
    return {'phase': phase, 'hold': hold, 'peer_wait': waits[0], 'replace_retries': retries[0],
            'exception_type': exception, 'peer_errors': failures, 'body_objects': len(files),
            'body_bytes': size, 'metadata_bytes': store.diagnostic_store.path.stat().st_size,
            'normal_pass': exception is None and not failures and retries[0] == 0
                           and hold <= .270 and waits[0] <= .270}


def measure_action(case, owner, action, phase, limit):
    """Same real outer boundary and peer; no serializer/clock/fsync mocks."""
    entered=threading.Event();waits=[];errors=[];retries=[0]
    def peer():
        entered.wait();started=time.perf_counter()
        try:case.service.require_active('peer')
        except Exception as error:errors.append(type(error).__name__)
        waits.append(time.perf_counter()-started)
    original=Path.replace
    def replace(source,target):
        try:return original(source,target)
        except PermissionError:
            if Path(target)==owner.path:retries[0]+=1
            raise
    thread=threading.Thread(target=peer,daemon=True);thread.start()
    failure=None;result=None
    with patch.object(Path,'replace',replace):
        with case.service._boundary():
            started=time.perf_counter();entered.set()
            try:result=action()
            except Exception as error:failure=type(error).__name__
            hold=time.perf_counter()-started
    thread.join(timeout=30)
    if thread.is_alive():raise RuntimeError('Gate peer did not finish')
    return {'phase':phase,'hold':hold,'peer_wait':waits[0],'replace_retries':retries[0],
            'exception_type':failure,'peer_errors':errors,'limit_seconds':limit,
            'normal_pass':failure is None and not errors and retries[0]==0 and hold<=limit and waits[0]<=limit},result


def structural_read(case,store):
    from tests.test_artifact_diagnostic_owner import ArtifactDiagnosticOwnerTests
    ledger=ArtifactDiagnosticOwnerTests.maximum_ledger()
    raw=json.dumps(ledger,ensure_ascii=True,allow_nan=False).encode('utf-8')
    assert len(raw)==810186
    owner=store.diagnostic_store;owner._persist_diagnostics(ledger)
    # Real equivalent rewrite outside the hold forces bounded strict reread,
    # rather than benchmarking a warmed fingerprint-cache hit.
    previous=owner._stamp
    storage.atomic_json(owner.path,ledger)
    if owner._fingerprint()==previous:
        info=owner.path.stat();storage.os.utime(owner.path,ns=(info.st_atime_ns,info.st_mtime_ns+1000000))
    assert owner._fingerprint()!=previous
    row,report=measure_action(case,owner,lambda:store.diagnostics(limit=100),'structural_read',.270)
    if row['exception_type'] is None:
        assert report['detailed_count']==1024 and report['dispatch_group_count']==256
        assert report['owners']['authoring']['available'] and report['owners']['diagnostics']['available']
        assert report['retained_body_bytes']==8388608 and len(report['rows'])==100
    row.update(metadata_bytes=810186,body_objects=1024,body_bytes=8388608,
        shape='Structural max metadata; physical quota full, historical body hashes are not matched by this max-width graph.',
        includes_parse=True,includes_full_validation=True)
    return row


def full_standalone_diagnostics(store):
    """Full reachable detail/body quotas without adding authoring requests."""
    owner=store.diagnostic_store
    ledger={'version':1,'diagnostics':{},'dispatch_overflow':{},'store_overflow':None}
    for ordinal in range(1024):
        raw=body(ordinal,8192)
        key={'request_id':None,'attempt_id':f'{ordinal+1:032x}','dispatch_id':f'{ordinal//8+1:032x}',
            'reason':'invalid_response','sha256':hashlib.sha256(raw).hexdigest(),'byte_count':len(raw),
            'actor_identity_id':'a'*32}
        encoded=json.dumps(key,sort_keys=True,ensure_ascii=False,separators=(',',':'),allow_nan=False)
        identifier=uuid.uuid5(uuid.NAMESPACE_URL,encoded).hex
        assert identifier==store._diagnostic_id(key)
        owner._put_bytes(owner._object_path('quarantine',identifier),raw)
        ledger['diagnostics'][identifier]={'id':identifier,'kind':'quarantine',**key,'received_at':STAMP,
            'updated_at':STAMP,'not_retained':False,'body_object_id':identifier,'attached_request_id':None}
    owner._persist_diagnostics(ledger)
    assert owner._body_inventory()[1]==8388608


def import_gates(number,existing,large,mode):
    case=ArtifactStoreTests();case.setUp();fixture_root=case.root
    try:
        _,store=case.owner('import-'+mode)
        for portable,objects in existing:
            plan=store.prepare_import_lineage(portable,objects)
            with case.service._boundary():store.import_lineage(plan,channel='review')
        assert len(store.export_lineage_ids())==100
        assert sum(len(store.export_metadata(key)['versions']) for key in store.export_lineage_ids())==100
        full_standalone_diagnostics(store)
        if mode=='held':
            store.diagnostic_store.path.write_bytes(b'HELD_DIAGNOSTIC_METADATA')
            try:store.diagnostic_store._check_diagnostics()
            except storage.ArtifactDiagnosticsUnavailable:pass
            else:raise AssertionError('Held diagnostic fixture was not held')
        prepared=store.prepare_import_lineage(*large)
        original_open=Path.open
        def opened(path,*args,**kwargs):
            if path==store.diagnostic_store.path:raise AssertionError('Authoring opened diagnostic metadata')
            return original_open(path,*args,**kwargs)
        with ExitStack() as stack:
            stack.enter_context(patch.object(Path,'open',opened))
            for name in ('_load_diagnostics','_check_diagnostics','_validate_diagnostics','request_diagnostics',
                         'report','record','_persist_diagnostics'):
                stack.enter_context(patch.object(storage.ArtifactDiagnosticStore,name,
                    side_effect=AssertionError('Authoring called diagnostic '+name)))
            row,result=measure_action(case,store,lambda:store.import_lineage(prepared,channel='review'),
                                      'import_'+mode,.300)
        if row['exception_type'] is None:
            assert result['created_requests']==128 and result['created_versions']==128
        row.update(sample=number,portable_envelope_bytes=4194304,existing_lineages=100,existing_versions=100,
            requests=128,versions=128,diagnostic_mode=mode,diagnostic_objects=1024,diagnostic_body_bytes=8388608,
            diagnostic_read_guard=True,includes_parse=True,includes_full_validation=True)
        return row
    finally:
        case.doCleanups();assert not fixture_root.exists()


def main():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument('--check-plan', action='store_true')
    parser.add_argument('--samples', type=int, default=10)
    parser.add_argument('--full-gate', action='store_true')
    args = parser.parse_args()
    assert 127 * 8 + 7 == 1023
    assert 1022 * 7680 + 15360 + 524288 == 8388608
    assert len(json.dumps(STAMP)) == 23
    if args.check_plan:
        print('Plan arithmetic only:128 groups,1023+1 bodies,8388608 bytes,23-char timestamp. No timing run.')
        if args.full_gate:
            from tests.test_artifact_diagnostic_owner import ArtifactDiagnosticOwnerTests
            from tests.test_artifact_import_benchmark import graph
            from sealed_result_io import canonical_utf8
            ledger=ArtifactDiagnosticOwnerTests.maximum_ledger()
            storage.ArtifactDiagnosticStore.__new__(storage.ArtifactDiagnosticStore)._validate_diagnostics(ledger)
            assert len(json.dumps(ledger).encode('utf-8'))==810186
            large,_=graph(128,exact_bytes=4194304)
            assert len(canonical_utf8({'version':1,'lineages':[large]}))==4194304
            storage.ArtifactStore.__new__(storage.ArtifactStore)._import_metadata(large)
            print('Pure structural-ledger/import-plan validation passed; no measured holds or file writes.')
        return 0
    if args.samples < 10:
        parser.error('At least10 independent samples per phase are required')
    if not hasattr(storage, 'ArtifactDiagnosticStore'):
        parser.error('R2 owner is not implemented; measurement unavailable, not a red test')
    samples = []
    for index in range(args.samples):
        case = ArtifactStoreTests()
        case.setUp()
        fixture_root = case.root
        try:
            store, audit = setup(case)
            heavy = measure(case, store, audit, 'heavy')
            heavy['sample'] = index + 1
            heavy['margin_pass'] = max(heavy['hold'],heavy['peer_wait']) <= .216
            samples.append(heavy)
            print(json.dumps(heavy), flush=True)
            if heavy['exception_type'] is None:
                first = record(store, audit, 'distinct summary key one')
                assert first['counter'] == 1
                summary = measure(case, store, audit, 'summary')
                summary['sample'] = index + 1
                samples.append(summary)
                print(json.dumps(summary), flush=True)
            if args.full_gate and heavy['exception_type'] is None:
                structural=structural_read(case,store);structural['sample']=index+1
                samples.append(structural);print(json.dumps(structural),flush=True)
        finally:
            case.doCleanups()
            assert not fixture_root.exists()
    if args.full_gate:
        from tests.test_artifact_import_benchmark import graph
        from sealed_result_io import canonical_utf8
        existing=[graph(1) for _ in range(100)];large=graph(128,exact_bytes=4194304)
        assert len(canonical_utf8({'version':1,'lineages':[large[0]]}))==4194304
        for mode in ('full','held'):
            for number in range(1,args.samples+1):
                row=import_gates(number,existing,large,mode);samples.append(row);print(json.dumps(row),flush=True)
    complete=len(samples)==(5 if args.full_gate else 2)*args.samples
    hard_pass=complete and all(row['normal_pass'] for row in samples)
    margin_pass=all(row['margin_pass'] for row in samples if row['phase']=='heavy')
    report = {'kind': 'R2 production full gate' if args.full_gate else 'R2 reachable heavy/summary measurement',
              'samples': samples, 'fsync_mocked': False, 'limit_seconds': .270,
              'full_gate':args.full_gate,'import_limit_seconds':.300,'heavy_clearance_limit_seconds':.216,
              'max_hold': max(row['hold'] for row in samples),
              'max_peer_wait': max(row['peer_wait'] for row in samples),
              'hard_pass':hard_pass,'heavy_margin_pass':margin_pass,'pass':hard_pass and margin_pass,
              'resampling': 'None automatic; retain counted-retry faults and every normal miss.'}
    report['margin'] = .270 - max(report['max_hold'], report['max_peer_wait'])
    path = ROOT / '.audit-tmp' / ('r2-diagnostic-measure-' + uuid.uuid4().hex + '.json')
    path.write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps({key: value for key, value in report.items() if key != 'samples'}), flush=True)
    return 0 if report['pass'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
