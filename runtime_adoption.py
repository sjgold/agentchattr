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


def _launch_record(manager, path):
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
    return {'snapshot': snapshot, 'path': path, 'identity': identity, 'effective': effective,
            'key': identity['launch_key'], 'manifest': manifest}


def _candidate(manager, path):
    item = _launch_record(manager, path)
    snapshot, identity, manifest = item['snapshot'], item['identity'], item['manifest']
    path = item['path']
    if manifest['spawn_outcome'] == 'failed':
        if path.with_name('birth.json').exists():
            raise ValueError('failed_spawn_has_conflicting_birth')
        return dict(item, birth=None)
    birth = _read(path.with_name('birth.json'))
    if (birth.get('ownership') != identity or birth.get('attempt') != identity['attempt']
            or birth.get('base') != snapshot['base']
            or os.path.normcase(str(birth.get('worker_root'))) != os.path.normcase(identity['root_path'])):
        raise ValueError('worker_birth_mismatch')
    return dict(item, birth=birth)


def recover_prepared_context(manager, key, context_key, fingerprint, binding, retry_attempt):
    """Recover an exact preparation lineage; replay alone never replaces it."""
    from api_seats import SeatError
    records = {}
    for path in (manager.store.path.parent / 'api_seat_runtime').glob('*/config.json'):
        matched = False
        try:
            snapshot = _read(path)
            matched = isinstance(snapshot.get('ownership'), dict) and snapshot['ownership'].get('launch_key') == key
            if not matched:
                continue
            item = _launch_record(manager, path)
            if (snapshot.get('context_key') != context_key
                    or snapshot.get('context_source_fingerprint') != fingerprint
                    or (binding is not None and any(snapshot.get(k) != v for k, v in binding.items()))):
                raise ValueError('Prepared context references differ.')
            records[item['identity']['attempt']] = item
        except (OSError, ValueError, KeyError, TypeError):
            if matched:
                raise SeatError('Prepared context evidence is incomplete or belongs to different settings.') from None
    if not records:
        return None
    replaced = {item['snapshot'].get('retried_from') for item in records.values()}
    leaves = set(records) - replaced
    if len(leaves) != 1:
        raise SeatError('Prepared context history has ambiguous unlinked attempts; no replacement was started.')
    attempt_id = leaves.pop()
    item = records[attempt_id]
    snapshot = item['snapshot']
    # Every other attempt must belong to this leaf's explicit repair ancestry.
    seen, current = set(), attempt_id
    while current in records and current not in seen:
        seen.add(current)
        current = records[current]['snapshot'].get('retried_from')
    if seen != set(records) or current in seen:
        raise SeatError('Prepared context history is not a single repair lineage.')
    manager.reconcile_runtime()
    history = manager.runtime_history.get(attempt_id)
    try:
        current = _candidate(manager, item['path'])
    except (OSError, ValueError, KeyError, TypeError):
        raise SeatError('Prepared context has conflicting or incomplete birth evidence; no replacement was started.') from None
    proven = bool(history and history['state'] in ('failed', 'exited')
                  and current['identity'] == history['identity'] and current['birth'] == history['birth'])
    view = {'key': key, 'state': 'failed' if proven else 'blocked',
            'reason': 'Explicit repair is required.' if proven else 'Prepared worker exit is unverified.',
            'launch_attempt': attempt_id, 'context_id': snapshot.get('context_id'),
            'identity_id': None, 'name': None, 'clean_context': False,
            'verification_basis': snapshot.get('verification_basis', 'same_turn_retry_relaunch'),
            'old_local_ended': snapshot.get('retry_source_ended', False), 'worker_alive': None}
    if retry_attempt is None or snapshot.get('retried_from') == retry_attempt:
        return {'view': view, 'replace': False}
    if retry_attempt != attempt_id:
        raise SeatError('The exact failed prepared launch is required for repair.')
    if not proven:
        return {'view': view, 'replace': False}
    preparation_history = deepcopy(snapshot.get('preparation_history', []))
    preparation_history.append({'launch_attempt': attempt_id, 'context_id': snapshot.get('context_id')})
    return {'view': view, 'replace': True, 'preparation_history': preparation_history}


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


def _display_key(manager, path):
    """Recognize a configured seat for display only, never for adoption."""
    import hashlib
    try:
        snapshot = _read(path)
        base = snapshot.get('base', '')
        for package in manager.store.list():
            for seat in package['seats']:
                key = package['id'] + '/' + seat['id']
                marker = hashlib.sha256(key.encode()).hexdigest()[:8] + '-'
                if isinstance(base, str) and any(base.startswith(prefix + marker) for prefix in ('api-', 'cli-')):
                    return key
    except (OSError, ValueError, KeyError, TypeError):
        pass
    return None


