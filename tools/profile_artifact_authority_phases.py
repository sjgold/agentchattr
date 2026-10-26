"""D4 DESIGN feasibility only, unchanged product, real IO, no acceptance gate.

A calls existing service paths up to a harness diagnostic stop. C is a
prospective guard/effect probe using existing primitives, not D4 implementation.
All samples and setup failures are retained; no fsync/validation bypass.
"""
from argparse import ArgumentParser
from contextlib import ExitStack
from copy import deepcopy
import hashlib
import json
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
        # Real valid cleared-R1 graph, seeded outside measurement, no fake persistence.
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


def probe(kind):
    case, audit, instance, record, box = setup(kind)
    fixture_root = case.root
    counts = {'packet_reads_A': 0, 'packet_reads_C': 0, 'contexts_A': 0, 'contexts_C': 0, 'packet_raw_reads_A': 0, 'packet_raw_reads_C': 0, 'content_validations_A': 0, 'content_validations_C': 0}
    phase = ['A']
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
        actual_packet = json.loads(case.artifacts._object_path('packet', audit['scope']['packet_id']).read_bytes())
        parent_id = audit['expected_parent']['version_id']
        actual_parent_bytes = case.artifacts._object_path('version', parent_id).stat().st_size
        actual_requests = len(case.artifacts._data['requests'])
        actual_markdown_bytes = len(record['payload']['markdown'].encode('utf-8'))
        return {'caller': kind, 'A_seconds': a_seconds, 'C_probe_seconds': c_seconds,
                'A_guard_copy_seconds': guard_seconds, 'A_mcp_encoding_seconds': encoding_seconds,
                'A_context_response_bytes': encoded_bytes, 'A_context_within_limit': context_within_limit,
                'A_margin_pass': a_seconds <= .216, 'C_probe_margin_pass': c_seconds <= .216,
                'A_hard_pass': a_seconds <= .270, 'C_probe_hard_pass': c_seconds <= .270,
                'A_exit': a_exception, **counts,
                'authoring_requests': actual_requests, 'small_prior_requests': actual_requests - 1,
                'packet_bytes': len(canonical_utf8(actual_packet)),
                'message_refs': len(audit['scope']['message_refs']), 'parent_bytes': actual_parent_bytes,
                'markdown_bytes': actual_markdown_bytes, 'authoring_schema': case.artifacts._data['version'],
                'authoring_index_bytes': case.artifacts.path.stat().st_size,
                'limitations': 'A1 cleared-R1-base DESIGN measurement. A includes actual MCP encoding/size and separately measured guard work; no subtraction for pass. No B/peer gate. C is prospective primitives only, not D4. Fixed caller order, no warmup discard; all sizes derived.'}
    finally:
        case.doCleanups()
        assert not fixture_root.exists()


def main():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument('--samples', type=int, default=10)
    args = parser.parse_args()
    assert args.samples >= 1
    kinds = ('brief_context', 'delivery', 'submit_cli', 'admit_saved', 'reject_response',
             'resume', 'retained_recovery', 'ack_repair', 'startup_terminal')
    rows = []
    error = None
    try:
        for kind in kinds:
            for sample in range(args.samples):
                row = {**probe(kind), 'sample': sample + 1}
                rows.append(row)
                print(json.dumps(row), flush=True)
    except BaseException as exc:
        error = {'type': type(exc).__name__, 'message': str(exc)}
        raise
    finally:
        result = {'kind': 'R2-on-closed-A1 authority-phase DESIGN, no D4 acceptance', 'samples': rows,
                  'error': error, 'fsync_mocked': False, 'harness_edits_product': False,
                  'product_pin': subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
                  'source_sha256': {name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in ('artifact_store.py','artifact_service.py','mcp_bridge.py','api_seats.py')},
                  'peer_measured': False, 'margin_seconds': .216, 'hard_seconds': .270,
                  'closed_a1_base': '2c34bbfb159a3334ad4ba66eb7a8fbd4175594ca',
                  'preserved_r2_parent': 'be6fd6522474fe2fab0e6f0573ec6e9ccb9eab4a',
                  'authoring_schema': 2, 'r2_d1_d2_present': True}
        destination = ROOT / '.audit-tmp' / ('r2-authority-phase-design-' + uuid.uuid4().hex + '.json')
        destination.write_text(json.dumps(result, indent=2), encoding='utf-8')
        print(json.dumps({'receipt': str(destination), 'samples': len(rows), 'error': error}), flush=True)


if __name__ == '__main__':
    main()
