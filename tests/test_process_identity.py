"""Windows birth verification against self and explicitly owned child handles."""
from copy import deepcopy
import importlib
import ctypes
from ctypes import wintypes
import os
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


@unittest.skipUnless(sys.platform == 'win32', 'Windows native handle contract')
class ProcessIdentityTests(unittest.TestCase):
    def setUp(self):
        self.identity = importlib.import_module('process_identity')

    def test_self_birth_retains_exact_decimal_filetime_and_absolute_image(self):
        birth = self.identity.capture_birth()
        self.assertEqual(birth['platform'], 'win32')
        self.assertEqual(birth['pid'], os.getpid())
        self.assertIs(type(birth['creation_filetime']), str)
        self.assertRegex(birth['creation_filetime'], r'^[0-9]+$')
        self.assertGreater(int(birth['creation_filetime']), 2 ** 53)
        self.assertTrue(Path(birth['image_path']).is_absolute())
        self.assertTrue(os.path.samefile(birth['image_path'], sys._base_executable))
        self.assertEqual(self.identity.capture_birth()['creation_filetime'], birth['creation_filetime'])
        # Independent kernel read verifies every FILETIME bit, including bits
        # that would disappear if the production value passed through float.
        kernel = ctypes.WinDLL('kernel32', use_last_error=True)
        kernel.GetCurrentProcess.restype = wintypes.HANDLE
        kernel.GetProcessTimes.argtypes = [wintypes.HANDLE] + [ctypes.POINTER(wintypes.FILETIME)] * 4
        times = [wintypes.FILETIME() for _ in range(4)]
        self.assertTrue(kernel.GetProcessTimes(kernel.GetCurrentProcess(), *(ctypes.byref(value) for value in times)))
        exact = (times[0].dwHighDateTime << 32) | times[0].dwLowDateTime
        self.assertEqual(birth['creation_filetime'], str(exact))

    def test_verified_self_handle_is_live_and_closes_idempotently(self):
        result = self.identity.open_verified_process(self.identity.capture_birth())
        self.assertEqual(result['status'], 'live')
        handle = result['process']
        try:
            self.assertEqual(handle.pid, os.getpid())
            self.assertIsNone(handle.poll())
        finally:
            handle.close()
            handle.close()

    def child(self, code=23):
        child = subprocess.Popen([sys._base_executable, '-u', '-c',
            'import sys; sys.stdin.buffer.read(1); sys.exit(' + str(code) + ')'],
            stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            creationflags=subprocess.CREATE_NO_WINDOW)
        def cleanup():
            if child.poll() is None:
                child.terminate()
            child.wait(timeout=5)
            if child.stdin and not child.stdin.closed:
                child.stdin.close()
        self.addCleanup(cleanup)
        return child

    def verified(self, child):
        birth = self.identity.capture_birth(child.pid)
        result = self.identity.open_verified_process(birth)
        self.assertEqual(result['status'], 'live')
        self.assertIsNotNone(result['process'])
        self.addCleanup(result['process'].close)
        return birth, result['process']

    def finish(self, child):
        child.stdin.write(b'x')
        child.stdin.flush()
        child.stdin.close()

    def assert_exit_code(self, code):
        child = self.child(code)
        birth, handle = self.verified(child)
        self.assertEqual(birth['pid'], child.pid)
        self.assertEqual(handle.pid, child.pid)
        self.assertTrue(hasattr(handle, 'args'))
        self.assertIsNone(handle.returncode)
        self.assertIsNone(handle.poll())
        self.finish(child)
        self.assertEqual(handle.wait(timeout=5), code)
        self.assertEqual(handle.poll(), code)
        self.assertEqual(handle.returncode, code)
        self.assertEqual(child.wait(timeout=5), code)
        exited = self.identity.open_verified_process(birth)
        try:
            # A fresh Windows image query after exit reports WinError31 here.
            # It cannot replace the original verified handle's exact exit proof.
            self.assertEqual(exited['status'], 'uncertain')
            self.assertEqual(exited['error_code'], 31)
            self.assertIsNone(exited['process'])
        finally:
            if exited['process'] is not None:
                exited['process'].close()

    def test_actual_owned_child_live_then_exit_23(self):
        self.assert_exit_code(23)

    def test_actual_exit_259_is_distinguished_from_still_active(self):
        self.assert_exit_code(259)

    def test_wait_timeout_does_not_invent_exit_or_terminate_child(self):
        child = self.child()
        _, handle = self.verified(child)
        with self.assertRaises(subprocess.TimeoutExpired):
            handle.wait(timeout=.05)
        self.assertIsNone(handle.poll())
        self.assertIsNone(child.poll())
        self.finish(child)
        self.assertEqual(handle.wait(timeout=5), 23)

    def test_retained_handle_terminate_and_wait_never_reopen_pid(self):
        child = self.child()
        _, handle = self.verified(child)
        with patch.object(self.identity, '_open_process', side_effect=AssertionError('PID reopened for control')) as opened:
            handle.terminate()
            code = handle.wait(timeout=5)
            self.assertEqual(handle.poll(), code)
            self.assertEqual(child.wait(timeout=5), code)
            handle.close()
            handle.close()
            opened.assert_not_called()

    def test_retained_handle_kill_targets_only_owned_child(self):
        child = self.child()
        _, handle = self.verified(child)
        with patch.object(self.identity, '_open_process', side_effect=AssertionError('PID reopened for kill')):
            handle.kill()
            self.assertEqual(handle.wait(timeout=5), child.wait(timeout=5))

    def test_changed_creation_time_is_mismatch_without_actuation(self):
        child = self.child()
        birth = self.identity.capture_birth(child.pid)
        changed = deepcopy(birth)
        changed['creation_filetime'] = str(int(changed['creation_filetime']) + 1)
        result = self.identity.open_verified_process(changed)
        self.assertEqual(result['status'], 'mismatch')
        self.assertIsNone(result['process'])
        self.assertIn('creation', result.get('reason', '').lower())
        self.assertIsNone(child.poll())
        self.finish(child)
        self.assertEqual(child.wait(timeout=5), 23)

    def test_changed_absolute_image_is_mismatch_without_actuation(self):
        child = self.child()
        birth = self.identity.capture_birth(child.pid)
        changed = {**birth, 'image_path': str(Path(birth['image_path']).with_name('different-fixture-image.exe'))}
        result = self.identity.open_verified_process(changed)
        self.assertEqual(result['status'], 'mismatch')
        self.assertIsNone(result['process'])
        self.assertIn('image', result.get('reason', '').lower())
        self.assertIsNone(child.poll())

    def test_absolute_image_comparison_is_case_normalized(self):
        child = self.child()
        birth = self.identity.capture_birth(child.pid)
        birth['image_path'] = birth['image_path'].swapcase()
        result = self.identity.open_verified_process(birth)
        self.assertEqual(result['status'], 'live')
        self.addCleanup(result['process'].close)
        self.assertIsNone(result['process'].poll())

    def test_access_denied_is_uncertain_and_only_invalid_parameter_is_absent(self):
        birth = self.identity.capture_birth()
        for winerror, expected in ((5, 'uncertain'), (87, 'absent'), (6, 'uncertain')):
            error = OSError('fixture native open refused')
            error.winerror = winerror
            with self.subTest(winerror=winerror), patch.object(self.identity, '_open_process', side_effect=error):
                result = self.identity.open_verified_process(birth)
                self.assertEqual(result['status'], expected)
                self.assertIsNone(result['process'])

    def test_post_open_query_failure_87_is_uncertain_and_closes_actual_handle(self):
        birth = self.identity.capture_birth()
        opened = []
        actual_open = self.identity._open_process
        def capture_open(pid, access):
            handle = actual_open(pid, access)
            opened.append(handle)
            return handle
        error = OSError('fixture metadata query refused after successful open')
        error.winerror = 87
        with patch.object(self.identity, '_open_process', side_effect=capture_open), \
             patch.object(self.identity, '_birth', side_effect=error):
            result = self.identity.open_verified_process(birth)
        self.assertEqual(len(opened), 1)
        kernel = ctypes.WinDLL('kernel32', use_last_error=True)
        kernel.GetHandleInformation.argtypes = [wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD)]
        kernel.GetHandleInformation.restype = wintypes.BOOL
        flags = wintypes.DWORD()
        self.assertFalse(kernel.GetHandleInformation(opened[0], ctypes.byref(flags)), 'real opened handle leaked')
        self.assertEqual(ctypes.get_last_error(), 6)
        self.assertEqual(result['status'], 'uncertain', 'query failure cannot prove PID absence')
        self.assertIsNone(result['process'])

    def test_invalid_pid_rejects_capture_and_probe_before_native_open(self):
        birth = self.identity.capture_birth()
        for pid in (True, False, 0, -1, 2 ** 32, '123', 1.5):
            with self.subTest(pid=pid), patch.object(self.identity, '_open_process') as opened:
                with self.assertRaises(ValueError):
                    self.identity.capture_birth(pid)
                with self.assertRaises(ValueError):
                    self.identity.open_verified_process({**birth, 'pid': pid})
                opened.assert_not_called()

    def test_malformed_creation_timestamp_rejects_before_native_open(self):
        birth = self.identity.capture_birth()
        for value in (None, True, 123, 1.5, '', '-1', '1.2', 'not-a-time', str(2 ** 64)):
            with self.subTest(timestamp=value), patch.object(self.identity, '_open_process') as opened:
                with self.assertRaises(ValueError):
                    self.identity.open_verified_process({**birth, 'creation_filetime': value})
                opened.assert_not_called()

    def test_malformed_image_or_birth_record_rejects_before_native_open(self):
        birth = self.identity.capture_birth()
        invalid = [None, [], True, {}, {key: value for key, value in birth.items() if key != 'image_path'}]
        invalid += [{**birth, 'image_path': value} for value in (None, True, '', 'relative-python.exe')]
        for value in invalid:
            with self.subTest(metadata=value), patch.object(self.identity, '_open_process') as opened:
                with self.assertRaises(ValueError):
                    self.identity.open_verified_process(value)
                opened.assert_not_called()


if __name__ == '__main__':
    unittest.main()
