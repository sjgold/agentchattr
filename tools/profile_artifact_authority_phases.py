"""D4 phase measurement: historical DESIGN or explicit --production-gate.

--production-gate measures actual A/B/C and concurrent peers with real IO.
The default historical DESIGN path below is not production acceptance.

A calls existing service paths up to a harness diagnostic stop. C is a
prospective guard/effect probe using existing primitives, not D4 implementation.
All samples and setup failures are retained; no fsync/validation bypass.
"""
from argparse import ArgumentParser
from contextlib import ExitStack
from copy import deepcopy
import hashlib
import json
import inspect
import os
from pathlib import Path
import statistics
import subprocess
import sys
import time
from unittest.mock import patch
import uuid

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from api_seats import atomic_json
from artifact_delivery import ArtifactOutbox
from artifact_store import ArtifactUnavailable, request_ids, _empty
from sealed_result_io import canonical_utf8
from artifact_worker import MAX_CONTEXT_BYTES
from tests.test_artifact_admission import ArtifactAdmissionTests
from tests.test_artifact_import_benchmark import graph
import runtime_ownership


def checkpoint_provenance(tool):
    """Untimed real-writer/implementation checks, never a latency result."""
    import api_seats
    import artifact_store
    assert inspect.isbuiltin(os.fsync) and os.fsync.__module__ in ('nt', 'posix')
    assert Path.replace.__module__ == 'pathlib' and Path.replace.__name__ == 'replace'
    writes = []
    original_open = Path.open
    target = ROOT / '.audit-tmp' / ('writer-provenance-' + uuid.uuid4().hex + '.json')
    target.parent.mkdir(exist_ok=True)
    class CountWrites:
        def __init__(self, stream): self.stream = stream
        def __enter__(self): return self
        def __exit__(self, *args): return self.stream.__exit__(*args)
        def __getattr__(self, name): return getattr(self.stream, name)
        def write(self, value):
            writes.append(value)
            return self.stream.write(value)
    def opened(path, *args, **kwargs):
        stream = original_open(path, *args, **kwargs)
        return CountWrites(stream) if path.name.startswith(target.name + '.') else stream
    payload = {'unicode': '\u00e9', 'values': [1, 2.5, None]}
    try:
        with patch.object(Path, 'open', opened):
            api_seats.atomic_json(target, payload)
        d2 = len(writes) == 1 and target.read_bytes() == json.dumps(payload, ensure_ascii=True, allow_nan=False).encode('utf-8')
    finally:
        target.unlink(missing_ok=True)
    r2 = hasattr(artifact_store, 'ArtifactDiagnosticStore')
    d1 = r2 and 'scandir' in artifact_store.ArtifactDiagnosticStore._body_inventory.__code__.co_names
    assert r2 and d1 and d2, (r2, d1, d2)
    fixtures = sorted({Path(module.__file__).resolve().relative_to(ROOT).as_posix()
        for name, module in list(sys.modules.items()) if name.startswith('tests.test_')
        and getattr(module, '__file__', None) and Path(module.__file__).resolve().is_relative_to(ROOT)})
    extra = ['sealed_result_io.py', 'artifact_worker.py', *fixtures]
    dirty = subprocess.check_output(['git','status','--porcelain'],cwd=ROOT,text=True)
    return {'fsync_mocked': not inspect.isbuiltin(os.fsync),
            'filesystem_primitives_verified_unpatched_before_counters': True,
            'detected_implementations': {'r2_diagnostic_owner': r2, 'd1_scandir': d1, 'd2_single_write_byte_identity': d2},
            'r2_d1_d2_present': r2 and d1 and d2, 'authoring_schema': artifact_store._empty()['version'],
            'dirty_tree': bool(dirty), 'git_status_porcelain': dirty,
            'fixture_and_support_sha256': {name: hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in extra},
            'tool_sha256': hashlib.sha256(Path(tool).read_bytes()).hexdigest(),
            'closed_a1_base': '2c34bbfb159a3334ad4ba66eb7a8fbd4175594ca',
            'preserved_r2_parent': 'be6fd6522474fe2fab0e6f0573ec6e9ccb9eab4a'}


