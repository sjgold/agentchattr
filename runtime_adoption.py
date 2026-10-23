"""Cold runtime inventory and authenticated proof, with no automatic spawning.

Files identify candidates. Only an authenticated current-boot adapter report
plus exact native birth verification grants a retained process handle.
"""
from copy import deepcopy
import json
import os
from pathlib import Path
import time

from process_identity import open_verified_process
from runtime_ownership import _validate, _manifest, _server_identity, _EFFECTIVE_FIELDS


def has_unverified_launch(manager, key):
    """A lost in-memory owner cannot turn an old launch into a fresh slot."""
    import hashlib
    marker = hashlib.sha256(key.encode()).hexdigest()[:8] + '-'
    known = {attempt['id'] for attempt in manager.attempts.values()}
    known.update(manager.retired_attempts)
    for path in (manager.store.path.parent / 'api_seat_runtime').glob('*/config.json'):
        if path.parent.name in known:
            continue
        matches = False
        try:
            snapshot = _read(path)
            identity = snapshot.get('ownership', {})
            base = snapshot.get('base', '')
            matches = (isinstance(identity, dict) and identity.get('launch_key') == key)
            matches = matches or (isinstance(base, str) and
                any(base.startswith(prefix + marker) for prefix in ('cli-', 'api-')))
            if not matches:
                continue
            validated = _validate(path, snapshot)
            if validated is not None:
                manifest = _manifest(path.with_name('launch.json'), validated[0])
                if manifest['spawn_outcome'] == 'failed' and not path.with_name('birth.json').exists():
                    continue
            return True
        except (OSError, ValueError, KeyError, TypeError):
            # A recognized key with incomplete evidence is a reservation,
            # never evidence that Popen failed before creation.
            if matches:
                return True
    return False


def _read(path):
    value = json.loads(path.read_text(encoding='utf-8'))
    if not isinstance(value, dict):
        raise ValueError('Runtime evidence must be a mapping.')
    return value


def _candidate(manager, path):
    snapshot = _read(path)
    validated = _validate(path, snapshot)
    if validated is None:
        raise ValueError('legacy_unverified')
    identity, path = validated
    effective = {key: snapshot[key] for key in _EFFECTIVE_FIELDS if key in snapshot}
    # Compare with this manager's approved server, independently of metadata
    # self-consistency. Current provider/model edits cannot alter the snapshot.
    approved = {'server': deepcopy(manager.config.get('server', {}))}
    approved['server']['data_dir'] = str(manager.store.path.parent.resolve())
    approved['mcp'] = deepcopy(manager.config.get('mcp', {}))
    root, data, server = _server_identity(manager.root, approved)
    if (os.path.normcase(root) != os.path.normcase(identity['root_path'])
            or os.path.normcase(data) != os.path.normcase(identity['data_path'])
            or server != identity['server_identity']):
        raise ValueError('foreign_server_identity')
    manifest = _manifest(path.with_name('launch.json'), identity)
    if manifest['spawn_outcome'] == 'failed':
        if path.with_name('birth.json').exists():
            raise ValueError('failed_spawn_has_conflicting_birth')
        return {'snapshot': snapshot, 'path': path, 'identity': identity,
                'birth': None, 'effective': effective, 'key': identity['launch_key'], 'manifest': manifest}
    birth = _read(path.with_name('birth.json'))
    if (birth.get('ownership') != identity or birth.get('attempt') != identity['attempt']
            or birth.get('base') != snapshot['base']
            or os.path.normcase(str(birth.get('worker_root'))) != os.path.normcase(root)):
        raise ValueError('worker_birth_mismatch')
    return {'snapshot': snapshot, 'path': path, 'identity': identity,
            'birth': birth, 'effective': effective, 'key': identity['launch_key'], 'manifest': manifest}


