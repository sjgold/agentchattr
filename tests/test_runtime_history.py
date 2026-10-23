"""Historical exit ALGORITHM tests; patched probe statuses are not native absence proof."""
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import Mock, patch
import uuid

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from api_seats import SeatError, SeatStore, atomic_json
from api_seat_runtime import SeatManager
from process_identity import open_verified_process
from registry import RuntimeRegistry
from runtime_ownership import new_launch_identity, record_spawn_outcome


@unittest.skipUnless(sys.platform == 'win32', 'owned Windows fixture self-birth')
class RuntimeHistoryTests(unittest.TestCase):
    def setUp(self):
        (ROOT / '.audit-tmp').mkdir(exist_ok=True)
        temporary = tempfile.TemporaryDirectory(dir=ROOT / '.audit-tmp')
        self.addCleanup(temporary.cleanup)
        self.data = Path(temporary.name)
        self.providers = {'fake-cli': {'command': sys._base_executable, 'cwd': str(self.data),
            'cli_args': ['-c', 'pass'], 'mcp_inject': 'env', 'mcp_env_var': 'HISTORY_FAKE_SETTINGS'},
            'fake-api': {'type': 'api', 'base_url': 'http://127.0.0.1:19999/v1',
                         'system_prompt': 'PRIVATE_PROVIDER_HISTORY_SENTINEL'}}
        self.store = SeatStore(self.data, self.providers)
        self.seat = {'id': 'cli', 'name': 'CLI', 'adapter': 'cli', 'provider': 'fake-cli',
            'model': None, 'reasoning': None, 'launch_profile': 'standard', 'secret_ref': ''}
        self.store.save({'id': 'team', 'name': 'Team', 'seats': [self.seat]})
        self.registry = RuntimeRegistry(str(self.data))
        self.manager = SeatManager(ROOT, {'server': {'port': 18300, 'host': '127.0.0.1'},
            'mcp': {'http_port': 18301, 'sse_port': 18302}}, self.store, self.registry,
            monitor=False, boot_id=uuid.uuid4().hex)
        def close_handles():
            for attempt in self.manager.attempts.values():
                process = attempt.get('process')
                if process is not None and hasattr(process, 'close'):
                    process.close()
        self.addCleanup(close_handles)
        self.addCleanup(self.manager.shutdown)
        self.actual_popen = subprocess.Popen
        self.old = self.make_record()
        self.patcher = patch('api_seat_runtime.subprocess.Popen', side_effect=AssertionError('cold inventory spawned'))
        self.spawn = self.patcher.start()
        self.addCleanup(self.patcher.stop)

    def make_record(self, key='team/cli', adapter='cli', alive=False):
        attempt = uuid.uuid4().hex
        seat = deepcopy(self.seat) if adapter == 'cli' else {**self.seat, 'id': 'api',
            'adapter': 'openai-compatible', 'provider': 'fake-api', 'model': 'frozen-model'}
        effective = self.manager._effective(seat)
        identity = new_launch_identity(ROOT, effective, key, attempt, uuid.uuid4().hex)
        base = ('cli-' if adapter == 'cli' else 'api-') + hashlib.sha256(key.encode()).hexdigest()[:8] + '-' + attempt[:12]
        path = self.data / 'api_seat_runtime' / attempt / 'config.json'
        snapshot = {**effective, 'attempt': attempt, 'base': base, 'ownership': identity}
        atomic_json(path, snapshot)
        record_spawn_outcome(path, snapshot, 'pending')
        code = ('import sys,json;sys.path.insert(0,' + repr(str(ROOT)) + ');'
            'from pathlib import Path;from runtime_ownership import record_worker_birth;'
            'p=Path(' + repr(str(path)) + ');record_worker_birth(p,json.loads(p.read_text(encoding="utf-8")));'
            'sys.stdin.buffer.read(1);sys.exit(7)')
        child = self.actual_popen([sys._base_executable, '-u', '-c', code], stdin=subprocess.PIPE,
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, creationflags=subprocess.CREATE_NO_WINDOW)
        def cleanup():
            if child.poll() is None:
                child.terminate()
            child.wait(timeout=5)
            child.stdin.close()
        self.addCleanup(cleanup)
        record_spawn_outcome(path, snapshot, 'spawned')
        deadline = time.monotonic() + 10
        while not path.with_name('birth.json').exists():
            self.assertIsNone(child.poll())
            self.assertLess(time.monotonic(), deadline)
            time.sleep(.02)
        birth = json.loads(path.with_name('birth.json').read_text('utf-8'))
        self.registry.seed({base: {'type': adapter, 'label': 'Fixture worker'}})
        principal = self.registry.register(base)
        receipt = {'attempt': attempt, 'state': 'ready' if alive else 'stopped', 'name': principal['name'],
            'identity_id': principal['identity_id'], 'adapter_connected': alive,
            'authentication': 'unknown', 'updated_at': time.time()}
        if not alive:
            child.stdin.write(b'x')
            child.stdin.flush()
            self.assertEqual(child.wait(timeout=5), 7)
            # Supplied protocol receipt, separate from the explicitly patched
            # wrapper probe. This does not claim a real CLI child was exercised.
            receipt['child_exit_code'] = 7
        atomic_json(path.with_name('receipt.json'), receipt)
        return dict(path=path, snapshot=snapshot, birth=birth, principal=principal, child=child,
                    attempt=attempt, key=key, receipt=receipt)

    def files(self):
        return {str(path.relative_to(self.data)): path.read_bytes()
                for path in (self.data / 'api_seat_runtime').rglob('*') if path.is_file()}

    def record(self, entry=None):
        entry = self.old if entry is None else entry
        return next(value for value in self.manager.reconcile_runtime() if value['attempt'] == entry['attempt'])

    def test_absent_probe_plus_exact_cli_exit_receipt_produces_structured_history(self):
        before = self.files()
        with patch('runtime_adoption.open_verified_process', return_value={
                'status': 'absent', 'process': None, 'error_code': 87, 'reason': 'pid_absent'}):
            record = self.record()
        self.assertEqual(record['state'], 'exited')
        self.assertEqual(record['exit_evidence'], {'wrapper_status': 'absent', 'child_exit_code': 7,
            'verification_basis': 'durable_receipt_and_observed_absent'})
        self.assertEqual(self.files(), before)
        self.assertNotIn(self.old['key'], self.manager.attempts)
        self.spawn.assert_not_called()

    def test_creation_time_mismatch_proves_old_wrapper_absent_not_image_mismatch(self):
        atomic_json(self.old['path'].with_name('receipt.json'), {**self.old['receipt'], 'state': 'failed'})
        with patch('runtime_adoption.open_verified_process', return_value={
                'status': 'mismatch', 'process': None, 'reason': 'creation_time_mismatch'}):
            record = self.record()
        self.assertEqual(record['state'], 'exited')
        self.assertEqual(record['exit_evidence'], {'wrapper_status': 'absent', 'child_exit_code': 7,
            'verification_basis': 'durable_receipt_and_observed_absent'})
        self.spawn.assert_not_called()

    def test_image_mismatch_access_denied_and_postmortem_31_leave_reservation_unproven(self):
        statuses = [{'status': 'mismatch', 'process': None, 'reason': 'image_mismatch'},
                    {'status': 'uncertain', 'process': None, 'error_code': 5},
                    {'status': 'uncertain', 'process': None, 'error_code': 31}]
        before = self.files()
        for status in statuses:
            with self.subTest(probe=status), patch('runtime_adoption.open_verified_process', return_value=status):
                record = self.record()
                self.assertEqual(record['reason'], 'unproven_worker_exit')
                self.assertNotEqual(record['state'], 'exited')
                self.assertNotIn('exit_evidence', record)
                with self.assertRaises(SeatError):
                    self.manager.launch('team', 'cli')
                self.assertEqual(self.files(), before)
        self.spawn.assert_not_called()

    def test_missing_noninteger_boolean_or_wrong_attempt_child_receipt_cannot_retire(self):
        receipt_path = self.old['path'].with_name('receipt.json')
        invalid = [{key: value for key, value in self.old['receipt'].items() if key != 'child_exit_code'},
                   {**self.old['receipt'], 'child_exit_code': True},
                   {**self.old['receipt'], 'child_exit_code': '7'},
                   {**self.old['receipt'], 'child_exit_code': 7.0},
                   {**self.old['receipt'], 'attempt': uuid.uuid4().hex}]
        with patch('runtime_adoption.open_verified_process', return_value={'status': 'absent', 'process': None, 'error_code': 87}):
            for receipt in invalid:
                with self.subTest(receipt=receipt):
                    atomic_json(receipt_path, receipt)
                    before = self.files()
                    record = self.record()
                    self.assertEqual(record['reason'], 'unproven_worker_exit')
                    self.assertNotIn('exit_evidence', record)
                    with self.assertRaises(SeatError):
                        self.manager.launch('team', 'cli')
                    self.assertEqual(self.files(), before)
            receipt_path.unlink()
            record = self.record()
            self.assertEqual(record['reason'], 'unproven_worker_exit')
        self.spawn.assert_not_called()

    def test_pending_without_ram_handle_never_becomes_synchronous_spawn_failure(self):
        path = self.old['path']
        manifest = json.loads(path.with_name('launch.json').read_text('utf-8'))
        atomic_json(path.with_name('launch.json'), {**manifest, 'spawn_outcome': 'pending'})
        atomic_json(path.with_name('receipt.json'), {**self.old['receipt'], 'state': 'ready', 'child_exit_code': None})
        before = self.files()
        with patch('runtime_adoption.open_verified_process', return_value={'status': 'absent', 'process': None, 'error_code': 87}):
            record = self.record()
            self.assertNotEqual(record['state'], 'failed')
            self.assertNotIn('exit_evidence', record)
            with self.assertRaises(SeatError):
                self.manager.launch('team', 'cli', restart=True)
        self.assertEqual(self.files(), before)
        self.spawn.assert_not_called()

    def test_validated_failed_spawn_allows_only_explicit_new_launch(self):
        seat = {**self.seat, 'id': 'failed', 'name': 'Failed before spawn'}
        self.store.save({'id': 'team', 'name': 'Team', 'seats': [self.seat, seat]})
        key, attempt = 'team/failed', uuid.uuid4().hex
        effective = self.manager._effective(seat)
        identity = new_launch_identity(ROOT, effective, key, attempt, uuid.uuid4().hex)
        base = 'cli-' + hashlib.sha256(key.encode()).hexdigest()[:8] + '-' + attempt[:12]
        path = self.data / 'api_seat_runtime' / attempt / 'config.json'
        snapshot = {**effective, 'attempt': attempt, 'base': base, 'ownership': identity}
        atomic_json(path, snapshot)
        record_spawn_outcome(path, snapshot, 'pending')
        record_spawn_outcome(path, snapshot, 'failed')
        before = self.files()
        self.manager.reconcile_runtime()
        self.assertEqual(self.files(), before)
        self.spawn.assert_not_called()
        process = Mock()
        process.poll.return_value = None
        def ended(*args, **kwargs):
            process.poll.return_value = 1
            process.returncode = 1
            return 1
        process.wait.side_effect = ended
        process.terminate.side_effect = ended
        self.spawn.side_effect = None
        self.spawn.return_value = process
        launched = self.manager.launch('team', 'failed')
        self.assertNotEqual(launched['attempt'], attempt)
        self.spawn.assert_called_once()
        self.assertEqual(path.with_name('launch.json').read_bytes(), before[str(path.with_name('launch.json').relative_to(self.data))])

    def test_terminal_cli_history_does_not_conflict_with_current_live_authenticated_owner(self):
        live = self.make_record(alive=True)
        # Terminal history deliberately has the newer mtime. Never choose a
        # winner by newest file/name rather than proof and launch identity.
        os.utime(self.old['path'], (time.time() + 600, time.time() + 600))
        before = self.files()
        def probe(birth):
            if birth['pid'] == self.old['birth']['pid']:
                return {'status': 'absent', 'process': None, 'error_code': 87}
            return open_verified_process(birth)
        with patch('runtime_adoption.open_verified_process', side_effect=probe):
            self.manager.reconcile_runtime()
            identity = live['snapshot']['ownership']
            payload = {'attempt': live['attempt'], 'launch_nonce': identity['launch_nonce'],
                'server_identity': identity['server_identity'], 'boot_id': self.manager.boot_id,
                'worker_pid': live['birth']['pid'], 'creation_filetime': live['birth']['creation_filetime'],
                'worker_root': live['birth']['worker_root']}
            reply = self.manager.observe_runtime_heartbeat(live['principal'], payload)
        self.assertTrue(reply['verified'])
        self.assertEqual(self.manager.attempts['team/cli']['id'], live['attempt'])
        self.assertIsNone(live['child'].poll())
        self.assertEqual(self.files(), before)
        self.spawn.assert_not_called()

    def test_two_unresolved_histories_still_conflict_with_current_boot_proof(self):
        live = self.make_record(alive=True)
        atomic_json(self.old['path'].with_name('receipt.json'), {**self.old['receipt'], 'child_exit_code': None})
        def probe(birth):
            if birth['pid'] == self.old['birth']['pid']:
                return {'status': 'absent', 'process': None, 'error_code': 87}
            return open_verified_process(birth)
        with patch('runtime_adoption.open_verified_process', side_effect=probe):
            self.manager.reconcile_runtime()
            identity = live['snapshot']['ownership']
            payload = {'attempt': live['attempt'], 'launch_nonce': identity['launch_nonce'],
                'server_identity': identity['server_identity'], 'boot_id': self.manager.boot_id,
                'worker_pid': live['birth']['pid'], 'creation_filetime': live['birth']['creation_filetime'],
                'worker_root': live['birth']['worker_root']}
            self.assertFalse(self.manager.observe_runtime_heartbeat(live['principal'], payload)['verified'])
        self.assertIsNone(live['child'].poll())
        self.spawn.assert_not_called()

    def test_dead_api_supervisor_receipt_is_not_cli_or_per_invocation_exit_proof(self):
        api = self.make_record(key='team/api', adapter='openai-compatible')
        before = self.files()
        with patch('runtime_adoption.open_verified_process', return_value={'status': 'absent', 'process': None, 'error_code': 87}):
            record = self.record(api)
        self.assertEqual(record['reason'], 'unproven_worker_exit')
        self.assertNotEqual(record['state'], 'exited')
        self.assertNotIn('exit_evidence', record)
        self.assertEqual(self.files(), before)
        self.spawn.assert_not_called()

    def test_corrupt_reference_cannot_be_retired_even_with_absent_probe_and_exit_receipt(self):
        snapshot = deepcopy(self.old['snapshot'])
        snapshot['ownership']['server_identity'] = '0' * 64
        atomic_json(self.old['path'], snapshot)
        before = self.files()
        with patch('runtime_adoption.open_verified_process', return_value={'status': 'absent', 'process': None, 'error_code': 87}):
            record = self.record()
            self.assertNotEqual(record['state'], 'exited')
            self.assertNotIn('exit_evidence', record)
            with self.assertRaises(SeatError):
                self.manager.launch('team', 'cli')
        self.assertEqual(self.files(), before)
        self.spawn.assert_not_called()


if __name__ == '__main__':
    unittest.main()