def reconcile_runtime(manager, *, now=None):
    with manager.lock:
        candidates, public = {}, []
        directory = manager.store.path.parent / 'api_seat_runtime'
        for path in sorted(directory.glob('*/config.json')):
            try:
                item = _candidate(manager, path)
                attempt_id = item['identity']['attempt']
                known = manager.attempts.get(item['key'])
                if (known and known['id'] == attempt_id and known.get('worker_birth') is not None
                        and (known['worker_birth'] != item['birth'] or known.get('ownership') != item['identity'])):
                    # A changed file cannot retire an owner whose immutable
                    # birth was already authenticated and retained this boot.
                    public.append({'attempt': attempt_id, 'key': item['key'],
                                   'state': 'unverified', 'reason': 'worker_birth_changed'})
                    continue
                classification = _historical_exit(item)
                if classification['state'] in ('exited', 'failed'):
                    manager.retired_attempts.add(attempt_id)
                    manager.runtime_history[attempt_id] = {**item, **classification}
                else:
                    candidates[attempt_id] = item
                public.append({'attempt': attempt_id, 'key': item['key'], **classification})
            except (OSError, ValueError, KeyError, TypeError) as exc:
                public.append({'attempt': path.parent.name, 'key': _display_key(manager, path),
                               'state': 'unverified', 'reason': 'legacy_unverified' if
                               str(exc) == 'legacy_unverified' else 'runtime_evidence_unverified'})
        manager.runtime_candidates = candidates
        manager.runtime_inventory = deepcopy(public)
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
        attempt.update(adopted_boot=manager.boot_id, authenticated_at=now, identity_id=instance['identity_id'],
                       worker_birth=deepcopy(birth))
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
                candidate = _candidate(manager, attempt['snapshot'])
                if (candidate['identity'] != attempt.get('ownership')
                        or candidate['birth'] != attempt.get('worker_birth')):
                    return dict(result, reason='worker_birth_changed')
                receipt = _read(attempt['receipt'])
            except (OSError, ValueError, KeyError, TypeError):
                return result
            live = next((item for item in manager.registry.get_all().values()
                         if item.get('identity_id') == identity_id and item.get('base') == attempt['base']), None)
            if (live and receipt.get('attempt') == attempt['id'] and receipt.get('identity_id') == identity_id
                    and receipt.get('state') == 'ready' and receipt.get('adapter_connected') is True):
                return {'state': 'ready', 'process_verified': True}
            return dict(result, reason='adapter_not_ready')
        return result