class DiagnosticStop(Exception):
    pass


def renew(case, instance, attempt):
    receipt = json.loads(attempt['receipt'].read_text(encoding='utf-8'))
    receipt['updated_at'] = time.time()
    atomic_json(attempt['receipt'], receipt)
    birth = json.loads(attempt['snapshot'].with_name('birth.json').read_text(encoding='utf-8'))
    with patch('runtime_adoption.open_verified_process', return_value={'status': 'live', 'process': attempt['process']}):
        assert case.manager.observe_runtime_heartbeat(instance,
            runtime_ownership.heartbeat_payload(birth, case.manager.boot_id))['verified']


def setup(kind):
    case = ArtifactAdmissionTests()
    case.setUp()
    try:
        case.setup_authority()
        instance, attempt = case.instance, case.attempt
        if kind in ('delivery', 'reject_response'):
            instance, attempt, _ = case.launch_binding('api')
        data = _empty()
        parent = None
        for number in range(128):
            portable, objects = graph(1)
            if number == 0:
                version = portable['versions'][0]
                raw = b'# Parent\r\n' + b'p' * (524288 - len(b'# Parent\r\n'))
                version.update(sha256=hashlib.sha256(raw).hexdigest(), byte_length=len(raw))
                objects[('version', version['version_id'])] = raw
                parent = (portable['lineage_id'], {'version_id': version['version_id'],
                    'sequence': 1, 'sha256': version['sha256']})
            converted = case.artifacts._import_metadata(portable)
            for group in ('lineages', 'requests', 'versions'):
                data[group].update(converted[group])
            for (object_kind, identifier), raw in objects.items():
                case.artifacts._put_bytes(case.artifacts._object_path(object_kind, identifier), raw)
        # Real valid imported graph, seeded outside measurement, no fake persistence.
        case.artifacts._persist(data)
        template, _ = case.new_request(instance=instance)
        request = uuid.uuid4().hex
        ids = request_ids(request)
        packet = {'version': 1, 'channel': 'review', 'scope_kind': 'selected_channel_messages',
            'source_run': None, 'input': None, 'messages': [
                {'id': i, 'uid': 'phase-' + str(i), 'sender': 'operator', 'type': 'chat',
                 'timestamp': 100.0, 'text': 'x' * 1800, 'attachments': [], 'provenance': {}}
                for i in range(1000)]}
        gap = 2097152 - len(canonical_utf8(packet))
        assert gap > 0
        packet['messages'][-1]['text'] += 'x' * gap
        assert len(canonical_utf8(packet)) == 2097152
        scope = case.artifacts.put_packet(request, packet)
        audit = {**template, **{k: ids[k] for k in ('attempt_id', 'dispatch_id', 'brief_id')},
                 'request_id': request, 'lineage_id': parent[0], 'expected_parent': parent[1], 'scope': scope}
        renew(case, instance, attempt)
        case.authority.prepare_request(audit, packet, request)
        consumer = case.claim(audit, instance)
        markdown = '# Content\r\n' + 'm' * (524288 - len('# Content\r\n'))
        record = case.sealed_fixture_record(audit, consumer, markdown,
            observation=({'confirmed_model': 'fixture-api', 'confirmation_reason': 'api_response'}
                         if kind in ('delivery', 'reject_response') else None))
        box = ArtifactOutbox(case.root / 'api_seat_runtime' / audit['producer']['launch_attempt'])
        private = case.briefs.get_private(audit['brief_id'])
        if kind in ('admit_saved', 'retained_recovery', 'ack_repair', 'startup_terminal'):
            box.save(record['payload'], private['_artifact_seal']['seal_secret'])
        if kind == 'admit_saved':
            record = case.sealed_fixture_record(audit, consumer, '# Different\r\n' + 'n' * (524288-len('# Different\r\n')))
        if kind in ('retained_recovery', 'ack_repair', 'startup_terminal'):
            case.authority.get_brief(audit['brief_id'], instance)
        if kind == 'retained_recovery':
            case.trigger.queue.release(instance, audit['dispatch_id'], consumer)
        if kind == 'ack_repair':
            case.artifacts.commit_version(request, audit['attempt_id'], audit['dispatch_id'],
                '# Different\r\n' + 'n' * (524288-len('# Different\r\n')), record['payload']['observation'])
        if kind == 'startup_terminal':
            case.authority.cancel_request(request)
        renew(case, instance, attempt)
        assert len(case.artifacts._data['requests']) == 129
        return case, audit, instance, record, box
    except BaseException:
        case.doCleanups()
        raise


