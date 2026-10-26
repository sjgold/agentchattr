"""R2 reachable heavy/summary MEASUREMENT, separate from unit reds.

Run --check-plan before implementation for arithmetic only. Actual measurements
require the reviewed R2 diagnostic owner, real fsync and >=10 fresh samples.
This harness does not implement R2 and is not a unit test or a passing gate.
The structural-profile and guarded 4MiB import gates remain separately required.
"""
from argparse import ArgumentParser
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


def main():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument('--check-plan', action='store_true')
    parser.add_argument('--samples', type=int, default=10)
    args = parser.parse_args()
    assert 127 * 8 + 7 == 1023
    assert 1022 * 7680 + 15360 + 524288 == 8388608
    assert len(json.dumps(STAMP)) == 23
    if args.check_plan:
        print('Plan arithmetic only:128 groups,1023+1 bodies,8388608 bytes,23-char timestamp. No timing run.')
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
            samples.append(heavy)
            print(json.dumps(heavy), flush=True)
            if heavy['exception_type'] is None:
                first = record(store, audit, 'distinct summary key one')
                assert first['counter'] == 1
                summary = measure(case, store, audit, 'summary')
                summary['sample'] = index + 1
                samples.append(summary)
                print(json.dumps(summary), flush=True)
        finally:
            case.doCleanups()
            assert not fixture_root.exists()
    report = {'kind': 'R2 reachable heavy/summary measurement, not unit reds',
              'samples': samples, 'fsync_mocked': False, 'limit_seconds': .270,
              'max_hold': max(row['hold'] for row in samples),
              'max_peer_wait': max(row['peer_wait'] for row in samples),
              'pass': len(samples) == 2 * args.samples and all(row['normal_pass'] for row in samples),
              'resampling': 'None automatic; retain counted-retry faults and every normal miss.'}
    report['margin'] = .270 - max(report['max_hold'], report['max_peer_wait'])
    path = ROOT / '.audit-tmp' / ('r2-diagnostic-measure-' + uuid.uuid4().hex + '.json')
    path.write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps({key: value for key, value in report.items() if key != 'samples'}), flush=True)
    return 0 if report['pass'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
