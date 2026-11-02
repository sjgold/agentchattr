"""Wrapper-side authenticated transport receipts; never opens queue storage."""
import json
import urllib.request
import uuid


class QueueClient:
    def __init__(self, port, get_token):
        self.port = port
        self.get_token = get_token
        # New process or watcher means new ownership, never inherited replay.
        self.consumer_id = uuid.uuid4().hex

    def _request(self, operation, **fields):
        request = urllib.request.Request(
            f'http://127.0.0.1:{self.port}/api/queue/{operation}',
            data=json.dumps({'consumer_id': self.consumer_id, **fields}).encode('utf-8'),
            headers={'Authorization': 'Bearer ' + self.get_token(), 'Content-Type': 'application/json'})
        with urllib.request.urlopen(request, timeout=5) as response:
            return json.loads(response.read())['dispatch']

    def claim(self):
        return self._request('claim')

    def inspect(self, dispatch_id):
        return self._request('inspect', dispatch_id=dispatch_id)

    def acknowledge(self, dispatch_id):
        return self._request('ack', dispatch_id=dispatch_id)

    def release(self, dispatch_id, *, failed=False, error_category='', http_status=None):
        extra = {'http_status': http_status} if http_status is not None else {}
        return self._request('release', dispatch_id=dispatch_id, failed=failed, error_category=error_category, **extra)

    def uncertain(self, dispatch_id):
        return self._request('uncertain', dispatch_id=dispatch_id)

    def cancellation_receipt(self, dispatch_id, status):
        return self._request('cancel', dispatch_id=dispatch_id, status=status)


class CliConsumer:
    def __init__(self, client, inject, prompt, *, artifact_preflight=None):
        self.client, self.inject, self.prompt = client, inject, prompt
        self.last_injected_dispatch_id = None
        self.artifact_preflight = artifact_preflight
        self.held_artifact_dispatch_id = None
        self.held_artifact_reason = None

    def _hold_artifact(self, dispatch, reason='artifact_generation_uncertain'):
        self.held_artifact_dispatch_id = dispatch
        self.held_artifact_reason = reason

    def _clear_artifact_hold(self):
        self.held_artifact_dispatch_id = self.held_artifact_reason = None

    def _release_artifact(self, dispatch, *, failed):
        """Inspect one original dispatch; never claim a successor as a reread."""
        def inspect():
            value = self.client.inspect(dispatch)
            if (value['envelope']['dispatch_id'] != dispatch
                    or value['consumer_id'] != self.client.consumer_id):
                raise ValueError('Retained dispatch ownership changed.')
            return value
        def finished(value):
            if value['state'] in ('released', 'failed', 'cancelled', 'settled_recovered'):
                self._clear_artifact_hold()
                return True
            if value['state'] == 'cancelling':
                self._hold_artifact(dispatch)
                self.client.cancellation_receipt(dispatch, 'unsupported')
                return True
            return False
        try:
            current = inspect()
            if finished(current):
                return
            if current['state'] not in ('dispatched', 'acknowledged', 'uncertain'):
                raise ValueError('No active artifact transport.')
            try:
                self.client.release(dispatch, **({'failed': True, 'error_category': 'local_delivery_failure'} if failed else {}))
                self._clear_artifact_hold()
            except Exception:
                if not finished(inspect()):
                    self._hold_artifact(dispatch, 'artifact_delivery_unconfirmed')
        except Exception:
            self._hold_artifact(dispatch, 'artifact_delivery_unconfirmed')

    def _poll_artifact(self, record):
        dispatch = record['envelope']['dispatch_id']
        if self.held_artifact_dispatch_id != dispatch:
            self._clear_artifact_hold()
        if record['envelope'].get('purpose') != 'artifact-v1' or self.artifact_preflight is None:
            self._release_artifact(dispatch, failed=True)
            return
        from artifact_worker import REASONS
        try:
            decision = self.artifact_preflight(record, injected_dispatch_id=self.last_injected_dispatch_id,
                                               held_dispatch_id=self.held_artifact_dispatch_id)
            if (not isinstance(decision, dict) or set(decision) != {'action', 'prompt', 'admission', 'reason'}
                    or decision['action'] not in ('inject', 'wait', 'complete', 'hold', 'reject')
                    or decision['reason'] is not None and decision['reason'] not in REASONS):
                raise ValueError('Invalid artifact preflight outcome.')
            action = decision['action']
            if action == 'wait':
                return  # In particular, transient first-fetch errors never latch.
            if action == 'hold' or (action == 'reject' and (self.last_injected_dispatch_id == dispatch
                    or decision['reason'] == 'artifact_result_quarantined')):
                self._hold_artifact(dispatch, decision['reason'] or 'artifact_generation_uncertain')
                return
            if action == 'complete':
                ack = decision['admission']
                if not isinstance(ack, dict) or ack.get('status') != 'admitted' or ack.get('event_id') != dispatch:
                    raise ValueError('No artifact admission authority.')
                self._release_artifact(dispatch, failed=False)
                return
            if action == 'reject':
                self._release_artifact(dispatch, failed=True)
                return
            if (record['state'] != 'dispatched' or self.last_injected_dispatch_id == dispatch
                    or self.held_artifact_dispatch_id == dispatch or not isinstance(decision['prompt'], str)):
                self._hold_artifact(dispatch)
                return
            self.last_injected_dispatch_id = dispatch  # Before any possible keystroke.
            try:
                if self.inject(decision['prompt']) is False:
                    raise RuntimeError('Artifact injection outcome is uncertain.')
                self.client.acknowledge(dispatch)
            except Exception:
                self._hold_artifact(dispatch)
                self.client.uncertain(dispatch)
                raise
        except Exception:
            self._hold_artifact(dispatch, self.held_artifact_reason or 'artifact_delivery_unconfirmed')
            raise

    def poll(self):
        record = self.client.claim()
        if not record:
            return
        envelope = record['envelope']
        dispatch_id = envelope['dispatch_id']
        if record.get('state') == 'cancelling':
            # Generic native consoles have no verified per-turn interrupt.
            # Keep the persistent process alive and never inject a new prompt.
            self.client.cancellation_receipt(dispatch_id, 'unsupported')
            if 'purpose' in envelope:
                self._hold_artifact(dispatch_id)
            return
        if 'purpose' in envelope:
            return self._poll_artifact(record)
        if dispatch_id == self.last_injected_dispatch_id:
            return
        # Set before injection. An exception may mean partial keystroke delivery.
        self.last_injected_dispatch_id = dispatch_id
        try:
            if self.inject(self.prompt(envelope)) is False:
                raise RuntimeError('CLI injection failed; delivery outcome is uncertain.')
            self.client.acknowledge(dispatch_id)
        except Exception:
            self.client.uncertain(dispatch_id)
            raise

    def close(self):
        if self.last_injected_dispatch_id:
            self.client.uncertain(self.last_injected_dispatch_id)