def stop(*args, **kwargs):
    raise DiagnosticStop()


def probe(kind, checkpoint=None):
    case, audit, instance, record, box = setup(kind)
    fixture_root = case.root
    counts = {'packet_reads_A': 0, 'packet_reads_C': 0, 'contexts_A': 0, 'contexts_C': 0, 'packet_raw_reads_A': 0, 'packet_raw_reads_C': 0, 'content_validations_A': 0, 'content_validations_C': 0}
    phase = ['A']
    retries = {'A': 0, 'C': 0}
    original_replace = Path.replace
    def counted_replace(source, target):
        try:
            return original_replace(source, target)
        except PermissionError:
            retries[phase[0]] += 1
            raise
    original_packet = case.artifacts.get_packet
    original_context = case.authority._context
    original_read = case.artifacts._read_object
    original_scope = case.storage._packet_scope
    def read_object(kind, *args, **kwargs):
        if kind == 'packet': counts['packet_raw_reads_' + phase[0]] += 1
        return original_read(kind, *args, **kwargs)
    def content_scope(*args, **kwargs):
        counts['content_validations_' + phase[0]] += 1
        return original_scope(*args, **kwargs)
    def packet(*args, **kwargs):
        counts['packet_reads_' + phase[0]] += 1
        value = original_packet(*args, **kwargs)
        if kind in ('resume', 'retained_recovery'):
            # Cost includes a FULL successful parse/validation before the fault.
            # This is an explicit late-read fault seam, not a corrupt-file profile.
            raise ArtifactUnavailable('Design probe after complete packet validation')
        return value
    def context(*args, **kwargs):
        counts['contexts_' + phase[0]] += 1
        return original_context(*args, **kwargs)
    def guard_copy():
        row = case.artifacts.get_request(audit['request_id'])
        frozen = json.dumps(row, sort_keys=True, ensure_ascii=True, allow_nan=False).encode('utf-8')
        hashlib.sha256(frozen).hexdigest()
        case.authority._queue_record(row)
        return row
    a_exception = None
    encoding_seconds = 0.0
    encoded_bytes = None
    context_within_limit = None
    try:
        with ExitStack() as stack:
            stack.enter_context(patch.object(Path, 'replace', counted_replace))
            stack.enter_context(patch.object(case.artifacts, 'get_packet', packet))
            stack.enter_context(patch.object(case.artifacts, '_read_object', read_object))
            stack.enter_context(patch.object(case.storage, '_packet_scope', content_scope))
            stack.enter_context(patch.object(case.authority, '_context', context))
            stack.enter_context(patch.object(case.authority, '_diagnostic', stop))
            stack.enter_context(patch.object(case.artifacts, 'quarantine_submission', stop))
            started = time.perf_counter()
            with case.service._boundary():
                try:
                    if kind == 'brief_context':
                        result = case.authority.get_brief_context(audit['brief_id'], instance)
                        encode_started = time.perf_counter()
                        encoded = json.dumps(result, ensure_ascii=True, allow_nan=False)
                        encoded_bytes = len(encoded.encode('utf-8'))
                        context_within_limit = encoded_bytes <= MAX_CONTEXT_BYTES
                        if not context_within_limit:
                            from artifact_transport import error_body
                            json.dumps(error_body('artifact_context_too_large'))
                        encoding_seconds = time.perf_counter() - encode_started
                        assert len(result['parent']['markdown'].encode('utf-8')) == 524288
                    elif kind == 'delivery':
                        case.authority.get_delivery(audit['brief_id'], instance)
                    elif kind == 'submit_cli':
                        case.authority.submit_cli(audit['brief_id'], ' ' * 524288, instance)
                    elif kind == 'admit_saved':
                        case.authority.admit_saved(record, instance)
                    elif kind == 'reject_response':
                        case.authority.reject_response(audit['brief_id'], 'x' * 524288, instance)
                    elif kind == 'resume':
                        case.authority.resume_request(audit['request_id'])
                    elif kind == 'retained_recovery':
                        case.authority.resume_request(audit['request_id'], recover_saved=True)
                    elif kind == 'ack_repair':
                        case.authority.resume_request(audit['request_id'], recover_saved=True)
                    elif kind == 'startup_terminal':
                        case.authority.recover_startup()
                except DiagnosticStop:
                    a_exception = 'DiagnosticStop (expected harness seam)'
                guard_started = time.perf_counter()
                guard_copy()
                guard_seconds = time.perf_counter() - guard_started
            a_seconds = time.perf_counter() - started
            if checkpoint is not None:
                checkpoint({'caller': kind, 'phase': 'A', 'seconds': a_seconds,
                            'guard_copy_seconds': guard_seconds, 'replace_retries': retries['A'], **counts})
            assert a_exception is not None or kind in ('brief_context', 'delivery'), kind
            phase[0] = 'C'
            started = time.perf_counter()
            with case.service._boundary():
                row = guard_copy()
                if kind not in ('retained_recovery', 'ack_repair', 'startup_terminal'):
                    case.authority._context(audit['brief_id'], instance, replay=True)
                elif kind == 'retained_recovery':
                    # Existing retained authority checks up to its packet seam.
                    with patch.object(case.authority, '_packet', side_effect=DiagnosticStop):
                        try:
                            case.authority._resume_recovered(row, case.authority._queue_record(row))
                        except DiagnosticStop:
                            pass
                elif kind == 'ack_repair':
                    try:
                        case.authority._repair_fulfilled_ack(row)
                    except DiagnosticStop:
                        pass
                elif kind == 'startup_terminal':
                    saved = box.get(audit['dispatch_id'])
                    case.protocol.verify_result(saved, case.briefs.get_private(audit['brief_id'])['_artifact_seal']['seal_secret'])
                if kind in ('resume', 'retained_recovery', 'reject_response'):
                    terminal = ('quarantined', 'invalid_response') if kind == 'reject_response' else ('failed', 'source_packet_unavailable')
                    case.artifacts.set_attempt_state(audit['request_id'], audit['attempt_id'], row['state'],
                        {'state': terminal[0], 'reason': terminal[1]})
                    case.authority._fence(row)
                elif kind == 'startup_terminal':
                    # Harness-only receipt id, no actual diagnostic committed.
                    box.quarantine(audit['dispatch_id'], 'f' * 32, 'cancelled')
            c_seconds = time.perf_counter() - started
            if checkpoint is not None:
                checkpoint({'caller': kind, 'phase': 'C_probe', 'seconds': c_seconds,
                            'replace_retries': retries['C'], **counts})
        actual_packet = json.loads(case.artifacts._object_path('packet', audit['scope']['packet_id']).read_bytes())
        parent_id = audit['expected_parent']['version_id']
        actual_parent_bytes = case.artifacts._object_path('version', parent_id).stat().st_size
        actual_requests = len(case.artifacts._data['requests'])
        actual_markdown_bytes = len(record['payload']['markdown'].encode('utf-8'))
        return {'caller': kind, 'A_seconds': a_seconds, 'C_probe_seconds': c_seconds,
                'A_guard_copy_seconds': guard_seconds, 'A_mcp_encoding_seconds': encoding_seconds,
                'A_context_response_bytes': encoded_bytes, 'A_context_within_limit': context_within_limit,
                'A_comparator_seconds': a_seconds - guard_seconds,
                'A_comparator_minus_0270_seconds': a_seconds - guard_seconds - .270,
                'C_probe_minus_0270_seconds': c_seconds - .270,
                'A_replace_retries': retries['A'], 'C_replace_retries': retries['C'],
                'A_exit': a_exception, **counts,
                'authoring_requests': actual_requests, 'small_prior_requests': actual_requests - 1,
                'packet_bytes': len(canonical_utf8(actual_packet)),
                'message_refs': len(audit['scope']['message_refs']), 'parent_bytes': actual_parent_bytes,
                'markdown_bytes': actual_markdown_bytes, 'authoring_schema': case.artifacts._data['version'],
                'authoring_index_bytes': case.artifacts.path.stat().st_size,
                'limitations': 'Merged R2-on-A1 DESIGN checkpoint. A raw includes MCP encode/size and guard_copy; only A_comparator subtracts measured guard_copy. No acceptance booleans or margin gate for unchanged code. C runs outside A1 scope (cold content validation), unlike a future same-scope D4 C. No B/peer gate. Fixed caller order, no warmup discard; sizes derived.'}
    finally:
        cleanup_probe(case, fixture_root, kind, checkpoint)