def saved_result_exit_proof(manager, payload):
    """Query exact saved transport lifetime, without controlling its worker."""
    import hashlib
    import re
    from invocation_evidence import classify, classify_history
    unproven = {'local_ended': False, 'reason': 'unproven_worker_exit'}
    with manager.lock:
        try:
            if not isinstance(payload, dict):
                return unproven
            for field, length in (('launch_attempt', 32), ('launch_nonce', 32),
                                  ('dispatch_id', 32), ('fingerprint', 64)):
                if not isinstance(payload.get(field), str) or not re.fullmatch('[0-9a-f]{%d}' % length, payload[field]):
                    return unproven
            launch, dispatch = payload['launch_attempt'], payload['dispatch_id']
            item = _candidate(manager, manager.store.path.parent / 'api_seat_runtime' / launch / 'config.json')
            ownership, birth = item['identity'], item['birth']
            receipt = _read(item['path'].with_name('receipt.json'))
            if (item['effective']['seat']['adapter'] != 'openai-compatible'
                    or item['manifest']['spawn_outcome'] != 'spawned'
                    or ownership['launch_nonce'] != payload['launch_nonce']
                    or ownership['fingerprint'] != payload['fingerprint']
                    or receipt.get('attempt') != launch
                    or not isinstance(payload.get('seat_identity_id'), str)
                    or receipt.get('identity_id') != payload['seat_identity_id']):
                return unproven
            attempt = next((value for value in manager.attempts.values() if value['id'] == launch), None)
            warm_ended = False
            if attempt is not None:
                cached_birth = attempt.get('worker_birth')
                if ((cached_birth is not None and cached_birth != birth) or attempt.get('ownership') != ownership
                        or attempt.get('identity_id') != payload['seat_identity_id']):
                    return unproven
                worker = attempt.get('worker_process') or attempt.get('process')
                # The Popen object can refer to a venv launcher shim. Its exit
                # never establishes the lifetime of the self-attested worker.
                if cached_birth is not None and birth and worker and worker.pid == birth['pid']:
                    if type(worker.poll()) is not int:
                        return unproven
                    warm_ended = True
            if warm_ended:
                models = classify_history(item['path'].parent)
                if not models['local_ended']:
                    return unproven
                if (item['path'].parent / 'invocations' / dispatch).exists():
                    exact = classify({'runtime_path': str(item['path'].parent), 'dispatch_id': dispatch,
                        'launch_attempt': launch, 'launch_nonce': ownership['launch_nonce']})
                    if not exact['local_ended']:
                        return unproven
                elif models.get('verification_basis') != 'protocol_one_no_invocations':
                    return unproven
                proof = dict(models, wrapper_status='observed_exited')
            else:
                effective = manager._provenance_effective(item['effective'])
                provenance = {'key': item['key'], 'launch_attempt': launch,
                    'identity_id': payload['seat_identity_id'], 'effective': effective}
                hashed = effective
                base = item['snapshot'].get('context_base_effective')
                if base:
                    provenance['fresh_base_effective'] = manager._provenance_effective(base)
                    hashed = {'effective': effective, 'fresh_base_effective': provenance['fresh_base_effective']}
                provenance['fingerprint'] = hashlib.sha256(json.dumps(hashed, sort_keys=True).encode()).hexdigest()
                proof = runtime_exit_proof(manager, provenance, dispatch)
                if not proof['local_ended']:
                    return unproven
            return dict(proof, local_ended=True, launch_attempt=launch,
                        dispatch_id=dispatch, seat_identity_id=payload['seat_identity_id'])
        except (OSError, ValueError, KeyError, TypeError):
            return unproven


def runtime_exit_proof(manager, provenance, dispatch_id=None):
    """Resolve one immutable original launch, never a latest-by-name guess."""
    import hashlib
    unproven = {'local_ended': False, 'reason': 'unproven_worker_exit'}
    with manager.lock:
        try:
            if not isinstance(provenance, dict):
                return unproven
            payload = ({'effective': provenance['effective'], 'fresh_base_effective': provenance['fresh_base_effective']}
                       if provenance.get('fresh_base_effective') else provenance['effective'])
            fingerprint = hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()
            if provenance.get('fingerprint') != fingerprint:
                return unproven
            attempt_id = provenance['launch_attempt']
            if attempt_id not in manager.runtime_history:
                reconcile_runtime(manager)
            history = manager.runtime_history.get(attempt_id)
            if not history or history.get('state') != 'exited':
                return unproven
            current = _candidate(manager, history['path'])
            if (current['identity'] != history['identity'] or current['birth'] != history['birth']
                    or current['key'] != provenance['key']
                    or manager._provenance_effective(current['effective']) != provenance['effective']):
                return unproven
            base = current['snapshot'].get('context_base_effective')
            if provenance.get('fresh_base_effective') != (manager._provenance_effective(base) if base else None):
                return unproven
            receipt = _read(current['path'].with_name('receipt.json'))
            if receipt.get('attempt') != attempt_id or receipt.get('identity_id') != provenance['identity_id']:
                return unproven
            proof = deepcopy(history['exit_evidence'])
            if current['effective']['seat']['adapter'] != 'cli':
                from invocation_evidence import classify, classify_history
                models = classify_history(current['path'].parent)
                if not models['local_ended']:
                    return unproven
                if dispatch_id is not None:
                    from runtime_ownership import _identifier
                    _identifier(dispatch_id, 'Dispatch')
                    path = current['path'].parent / 'invocations' / dispatch_id
                    if path.exists():
                        model = classify({'runtime_path': str(current['path'].parent), 'dispatch_id': dispatch_id,
                                          'launch_attempt': attempt_id, 'launch_nonce': current['identity']['launch_nonce']})
                        if not model['local_ended']:
                            return unproven
                    elif models.get('verification_basis') != 'protocol_one_no_invocations':
                        # A different dispatch's completed child cannot stand
                        # in for this turn's missing execution receipt.
                        return unproven
                proof.update(models)
            elif (type(receipt.get('child_exit_code')) is not int
                  or receipt['child_exit_code'] != proof['child_exit_code']):
                return unproven
            return dict(proof, local_ended=True, launch_attempt=attempt_id)
        except (OSError, ValueError, KeyError, TypeError):
            return unproven
