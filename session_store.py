"""Session store — persists active session runs to JSON."""

import json
import time
import threading
import logging
from copy import deepcopy
from pathlib import Path

from api_seats import atomic_json

log = logging.getLogger(__name__)


class SessionStore:
    def __init__(self, path: str, templates_dir: str | None = None, capacity_policy=None):
        from session_capacity import capacity_policy as validate_capacity
        self._capacity_policy = validate_capacity(capacity_policy)
        self._path = Path(path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._sessions: list[dict] = []
        self._next_id = 1
        self._lock = threading.Lock()
        self._callbacks: list = []
        self._templates: dict[str, dict] = {}
        from review_brief import BriefStore
        self.briefs = BriefStore(self._path.parent)
        self._load()

        # Warn about legacy file
        legacy = self._path.parent / "sessions.json"
        if legacy.exists() and legacy != self._path:
            log.info("Ignoring legacy sessions.json; Sessions uses %s", self._path.name)

        if templates_dir:
            self._load_templates(Path(templates_dir))

        # Load custom (user/agent-created) templates
        custom_path = self._path.parent / "custom_templates.json"
        if custom_path.exists():
            try:
                custom = json.loads(custom_path.read_text("utf-8"))
                for tmpl in (custom if isinstance(custom, list) else []):
                    tid = tmpl.get("id", "")
                    if tid:
                        tmpl["is_custom"] = True
                        self._templates[tid] = tmpl
                        log.info("Loaded custom template: %s", tid)
            except (json.JSONDecodeError, KeyError) as exc:
                log.warning("Failed to load custom templates: %s", exc)

    # --- Persistence ---

    def _load(self):
        if not self._path.exists():
            return
        try:
            raw = json.loads(self._path.read_text("utf-8"))
            if isinstance(raw, list):
                self._sessions = raw
                if self._sessions:
                    self._next_id = max(s["id"] for s in self._sessions) + 1
        except (json.JSONDecodeError, KeyError):
            self._sessions = []

    def _save(self):
        atomic_json(self._path, self._sessions)

    # --- Templates ---

    def _load_templates(self, directory: Path):
        if not directory.exists():
            log.warning("Session templates directory not found: %s", directory)
            return
        for f in sorted(directory.glob("*.json")):
            try:
                tmpl = json.loads(f.read_text("utf-8"))
                tid = tmpl.get("id", f.stem)
                tmpl["id"] = tid
                tmpl.setdefault("is_custom", False)
                self._templates[tid] = tmpl
                log.info("Loaded session template: %s", tid)
            except (json.JSONDecodeError, KeyError) as exc:
                log.warning("Failed to load template %s: %s", f.name, exc)

    def get_templates(self) -> list[dict]:
        return list(self._templates.values())

    @property
    def capacity_policy(self):
        return deepcopy(self._capacity_policy)

    def get_template(self, template_id: str) -> dict | None:
        return self._templates.get(template_id)

    def save_custom_template(self, tmpl: dict) -> dict:
        from review_brief import BriefError
        errors = validate_session_template(tmpl, self._capacity_policy)
        if errors:
            raise BriefError('; '.join(errors))
        custom_path = self._path.parent / "custom_templates.json"
        custom = []
        if custom_path.exists():
            try:
                custom = json.loads(custom_path.read_text("utf-8"))
            except (json.JSONDecodeError, KeyError):
                custom = []

        saved = dict(tmpl)
        saved["is_custom"] = True
        custom = [t for t in custom if t.get("id") != saved.get("id")]
        custom.append(saved)
        custom_path.write_text(json.dumps(custom, indent=2, ensure_ascii=False) + "\n", "utf-8")
        self._templates[saved["id"]] = saved
        return saved

    def delete_custom_template(self, template_id: str) -> bool:
        tmpl = self._templates.get(template_id)
        if not tmpl or not tmpl.get("is_custom"):
            return False

        custom_path = self._path.parent / "custom_templates.json"
        custom = []
        if custom_path.exists():
            try:
                custom = json.loads(custom_path.read_text("utf-8"))
            except (json.JSONDecodeError, KeyError):
                custom = []

        new_custom = [t for t in custom if t.get("id") != template_id]
        if len(new_custom) != len(custom):
            custom_path.write_text(json.dumps(new_custom, indent=2, ensure_ascii=False) + "\n", "utf-8")

        self._templates.pop(template_id, None)
        return True

    # --- Callbacks ---

    def on_change(self, callback):
        """Register a callback(action, session) on any change.
        action: 'create', 'update', 'complete', 'interrupt'."""
        self._callbacks.append(callback)

    def _fire(self, action: str, session: dict):
        for cb in self._callbacks:
            try:
                cb(action, deepcopy(session))
            except Exception:
                pass

    # --- Session lifecycle ---

    def create(self, template_id: str, channel: str, cast: dict,
               started_by: str, goal: str = "", input_text: str = "", rules_snapshot=None,
               participant_bindings=None, recovery_policy=None, *, source_file=None) -> dict | None:
        """Create and persist a new session run."""
        tmpl = self._templates.get(template_id)
        if not tmpl:
            return None
        from review_brief import BriefError, freeze_inputs
        from turn_recovery import recovery_policy as validate_policy
        policy = validate_policy(recovery_policy)
        frozen = freeze_inputs(tmpl, goal, input_text, rules_snapshot, capacity_policy=self._capacity_policy, source_file=source_file)
        if (not isinstance(cast, dict) or any(not isinstance(k, str) or not isinstance(v, str) or not v for k, v in cast.items())
                or set(cast) != set(tmpl['roles'])):
            raise BriefError('Assign every design role to a named participant before Start.')

        with self._lock:
            # One active session per channel
            for s in self._sessions:
                if s.get("channel") == channel and (s.get("state") in ("active", "waiting", "paused", "awaiting_input", "prepared", "stalled", "retrying")
                        or (s.get('state') == 'interrupted' and s.get('restart_recovery'))):
                    return None

            session = {
                "id": self._next_id,
                "template_id": template_id,
                "template_name": tmpl.get("name", template_id),
                "channel": channel,
                "cast": deepcopy(cast),
                "cast_snapshot": deepcopy(cast),
                "participant_bindings": deepcopy(participant_bindings or {}),
                "state": "active",
                "current_phase": 0,
                "current_turn": 0,
                "started_by": started_by,
                "started_at": time.time(),
                "updated_at": time.time(),
                "last_message_id": None,
                "output_message_id": None,
                **frozen,
                "result_message_ids": [],
                "completion_protocol": 1,
                "active_invocation": None,
                "admitted_events": [],
                "continuation_context": [],
                "dispatch_eligible": True,
                "quarantined_events": [],
                "recovery_policy": policy,
                "turn_recovery": None,
                "superseded_attempts": [],
                "retry_requests": {},
            }
            self._next_id += 1
            self._sessions.append(session)
            try:
                self._save()
            except OSError:
                self._sessions.pop()
                self._next_id -= 1
                raise

        self._fire("create", session)
        return deepcopy(session)

    def get(self, session_id: int) -> dict | None:
        with self._lock:
            for s in self._sessions:
                if s["id"] == session_id:
                    return deepcopy(s)
            return None

    def get_active(self, channel: str) -> dict | None:
        """Get the active/waiting/paused session for a channel."""
        with self._lock:
            for s in self._sessions:
                if s.get("channel") == channel and (s.get("state") in ("active", "waiting", "paused", "awaiting_input", "stalled", "retrying")
                        or (s.get('state') == 'interrupted' and s.get('restart_recovery'))):
                    return deepcopy(s)
            return None

    def list_all(self, channel: str | None = None) -> list[dict]:
        with self._lock:
            result = deepcopy(self._sessions)
        if channel:
            result = [s for s in result if s.get("channel") == channel]
        return result

    def advance_turn(self, session_id: int, message_id: int | None = None) -> dict | None:
        """Advance to the next turn within the current phase."""
        with self._lock:
            session = self._find(session_id)
            if not session or session["state"] not in ("active", "waiting"):
                return None
            session["current_turn"] += 1
            session["state"] = "active"
            session["updated_at"] = time.time()
            if message_id is not None:
                session["last_message_id"] = message_id
                session.setdefault('result_message_ids', []).append(message_id)
            self._save()
            result = deepcopy(session)
        self._fire("update", result)
        return result

    def _event_update(self, session_id, change, action='update', *, skip_if_unchanged=False):
        """Commit one admission transaction, rolling back memory on any failure."""
        from turn_events import EventConflict
        with self._lock:
            session = self._find(session_id)
            if not session or session.get('completion_protocol') != 1:
                raise EventConflict('Session has no explicit completion protocol; legacy history is read-only.')
            before = deepcopy(self._sessions)
            try:
                change(session)
                if skip_if_unchanged and self._sessions == before:
                    return deepcopy(session)
                session['updated_at'] = time.time()
                self._save()
                result = deepcopy(session)
            except Exception:
                self._sessions = before
                raise
        self._fire(action, result)
        return result

    def bind_invocation(self, session_id, envelope, dispatch_id, *, human=False, now=None):
        from turn_events import EventConflict
        def bind(session):
            if session['state'] != 'active' or session.get('active_invocation'):
                raise EventConflict('A current invocation is already bound or this session is not active.')
            session['active_invocation'] = self._invocation(session, envelope, dispatch_id, human, now)
            session['state'] = 'waiting'
            session['waiting_on'] = envelope['expected_agent']
        return self._event_update(session_id, bind)

    def bind_missing_participant(self, session_id, envelope, dispatch_id, *, now=None):
        """Reserve an undelivered turn, without creating a review brief owner."""
        from turn_events import EventConflict
        import uuid
        at = time.time() if now is None else now
        def bind(session):
            if session['state'] != 'active' or session.get('active_invocation') or session.get('stop_id'):
                raise EventConflict('This missing participant no longer owns the current turn.')
            invocation = self._invocation(session, envelope, dispatch_id, False, at)
            invocation['intent_only'] = True
            session.update(active_invocation=invocation, state='stalled', waiting_on=envelope['expected_agent'])
            session['turn_recovery'] = {'checkpoint_id': uuid.uuid4().hex, 'attempt_id': invocation['attempt_id'],
                'turn_id': invocation['turn_id'], 'dispatch_id': dispatch_id, 'first_at': at, 'actions': [],
                'recoverable_result': False, 'reason': 'disconnected', 'status': 'stalled',
                'last_event': {'state': 'not_delivered', 'at': at}}
        return self._event_update(session_id, bind)

    @staticmethod
    def _invocation(session, envelope, dispatch_id, human, now):
        invocation = {key: deepcopy(envelope[key]) for key in (
            'brief_id', 'run_id', 'turn_id', 'attempt_id', 'input_revision',
            'expected_agent', 'expected_identity_id', 'phase_index', 'turn_index', 'role')}
        invocation.update(dispatch_id=dispatch_id, consumed=False, human=human)
        if not human:
            from turn_recovery import recovery_policy
            created = time.time() if now is None else now
            binding = session.get('participant_bindings', {}).get(envelope['role'], {})
            policy = recovery_policy(binding.get('recovery_policy') or session.get('recovery_policy'))
            invocation['monitoring'] = {'policy': policy, 'created_at': created,
                'ack_deadline': created + policy['ack_timeout'], 'acknowledged_at': None,
                'response_deadline': None, 'last_event': {'state': 'bound', 'at': created}}
        return invocation

    def settle_bound_retry(self, session_id, request_id, envelope, dispatch_id, *, queued, now):
        """Repair bookkeeping for already-sealed authority, never create work."""
        from turn_events import EventConflict
        import uuid
        def settle(session):
            pending = session.get('pending_retry')
            if (session.get('stop_id') or not pending or pending['request_id'] != request_id
                    or pending['new_brief_id'] != envelope['brief_id']
                    or pending['new_attempt_id'] != envelope['attempt_id']
                    or pending['new_dispatch_id'] != dispatch_id or envelope['run_id'] != session['run_id']
                    or envelope['input_revision'] != session['input_revision']
                    or session['participant_bindings'][envelope['role']]['identity_id'] != envelope['expected_identity_id']):
                raise EventConflict('Sealed retry authority no longer matches this turn.')
            invocation = session.get('active_invocation')
            if invocation is None:
                invocation = self._invocation(session, envelope, dispatch_id, False, pending['requested_at'])
                session['active_invocation'] = invocation
            if (invocation['attempt_id'] != envelope['attempt_id'] or invocation['dispatch_id'] != dispatch_id
                    or invocation['brief_id'] != envelope['brief_id'] or invocation.get('consumed')):
                raise EventConflict('Another invocation occupies this sealed turn.')
            session['waiting_on'] = envelope['expected_agent']
            interrupted = session.get('restart_recovery') and session.get('dispatch_eligible') is False
            if queued:
                session['state'] = 'interrupted' if interrupted else 'waiting'
                if session.get('turn_recovery', {}).get('status') == 'retrying':
                    session['turn_recovery'].update(status='resolved', resolved_by='retry',
                                                   new_attempt_id=invocation['attempt_id'])
            else:
                session['state'] = 'interrupted' if interrupted else 'stalled'
                session['turn_recovery'] = {'checkpoint_id': uuid.uuid4().hex, 'attempt_id': invocation['attempt_id'],
                    'turn_id': invocation['turn_id'], 'dispatch_id': dispatch_id, 'first_at': now,
                    'actions': [], 'recoverable_result': False, 'reason': 'local_delivery_failure',
                    'last_event': {'state': 'publication_failed', 'at': now}, 'status': 'stalled'}
            session.pop('pending_retry')
        return self._event_update(session_id, settle)

    def stop_run(self, session_id, reason):
        import uuid
        def stop(session):
            if session.get('stop_id'):
                return
            session.update(dispatch_eligible=False, stop_id=uuid.uuid4().hex,
                           stopped_at=time.time(), stop_reason=reason, state='stopping')
        return self._event_update(session_id, stop)

    def prepare_restart(self, parent_id, input_text, request_id, *, participant_bindings=None, intent_fingerprint=None):
        """Atomically link a single immutable prepared replacement to its parent."""
        import re
        from review_brief import BriefError, freeze_inputs, _revision
        from turn_events import EventConflict
        if not isinstance(request_id, str) or not re.fullmatch(r'[a-zA-Z0-9_.-]{1,128}', request_id):
            raise BriefError('Corrected restart requires a stable request ID.')
        with self._lock:
            parent = self._find(parent_id)
            if (not parent or parent.get('completion_protocol') != 1 or not parent.get('stop_id')
                    or parent['state'] not in ('stopped', 'unresolved')):
                raise EventConflict('Stop the original run and resolve its stopping state before preparing a replacement.')
            from session_capacity import LEGACY_POLICY
            file_origin = 'document' in parent['input_snapshot']
            if file_origin:
                from review_brief import _validated_document
                _validated_document(parent['input_snapshot']['document'], parent['input_snapshot']['text'])
            frozen = freeze_inputs(parent['design_snapshot'], parent['goal'], input_text, parent['rules_snapshot'],
                                   capacity_policy=parent.get('capacity_policy') or LEGACY_POLICY)
            unchanged = frozen['input_revision'] == parent['input_revision']
            if file_origin:
                def newlines(text):
                    return text.replace('\r\n', '\n').replace('\r', '\n')
                unchanged = newlines(parent['input_snapshot']['text']) == newlines(input_text)
            if unchanged:
                raise BriefError('The source is unchanged. Use turn Retry for the same document; correct the source before restarting.')
            bindings = deepcopy(parent['participant_bindings'] if participant_bindings is None else participant_bindings)
            if not isinstance(bindings, dict) or set(bindings) != set(parent['cast']):
                raise BriefError('Retain or explicitly replace every role assignment.')
            fingerprint = _revision({'input_revision': frozen['input_revision'], 'bindings': bindings})
            if parent.get('replaced_by_run_id'):
                child = next((s for s in self._sessions if s['run_id'] == parent['replaced_by_run_id']), None)
                matches = (child and (child.get('intent_fingerprint') == intent_fingerprint
                           if intent_fingerprint and child.get('intent_fingerprint') else
                           child.get('preparation_fingerprint') == fingerprint))
                if child and child.get('request_id') == request_id and matches:
                    return deepcopy(child)
                raise EventConflict('This run already has a replacement; continue or stop that replacement before correcting again.')
            if any(s.get('request_id') == request_id for s in self._sessions):
                raise EventConflict('This request ID belongs to a different replacement.')
            child = dict(frozen, id=self._next_id, template_id=parent['template_id'],
                template_name=parent['template_name'], channel=parent['channel'],
                cast=deepcopy(parent['cast']), cast_snapshot=deepcopy(parent['cast_snapshot']),
                participant_bindings=bindings, state='prepared', prepared=True, dispatch_eligible=False,
                stop_id=None, parent_run_id=parent['run_id'], parent_session_id=parent_id,
                lineage_root_id=parent.get('lineage_root_id', parent['run_id']), request_id=request_id,
                preparation_fingerprint=fingerprint, completion_protocol=1, current_phase=0, current_turn=0,
                intent_fingerprint=intent_fingerprint,
                started_by=parent['started_by'], started_at=time.time(), updated_at=time.time(),
                result_message_ids=[], admitted_events=[], quarantined_events=[], continuation_context=[],
                active_invocation=None, last_message_id=None, output_message_id=None,
                recovery_policy=deepcopy(parent.get('recovery_policy')), turn_recovery=None,
                superseded_attempts=[], retry_requests={})
            before, before_id = deepcopy(self._sessions), self._next_id
            try:
                parent['replaced_by_run_id'] = child['run_id']
                parent['replaced_by_session_id'] = child['id']
                self._sessions.append(child)
                self._next_id += 1
                self._save()
            except Exception:
                self._sessions, self._next_id = before, before_id
                raise
            result = deepcopy(child)
        self._fire('update', result)
        return result

    def stage_contexts(self, child_id, context_request_id, fingerprint, bindings):
        from turn_events import EventConflict
        def stage(session):
            if session['state'] != 'prepared' or session.get('stop_id') or not session.get('parent_run_id'):
                raise EventConflict('Only an un-stopped prepared child can repair contexts.')
            requests = session.setdefault('context_requests', {})
            if context_request_id in requests:
                raise EventConflict('Context request was already staged; inspect its current status.')
            session.setdefault('reassigned_contexts_history', []).append({
                'context_request_id': context_request_id, 'at': time.time(),
                'participant_bindings': deepcopy(session['participant_bindings']),
                'preparation_contexts': deepcopy(session.get('preparation_contexts', {}))})
            requests[context_request_id] = {'fingerprint': fingerprint, 'at': time.time()}
            session['current_context_request_id'] = context_request_id
            session['participant_bindings'] = deepcopy(bindings)
            session['preparation_contexts'] = {}
        return self._event_update(child_id, stage)

    def activate_restart(self, child_id, participant_bindings=None):
        from turn_events import EventConflict
        def activate(session):
            if session.get('state') != 'prepared' or session.get('stop_id') or not session.get('parent_run_id'):
                raise EventConflict('Only an un-stopped prepared replacement can start.')
            if participant_bindings is not None:
                if not isinstance(participant_bindings, dict) or set(participant_bindings) != set(session['cast']):
                    raise EventConflict('Every corrected role needs a prepared participant binding.')
                session['participant_bindings'] = deepcopy(participant_bindings)
                for role, binding in participant_bindings.items():
                    if binding.get('name'):
                        session['cast'][role] = binding['name']
                session['cast_snapshot'] = deepcopy(session['cast'])
            session.update(state='active', dispatch_eligible=True, prepared=False)
        return self._event_update(child_id, activate)

    def stop_outcome(self, session_id, state, receipts):
        from turn_events import EventConflict
        def update(session):
            if not session.get('stop_id'):
                raise EventConflict('This run has no Stop fence.')
            session.update(state=state, cancellation_receipts=deepcopy(receipts))
        return self._event_update(session_id, update)

    def quarantine_event(self, session_id, event, instance, *, reason='stopped_run'):
        def quarantine(session):
            record = deepcopy(event)
            record.update(quarantined_at=time.time(), provenance=event.get('provenance', 'authenticated_seat'),
                          expected_identity_id=instance['identity_id'], reason=reason)
            records = session.setdefault('quarantined_events', [])
            records.append(record)
            while len(records) > 64 or sum(len(e['content'].encode('utf-8')) for e in records) > 8 * 1024 * 1024:
                records.pop(0)
                session['quarantine_evicted'] = session.get('quarantine_evicted', 0) + 1
        return self._event_update(session_id, quarantine)

    def admit_event(self, session_id, event, instance, *, human=False):
        return self._admit_event(session_id, event, instance, human=human)

    @staticmethod
    def _participant_checkpoint(session, checkpoint_id, attempt_id):
        """Validate the current failed contribution without inferring process exit."""
        from turn_events import EventConflict
        invocation = session.get('active_invocation')
        checkpoint = session.get('turn_recovery')
        if (session.get('stop_id') or session.get('replaced_by_run_id')
                or session.get('pending_retry') or session.get('pending_replacement')
                or session['state'] not in ('stalled', 'waiting', 'interrupted')
                or not invocation or invocation.get('consumed') is not False
                or invocation.get('human') is not False or not checkpoint
                or invocation['attempt_id'] != attempt_id
                or checkpoint.get('checkpoint_id') != checkpoint_id
                or checkpoint.get('attempt_id') != attempt_id
                or checkpoint.get('status') not in ('stalled', 'waiting')
                or any(item.get('attempt_id') == attempt_id
                       for item in session.get('superseded_attempts', []))):
            raise EventConflict('Participant recovery belongs to a different, completed or stopped turn.')
        phase_index, turn_index = session['current_phase'], session['current_turn']
        phase = session['design_snapshot']['phases'][phase_index]
        if (invocation['run_id'] != session['run_id']
                or invocation['input_revision'] != session['input_revision']
                or invocation['phase_index'] != phase_index or invocation['turn_index'] != turn_index
                or invocation['role'] != phase['participants'][turn_index]
                or invocation['turn_id'] != f"{session['run_id']}:{phase_index}:{turn_index}"):
            raise EventConflict('Participant recovery does not match this logical turn.')
        return invocation

    def replace_participant(self, session_id, *, checkpoint_id, attempt_id, request_id,
                            target_provenance, boot_id, reason='', submitted_by='operator', now=None):
        from participant_replacement_store import replace_participant
        return replace_participant(self, session_id, checkpoint_id=checkpoint_id, attempt_id=attempt_id,
            request_id=request_id, target_provenance=target_provenance, boot_id=boot_id,
            reason=reason, submitted_by=submitted_by, now=now)

    def bind_replacement(self, session_id, request_id, context, provenance, *, boot_id):
        from participant_replacement_store import bind_replacement
        return bind_replacement(self, session_id, request_id, context, provenance, boot_id=boot_id)

    def skip_participant(self, session_id, *, checkpoint_id, attempt_id, request_id,
                         reason, confirm_skip, submitted_by='operator', now=None):
        """Record missing work and fence its attempt atomically, without actuating it."""
        import math
        import uuid
        from turn_events import EventConflict, EventValidationError, event_id
        if type(session_id) is not int or session_id <= 0:
            raise EventValidationError('Session ID must be a positive integer.')
        for identifier in (checkpoint_id, attempt_id, request_id):
            event_id(identifier)
        if (confirm_skip is not True or not isinstance(reason, str) or not reason.strip()
                or len(reason) > 256 or '\0' in reason
                or not isinstance(submitted_by, str) or not submitted_by.strip()
                or len(submitted_by) > 80 or '\0' in submitted_by):
            raise EventValidationError('Confirm skipping this contribution with a reason of 1-256 characters.')
        try:
            reason.encode('utf-8')
            submitted_by.encode('utf-8')
        except UnicodeError:
            raise EventValidationError('Skip reason and operator name must be valid UTF-8.') from None
        requested_at = time.time() if now is None else now
        if (type(requested_at) not in (int, float) or not math.isfinite(requested_at)
                or requested_at < 0):
            raise EventValidationError('Skip time must be a finite nonnegative number.')
        intent = {'request_id': request_id, 'checkpoint_id': checkpoint_id, 'attempt_id': attempt_id,
                  'reason': reason, 'confirm_skip': True, 'submitted_by': submitted_by}

        def skip(session):
            previous = next((item for item in session.get('skipped_turns', [])
                             if item['request_id'] == request_id), None)
            if previous is not None:
                if previous['skip_request'] != intent:
                    raise EventConflict('Skip request ID was already used for a different decision.')
                return
            invocation = self._participant_checkpoint(session, checkpoint_id, attempt_id)
            record = {'request_id': request_id, 'checkpoint_id': checkpoint_id,
                      'role': invocation['role'], 'phase': session['current_phase'],
                      'turn': session['current_turn'], 'turn_id': invocation['turn_id'],
                      'run_id': session['run_id'], 'input_revision': session['input_revision'],
                      'attempt_id': invocation['attempt_id'], 'dispatch_id': invocation['dispatch_id'],
                      'seat_identity_id': invocation['expected_identity_id'],
                      'agent_name': invocation['expected_agent'], 'reason': reason,
                      'submitted_by': submitted_by, 'skipped_at': requested_at,
                      'projection_id': uuid.uuid4().hex, 'projected_message_id': None,
                      'is_output': bool(session['design_snapshot']['phases'][session['current_phase']].get('is_output')),
                      'skip_request': deepcopy(intent)}
            self._advance_skipped_turn(session, record)
        return self._event_update(session_id, skip, skip_if_unchanged=True)

    @staticmethod
    def _advance_skipped_turn(session, skip_record):
        """Lock-held skip transaction; missing work never enters admitted_events."""
        invocation = session['active_invocation']
        binding = session.get('participant_bindings', {}).get(invocation['role'], {})
        session.setdefault('superseded_attempts', []).append({
            **{key: invocation[key] for key in ('attempt_id', 'turn_id', 'dispatch_id', 'expected_identity_id')},
            'run_id': session['run_id'], 'input_revision': session['input_revision'],
            'superseded_at': skip_record['skipped_at'], 'reason': 'participant_skipped',
            'request_id': skip_record['request_id'],
            'old_transport': {'dispatch_id': invocation['dispatch_id'],
                'seat_identity_id': invocation['expected_identity_id'],
                'launch_provenance': deepcopy(binding.get('launch_provenance')),
                'resolved': False, 'resolved_at': None}})
        session.setdefault('skipped_turns', []).append(deepcopy(skip_record))
        session['turn_recovery'].update(status='resolved', resolved_by=skip_record['projection_id'])
        session['turn_recovery'].setdefault('actions', []).append({
            'action': 'skip', 'at': skip_record['skipped_at'], 'request_id': skip_record['request_id']})
        session['active_invocation'] = None
        session.pop('current_question', None)
        session['waiting_on'] = None
        phases = session['design_snapshot']['phases']
        phase = phases[session['current_phase']]
        session.setdefault('missing_output', False)
        if session['current_turn'] + 1 < len(phase['participants']):
            session['current_turn'] += 1
            session['state'] = 'active'
        elif session['current_phase'] + 1 < len(phases):
            session['current_phase'] += 1
            session['current_turn'] = 0
            session['state'] = 'active'
        else:
            session['state'] = 'complete'
            if skip_record['is_output']:
                session['missing_output'] = True

    def admit_selected_cli_event(self, session_id, snapshot, *, request_id, message_uid,
                                 snapshot_hash, checkpoint, kind='final',
                                 confirm_operator_attribution=False, submitted_by='operator'):
        """Internal selected-content admission and attempt fence in one transaction."""
        import re
        import uuid
        from cli_result_recovery import _current_session, _source, _snapshot_identity
        from turn_events import EventConflict, EventValidationError, event_id, validate_content, IDENTITY_FIELDS
        if type(session_id) is not int or session_id <= 0:
            raise EventValidationError('Session ID must be a positive integer.')
        event_id(request_id)
        checkpoint, snapshot = deepcopy(checkpoint), deepcopy(snapshot)
        if (not isinstance(checkpoint, dict)
                or set(checkpoint) != {'session_id', 'run_id', 'turn_id', 'attempt_id', 'input_revision'}
                or type(checkpoint['session_id']) is not int or checkpoint['session_id'] != session_id
                or not isinstance(checkpoint['turn_id'], str)
                or not isinstance(checkpoint['input_revision'], str)
                or not re.fullmatch('[0-9a-f]{64}', checkpoint['input_revision'])
                or not isinstance(snapshot_hash, str) or not re.fullmatch('[0-9a-f]{64}', snapshot_hash)
                or not isinstance(message_uid, str) or not message_uid
                or type(confirm_operator_attribution) is not bool
                or not isinstance(submitted_by, str) or not submitted_by.strip() or len(submitted_by) > 80):
            raise EventValidationError('Selected message decision is malformed.')
        event_id(checkpoint['run_id'])
        event_id(checkpoint['attempt_id'])
        uid, digest = _snapshot_identity(snapshot)
        validate_content(kind, snapshot.get('text'))
        if uid != message_uid or digest != snapshot_hash:
            raise EventConflict('Selected message changed since preview.')
        intent = {'request_id': request_id, 'checkpoint': checkpoint,
                  'message_id': snapshot['id'], 'message_uid': message_uid,
                  'snapshot_hash': snapshot_hash, 'kind': kind,
                  'confirm_operator_attribution': confirm_operator_attribution,
                  'submitted_by': submitted_by}

        def admit(session):
            previous = next((e for e in session.get('admitted_events', [])
                             if e.get('selected_request', {}).get('request_id') == request_id), None)
            if previous is not None:
                if previous['selected_request'] != intent:
                    raise EventConflict('Recovery request ID was already used for a different decision.')
                return
            _, invocation = _current_session(session, session_id)
            actual = {'session_id': session_id, 'run_id': session['run_id'],
                      **{key: invocation[key] for key in ('turn_id', 'attempt_id', 'input_revision')}}
            if actual != checkpoint:
                raise EventConflict('Session checkpoint has changed since preview.')
            attribution, source_attempt = _source(session, invocation, snapshot)
            if attribution == 'operator_attributed' and confirm_operator_attribution is not True:
                raise EventConflict('Confirm operator attribution for a message without complete turn metadata.')
            if any(e.get('source_message_uid') == uid for run in self._sessions
                   for e in run.get('admitted_events', [])):
                raise EventConflict('Message has already been used to complete a review turn.')
            now = time.time()
            session.setdefault('superseded_attempts', []).append({
                **{key: invocation[key] for key in ('attempt_id', 'turn_id', 'dispatch_id', 'expected_identity_id')},
                'run_id': session['run_id'], 'input_revision': session['input_revision'],
                'superseded_at': now, 'reason': 'superseded_by_operator_recovery', 'request_id': request_id,
                'selected_transport': {'dispatch_id': invocation['dispatch_id'],
                    'seat_identity_id': invocation['expected_identity_id'],
                    'launch_provenance': deepcopy(session['participant_bindings'][invocation['role']]['launch_provenance']),
                    'resolved': False, 'resolved_at': None}})
            record = {key: invocation[key] for key in IDENTITY_FIELDS}
            record.update(session_id=session_id, event_id=uuid.uuid4().hex, kind=kind,
                content=snapshot['text'], projected_message_id=None, accepted_at=now,
                sender=snapshot.get('sender'), expected_identity_id=invocation['expected_identity_id'],
                provenance='operator_selected_cli_result', submitted_by=submitted_by,
                source_message_id=snapshot['id'], source_message_uid=uid, snapshot_hash=digest,
                source_identity_id=snapshot['metadata']['seat_identity_id'], source_attempt_id=source_attempt,
                attribution=attribution, recovered_at=now, selected_request=deepcopy(intent))
            self._append_admission(session, record)
        return self._event_update(session_id, admit, skip_if_unchanged=True)

    def resolve_selected_transport(self, session_id, request_id, evidence):
        """Internal audit after genuine CLI exit proof, including unpublished work."""
        from turn_events import EventConflict, EventValidationError, event_id
        event_id(request_id)
        if (type(session_id) is not int or session_id <= 0 or not isinstance(evidence, dict)
                or evidence.get('local_ended') is not True
                or not isinstance(evidence.get('verification_basis'), str)
                or evidence['verification_basis'] not in {'observed_child_exit_and_ipc',
                    'durable_receipt_and_observed_absent', 'retained_native_handle_observed_end'}):
            raise EventValidationError('Exact verified CLI exit evidence is required.')
        event_id(evidence.get('dispatch_id'))
        event_id(evidence.get('launch_attempt'))
        proof = {key: evidence.get(key) for key in
                 ('dispatch_id', 'seat_identity_id', 'launch_attempt', 'verification_basis')}
        def resolve(session):
            fence = next((item for item in session.get('superseded_attempts', [])
                          if item.get('request_id') == request_id
                          and item.get('reason') == 'superseded_by_operator_recovery'), None)
            transport = (fence or {}).get('selected_transport')
            if (not transport or proof['dispatch_id'] != transport['dispatch_id']
                    or proof['seat_identity_id'] != transport['seat_identity_id']
                    or proof['launch_attempt'] != transport['launch_provenance'].get('launch_attempt')):
                raise EventConflict('CLI exit evidence does not match the selected transport.')
            if transport.get('resolved') is True:
                if transport.get('exit_proof') != proof:
                    raise EventConflict('Selected transport exit evidence changed.')
                return
            transport.update(resolved=True, resolved_at=time.time(), exit_proof=deepcopy(proof))
        return self._event_update(session_id, resolve, skip_if_unchanged=True)

    @staticmethod
    def _old_transport_proof(session, request_id, evidence):
        """Validate a copied audit without IO; also used before queue settlement."""
        from turn_events import EventConflict, EventValidationError, event_id
        event_id(request_id)
        if (not isinstance(session, dict) or not isinstance(evidence, dict)
                or evidence.get('local_ended') is not True
                or evidence.get('wrapper_status') not in ('observed_exited', 'absent')
                or not isinstance(evidence.get('verification_basis'), str)):
            raise EventValidationError('Verified worker and child exit evidence is required.')
        proof = {key: deepcopy(evidence.get(key)) for key in
                 ('local_ended', 'dispatch_id', 'seat_identity_id', 'launch_attempt',
                  'verification_basis', 'wrapper_status', 'child_exit_code', 'model_status')}
        for key in ('dispatch_id', 'seat_identity_id', 'launch_attempt'):
            event_id(proof[key])

        matches = [item for item in session.get('superseded_attempts', [])
                   if item.get('request_id') == request_id
                   and item.get('reason') in ('participant_replacement', 'participant_skipped')]
        if len(matches) != 1:
            raise EventConflict('The exact retired participant transport is unavailable.')
        transport = matches[0].get('old_transport') or {}
        provenance = transport.get('launch_provenance') or {}
        if (proof['dispatch_id'] != transport.get('dispatch_id')
                or proof['seat_identity_id'] != transport.get('seat_identity_id')
                or proof['launch_attempt'] != provenance.get('launch_attempt')):
            raise EventConflict('Exit evidence does not match the retired participant transport.')
        adapter = provenance.get('effective', {}).get('seat', {}).get('adapter')
        basis = proof['verification_basis']
        if adapter == 'cli':
            if (basis not in {'observed_child_exit_and_ipc', 'durable_receipt_and_observed_absent',
                              'retained_native_handle_observed_end'} or type(proof['child_exit_code']) is not int):
                raise EventValidationError('Verified CLI worker and child exit evidence is required.')
            canonical = {key: value for key, value in proof.items() if key != 'model_status'}
        elif adapter == 'openai-compatible':
            expected = {'all_bound_invocations_ended': 'ended', 'protocol_one_no_invocations': 'never_spawned'}
            if basis not in expected or proof['model_status'] != expected[basis]:
                raise EventValidationError('Verified API supervisor and model history exit is required.')
            canonical = {key: value for key, value in proof.items() if key != 'child_exit_code'}
        else:
            raise EventConflict('No managed participant lifecycle is bound to this audit.')
        if transport.get('resolved') is True and transport.get('exit_proof') != canonical:
            raise EventConflict('Retired participant exit evidence changed.')
        return transport, canonical

    def resolve_old_transport(self, session_id, request_id, evidence):
        """Record verified retired-worker lifetime, never a worker acknowledgement."""
        from turn_events import EventValidationError
        if type(session_id) is not int or session_id <= 0:
            raise EventValidationError('Session ID must be a positive integer.')
        def resolve(session):
            transport, canonical = self._old_transport_proof(session, request_id, evidence)
            if transport.get('resolved') is True:
                return
            transport.update(resolved=True, resolved_at=time.time(), exit_proof=deepcopy(canonical))
        return self._event_update(session_id, resolve, skip_if_unchanged=True)

    def admit_verified_saved_event(self, session_id, payload, *, submitted_by='operator'):
        """Internal ingress after private brief seal verification by the engine."""
        from result_outbox import _payload
        from turn_events import EventConflict, IDENTITY_FIELDS, EventValidationError
        payload = _payload(payload)
        if payload['session_id'] != session_id:
            raise EventConflict('Saved result belongs to another session.')
        if not isinstance(submitted_by, str) or not submitted_by.strip() or len(submitted_by) > 80:
            raise EventValidationError('Operator display name must contain 1-80 characters.')
        event = {key: payload[key] for key in (*IDENTITY_FIELDS, 'session_id', 'event_id', 'kind', 'content')}
        event.update(submitted_by=submitted_by, result_id=payload['result_id'],
                     result_launch_attempt=payload['launch_attempt'])
        return self._admit_event(session_id, event, None, saved_payload=payload)

    def _admit_event(self, session_id, event, instance, *, human=False, saved_payload=None):
        from turn_events import EventConflict, EventAccessError, IDENTITY_FIELDS, validate_content
        validate_content(event['kind'], event['content'])
        def admit(session):
            invocation = session.get('active_invocation')
            if not invocation:
                raise EventConflict('No current invocation can accept this event.')
            if (session['state'] not in ('active', 'waiting', 'stalled', 'interrupted') or session.get('stop_id') or invocation['consumed']
                    or any(event.get(key) != invocation.get(key) for key in IDENTITY_FIELDS)
                    or event['input_revision'] != session['input_revision']
                    or any(item['attempt_id'] == event['attempt_id'] for item in session.get('superseded_attempts', []))
                    or any(prior['event_id'] == event['event_id'] for run in self._sessions for prior in run.get('admitted_events', []))):
                raise EventConflict('Event is stale, duplicated, superseded or this session is not accepting results.')
            if saved_payload is not None:
                binding = session.get('participant_bindings', {}).get(invocation['role'], {})
                provenance = binding.get('launch_provenance') or {}
                if (invocation.get('human') or binding.get('kind') != 'agent'
                        or provenance.get('effective', {}).get('seat', {}).get('adapter') != 'openai-compatible'
                        or provenance.get('launch_attempt') != saved_payload['launch_attempt']
                        or saved_payload['seat_identity_id'] != invocation['expected_identity_id']
                        or saved_payload['dispatch_id'] != invocation['dispatch_id']):
                    raise EventAccessError('Saved API result does not belong to this original managed invocation.')
            elif human:
                if not invocation.get('human'):
                    raise EventAccessError('Operator results cannot impersonate an agent seat.')
            elif (invocation.get('human') or not isinstance(instance, dict)
                    or instance.get('identity_id') != invocation['expected_identity_id']):
                raise EventAccessError('This event belongs to another seat identity.')
            record = deepcopy(event)
            record.update(projected_message_id=None, accepted_at=time.time(),
                          sender=invocation['expected_agent'],
                          provenance=('verified_saved_api_result' if saved_payload is not None else
                                      'human_operator' if human else 'authenticated_seat'),
                          expected_identity_id=invocation['expected_identity_id'])
            self._append_admission(session, record)
        return self._event_update(session_id, admit)

    @staticmethod
    def _append_admission(session, record):
        """Apply shared final/question progression after the ingress has authorized it."""
        invocation = session['active_invocation']
        invocation['consumed'] = True
        if session.get('turn_recovery'):
            session['turn_recovery'].update(status='resolved', resolved_by=record['event_id'])
        phases = session['design_snapshot']['phases']
        phase = phases[session['current_phase']]
        record['is_output'] = bool(phase.get('is_output'))
        session['admitted_events'].append(record)
        if record['kind'] == 'question':
            session['state'] = 'awaiting_input'
            session['current_question'] = {'event_id': record['event_id'], 'text': record['content'],
                'asked_by': record['sender'], 'attempt_id': invocation['attempt_id']}
            return
        session['active_invocation'] = None
        session.pop('current_question', None)
        if session['current_turn'] + 1 < len(phase['participants']):
            session['current_turn'] += 1
            session['state'] = 'active'
        elif session['current_phase'] + 1 < len(phases):
            session['current_phase'] += 1
            session['current_turn'] = 0
            session['state'] = 'active'
        else:
            session['state'] = 'complete'

    def link_skip_projection(self, session_id, projection_id, message_id):
        from turn_events import EventConflict, EventValidationError
        if type(message_id) is not int or message_id < 0:
            raise EventValidationError('Projected message ID must be a nonnegative integer.')
        def link(session):
            record = next((item for item in session.get('skipped_turns', []) if item['projection_id'] == projection_id), None)
            if record is None or record['projected_message_id'] not in (None, message_id):
                raise EventConflict('Skipped-turn projection does not match.')
            record['projected_message_id'] = message_id
            if session.get('missing_output') and record == session['skipped_turns'][-1]:
                session['output_message_id'] = message_id
        return self._event_update(session_id, link, skip_if_unchanged=True)

    def link_event_projection(self, session_id, event_id, message_id):
        from turn_events import EventConflict
        def link(session):
            record = next((e for e in session['admitted_events'] if e['event_id'] == event_id), None)
            if record is None or record['projected_message_id'] not in (None, message_id):
                raise EventConflict('Accepted event projection does not match.')
            record['projected_message_id'] = message_id
            if record['kind'] == 'final':
                if message_id not in session['result_message_ids']:
                    session['result_message_ids'].append(message_id)
                session['last_message_id'] = message_id
                if record['is_output'] and session['state'] == 'complete':
                    session['output_message_id'] = message_id
        return self._event_update(session_id, link)

    def continue_question(self, session_id, question_event_id, answer):
        from turn_events import EventConflict, validate_content
        validate_content('final', answer)
        def resume(session):
            question = session.get('current_question')
            if session['state'] != 'awaiting_input' or not question or question['event_id'] != question_event_id:
                raise EventConflict('Only the current awaiting-input question can be continued.')
            session['continuation_context'].append({'question_event_id': question_event_id,
                'question': question['text'], 'answer': answer, 'projected_message_id': None})
            session['active_invocation'] = None
            session.pop('current_question', None)
            session['state'] = 'active'
        return self._event_update(session_id, resume)

    def link_continuation_projection(self, session_id, question_event_id, message_id):
        from turn_events import EventConflict
        def link(session):
            context = next((item for item in session['continuation_context']
                            if item['question_event_id'] == question_event_id), None)
            if context is None or context.get('projected_message_id') not in (None, message_id):
                raise EventConflict('Continuation projection does not match the saved answer.')
            context['projected_message_id'] = message_id
        return self._event_update(session_id, link)

    def resume_explicit(self, session_id):
        from turn_events import EventConflict
        def resume(session):
            if session['state'] != 'paused' or not session.get('active_invocation'):
                raise EventConflict('No paused invocation can be resumed.')
            session['state'] = 'waiting'
            monitoring = session['active_invocation'].get('monitoring')
            if monitoring and monitoring.get('paused_at') is not None:
                elapsed = max(0, time.time() - monitoring.pop('paused_at'))
                for key in ('ack_deadline', 'response_deadline'):
                    if monitoring.get(key) is not None:
                        monitoring[key] += elapsed
        return self._event_update(session_id, resume)

    def advance_phase(self, session_id: int, message_id: int | None = None) -> dict | None:
        """Advance to the next phase, resetting turn to 0."""
        with self._lock:
            session = self._find(session_id)
            if not session or session["state"] not in ("active", "waiting"):
                return None
            session["current_phase"] += 1
            session["current_turn"] = 0
            session["state"] = "active"
            session["updated_at"] = time.time()
            if message_id is not None:
                session["last_message_id"] = message_id
                session.setdefault('result_message_ids', []).append(message_id)
            self._save()
            result = deepcopy(session)
        self._fire("update", result)
        return result

    def set_waiting(self, session_id: int, agent: str) -> dict | None:
        """Mark session as waiting on a specific agent."""
        with self._lock:
            session = self._find(session_id)
            if not session:
                return None
            session["state"] = "waiting"
            session["waiting_on"] = agent
            session["updated_at"] = time.time()
            self._save()
            result = deepcopy(session)
        self._fire("update", result)
        return result

    def set_choice(self, session_id: int, message_id: int | None) -> dict | None:
        """Keep the current turn while its participant asks the human a question."""
        with self._lock:
            session = self._find(session_id)
            if not session or session["state"] not in ("active", "waiting", "paused", "awaiting_input"):
                return None
            session["choice_message_id"] = message_id
            if message_id is not None:
                session["last_choice_message_id"] = message_id
            session["updated_at"] = time.time()
            self._save()
            result = deepcopy(session)
        self._fire("update", result)
        return result

    def pause(self, session_id: int) -> dict | None:
        """Pause session (human interruption)."""
        with self._lock:
            session = self._find(session_id)
            if not session or session["state"] not in ("active", "waiting"):
                return None
            session["state"] = "paused"
            monitoring = (session.get('active_invocation') or {}).get('monitoring')
            if monitoring:
                monitoring['paused_at'] = time.time()
            session["updated_at"] = time.time()
            self._save()
            result = deepcopy(session)
        self._fire("update", result)
        return result

    def resume(self, session_id: int) -> dict | None:
        """Resume a paused session."""
        with self._lock:
            session = self._find(session_id)
            if not session or session["state"] != "paused":
                return None
            session["state"] = "active"
            session["updated_at"] = time.time()
            self._save()
            result = deepcopy(session)
        self._fire("update", result)
        return result

    def complete(self, session_id: int, output_message_id: int | None = None) -> dict | None:
        """Mark session as complete."""
        with self._lock:
            session = self._find(session_id)
            if not session:
                return None
            session["state"] = "complete"
            session["updated_at"] = time.time()
            if output_message_id is not None:
                session["output_message_id"] = output_message_id
            self._save()
            result = deepcopy(session)
        self._fire("complete", result)
        return result

    def interrupt(self, session_id: int, reason: str = "ended by user") -> dict | None:
        """End session early."""
        with self._lock:
            session = self._find(session_id)
            if not session or session["state"] in ("complete", "interrupted"):
                return None
            session["state"] = "interrupted"
            session["interrupt_reason"] = reason
            session["updated_at"] = time.time()
            self._save()
            result = deepcopy(session)
        self._fire("interrupt", result)
        return result

    def _find(self, session_id: int) -> dict | None:
        """Find session by ID (caller must hold lock)."""
        for s in self._sessions:
            if s["id"] == session_id:
                return s
        return None


def validate_session_template(tmpl: dict, capacity_policy=None) -> list[str]:
    """Validate a session template dict. Returns list of errors (empty = valid)."""
    from session_capacity import capacity_policy as validate_capacity
    limits = validate_capacity(capacity_policy)
    errors = []

    if not isinstance(tmpl, dict):
        return ["Template must be a JSON object"]

    if not tmpl.get("name") or not isinstance(tmpl.get("name"), str):
        errors.append("Missing or invalid 'name' (string required)")

    roles = tmpl.get("roles", [])
    if not isinstance(roles, list) or len(roles) == 0:
        errors.append("'roles' must be a non-empty array")
    elif len(roles) > limits['max_roles']:
        errors.append(f"Too many roles ({len(roles)}, max {limits['max_roles']})")
    if isinstance(roles, list) and any(not isinstance(role, str) or not role.strip() for role in roles):
        errors.append('Each role must be a nonempty string')
    if isinstance(roles, list) and all(isinstance(role, str) for role in roles) and len(set(roles)) != len(roles):
        errors.append('Roles must be unique')

    phases = tmpl.get("phases", [])
    if not isinstance(phases, list) or len(phases) == 0:
        errors.append("'phases' must be a non-empty array")
    elif len(phases) > limits['max_phases']:
        errors.append(f"Too many phases ({len(phases)}, max {limits['max_phases']})")

    roles_set = {role for role in roles if isinstance(role, str)} if isinstance(roles, list) else set()
    output_count = 0
    total_turns = 0

    for i, phase in enumerate(phases if isinstance(phases, list) else []):
        if not isinstance(phase, dict):
            errors.append(f"Phase {i + 1}: must be an object")
            continue
        if not isinstance(phase.get("name"), str) or not phase['name'].strip():
            errors.append(f"Phase {i + 1}: missing 'name'")
        participants = phase.get("participants", [])
        if isinstance(participants, list):
            total_turns += len(participants)
        if not isinstance(participants, list) or len(participants) == 0:
            errors.append(f"Phase {i + 1}: 'participants' must be a non-empty array")
        elif len(participants) > limits['max_participants_per_phase']:
            errors.append(f"Phase {i + 1}: too many participants ({len(participants)}, max {limits['max_participants_per_phase']})")
        for p in (participants if isinstance(participants, list) else []):
            if not isinstance(p, str) or p not in roles_set:
                errors.append(f"Phase {i + 1}: participant '{p}' not in roles list")
        prompt = phase.get("prompt", "")
        if not isinstance(prompt, str):
            errors.append(f'Phase {i + 1}: prompt must be text')
        elif len(prompt) > limits['max_prompt_chars']:
            errors.append(f"Phase {i + 1}: prompt too long ({len(prompt)} chars, max {limits['max_prompt_chars']})")
        if phase.get("is_output"):
            output_count += 1

    if output_count == 0 and isinstance(phases, list) and len(phases) > 0:
        errors.append("No phase marked as 'is_output: true'")
    elif output_count > 1:
        errors.append(f"Multiple phases marked as output ({output_count}, expected 1)")

    if total_turns > limits['max_total_turns']:
        errors.append(f"Too many total turns ({total_turns}, max {limits['max_total_turns']})")
    return errors