def cleanup_probe(case, fixture_root, kind, checkpoint):
    try:
        case.doCleanups()
        assert not fixture_root.exists()
    except Exception as exc:
        if checkpoint is None:
            raise
        checkpoint({'caller': kind, 'phase': 'cleanup',
                    'error': {'type': type(exc).__name__, 'message': str(exc)}})


def production_observe(case, action, *, persist=True, healthy=False, checkpoint=None):
    """Observe real outermost lock holds, real B IO, and repeated same-boundary peers."""
    import threading
    from contextlib import contextmanager
    boundary = case.service._boundary
    writer = case.authority._persist_diagnostic_intent
    settle = case.authority._settle_diagnostic_intent
    local = threading.local()
    phase = ['A']; holds = []; latencies = []; waits = []; errors = []; ownership = []
    retries = {'A': 0, 'B': 0, 'C': 0}
    entered = threading.Event(); finished = threading.Event(); peer_started = threading.Event()
    def peer():
        if not entered.wait(30):
            errors.append('peer_never_started'); return
        while not finished.is_set():
            started = time.perf_counter(); peer_started.set()
            try: case.service.require_active('peer')
            except Exception as error: errors.append(type(error).__name__)
            waits.append(time.perf_counter() - started)
            finished.wait(.001)
    @contextmanager
    def observed_boundary():
        depth = getattr(local, 'depth', 0)
        local.depth = depth + 1
        completed=None
        try:
            with boundary():
                started = time.perf_counter()
                if healthy and depth==0 and threading.current_thread() is threading.main_thread():entered.set()
                try: yield
                finally:
                    if depth == 0 and threading.current_thread() is threading.main_thread():
                        completed={'phase': phase[0], 'seconds': time.perf_counter() - started}
                        holds.append(completed)
        finally:
            local.depth = depth
            # Receipt IO happens after releasing the measured authority locks.
            if completed is not None and checkpoint is not None:checkpoint(completed)
    def measured_work(work):
        phase[0] = 'B'
        ownership.append([owner._lock._is_owned() for owner in (case.engine, case.catalog, case.artifacts)])
        entered.set()
        if not peer_started.wait(5): raise RuntimeError('No concurrent boundary peer')
        started = time.perf_counter()
        try: return work()
        finally:
            latencies.append(time.perf_counter() - started); finished.set()
            if checkpoint is not None:checkpoint({'phase':'B','seconds':latencies[-1],
                'authority_owned':ownership[-1],'peer_samples_so_far':len(waits)})
    def persisted(intent):
        return measured_work(lambda: writer(intent))
    def settled(*args, **kwargs):
        phase[0] = 'C'
        return settle(*args, **kwargs)
    replace = Path.replace
    def counted(source, target):
        try: return replace(source, target)
        except PermissionError:
            retries[phase[0]] += 1; raise
    thread = threading.Thread(target=peer, name='D4-boundary-peer')
    thread.start(); outcome = None; value = None
    try:
        with ExitStack() as stack:
            stack.enter_context(patch.object(case.service, '_boundary', observed_boundary))
            stack.enter_context(patch.object(case.authority, '_persist_diagnostic_intent', persisted))
            stack.enter_context(patch.object(case.authority, '_settle_diagnostic_intent', settled))
            stack.enter_context(patch.object(Path, 'replace', counted))
            try: value = action() if persist else measured_work(action)
            except Exception as error: outcome = type(error).__name__
    finally:
        finished.set(); entered.set(); thread.join(timeout=30)
    if thread.is_alive(): raise RuntimeError('Boundary peer did not finish')
    expected = outcome in (None, 'ArtifactInputError', 'ArtifactUnavailable')
    hard = expected and not errors and bool(waits) and all(not any(row) for row in ownership)
    hard = hard and all(row['seconds'] <= .270 and row['phase'] != 'B' for row in holds) and max(waits, default=1) <= .270
    margin = hard and all(row['seconds'] <= .216 for row in holds) and max(waits, default=1) <= .216
    return {'holds': holds, 'B_seconds': latencies, 'B_authority_owned': ownership,
            'peer_waits': waits, 'peer_max_seconds': max(waits, default=None), 'peer_errors': errors,
            'replace_retries': retries, 'exception_type': outcome,
            'hard_pass': hard, 'margin_pass': margin, 'pass': margin and not any(retries.values())}, value


