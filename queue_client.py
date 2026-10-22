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

    def acknowledge(self, dispatch_id):
        return self._request('ack', dispatch_id=dispatch_id)

    def release(self, dispatch_id, *, failed=False):
        return self._request('release', dispatch_id=dispatch_id, failed=failed)

    def uncertain(self, dispatch_id):
        return self._request('uncertain', dispatch_id=dispatch_id)


class CliConsumer:
    def __init__(self, client, inject, prompt):
        self.client, self.inject, self.prompt = client, inject, prompt
        self.last_injected_dispatch_id = None

    def poll(self):
        record = self.client.claim()
        if not record:
            return
        envelope = record['envelope']
        dispatch_id = envelope['dispatch_id']
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
