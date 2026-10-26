"""Design-only phase profile of unchanged R2 production, NOT a timing gate.

Wraps the existing measurement fixture/call. Actual writes/fsync/locks remain
real. Wrapper overhead is retained. Original uninstrumented misses are preserved.
"""
from argparse import ArgumentParser
from collections import defaultdict
from contextlib import ExitStack
import json
from pathlib import Path
import statistics
import time
from unittest.mock import patch
import uuid

import measure_artifact_diagnostics as measurement


class TimedFile:
    def __init__(self, stream, profile, owner):
        self.stream, self.profile, self.owner = stream, profile, owner

    def __getattr__(self, name):
        return getattr(self.stream, name)

    def __enter__(self):
        self.stream.__enter__()
        return self

    def __exit__(self, *args):
        return self.stream.__exit__(*args)

    def write(self, value):
        return self.profile.timed(self.owner + '_stream_write', self.stream.write, value)

    def flush(self):
        return self.profile.timed(self.owner + '_flush', self.stream.flush)


class Profile:
    def __init__(self, store):
        self.store = store
        self.active = False
        self.persist = False
        self.atomic = False
        self.body_put = False
        self.seconds = defaultdict(float)
        self.calls = defaultdict(int)
        self.inventory_counts = []

    def timed(self, name, function, *args, **kwargs):
        if not self.active:
            return function(*args, **kwargs)
        started = time.perf_counter()
        try:
            return function(*args, **kwargs)
        finally:
            self.seconds[name] += time.perf_counter() - started
            self.calls[name] += 1

    def wrappers(self, stack):
        owner = self.store.diagnostic_store
        original_facade = self.store.quarantine_submission
        def facade(*args, **kwargs):
            self.active = True
            try:
                return original_facade(*args, **kwargs)
            finally:
                self.active = False
        stack.enter_context(patch.object(self.store, 'quarantine_submission', facade))
        for method in ('_snapshot_diagnostic_attachment', '_check_diagnostic_legacy'):
            original = getattr(self.store, method)
            def snapshot(*args, _original=original, **kwargs):
                return self.timed('facade_snapshot', _original, *args, **kwargs)
            stack.enter_context(patch.object(self.store, method, snapshot))
        original_persist = owner._persist_diagnostics
        def persist(*args, **kwargs):
            previous = self.persist
            self.persist = True
            try:
                return self.timed('persist_inclusive', original_persist, *args, **kwargs)
            finally:
                self.persist = previous
        stack.enter_context(patch.object(owner, '_persist_diagnostics', persist))
        for method, suffix in (('_validate_diagnostics', 'validate'), ('_encoded', 'size')):
            original = getattr(owner, method)
            def validator(*args, _original=original, _suffix=suffix, **kwargs):
                return self.timed(('persist_' if self.persist else 'pre_') + _suffix,
                                  _original, *args, **kwargs)
            stack.enter_context(patch.object(owner, method, validator))
        original_inventory = owner._body_inventory
        def inventory(*args, **kwargs):
            result = self.timed('inventory', original_inventory, *args, **kwargs)
            if self.active:
                self.inventory_counts.append({'objects': len(result[0]), 'bytes': result[1]})
            return result
        stack.enter_context(patch.object(owner, '_body_inventory', inventory))
        original_body = owner._put_bytes
        def body(*args, **kwargs):
            previous = self.body_put
            self.body_put = True
            try:
                return self.timed('body_put_inclusive', original_body, *args, **kwargs)
            finally:
                self.body_put = previous
        stack.enter_context(patch.object(owner, '_put_bytes', body))
        original_atomic = measurement.storage.atomic_json
        def atomic(*args, **kwargs):
            previous = self.atomic
            self.atomic = True
            try:
                return self.timed('atomic_json_inclusive', original_atomic, *args, **kwargs)
            finally:
                self.atomic = previous
        stack.enter_context(patch.object(measurement.storage, 'atomic_json', atomic))
        original_dump = json.dump
        def dump(*args, **kwargs):
            if self.atomic:
                return self.timed('metadata_dump_inclusive', original_dump, *args, **kwargs)
            return original_dump(*args, **kwargs)
        stack.enter_context(patch.object(json, 'dump', dump))
        original_open = Path.open
        def opened(path, *args, **kwargs):
            stream = original_open(path, *args, **kwargs)
            mode = kwargs.get('mode', args[0] if args else 'r')
            if self.active and 'x' in mode and (self.atomic or self.body_put):
                return TimedFile(stream, self, 'metadata' if self.atomic else 'body')
            return stream
        stack.enter_context(patch.object(Path, 'open', opened))
        original_fsync = measurement.storage.os.fsync
        def fsync(*args, **kwargs):
            if self.atomic or self.body_put:
                return self.timed('metadata_fsync' if self.atomic else 'body_fsync', original_fsync, *args, **kwargs)
            return original_fsync(*args, **kwargs)
        stack.enter_context(patch.object(measurement.storage.os, 'fsync', fsync))
        original_replace = Path.replace
        def replace(path, *args, **kwargs):
            if self.atomic or self.body_put:
                return self.timed('metadata_replace' if self.atomic else 'body_replace',
                                  original_replace, path, *args, **kwargs)
            return original_replace(path, *args, **kwargs)
        stack.enter_context(patch.object(Path, 'replace', replace))

    def result(self, measurement_result):
        values = dict(self.seconds)
        values['metadata_serialize_excluding_stream_write'] = (
            values.get('metadata_dump_inclusive', 0) - values.get('metadata_stream_write', 0))
        values['metadata_flush_fsync_replace'] = sum(values.get(key, 0) for key in
            ('metadata_flush', 'metadata_fsync', 'metadata_replace'))
        exclusive = ('facade_snapshot', 'pre_validate', 'pre_size', 'inventory', 'body_put_inclusive',
                     'persist_validate', 'persist_size', 'atomic_json_inclusive')
        values['other_hold'] = measurement_result['hold'] - sum(values.get(key, 0) for key in exclusive)
        return {**measurement_result, 'seconds': values, 'calls': dict(self.calls),
                'inside_hold_inventory': self.inventory_counts,
                'interpretation': 'Inclusive parents overlap children; exclusive top-level phases partition hold. Instrumented design profile, not acceptance.'}