def production_gate(count, *, facade=False):
    """Separate acceptance mode. Historical DESIGN receipts are never relabeled."""
    from measure_artifact_diagnostics import setup as diagnostic_setup, body, record as diagnostic_record, import_gates
    from tests.test_artifact_diagnostic_owner import ArtifactDiagnosticOwnerTests
    kinds = (('facade_reads',) if facade else ('brief_context', 'delivery', 'submit_cli', 'admit_saved',
        'reject_response', 'resume', 'retained_recovery', 'ack_repair', 'startup_terminal', 'healthy_brief_context', 'healthy_delivery'))
    destination = ROOT / '.audit-tmp' / ('d4-production-' + ('reads-imports-' if facade else 'service-') + uuid.uuid4().hex + '.json')
    result = {'kind': 'D4 PRODUCTION acceptance gate', 'samples': [], 'phase_observations': [],
        'product_pin': subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        'source_sha256': {name: hashlib.sha256((ROOT/name).read_bytes()).hexdigest()
            for name in ('artifact_store.py','artifact_service.py','mcp_bridge.py','api_seats.py')},
        'fixed_order': list(kinds), 'samples_per_caller': count, 'warmup_discarded': 0,
        'resampling': 'None; every original miss, retry and error retained.',
        'cache_disclosure': 'Warm after setup; structural report forces metadata reread. Cold restart tails unmeasured.',
        'phase_definition': 'Outermost acquired main-thread boundary holds; B and C identified by private production hooks. No guard-copy or hypothetical C probe.',
        'peer_definition': 'Repeated require_active on the same engine/catalog locks during real B. Waits include contention through completion; B has no wall clock gate.',
        'limits': {'hard': .270, 'changed_hold_and_peer': .216, 'import': .300}}
    result.update(checkpoint_provenance(__file__))
    def retain(row=None):
        if row is not None: result['samples'].append(row)
        destination.write_text(json.dumps(result, indent=2), encoding='utf-8')
        if row is not None: print(json.dumps(row), flush=True)
    retain()
    for kind in kinds:
        for number in range(1, count + 1):
            case = None
            def checkpoint(observation):
                result['phase_observations'].append({**observation,'caller':kind,'sample':number})
                retain()
            try:
                case, audit, instance, saved_record, box = setup('brief_context' if facade else kind.removeprefix('healthy_'))
                audits = [row['audit'] for row in case.artifacts._data['requests'].values()
                          if row['audit']['request_id'] != audit['request_id']][:127] + [audit]
                diagnostic_setup(case, store=case.artifacts, audits=audits)
                store = case.artifacts
                if facade:
                    actions = [('heavy', lambda: diagnostic_record(store, audit, body(1023,524288).decode('ascii')))]
                    for label, action in actions:
                        row, value = production_observe(case, action, persist=False,checkpoint=checkpoint)
                        if value is None or value['kind'] != 'quarantine': row['pass'] = False
                        row.update(caller=kind, phase=label, sample=number)
                        retain(row)
                    diagnostic_record(store,audit,'distinct summary key one')
                    row,value = production_observe(case,lambda:diagnostic_record(store,audit,'distinct summary key two'),persist=False,checkpoint=checkpoint)
                    if value is None or value['kind'] != 'dispatch_overflow': row['pass']=False
                    row.update(caller=kind,phase='summary',sample=number);retain(row)
                    def attached_reads():
                        attached=store.request_diagnostics(audit['request_id'])
                        unattached=store.request_diagnostics('f'*32)
                        assert attached['available'] and unattached['available']
                        return attached
                    row,_=production_observe(case,attached_reads,persist=False,checkpoint=checkpoint)
                    row.update(caller=kind,phase='request_diagnostics',sample=number);retain(row)
                    ledger=ArtifactDiagnosticOwnerTests.maximum_ledger()
                    store.diagnostic_store._persist_diagnostics(ledger)
                    previous=store.diagnostic_store._stamp
                    atomic_json(store.diagnostic_store.path,ledger)
                    if store.diagnostic_store._fingerprint()==previous:
                        info=store.diagnostic_store.path.stat()
                        os.utime(store.diagnostic_store.path,ns=(info.st_atime_ns,info.st_mtime_ns+1000000))
                    row,value=production_observe(case,lambda:store.diagnostics(limit=100),persist=False,checkpoint=checkpoint)
                    if value is None or value['detailed_count'] != 1024: row['pass']=False
                    row.update(caller=kind,phase='structural_read',sample=number,metadata_bytes=810186);retain(row)
                    continue
                original_packet=store.get_packet;packet_reads=[0]
                def packet(*args,**kwargs):
                    value=original_packet(*args,**kwargs);packet_reads[0]+=1
                    if kind=='brief_context' and packet_reads[0]==1:return value
                    raise ArtifactUnavailable('Gate late-read source fault after full content validation')
                # Source failure entries pay for the full healthy validation before the fault.
                source_fault = kind in ('brief_context','delivery','resume','retained_recovery')
                action = {
                    'brief_context': lambda:case.authority.get_brief_context(audit['brief_id'],instance),
                    'delivery': lambda:case.authority.get_delivery(audit['brief_id'],instance),
                    'submit_cli': lambda:case.authority.submit_cli(audit['brief_id'],' '*524288,instance),
                    'admit_saved': lambda:case.authority.admit_saved(saved_record,instance),
                    'reject_response': lambda:case.authority.reject_response(audit['brief_id'],'x'*524288,instance),
                    'resume': lambda:case.authority.resume_request(audit['request_id']),
                    'retained_recovery': lambda:case.authority.resume_request(audit['request_id'],recover_saved=True),
                    'ack_repair': lambda:case.authority.resume_request(audit['request_id'],recover_saved=True),
                    'startup_terminal': case.authority.recover_startup,
                    'healthy_brief_context': lambda:case.authority.get_brief_context(audit['brief_id'],instance),
                    'healthy_delivery': lambda:case.authority.get_delivery(audit['brief_id'],instance)}[kind]
                with patch.object(store,'get_packet',packet) if source_fault else ExitStack():
                    row,value=production_observe(case,action,healthy=kind.startswith('healthy_'),checkpoint=checkpoint)
                if kind.startswith('healthy_'):
                    if row['exception_type'] is not None or row['B_seconds'] or not row['holds']:row['pass']=False
                    # MCP encoding is outside the boundary under D4, latency remains visible.
                    encoded_start=time.perf_counter();encoded=json.dumps(value,ensure_ascii=True,allow_nan=False)
                    row['outside_boundary_response_encode_seconds']=time.perf_counter()-encoded_start
                    row['response_bytes']=len(encoded.encode('utf-8'))
                elif len(row['B_seconds']) != 1 or not any(h['phase']=='C' for h in row['holds']): row['pass']=False
                row.update(caller=kind,sample=number,source_fault_hook_calls=packet_reads[0],authoring_requests=len(store._data['requests']),
                    packet_bytes=2097152,message_refs=1000,parent_bytes=524288,markdown_bytes=524288,
                    source_fault='after full successful bounded read/validation' if source_fault else None,
                    diagnostic_body_objects=len(store.diagnostic_store._body_inventory()[0]),
                    diagnostic_body_bytes=store.diagnostic_store._body_inventory()[1])
                retain(row)
            except Exception as error:
                retain({'caller':kind,'sample':number,'error':type(error).__name__,'message':str(error),'pass':False})
            finally:
                if case is not None: cleanup_probe(case,case.root,kind,lambda row:retain({**row,'sample':number,'pass':False}))
    if facade:
        existing=[graph(1) for _ in range(100)];large=graph(128,exact_bytes=4194304)
        for mode in ('full','held'):
            for number in range(1,count+1):
                try:
                    row=import_gates(number,existing,large,mode,checkpoint=lambda observation:(result['phase_observations'].append({**observation,'sample':number}),retain()))
                    row['pass']=row['normal_pass'];retain(row)
                except Exception as error: retain({'phase':'import_'+mode,'sample':number,'error':type(error).__name__,'pass':False})
    result['pass']=all(row['pass'] for row in result['samples']) and len(result['samples'])==(6 if facade else 11)*count
    retain();print(json.dumps({'receipt':str(destination),'pass':result['pass'],'rows':len(result['samples'])}),flush=True)
    return 0 if result['pass'] else 1


