"""Draft Python-only post-site guard. No product/resource imports or startup IO on import."""
import hashlib
import json
import ntpath
import os
from pathlib import Path
import socket
import sys
import threading
import time


def install_guard(label):
    """Python audit + explicit stat/existence/access wrappers, separate self-tests.

    Non-Python console-host behavior is outside this guard; launch cwd/env and
    native births bound that scope. DirEntry.stat, direct ctypes/pywin32 and
    non-Python access remain unobserved. No forbidden content is read or hashed.
    """
    if getattr(sys, '_channel_fixture_guard', False):
        return
    root = os.path.abspath(os.environ['CHANNEL_FIXTURE_ROOT'])
    policy = json.loads(os.environ['CHANNEL_GUARD_POLICY'])
    own_hash = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    assert own_hash == policy['guard_sha256'], 'Owned guard source changed'
    normalize = lambda value: os.path.normcase(os.path.abspath(os.fsdecode(value))).casefold()
    allowed_python_roots = [normalize(value) for value in policy['allowed_python_roots']]
    python_paths = [normalize(value or os.getcwd()) for value in sys.path]
    assert all(any(value == base or value.startswith(base + os.sep) for base in allowed_python_roots)
               for value in python_paths), 'Unexpected Python module search path'
    forbidden = [normalize(value) for value in policy['forbidden_roots']]
    forbidden.append(normalize(os.path.join(root, 'guard-selftest-forbidden')))
    ports = set(policy['forbidden_ports']) | {65500}
    local = threading.local()
    write_lock = threading.RLock()
    report = {'label': label, 'pid': os.getpid(), 'selftest_blocks': {}, 'selftest_results': {}, 'real_attempts': [], 'loopback_connections': [],
              'unobserved': ['DirEntry.stat', 'direct ctypes/pywin32 filesystem calls', 'non-Python code', 'trusted pre-hook site initialization'],
              'guard_sha256': own_hash,
              'python_paths': python_paths, 'coverage_start': 'owned_sitecustomize_or_explicit_entry_after_trusted_site_initialization',
              'coverage_started_at': time.time(), 'effective_env': {key: os.environ.get(key) for key in (
                  'HOME', 'USERPROFILE', 'APPDATA', 'LOCALAPPDATA', 'TEMP', 'TMP', 'HOMEDRIVE', 'HOMEPATH',
                  'XDG_CONFIG_HOME', 'XDG_DATA_HOME', 'XDG_CACHE_HOME', 'PYTHONPATH', 'PYTHONNOUSERSITE',
                  'PYTHONSTARTUP', 'PYTHONHOME', 'PYTHONUSERBASE', 'PYTHONINSPECT')}}
    phase = ['selftest']
    target = os.path.join(root, 'audit', 'guard-' + label + '-' + str(os.getpid()) + '.json')

    def save():
        if getattr(local, 'saving', False):
            return
        local.saving = True
        try:
            with write_lock:
                with open(target, 'w', encoding='utf-8') as stream:
                    json.dump(report, stream)
        finally:
            local.saving = False

    def blocked(kind):
        if phase[0] == 'selftest':
            report['selftest_blocks'][kind] = report['selftest_blocks'].get(kind, 0) + 1
        else:
            report['real_attempts'].append({'kind': kind})
        save()
        raise PermissionError('Fixture isolation guard refused access')

    def path_check(value, kind):
        if isinstance(value, (str, bytes, os.PathLike)):
            value = normalize(value)
            if any(value == base or value.startswith(base + os.sep) for base in forbidden):
                blocked(kind)

    def audit(event, args):
        if getattr(local, 'saving', False):
            return
        if event in ('open', 'os.listdir', 'os.scandir', 'os.remove', 'os.mkdir', 'os.rmdir') and args:
            path_check(args[0], event)
        elif event in ('os.rename', 'os.replace'):
            for value in args[:2]:
                path_check(value, event)
        elif event in ('socket.bind', 'socket.connect'):
            address = args[1]
            if isinstance(address, tuple) and len(address) > 1 and address[1] in ports:
                blocked(event)
            if isinstance(address, tuple) and address[0] not in ('127.0.0.1', 'localhost', '::1'):
                blocked('non_loopback_' + event)
            if event == 'socket.connect' and phase[0] == 'real':
                report['loopback_connections'].append({'host': address[0], 'port': address[1]})
                save()
    sys.addaudithook(audit)
    for name in ('stat', 'lstat'):
        original = getattr(os, name)
        def checked(value, *args, _original=original, _kind=name, **kwargs):
            path_check(value, _kind)
            return _original(value, *args, **kwargs)
        setattr(os, name, checked)
    # Python3.14 Windows existence probes can bypass os.stat entirely.
    wrapped = set()
    for module, prefix in ((os.path, 'os.path'), (ntpath, 'ntpath')):
        for name in ('exists', 'lexists', 'isfile', 'isdir', 'islink', 'isjunction'):
            assert hasattr(module, name), 'Required Windows path probe is absent'
            key = id(module), name
            if key in wrapped:
                continue
            wrapped.add(key)
            original = getattr(module, name)
            def checked(value, *args, _original=original, _kind=prefix + '.' + name, **kwargs):
                path_check(value, _kind)
                return _original(value, *args, **kwargs)
            setattr(module, name, checked)
    original_access = os.access
    def access(value, *args, **kwargs):
        path_check(value, 'os.access')
        return original_access(value, *args, **kwargs)
    os.access = access
    for name in ('exists', 'is_file', 'is_dir'):
        original = getattr(Path, name)
        def checked(value, *args, _original=original, _kind='Path.' + name, **kwargs):
            path_check(value, _kind)
            return _original(value, *args, **kwargs)
        setattr(Path, name, checked)
    fake = os.path.join(root, 'guard-selftest-forbidden', 'must-not-exist')
    probes = [('open', lambda: open(fake, 'rb')), ('os.listdir', lambda: os.listdir(os.path.dirname(fake))),
              ('os.scandir', lambda: os.scandir(os.path.dirname(fake))), ('stat', lambda: os.stat(fake)),
              ('lstat', lambda: os.lstat(fake))]
    for module, prefix in ((os.path, 'os.path'), (ntpath, 'ntpath')):
        for name in ('exists', 'lexists', 'isfile', 'isdir', 'islink', 'isjunction'):
            probes.append((prefix + '.' + name, lambda module=module, name=name: getattr(module, name)(fake)))
    probes.append(('os.access', lambda: os.access(fake, os.R_OK)))
    for name in ('exists', 'is_file', 'is_dir'):
        probes.append(('Path.' + name, lambda name=name: getattr(Path(fake), name)()))
    for kind, probe in probes:
        try:
            probe()
        except PermissionError:
            report['selftest_results'][kind] = True
        else:
            raise RuntimeError('Isolation self-test did not block ' + kind)
    for operation in ('connect', 'bind'):
        with socket.socket() as handle:
            try:
                getattr(handle, operation)(('127.0.0.1', 65500))
            except PermissionError:
                report['selftest_results']['socket.' + operation] = True
            else:
                raise RuntimeError('Isolation socket self-test did not block')
    assert all(report['selftest_blocks'].get(kind) for kind in
        ('open', 'os.listdir', 'os.scandir', 'stat', 'lstat', 'socket.connect', 'socket.bind'))
    assert all(report['selftest_results'].get(kind) for kind, _ in probes)
    phase[0] = 'real'
    sys._channel_fixture_guard = True
    save()


