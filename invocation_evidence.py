"""Secret-free process lifecycle journal, never generated answer recovery."""
from copy import deepcopy
import json
import os
from pathlib import Path
import uuid

from api_seats import atomic_json
from process_identity import capture_birth, open_verified_process
from runtime_ownership import _identifier, _validate, _manifest

_REFERENCES = ('version', 'launch_attempt', 'launch_nonce', 'dispatch_id', 'invocation_id', 'fingerprint')


def _scope(scope):
    if not isinstance(scope, dict) or set(scope) != {'runtime_path', 'launch_attempt', 'launch_nonce', 'dispatch_id'}:
        raise ValueError('Invocation evidence requires the exact owned dispatch scope.')
    for field in ('launch_attempt', 'launch_nonce', 'dispatch_id'):
        _identifier(scope[field], field)
    runtime = Path(scope['runtime_path']).resolve()
    snapshot = json.loads((runtime / 'config.json').read_text(encoding='utf-8'))
    validated = _validate(runtime / 'config.json', snapshot)
    if validated is None:
        raise ValueError('Legacy launches cannot manufacture invocation ownership.')
    identity, path = validated
    if identity['attempt'] != scope['launch_attempt'] or identity['launch_nonce'] != scope['launch_nonce']:
        raise ValueError('Invocation scope differs from immutable launch ownership.')
    if _manifest(path.with_name('launch.json'), identity)['spawn_outcome'] == 'failed':
        raise ValueError('A failed worker spawn cannot own a model invocation.')
    return runtime / 'invocations' / scope['dispatch_id'], identity


def begin(scope):
    directory, identity = _scope(scope)
    intent = {'version': 1, 'launch_attempt': scope['launch_attempt'], 'launch_nonce': scope['launch_nonce'],
              'dispatch_id': scope['dispatch_id'], 'invocation_id': uuid.uuid4().hex,
              'fingerprint': identity['fingerprint'], 'spawn_outcome': 'pending'}
    # Repeated delivery of one dispatch cannot allocate another model call.
    directory.mkdir(parents=True, exist_ok=False)
    atomic_json(directory / 'invocation.json', intent)
    return {'scope': deepcopy(scope), 'intent': intent}


def spawn_outcome(evidence, outcome):
    if outcome not in ('spawned', 'failed'):
        raise ValueError('Invalid invocation spawn outcome.')
    directory, _ = _scope(evidence['scope'])
    intent = dict(evidence['intent'], spawn_outcome=outcome)
    atomic_json(directory / 'invocation.json', intent)
    evidence['intent'] = intent


def record_birth(evidence):
    directory, identity = _scope(evidence['scope'])
    intent = json.loads((directory / 'invocation.json').read_text(encoding='utf-8'))
    expected = evidence['intent']
    if (not isinstance(intent, dict) or any(intent.get(key) != expected.get(key) for key in _REFERENCES)
            or intent.get('fingerprint') != identity['fingerprint']
            or intent.get('spawn_outcome') not in ('pending', 'spawned')):
        raise ValueError('Invocation birth conflicts with durable spawn intent.')
    result = {key: intent[key] for key in _REFERENCES}
    result.update(capture_birth())
    result.setdefault('pid', os.getpid())  # Unsupported platforms still fail native adoption closed.
    target = directory / 'birth.json'
    if target.exists():
        if json.loads(target.read_text(encoding='utf-8')) != result:
            raise ValueError('Existing invocation birth was preserved.')
        return result
    atomic_json(target, result)
    return result


def record_exit(evidence, exit_code):
    if type(exit_code) is not int:
        raise ValueError('Observed child exit requires an integer code.')
    directory, _ = _scope(evidence['scope'])
    result = {key: evidence['intent'][key] for key in _REFERENCES}
    result.update(child_exit_code=exit_code, ipc_cleaned=True)
    atomic_json(directory / 'exit.json', result)


