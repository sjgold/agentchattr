"""Verify Windows process birth before retaining any lifecycle authority.

Local metadata is not sufficient ownership proof by itself. The runtime manager
also verifies launch provenance and fresh authenticated adapter evidence.
"""
import ctypes
from ctypes import wintypes
import math
import os
from pathlib import Path
import re
import subprocess
import sys
import time

_QUERY = 0x1000
_SYNCHRONIZE = 0x00100000
_TERMINATE = 0x0001
_kernel = None


def _api():
    global _kernel
    if _kernel is None:
        kernel = ctypes.WinDLL('kernel32', use_last_error=True)
        definitions = {
            'OpenProcess': ([wintypes.DWORD, wintypes.BOOL, wintypes.DWORD], wintypes.HANDLE),
            'CloseHandle': ([wintypes.HANDLE], wintypes.BOOL),
            'GetProcessTimes': ([wintypes.HANDLE] + [ctypes.POINTER(wintypes.FILETIME)] * 4, wintypes.BOOL),
            'QueryFullProcessImageNameW': ([wintypes.HANDLE, wintypes.DWORD, wintypes.LPWSTR,
                                          ctypes.POINTER(wintypes.DWORD)], wintypes.BOOL),
            'WaitForSingleObject': ([wintypes.HANDLE, wintypes.DWORD], wintypes.DWORD),
            'GetExitCodeProcess': ([wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD)], wintypes.BOOL),
            'TerminateProcess': ([wintypes.HANDLE, wintypes.UINT], wintypes.BOOL),
        }
        for name, (arguments, result) in definitions.items():
            function = getattr(kernel, name)
            function.argtypes, function.restype = arguments, result
        _kernel = kernel
    return _kernel


def _pid(value):
    if type(value) is not int or not 0 < value <= 0xffffffff:
        raise ValueError('Process ID must be a positive Windows DWORD integer.')
    return value


def _open_process(pid, access):
    handle = _api().OpenProcess(access, False, _pid(pid))
    if not handle:
        raise ctypes.WinError(ctypes.get_last_error())
    return handle


def _birth(handle, pid):
    times = [wintypes.FILETIME() for _ in range(4)]
    if not _api().GetProcessTimes(handle, *(ctypes.byref(value) for value in times)):
        raise ctypes.WinError(ctypes.get_last_error())
    image = ctypes.create_unicode_buffer(32768)
    length = wintypes.DWORD(len(image))
    if not _api().QueryFullProcessImageNameW(handle, 0, image, ctypes.byref(length)):
        raise ctypes.WinError(ctypes.get_last_error())
    created = (times[0].dwHighDateTime << 32) | times[0].dwLowDateTime
    return {'platform': 'win32', 'pid': pid, 'creation_filetime': str(created), 'image_path': image.value}


def capture_birth(pid=None):
    if sys.platform != 'win32':
        return {'platform': sys.platform, 'supported': False, 'status': 'unsupported'}
    pid = _pid(os.getpid() if pid is None else pid)
    handle = _open_process(pid, _QUERY | _SYNCHRONIZE)
    try:
        return _birth(handle, pid)
    finally:
        _api().CloseHandle(handle)


class OwnedProcessHandle:
    """A verified retained kernel handle, never a later PID lookup for control."""
    def __init__(self, handle, pid):
        self._handle, self.pid = handle, pid
        self.args = ['owned-process', str(pid)]
        self.returncode = None

    def _checked(self):
        if self._handle is None:
            raise ValueError('Owned process handle is closed.')
        return self._handle

    def poll(self):
        result = _api().WaitForSingleObject(self._checked(), 0)
        if result == 0x102:
            return None
        if result != 0:
            raise ctypes.WinError(ctypes.get_last_error())
        code = wintypes.DWORD()
        if not _api().GetExitCodeProcess(self._checked(), ctypes.byref(code)):
            raise ctypes.WinError(ctypes.get_last_error())
        self.returncode = code.value
        return self.returncode

    def wait(self, timeout=None):
        if timeout is not None and (type(timeout) not in (int, float) or not math.isfinite(timeout)):
            raise ValueError('Process wait requires a finite timeout.')
        deadline = None if timeout is None else time.monotonic() + max(0, timeout)
        while True:
            milliseconds = (0xffffffff if deadline is None else
                            min(0xfffffffe, math.ceil(max(0, deadline - time.monotonic()) * 1000)))
            result = _api().WaitForSingleObject(self._checked(), milliseconds)
            if result == 0:
                return self.poll()
            if result != 0x102:
                raise ctypes.WinError(ctypes.get_last_error())
            if deadline is not None and time.monotonic() >= deadline:
                raise subprocess.TimeoutExpired(self.args, timeout)

    def terminate(self):
        if self.poll() is not None:
            return
        if not _api().TerminateProcess(self._checked(), 1):
            raise ctypes.WinError(ctypes.get_last_error())

    kill = terminate

    def close(self):
        if self._handle is not None:
            _api().CloseHandle(self._handle)
            self._handle = None


def open_verified_process(birth):
    if sys.platform != 'win32':
        return {'status': 'unsupported', 'process': None, 'reason': 'unsupported_platform'}
    if not isinstance(birth, dict):
        raise ValueError('Process birth metadata must be a mapping.')
    pid = _pid(birth.get('pid'))
    created, image = birth.get('creation_filetime'), birth.get('image_path')
    if (not isinstance(created, str) or not re.fullmatch(r'[0-9]{1,20}', created)
            or not 0 < int(created) <= 0xffffffffffffffff
            or not isinstance(image, str) or '\0' in image or not Path(image).is_absolute()
            or birth.get('platform') != 'win32'):
        raise ValueError('Process birth requires exact creation time and absolute executable identity.')
    handle = None
    try:
        handle = _open_process(pid, _QUERY | _SYNCHRONIZE | _TERMINATE)
        observed = _birth(handle, pid)
        if int(created) != int(observed['creation_filetime']):
            return {'status': 'mismatch', 'process': None, 'reason': 'creation_time_mismatch'}
        if os.path.normcase(image) != os.path.normcase(observed['image_path']):
            return {'status': 'mismatch', 'process': None, 'reason': 'image_mismatch'}
        process = OwnedProcessHandle(handle, pid)
        code = process.poll()
        handle = None  # Ownership transfers only after all verification succeeds.
        return {'status': 'live' if code is None else 'exited', 'process': process, 'exit_code': code}
    except OSError as exc:
        # Only OpenProcess can establish PID absence. A failed identity query
        # on an opened handle, even error87, leaves ownership uncertain.
        absent = handle is None and getattr(exc, 'winerror', None) == 87
        return {'status': 'absent' if absent else 'uncertain', 'process': None,
                'reason': 'pid_absent' if absent else 'process_probe_failed',
                'error_code': getattr(exc, 'winerror', None)}
    finally:
        if handle is not None:
            _api().CloseHandle(handle)
