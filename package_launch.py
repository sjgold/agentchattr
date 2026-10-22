"""Frozen team selections and fresh preflight readiness, separate from review sessions."""
from copy import deepcopy
import hashlib
import json
import time
import uuid

from api_seats import SeatError, atomic_json, package_revision
from launcher import startup_lock


def _choices(values, known, label):
    if values is None:
        return []
    if (not isinstance(values, list) or any(not isinstance(v, str) for v in values)
            or len(values) != len(set(values)) or any(v not in known for v in values)):
        raise SeatError(f'{label} must contain unique saved seat IDs.')
    return list(values)


def launch_package(manager, package_id, revision, restart_seats=None, omitted_seats=None):
    with manager.lock, startup_lock(manager.store.path.with_suffix('.lock'), time.monotonic() + 10):
        if manager.closed.is_set():
            raise SeatError('Server is shutting down; no new team can launch.')
        package = manager.store.package(package_id)
        if not isinstance(revision, str) or revision != package_revision(package):
            raise SeatError('Saved team changed. Reload the saved package before launching.')
        known = {seat['id'] for seat in package['seats']}
        omitted = _choices(omitted_seats, known, 'Omitted seats')
        restart = _choices(restart_seats, known, 'Restart seats')
        if not known - set(omitted):
            raise SeatError('Choose at least one seat for this launch.')
        if set(omitted) & set(restart):
            raise SeatError('A seat cannot be restarted and omitted in the same launch.')
        selection = {'selection_id': uuid.uuid4().hex, 'package': deepcopy(package),
                     'revision': revision, 'omitted_seats': omitted, 'attempts': {}, 'errors': {}}
        path = manager.store.path.parent / 'package_selections' / (selection['selection_id'] + '.json')
        # No processes are started if the initial provenance write fails.
        atomic_json(path, selection)
        manager.package_selections[package_id] = selection
        for seat in package['seats']:
            seat_id = seat['id']
            if seat_id in omitted:
                continue
            key = package_id + '/' + seat_id
            try:
                result = manager.launch(package_id, seat_id, restart=seat_id in restart)
                selection['attempts'][seat_id] = result.get('attempt')
            except (SeatError, OSError) as exc:
                previous = manager.attempts.get(key, {})
                selection['attempts'][seat_id] = previous.get('id')
                selection['errors'][seat_id] = str(exc) if isinstance(exc, SeatError) else 'Seat launch failed. Check local settings and retry this seat.'
        try:
            atomic_json(path, selection)
        except OSError:
            # Preserve running peers and expose the failed receipt; do not
            # claim the incomplete record proves a ready team.
            selection['persistence_error'] = True
        return package_status(manager, package_id)


def package_status(manager, package_id):
    with manager.lock:
        current = manager.store.package(package_id)
        current_revision = package_revision(current)
        selection = manager.package_selections.get(package_id)
        if selection is None:
            return {'state': 'not_started', 'ready': False, 'selection_id': None,
                    'revision': current_revision, 'current_revision': current_revision,
                    'omitted_seats': [], 'seats': {}, 'error': None}
        views = {}
        for seat in selection['package']['seats']:
            seat_id = seat['id']
            if seat_id in selection['omitted_seats']:
                continue
            key = package_id + '/' + seat_id
            attempt = manager.attempts.get(key)
            try:
                view = manager._inspect(key) if attempt else {'state': 'not_started', 'attempt': None}
                if seat_id in selection['errors']:
                    view = {**view, 'state': 'action_required', 'error': selection['errors'][seat_id]}
                elif not attempt or attempt['id'] != selection['attempts'].get(seat_id):
                    view = {**view, 'state': 'action_required', 'error': 'This seat has a different launch attempt. Launch the team again to check it.'}
                else:
                    effective = manager._effective(seat)
                    fingerprint = hashlib.sha256(json.dumps(effective, sort_keys=True).encode()).hexdigest()
                    if attempt['fingerprint'] != fingerprint:
                        view = {**view, 'state': 'action_required', 'error': 'Running settings changed. Choose explicit restart for this seat.'}
            except (SeatError, OSError):
                view = {'state': 'action_required', 'attempt': attempt.get('id') if attempt else None,
                        'error': 'This seat could not be verified. Check its settings and retry.'}
            views[seat_id] = view
        error = None
        if selection['revision'] != current_revision:
            error = 'Saved team changed. Launch the current saved package before continuing.'
        elif selection.get('persistence_error'):
            error = 'Team launch receipt could not be saved. Check permissions and launch the team again.'
        ready = bool(views) and not error and all(view['state'] == 'ready' for view in views.values())
        return {'selection_id': selection['selection_id'], 'revision': selection['revision'],
                'current_revision': current_revision, 'omitted_seats': list(selection['omitted_seats']),
                'seats': views, 'ready': ready, 'error': error,
                'state': 'ready' if ready else ('starting' if not error and views and
                    all(view['state'] in ('starting', 'ready') for view in views.values()) else 'action_required')}


def continue_package(manager, package_id, selection_id):
    with manager.lock, startup_lock(manager.store.path.with_suffix('.lock'), time.monotonic() + 10):
        state = package_status(manager, package_id)
        if not isinstance(selection_id, str) or selection_id != state['selection_id'] or not state['ready']:
            raise SeatError('The current selected team is not ready. Refresh its checks and resolve the listed seats before continuing.')
        return {'selection_id': selection_id, 'url': '/?package_launch=' + selection_id}