def _read(path):
    value = json.loads(path.read_text(encoding='utf-8'))
    if not isinstance(value, dict):
        raise ValueError('Invocation evidence must be a mapping.')
    return value


def classify(scope):
    """Read-only local end proof; an unverified live PID grants no control."""
    unproven = {'local_ended': False, 'model_status': 'unproven', 'reason': 'unproven_worker_exit'}
    try:
        directory, identity = _scope(scope)
        intent = _read(directory / 'invocation.json')
        if (set(intent) != set(_REFERENCES) | {'spawn_outcome'} or type(intent['version']) is not int
                or intent['version'] != 1 or intent['fingerprint'] != identity['fingerprint']
                or any(intent[field] != scope[field] for field in ('dispatch_id', 'launch_attempt', 'launch_nonce'))
                or intent['spawn_outcome'] not in ('pending', 'spawned', 'failed')):
            return unproven
        _identifier(intent['invocation_id'], 'Invocation')
        if intent['spawn_outcome'] == 'failed':
            if (directory / 'birth.json').exists():
                return unproven
            return {'local_ended': True, 'model_status': 'never_spawned',
                    'verification_basis': 'synchronous_spawn_failed'}
        if (directory / 'exit.json').exists():
            ended = _read(directory / 'exit.json')
            if (all(ended.get(key) == intent[key] for key in _REFERENCES)
                    and type(ended.get('child_exit_code')) is int and ended.get('ipc_cleaned') is True):
                return {'local_ended': True, 'model_status': 'exited', 'child_exit_code': ended['child_exit_code'],
                        'verification_basis': 'observed_child_exit_and_ipc'}
        birth = _read(directory / 'birth.json')
        if not all(birth.get(key) == intent[key] for key in _REFERENCES):
            return unproven
        observed = open_verified_process(birth)
        if observed.get('process'):
            observed['process'].close()
        if ((observed.get('status') == 'absent' and observed.get('error_code') == 87)
                or (observed.get('status') == 'mismatch' and observed.get('reason') == 'creation_time_mismatch')):
            return {'local_ended': True, 'model_status': 'absent',
                    'verification_basis': 'bound_invocation_birth_and_observed_absent'}
        if observed.get('status') == 'live':
            return dict(unproven, model_status='live', reason='model_child_still_running')
    except (OSError, ValueError, KeyError, TypeError):
        pass
    return unproven


def classify_history(runtime_path):
    """All recorded children must end; an empty legacy history proves nothing."""
    runtime = Path(runtime_path)
    unproven = {'local_ended': False, 'model_status': 'unproven', 'reason': 'unproven_worker_exit'}
    try:
        snapshot = _read(runtime / 'config.json')
        validated = _validate(runtime / 'config.json', snapshot)
        if validated is None:
            return unproven
        identity, _ = validated
        base = runtime / 'invocations'
        directories = list(base.iterdir()) if base.exists() else []
        if not directories:
            birth = _read(runtime / 'birth.json')
            if (type(snapshot.get('invocation_protocol')) is int and snapshot['invocation_protocol'] == 1
                    and type(birth.get('invocation_protocol')) is int and birth['invocation_protocol'] == 1
                    and birth.get('ownership') == identity and birth.get('attempt') == identity['attempt']
                    and birth.get('base') == snapshot['base']):
                return {'local_ended': True, 'model_status': 'never_spawned',
                        'verification_basis': 'protocol_one_no_invocations'}
            return unproven
        proofs = []
        for directory in directories:
            proof = classify({'runtime_path': str(runtime), 'launch_attempt': identity['attempt'],
                              'launch_nonce': identity['launch_nonce'], 'dispatch_id': directory.name})
            proofs.append({'dispatch_id': directory.name, **proof})
            if not proof['local_ended']:
                return dict(proof, invocations=proofs)
        return {'local_ended': True, 'model_status': 'ended',
                'verification_basis': 'all_bound_invocations_ended', 'invocations': proofs}
    except (OSError, ValueError, KeyError, TypeError):
        return unproven
