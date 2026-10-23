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
               participant_bindings=None, recovery_policy=None) -> dict | None:
        """Create and persist a new session run."""
        tmpl = self._templates.get(template_id)
        if not tmpl:
            return None
        from review_brief import BriefError, freeze_inputs
        from turn_recovery import recovery_policy as validate_policy
        policy = validate_policy(recovery_policy)
        frozen = freeze_inputs(tmpl, goal, input_text, rules_snapshot, capacity_policy=self._capacity_policy)
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

    def _event_update(self, session_id, change, action='update'):
        """Commit one admission transaction, rolling back memory on any failure."""
        from turn_events import EventConflict
        with self._lock:
            session = self._find(session_id)
            if not session or session.get('completion_protocol') != 1:
                raise EventConflict('Session has no explicit completion protocol; legacy history is read-only.')
            before = deepcopy(self._sessions)
            try:
                change(session)
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
            frozen = freeze_inputs(parent['design_snapshot'], parent['goal'], input_text, parent['rules_snapshot'],
                                   capacity_policy=parent.get('capacity_policy') or LEGACY_POLICY)
            if frozen['input_revision'] == parent['input_revision']:
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
            invocation['consumed'] = True
            if session.get('turn_recovery'):
                session['turn_recovery'].update(status='resolved', resolved_by=event['event_id'])
            record = deepcopy(event)
            record.update(projected_message_id=None, accepted_at=time.time(),
                          sender=invocation['expected_agent'],
                          provenance=('verified_saved_api_result' if saved_payload is not None else
                                      'human_operator' if human else 'authenticated_seat'),
                          expected_identity_id=invocation['expected_identity_id'])
            phases = session['design_snapshot']['phases']
            phase = phases[session['current_phase']]
            record['is_output'] = bool(phase.get('is_output'))
            session['admitted_events'].append(record)
            if event['kind'] == 'question':
                session['state'] = 'awaiting_input'
                session['current_question'] = {'event_id': event['event_id'], 'text': event['content'],
                    'asked_by': invocation['expected_agent'], 'attempt_id': invocation['attempt_id']}
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
        return self._event_update(session_id, admit)

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
