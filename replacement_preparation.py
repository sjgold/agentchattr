"""Explicit pre-brief repair of one immutable replacement preparation."""
from copy import deepcopy
import hashlib
import json
import re
import uuid

from api_seats import SeatError


def scope(source_provenance, context_key, binding):
    if (not isinstance(context_key, str) or not re.fullmatch(r'[A-Za-z0-9_.-]{1,128}', context_key)
            or not isinstance(binding, dict) or set(binding) != {'child_run_id', 'role'}
            or not isinstance(binding['child_run_id'], str)
            or not re.fullmatch(r'[0-9a-f]{32}', binding['child_run_id'])
            or not isinstance(binding['role'], str) or not binding['role'].strip()):
        raise SeatError('Replacement preparation requires an exact run, role and bounded context key.')
    try:
        provenance = deepcopy(source_provenance)
        effective = provenance['effective']
        payload = ({'effective': effective, 'fresh_base_effective': provenance['fresh_base_effective']}
                   if provenance.get('fresh_base_effective') else effective)
        fingerprint = hashlib.sha256(json.dumps(payload, sort_keys=True).encode('utf-8')).hexdigest()
        if fingerprint != provenance['fingerprint']:
            raise ValueError('Changed source profile')
        source = {field: provenance[field] for field in ('key', 'launch_attempt', 'identity_id', 'fingerprint')}
        base = deepcopy(provenance.get('fresh_base_effective', effective))
        if base['seat']['adapter'] not in ('cli', 'openai-compatible'):
            raise ValueError('Unknown adapter')
    except (KeyError, TypeError, ValueError, UnicodeError):
        raise SeatError('Replacement source provenance is malformed or changed.') from None
    metadata = {**deepcopy(binding), 'replacement_source': source, 'context_base_effective': base}
    key = 'replacement-' + hashlib.sha256(context_key.encode('utf-8')).hexdigest()[:24] + '/context'
    return provenance, fingerprint, base, metadata, key


def validate_record(manager, key, attempt, metadata, context_key, fingerprint):
    from runtime_adoption import _candidate, _launch_record
    try:
        item = (_candidate(manager, attempt['snapshot']) if attempt.get('worker_birth') is not None
                else _launch_record(manager, attempt['snapshot']))
        if (item['identity'] != attempt.get('ownership') or item['key'] != key
                or (attempt.get('worker_birth') is not None and item['birth'] != attempt['worker_birth'])
                or any(item['snapshot'].get(field) != value or attempt.get(field) != value
                       for field, value in {**metadata, 'context_key': context_key,
                                            'context_source_fingerprint': fingerprint}.items())):
            raise ValueError('Prepared replacement changed')
    except (OSError, ValueError, KeyError, TypeError):
        raise SeatError('Replacement preparation evidence changed; no worker was replaced.') from None


def _unused(manager, directory, identity, launch_attempt):
    """Any delivered authority or work permanently closes preparation repair."""
    from dispatch_queue import QueueStore
    try:
        receipt = {}
        receipt_path = directory / 'receipt.json'
        if receipt_path.exists():
            receipt = json.loads(receipt_path.read_text(encoding='utf-8'))
            if receipt.get('attempt') != launch_attempt:
                raise ValueError('Prepared worker receipt changed')
            recorded_identity = receipt.get('identity_id')
            if identity and recorded_identity and recorded_identity != identity:
                raise ValueError('Prepared worker identity changed')
            identity = identity or recorded_identity
        if identity and QueueStore(manager.store.path.parent).for_identity({'name': 'prepared-replacement', 'identity_id': identity}):
            raise ValueError('Prepared worker has queue history')
        invocations = directory / 'invocations'
        if invocations.exists() and any(invocations.iterdir()):
            raise ValueError('Prepared worker has invocation history')
        for path in (manager.store.path.parent / 'review_briefs').glob('*.json'):
            value = json.loads(path.read_text(encoding='utf-8'))
            owner = (value.get('_result_seal') or {}).get('owner') or {}
            if ((identity and value.get('expected_identity_id') == identity)
                    or owner.get('launch_attempt') == launch_attempt):
                raise ValueError('Prepared worker has immutable brief authority')
    except (OSError, ValueError, TypeError, AttributeError):
        raise SeatError('Prepared replacement has bound work or unreadable evidence; repair is unavailable.') from None
    return receipt


