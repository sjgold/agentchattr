"""Cold inventory plus authenticated boot challenge, using an actual owned child."""
from copy import deepcopy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch
import uuid

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from api_seats import SeatError, SeatStore, atomic_json
from api_seat_runtime import SeatManager
from registry import RuntimeRegistry
from runtime_ownership import new_launch_identity, record_spawn_outcome


@unittest.skipUnless(sys.platform == 'win32', 'Actual Windows child birth/retained handle proof')
class RuntimeAdoptionTests(unittest.TestCase):
    def setUp(self):
        (ROOT / '.audit-tmp').mkdir(exist_ok=True)
        temporary = tempfile.TemporaryDirectory(dir=ROOT / '.audit-tmp')
        self.addCleanup(temporary.cleanup)
        self.data = Path(temporary.name)
        self.config = {'server': {'port': 18300, 'host': '127.0.0.1'},
                       'mcp': {'http_port': 18301, 'sse_port': 18302}}
        self.store = SeatStore(self.data, {'fake': {'type': 'api', 'base_url': 'http://127.0.0.1:19999/v1',
            'system_prompt': 'PRIVATE_PROVIDER_SOURCE_SENTINEL'}})
        self.store.save({'id': 'team', 'name': 'Team', 'seats': [{'id': 'api', 'name': 'API',
            'adapter': 'openai-compatible', 'provider': 'fake', 'model': 'frozen-model', 'reasoning': None,
            'launch_profile': 'standard', 'secret_ref': ''}]})
        self.registry = RuntimeRegistry(str(self.data))
        self.boot = uuid.uuid4().hex
        self.manager = SeatManager(ROOT, self.config, self.store, self.registry, monitor=False, boot_id=self.boot)
        def close_retained_handles():
            for attempt in self.manager.attempts.values():
                process = attempt.get('process')
                if process is not None and hasattr(process, 'close'):
                    process.close()
        self.addCleanup(close_retained_handles)
        self.addCleanup(self.manager.shutdown)
        self.key, self.attempt = 'team/api', uuid.uuid4().hex
        self.effective = self.manager._effective(self.store.seat('team', 'api'))
        identity = new_launch_identity(ROOT, self.effective, self.key, self.attempt, uuid.uuid4().hex)
        import hashlib
        self.base = 'api-' + hashlib.sha256(self.key.encode()).hexdigest()[:8] + '-' + self.attempt[:12]
        self.path = self.data / 'api_seat_runtime' / self.attempt / 'config.json'
        self.snapshot = {**self.effective, 'attempt': self.attempt, 'base': self.base, 'ownership': identity}
        atomic_json(self.path, self.snapshot)
        record_spawn_outcome(self.path, self.snapshot, 'pending')
        self.child_log = (self.data / 'child.log').open('wb')
        self.addCleanup(self.child_log.close)
        code = ('import sys,json;sys.path.insert(0,' + repr(str(ROOT)) + ');'
                'from pathlib import Path;from runtime_ownership import record_worker_birth;'
                'p=Path(' + repr(str(self.path)) + ');record_worker_birth(p,json.loads(p.read_text(encoding="utf-8")));'
                'sys.stdin.buffer.read(1)')
        self.actual_popen = subprocess.Popen
        self.child = self.actual_popen([sys._base_executable, '-u', '-c', code], stdin=subprocess.PIPE,
            stdout=self.child_log, stderr=subprocess.STDOUT, creationflags=subprocess.CREATE_NO_WINDOW)
        def cleanup_child():
            if self.child.poll() is None:
                self.child.terminate()
            self.child.wait(timeout=5)
            self.child.stdin.close()
        self.addCleanup(cleanup_child)
        record_spawn_outcome(self.path, self.snapshot, 'spawned')
        deadline = time.monotonic() + 10
        while not self.path.with_name('birth.json').exists():
            if self.child.poll() is not None or time.monotonic() > deadline:
                self.fail('owned fixture child failed to write actual birth')
            time.sleep(.02)
        self.birth = json.loads(self.path.with_name('birth.json').read_text('utf-8'))
        self.registry.seed({self.base: {'type': 'api', 'label': 'Actual fixture worker'}})
        self.principal = self.registry.register(self.base)
        self.assertEqual(self.registry.resolve_token(self.principal['token'])['identity_id'], self.principal['identity_id'])
        atomic_json(self.path.with_name('receipt.json'), {'attempt': self.attempt, 'state': 'ready',
            'name': self.principal['name'], 'identity_id': self.principal['identity_id'], 'adapter_connected': True,
            'authentication': 'unknown', 'updated_at': time.time()})
        self.payload = {'attempt': self.attempt, 'launch_nonce': identity['launch_nonce'],
            'server_identity': identity['server_identity'], 'boot_id': self.boot,
            'worker_pid': self.birth['pid'], 'creation_filetime': self.birth['creation_filetime'],
            'worker_root': self.birth['worker_root']}
        self.now = time.time()
        self.patcher = patch('api_seat_runtime.subprocess.Popen', side_effect=AssertionError('inventory/heartbeat spawned a worker'))
        self.spawn = self.patcher.start()
        self.addCleanup(self.patcher.stop)

    def files(self):
        return {str(path.relative_to(self.path.parent)): path.read_bytes()
                for path in self.path.parent.iterdir() if path.is_file()}

    def heartbeat(self, payload=None, principal=None, now=None):
        return self.manager.observe_runtime_heartbeat(self.principal if principal is None else principal,
            self.payload if payload is None else payload, now=self.now if now is None else now)

    def assert_unverified_alive(self, reply):
        self.assertEqual(reply['boot_id'], self.boot)
        self.assertFalse(reply['verified'])
        self.assertIsNone(self.child.poll(), 'reconciliation actuated a rejected worker')
        self.spawn.assert_not_called()

    def test_cold_inventory_is_not_readiness_or_adoption(self):
        self.manager.reconcile_runtime(now=self.now)
        readiness = self.manager.restart_readiness(self.principal['identity_id'], self.boot, now=self.now)
        self.assertEqual(readiness['state'], 'unverified')
        self.assertFalse(readiness['process_verified'])
        self.assertIsNone(self.child.poll())
        self.spawn.assert_not_called()

    def test_fresh_authenticated_current_boot_proof_adopts_actual_child_without_spawn(self):
        self.manager.reconcile_runtime(now=self.now)
        reply = self.manager.observe_runtime_heartbeat(self.principal, self.payload, now=self.now)
        self.assertEqual(reply['boot_id'], self.boot)
        self.assertTrue(reply['verified'])
        readiness = self.manager.restart_readiness(self.principal['identity_id'], self.boot, now=self.now)
        self.assertEqual(readiness['state'], 'ready')
        self.assertTrue(readiness['process_verified'])
        self.assertEqual(self.manager.attempts[self.key]['id'], self.attempt)
        self.assertEqual(self.manager.attempts[self.key]['process'].pid, self.child.pid)
        self.spawn.assert_not_called()

    def test_none_or_stale_boot_echo_returns_challenge_without_adoption(self):
        self.manager.reconcile_runtime(now=self.now)
        before = self.files()
        for boot in (None, self.snapshot['ownership']['boot_id']):
            with self.subTest(boot_id=boot):
                self.assert_unverified_alive(self.heartbeat({**self.payload, 'boot_id': boot}))
                self.assertEqual(self.files(), before)
        self.assertFalse(self.manager.restart_readiness(self.principal['identity_id'], self.boot, now=self.now)['process_verified'])

    def test_wrong_payload_references_never_authorize_process_or_touch_evidence(self):
        self.manager.reconcile_runtime(now=self.now)
        before = self.files()
        for field, value in (('attempt', uuid.uuid4().hex), ('launch_nonce', uuid.uuid4().hex),
                             ('server_identity', '0' * 64), ('worker_pid', 0),
                             ('creation_filetime', str(int(self.birth['creation_filetime']) + 1)),
                             ('worker_root', str(self.data / 'foreign-checkout'))):
            with self.subTest(field=field):
                self.assert_unverified_alive(self.heartbeat({**self.payload, field: value}))
                self.assertEqual(self.files(), before)

    def test_wrong_authenticated_principal_cannot_adopt_another_birth(self):
        self.registry.seed({'unrelated': {'type': 'api', 'label': 'Unrelated real principal'}})
        other = self.registry.register('unrelated')
        self.assertEqual(self.registry.resolve_token(other['token'])['identity_id'], other['identity_id'])
        self.manager.reconcile_runtime(now=self.now)
        self.assert_unverified_alive(self.heartbeat(principal=other))
        self.assertFalse(self.manager.restart_readiness(self.principal['identity_id'], self.boot, now=self.now)['process_verified'])

    def test_self_consistent_foreign_root_metadata_still_fails_approved_manager_root(self):
        foreign = new_launch_identity(ROOT / 'not-this-checkout', self.effective, self.key,
                                      self.attempt, self.snapshot['ownership']['boot_id'])
        changed = {**self.snapshot, 'ownership': foreign}
        birth = {**self.birth, 'ownership': foreign}
        atomic_json(self.path, changed)
        atomic_json(self.path.with_name('launch.json'), {**foreign, 'spawn_outcome': 'spawned'})
        atomic_json(self.path.with_name('birth.json'), birth)
        before = self.files()
        self.manager.reconcile_runtime(now=self.now)
        self.assert_unverified_alive(self.heartbeat({**self.payload, 'launch_nonce': foreign['launch_nonce'],
            'server_identity': foreign['server_identity']}))
        self.assertEqual(self.files(), before)

    def test_changed_active_server_port_or_mcp_cannot_adopt_foreign_server_identity(self):
        for field in ('port', 'mcp'):
            config = deepcopy(self.config)
            if field == 'port':
                config['server']['port'] += 1
            else:
                config['mcp']['http_port'] += 1
            other = SeatManager(ROOT, config, self.store, self.registry, monitor=False, boot_id=uuid.uuid4().hex)
            try:
                other.reconcile_runtime(now=self.now)
                reply = other.observe_runtime_heartbeat(self.principal, {**self.payload, 'boot_id': other.boot_id}, now=self.now)
                self.assertFalse(reply['verified'])
                self.assertIsNone(self.child.poll())
            finally:
                other.shutdown()
        self.spawn.assert_not_called()

    def test_legacy_missing_manifest_and_pending_intent_are_not_spawn_failure_proof(self):
        # This actual worker exists; a pending intent cannot be relabelled failed
        # merely because the cold manager has no original Popen object.
        manifest_path = self.path.with_name('launch.json')
        original_manifest = json.loads(manifest_path.read_text('utf-8'))
        atomic_json(manifest_path, {**original_manifest, 'spawn_outcome': 'pending'})
        before = self.files()
        self.manager.reconcile_runtime(now=self.now)
        self.assertEqual(self.files(), before)
        self.assertIsNone(self.child.poll())
        # Legacy birth/intent absence remains visible and untouched.
        manifest_path.unlink()
        legacy = deepcopy(self.snapshot)
        legacy.pop('ownership')
        atomic_json(self.path, legacy)
        before = self.files()
        self.manager.reconcile_runtime(now=self.now)
        self.assert_unverified_alive(self.heartbeat())
        self.assertEqual(self.files(), before)

    def test_repeated_current_proof_reuses_retained_handle_and_is_metadata_readonly(self):
        self.manager.reconcile_runtime(now=self.now)
        before = self.files()
        self.assertTrue(self.heartbeat()['verified'])
        process = self.manager.attempts[self.key]['process']
        for _ in range(3):
            self.manager.reconcile_runtime(now=self.now)
            self.assertTrue(self.heartbeat()['verified'])
            self.assertIs(self.manager.attempts[self.key]['process'], process)
            self.assertEqual(self.manager.attempts[self.key]['effective'], self.effective)
            self.assertEqual(self.manager.attempts[self.key]['fingerprint'], self.snapshot['ownership']['fingerprint'])
            self.assertEqual(self.files(), before)
        public = json.dumps(self.manager.reconcile_runtime(now=self.now))
        self.assertNotIn('PRIVATE_PROVIDER_SOURCE_SENTINEL', public)
        self.assertNotIn(self.principal['token'], public)
        self.spawn.assert_not_called()

    def test_authenticated_lease_expiry_blocks_readiness_without_inventory_renewal(self):
        self.manager.reconcile_runtime(now=self.now)
        self.assertTrue(self.heartbeat()['verified'])
        self.assertEqual(self.manager.restart_readiness(self.principal['identity_id'], self.boot,
                                                       now=self.now + 14)['state'], 'ready')
        self.manager.reconcile_runtime(now=self.now + 16)
        expired = self.manager.restart_readiness(self.principal['identity_id'], self.boot, now=self.now + 16)
        self.assertNotEqual(expired['state'], 'ready')
        self.assertIsNone(self.child.poll())
        self.assertNotEqual(self.manager.restart_readiness(self.principal['identity_id'], uuid.uuid4().hex,
                                                          now=self.now)['state'], 'ready')

    def test_ready_receipt_and_adapter_connection_both_required_after_native_proof(self):
        self.manager.reconcile_runtime(now=self.now)
        self.assertTrue(self.heartbeat()['verified'])
        receipt_path = self.path.with_name('receipt.json')
        receipt = json.loads(receipt_path.read_text('utf-8'))
        for state, connected in (('failed', True), ('ready', False)):
            with self.subTest(state=state, adapter_connected=connected):
                atomic_json(receipt_path, {**receipt, 'state': state, 'adapter_connected': connected})
                self.assertNotEqual(self.manager.restart_readiness(self.principal['identity_id'], self.boot,
                                                                  now=self.now)['state'], 'ready')
        self.assertIsNone(self.child.poll())

    def test_conflicting_same_key_live_attempts_fail_closed_without_killing_either(self):
        attempt = uuid.uuid4().hex
        import hashlib
        base = 'api-' + hashlib.sha256(self.key.encode()).hexdigest()[:8] + '-' + attempt[:12]
        identity = new_launch_identity(ROOT, self.effective, self.key, attempt, uuid.uuid4().hex)
        path = self.data / 'api_seat_runtime' / attempt / 'config.json'
        snapshot = {**self.effective, 'attempt': attempt, 'base': base, 'ownership': identity}
        atomic_json(path, snapshot)
        record_spawn_outcome(path, snapshot, 'pending')
        code = ('import sys,json;sys.path.insert(0,' + repr(str(ROOT)) + ');'
                'from pathlib import Path;from runtime_ownership import record_worker_birth;'
                'p=Path(' + repr(str(path)) + ');record_worker_birth(p,json.loads(p.read_text(encoding="utf-8")));'
                'sys.stdin.buffer.read(1)')
        extra = self.actual_popen([sys._base_executable, '-u', '-c', code], stdin=subprocess.PIPE,
            stdout=self.child_log, stderr=subprocess.STDOUT, creationflags=subprocess.CREATE_NO_WINDOW)
        def cleanup_extra():
            if extra.poll() is None:
                extra.terminate()
            extra.wait(timeout=5)
            extra.stdin.close()
        self.addCleanup(cleanup_extra)
        record_spawn_outcome(path, snapshot, 'spawned')
        deadline = time.monotonic() + 10
        while not path.with_name('birth.json').exists():
            self.assertIsNone(extra.poll())
            self.assertLess(time.monotonic(), deadline)
            time.sleep(.02)
        self.registry.seed({base: {'type': 'api', 'label': 'Conflicting real worker'}})
        principal = self.registry.register(base)
        atomic_json(path.with_name('receipt.json'), {'attempt': attempt, 'state': 'ready',
            'name': principal['name'], 'identity_id': principal['identity_id'], 'adapter_connected': True,
            'authentication': 'unknown', 'updated_at': self.now})
        self.manager.reconcile_runtime(now=self.now)
        self.assert_unverified_alive(self.heartbeat())
        self.assertIsNone(extra.poll())

    def test_unverified_live_candidate_blocks_launch_and_restart_before_popen(self):
        self.manager.reconcile_runtime(now=self.now)
        before = self.files()
        for restart in (False, True):
            with self.subTest(restart=restart), self.assertRaises(SeatError):
                self.manager.launch('team', 'api', restart=restart)
            self.assertIsNone(self.child.poll())
            self.assertEqual(self.files(), before)
        self.spawn.assert_not_called()

    def test_candidate_missing_birth_still_blocks_blind_same_key_launch(self):
        self.path.with_name('birth.json').unlink()
        self.manager.reconcile_runtime(now=self.now)
        before = self.files()
        for restart in (False, True):
            with self.subTest(restart=restart), self.assertRaises(SeatError):
                self.manager.launch('team', 'api', restart=restart)
            self.assertIsNone(self.child.poll())
            self.assertEqual(self.files(), before)
        self.spawn.assert_not_called()

    def test_nonadopted_stop_and_shutdown_cannot_actuate_or_claim_stopped(self):
        self.manager.reconcile_runtime(now=self.now)
        before = self.files()
        with self.assertRaises(SeatError):
            self.manager.stop('team', 'api')
        self.manager.shutdown()
        self.assertIsNone(self.child.poll())
        self.assertEqual(self.files(), before)
        self.assertEqual(json.loads(self.path.with_name('receipt.json').read_text('utf-8'))['state'], 'ready')
        self.spawn.assert_not_called()


if __name__ == '__main__':
    unittest.main()