def main():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument('--samples', type=int, default=10)
    parser.add_argument('--production-gate', action='store_true')
    args = parser.parse_args()
    if args.samples < 10:
        parser.error('At least 10 fresh samples per caller are required')
    if args.production_gate:
        return production_gate(args.samples)
    kinds = ('brief_context', 'delivery', 'submit_cli', 'admit_saved', 'reject_response',
             'resume', 'retained_recovery', 'ack_repair', 'startup_terminal')
    rows = []
    destination = ROOT / '.audit-tmp' / ('r2-authority-phase-design-' + uuid.uuid4().hex + '.json')
    destination.parent.mkdir(exist_ok=True)
    result = {'kind': 'DESIGN checkpoint: R2-on-closed-A1 authority phases', 'samples': rows, 'phase_observations': [],
              'fsync_mocked': False, 'harness_edits_product': False,
              'product_pin': subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
              'source_sha256': {name: hashlib.sha256((ROOT/name).read_bytes()).hexdigest()
                  for name in ('artifact_store.py','artifact_service.py','mcp_bridge.py','api_seats.py')},
              'tool_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              'peer_measured': False, 'reference_seconds': .270,
              'closed_a1_base': '2c34bbfb159a3334ad4ba66eb7a8fbd4175594ca',
              'preserved_r2_parent': 'be6fd6522474fe2fab0e6f0573ec6e9ccb9eab4a',
              'authoring_schema': 2, 'r2_d1_d2_present': True,
              'fixed_order': list(kinds), 'samples_per_caller': args.samples,
              'cache_disclosure': 'Owner caches warm after setup; no cold-restart tail measurement.',
              'warmup_discarded': 0, 'resampling': 'None; error rows retained, continue remaining samples/callers.'}
    result.update(checkpoint_provenance(__file__))
    def retain(row=None):
        if row is not None:
            rows.append(row)
        destination.write_text(json.dumps(result, indent=2), encoding='utf-8')
        if row is not None:
            print(json.dumps(row), flush=True)
    retain()
    for kind in kinds:
        for sample in range(args.samples):
            try:
                def checkpoint(observation):
                    result['phase_observations'].append({**observation, 'sample': sample + 1})
                    if observation.get('phase') == 'cleanup' and 'error' in observation:
                        retain({**observation, 'sample': sample + 1})
                    else:
                        retain()
                row = {**probe(kind, checkpoint=checkpoint), 'sample': sample + 1}
            except Exception as exc:
                row = {'caller': kind, 'sample': sample + 1,
                       'error': {'type': type(exc).__name__, 'message': str(exc)}}
            retain(row)
    print(json.dumps({'receipt': str(destination), 'samples': len(rows)}), flush=True)


if __name__ == '__main__':
    raise SystemExit(main())