def _historical_exit(item):
    """Classify evidence without adopting or controlling a candidate process."""
    if item['manifest']['spawn_outcome'] == 'failed':
        return {'state': 'failed', 'reason': 'synchronous_spawn_failed', 'spawn_outcome': 'failed'}
    try:
        observed = open_verified_process(item['birth'])
    except (OSError, ValueError):
        return {'state': 'unverified', 'reason': 'process_probe_failed'}
    process = observed.get('process')
    if process:
        process.close()  # Inventory never retains lifecycle authority.
    absent = ((observed.get('status') == 'absent' and observed.get('error_code') == 87)
              or (observed.get('status') == 'mismatch' and observed.get('reason') == 'creation_time_mismatch'))
    if not absent:
        return {'state': 'unverified', 'reason': ('awaiting_authenticated_boot_proof'
                if observed.get('status') == 'live' else 'unproven_worker_exit')}
    if item['effective']['seat']['adapter'] != 'cli':
        from invocation_evidence import classify_history
        child_proof = classify_history(item['path'].parent)
        if child_proof['local_ended']:
            return {'state': 'exited', 'reason': 'local_exit_proven',
                    'exit_evidence': {'wrapper_status': 'absent', **child_proof}}
        return {'state': 'unverified', 'reason': 'unproven_worker_exit'}
    try:
        receipt = _read(item['path'].with_name('receipt.json'))
        if (receipt.get('attempt') == item['identity']['attempt']
                and receipt.get('state') in ('stopped', 'failed')
                and type(receipt.get('child_exit_code')) is int):
            return {'state': 'exited', 'reason': 'local_exit_proven', 'exit_evidence': {
                'wrapper_status': 'absent', 'child_exit_code': receipt['child_exit_code'],
                'verification_basis': 'durable_receipt_and_observed_absent'}}
    except (OSError, ValueError):
        pass
    return {'state': 'unverified', 'reason': 'unproven_worker_exit'}


def reconcile_runtime(manager, *, now=None):
    with manager.lock:
        candidates, public = {}, []
        directory = manager.store.path.parent / 'api_seat_runtime'
        for path in sorted(directory.glob('*/config.json')):
            try:
                item = _candidate(manager, path)
                classification = _historical_exit(item)
                attempt_id = item['identity']['attempt']
                if classification['state'] in ('exited', 'failed'):
                    manager.retired_attempts.add(attempt_id)
                    manager.runtime_history[attempt_id] = {**item, **classification}
                else:
                    candidates[attempt_id] = item
                public.append({'attempt': attempt_id, 'key': item['key'], **classification})
            except (OSError, ValueError, KeyError, TypeError):
                public.append({'attempt': path.parent.name, 'state': 'unverified',
                               'reason': 'runtime_evidence_unverified'})
        manager.runtime_candidates = candidates
        return public