def repair(manager, source_provenance, context_key, *, binding, preparation_attempt,
           dispatch_id, confirmation=None):
    from runtime_adoption import recover_prepared_context
    from turn_events import event_id
    try:
        event_id(preparation_attempt)
        event_id(dispatch_id)
    except ValueError:
        raise SeatError('Repair requires exact preparation and reserved dispatch identifiers.') from None
    _, fingerprint, base, metadata, key = scope(source_provenance, context_key, binding)
    with manager.lock:
        if manager.closed.is_set():
            raise SeatError('Server is shutting down; no replacement can launch.')
        attempt = manager.attempts.get(key)
        if attempt:
            validate_record(manager, key, attempt, metadata, context_key, fingerprint)
            if attempt.get('retried_from') == preparation_attempt:
                return manager._replacement_context_view(key)
            if attempt['id'] != preparation_attempt:
                raise SeatError('Prepared launch changed; refresh before repairing.')
            receipt = _unused(manager, attempt['snapshot'].parent, attempt.get('identity_id'), attempt['id'])
            if (attempt.get('state') not in ('failed', 'action_required', 'stopped')
                    and receipt.get('state') not in ('failed', 'action_required', 'stopped')):
                raise SeatError('This preparation has not failed; repair cannot replace a healthy context.')
            process = attempt.get('worker_process') or attempt.get('process')
            if process and process.poll() is None:
                if confirmation is None:
                    return dict(manager._view(attempt), key=key, launch_attempt=attempt['id'],
                                state='blocked', clean_context=False, reason='preparation_confirmation_required')
                if (not isinstance(confirmation, dict) or set(confirmation) != {'confirm', 'launch_attempt'}
                        or confirmation['confirm'] is not True or confirmation['launch_attempt'] != attempt['id']):
                    raise SeatError('Confirm the exact failed preparation before requesting its exit.')
                if base['seat']['adapter'] == 'cli':
                    instance = next((item for item in manager.registry.get_all().values()
                                     if item.get('base') == attempt['base']), None)
                    ended = bool(instance and manager.terminate_owned(instance['identity_id'], attempt['id'])['local_ended'])
                else:
                    ended = manager._end_api_preparation(attempt, confirmation)
                if not ended:
                    return {'state': 'blocked', 'clean_context': False, 'launch_attempt': attempt['id'],
                            'reason': 'prepared_client_exit_unverified', 'key': key}
            # A shim poll or a receipt alone never proves a spawned worker ended.
            ended = attempt.get('process') is None and manager._retry_preparation_exit_proven(attempt)
            if not ended and base['seat']['adapter'] == 'openai-compatible':
                ended = bool((attempt.get('verified_api_exit') or {}).get('local_ended') is True
                             and attempt['verified_api_exit'].get('launch_attempt') == attempt['id'])
            if not ended:
                effective = manager._provenance_effective(attempt['effective'])
                frozen_base = manager._provenance_effective(attempt['context_base_effective'])
                provenance = {'key': key, 'launch_attempt': attempt['id'], 'identity_id': attempt.get('identity_id'),
                              'effective': effective, 'fresh_base_effective': frozen_base}
                provenance['fingerprint'] = hashlib.sha256(json.dumps(
                    {'effective': effective, 'fresh_base_effective': frozen_base}, sort_keys=True).encode('utf-8')).hexdigest()
                ended = manager.participant_exit_proof(provenance, dispatch_id).get('local_ended') is True
            if not ended:
                return {'state': 'blocked', 'clean_context': False, 'launch_attempt': attempt['id'],
                        'reason': 'prepared_client_exit_unverified', 'key': key}
            history = deepcopy(attempt.get('preparation_history', []))
            history.append({'launch_attempt': attempt['id'], 'context_id': attempt.get('context_id')})
            manager._release(attempt)
        else:
            cold = recover_prepared_context(manager, key, context_key, fingerprint, metadata, preparation_attempt)
            if not cold:
                raise SeatError('No owned preparation matches this repair; no initial launch was started.')
            if not cold['replace']:
                return cold['view']
            from runtime_adoption import _launch_record
            item = _launch_record(manager, manager.store.path.parent / 'api_seat_runtime' / preparation_attempt / 'config.json')
            receipt_path = item['path'].with_name('receipt.json')
            receipt = json.loads(receipt_path.read_text(encoding='utf-8')) if receipt_path.exists() else {}
            _unused(manager, item['path'].parent, receipt.get('identity_id'), preparation_attempt)
            history = cold['preparation_history']
        context_id = uuid.uuid4().hex
        fresh = deepcopy(base)
        cli = fresh['seat']['adapter'] == 'cli'
        if cli:
            from cli_seats import build_fresh_context_args
            fresh['provider']['cli_args'] = list(fresh['provider'].get('cli_args', [])) + build_fresh_context_args(fresh['provider'], context_id)
        manager._launch_effective(key, fresh, launch_metadata={
            **metadata, 'context_key': context_key, 'context_source_fingerprint': fingerprint,
            'context_id': context_id, 'retried_from': preparation_attempt, 'preparation_history': history,
            'verification_basis': 'verified_fresh_launch_contract' if cli else 'isolated_request_packet'})
        return manager._replacement_context_view(key)