def main():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument('--samples', type=int, default=10)
    args = parser.parse_args()
    if args.samples < 10:
        parser.error('At least10 design-profile samples required')
    original_path = measurement.ROOT / '.audit-tmp' / 'r2-diagnostic-measure-ef1a3a5d53d448db9591615c4cf67ffa.json'
    original = json.loads(original_path.read_text(encoding='utf-8'))
    assert original['pass'] is False and len(original['samples']) == 20
    samples = []
    for index in range(args.samples):
        case = measurement.ArtifactStoreTests()
        case.setUp()
        fixture_root = case.root
        try:
            store, audit = measurement.setup(case)
            profile = Profile(store)
            with ExitStack() as stack:
                profile.wrappers(stack)
                measured = measurement.measure(case, store, audit, 'heavy')
            result = profile.result(measured)
            result['sample'] = index + 1
            samples.append(result)
            print(json.dumps(result), flush=True)
        finally:
            case.doCleanups()
            assert not fixture_root.exists()
    result = {'kind': 'DESIGN PROFILE ONLY, original uninstrumented gate remains failed',
        'original_measurement': original, 'profile_samples': samples,
        'fsync_mocked': False, 'product_change': False,
        'median_instrumented_hold': statistics.median(row['hold'] for row in samples),
        'max_instrumented_hold': max(row['hold'] for row in samples),
        'limits': 'Instrumentation overhead retained; no retrospective phase attribution for original misses. Serialization-minus-write is wall time, not CPU accounting.'}
    path = measurement.ROOT / '.audit-tmp' / ('r2-diagnostic-profile-' + uuid.uuid4().hex + '.json')
    path.write_text(json.dumps(result, indent=2), encoding='utf-8')
    print(json.dumps({'profile_receipt': path.name, 'median': result['median_instrumented_hold'],
                      'max': result['max_instrumented_hold'], 'gate_status': 'original failure retained'}), flush=True)


if __name__ == '__main__':
    main()