def observe_runtime_heartbeat(manager, instance, payload, *, now=None):
    now = time.time() if now is None else now
    reply = {'boot_id': manager.boot_id, 'verified': False, 'reason': 'runtime_evidence_unverified'}
    with manager.lock:
        if not isinstance(payload, dict) or not isinstance(instance, dict):
            return reply
        if payload.get('boot_id') != manager.boot_id:
            return dict(reply, reason='current_boot_echo_required')
        reconcile_runtime(manager, now=now)
        item = manager.runtime_candidates.get(payload.get('attempt'))
        if not item:
            return reply
        identity, birth = item['identity'], item['birth']
        expected = {'attempt': identity['attempt'], 'launch_nonce': identity['launch_nonce'],
                    'server_identity': identity['server_identity'], 'boot_id': manager.boot_id,
                    'worker_pid': birth.get('pid'), 'creation_filetime': birth.get('creation_filetime'),
                    'worker_root': birth.get('worker_root')}
        if payload != expected or type(payload.get('worker_pid')) is not int:
            return reply
        try:
            receipt = _read(item['path'].with_name('receipt.json'))
        except (OSError, ValueError):
            return reply
        live = manager.registry.get_instance(instance.get('name'))
        if (not live or live.get('identity_id') != instance.get('identity_id')
                or live.get('base') != item['snapshot']['base']
                or receipt.get('identity_id') != instance.get('identity_id')
                or receipt.get('attempt') != identity['attempt']):
            return reply
        # Ambiguous histories cannot select a winner by mtime, name or PID.
        if sum(other['key'] == item['key'] and other['identity']['attempt'] not in manager.retired_attempts
               for other in manager.runtime_candidates.values()) != 1:
            return dict(reply, reason='conflicting_launch_attempts')
        previous = manager.attempts.get(item['key'])
        if previous and previous['id'] != identity['attempt']:
            return dict(reply, reason='conflicting_launch_attempts')
        if previous and previous.get('adopted_boot') == manager.boot_id:
            if previous.get('released') or previous['process'].poll() is not None:
                return dict(reply, reason='worker_exited')
            previous['authenticated_at'] = now
            return dict(reply, verified=True, reason='verified_runtime')
        try:
            observed = open_verified_process(birth)
        except (OSError, ValueError):
            return reply
        process = observed.get('process')
        if observed['status'] != 'live':
            if process:
                process.close()
            return dict(reply, reason=observed.get('reason', 'worker_not_live'))
        if previous and previous.get('process') is not None:
            # A same-boot launch already has the original Popen authority.
            process.close()
            process = previous['process']
            attempt = previous
        else:
            attempt = {'id': identity['attempt'], 'fingerprint': identity['fingerprint'],
                       'process': process, 'snapshot': item['path'], 'receipt': item['path'].with_name('receipt.json'),
                       'started': time.monotonic(), 'seat': deepcopy(item['effective']['seat']),
                       'effective': deepcopy(item['effective']), 'last_receipt_at': receipt.get('updated_at'),
                       'state': 'starting', 'error': None, 'name': instance['name'],
                       'confirmed_model': None, 'authentication': 'unknown', 'adapter_connected': False,
                       'base': item['snapshot']['base'], 'identity_id': instance['identity_id'],
                       'ownership': identity, 'spawn_outcome': 'spawned'}
            for field in ('context_id', 'context_source_fingerprint', 'context_base_effective',
                          'context_key', 'child_run_id', 'role', 'retried_from', 'retry_source_ended',
                          'verification_basis', 'context_clean_verified', 'preparation_history', 'invocation_protocol'):
                if field in item['snapshot']:
                    attempt[field] = deepcopy(item['snapshot'][field])
            manager.attempts[item['key']] = attempt
        attempt.update(adopted_boot=manager.boot_id, authenticated_at=now, identity_id=instance['identity_id'])
        return dict(reply, verified=True, reason='verified_runtime')


def restart_readiness(manager, identity_id, boot_id, *, now=None):
    now = time.time() if now is None else now
    result = {'state': 'unverified', 'process_verified': False, 'reason': 'awaiting_authenticated_boot_proof'}
    with manager.lock:
        if boot_id != manager.boot_id:
            return result
        for attempt in manager.attempts.values():
            if attempt.get('identity_id') != identity_id or attempt.get('adopted_boot') != boot_id:
                continue
            process = attempt.get('process')
            if attempt.get('released') or process is None or process.poll() is not None:
                return dict(result, state='exited', reason='worker_exited')
            if now - attempt.get('authenticated_at', 0) > 15:
                return dict(result, state='disconnected', reason='authenticated_lease_expired')
            try:
                receipt = _read(attempt['receipt'])
            except (OSError, ValueError):
                return result
            live = next((item for item in manager.registry.get_all().values()
                         if item.get('identity_id') == identity_id and item.get('base') == attempt['base']), None)
            if (live and receipt.get('attempt') == attempt['id'] and receipt.get('identity_id') == identity_id
                    and receipt.get('state') == 'ready' and receipt.get('adapter_connected') is True):
                return {'state': 'ready', 'process_verified': True}
            return dict(result, reason='adapter_not_ready')
        return result
