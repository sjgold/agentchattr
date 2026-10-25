"""Private immutable artifact authority; callers must enforce seat/claim access."""
from copy import deepcopy
from pathlib import Path
import secrets
import time

from api_seats import atomic_json
from artifact_store import ArtifactConflict, ArtifactUnavailable, _fields, _hex
from artifact_protocol import (MAX_BRIEF_RECORD_BYTES, validate_brief, validate_owner,
                               _owned_path, _size)
from launcher import LaunchError, startup_lock
from sealed_result_io import read_bounded_json


class ArtifactBriefStore:
    def __init__(self, data_dir):
        self.root = Path(data_dir).absolute()
        _owned_path(self.root, self.root)

    def _path(self, brief_id):
        return _owned_path(self.root, self.root / 'artifact_briefs' / 'requests' / (_hex(brief_id) + '.json'))

    @staticmethod
    def _owner_matches(body, owner):
        producer = body['producer']
        if (owner['dispatch_id'] != body['dispatch_id']
                or owner['seat_identity_id'] != producer['identity_id']
                or any(owner[key] != producer[key] for key in ('adapter', 'launch_attempt', 'launch_nonce', 'fingerprint'))):
            raise ArtifactConflict('Artifact brief authority differs from its producer.')

    def put(self, body, *, owner):
        value, owner = validate_brief(body), validate_owner(owner)
        self._owner_matches(value, owner)
        path = self._path(value['brief_id'])
        try:
            with startup_lock(_owned_path(self.root, path.with_suffix('.lock')), time.monotonic() + 10):
                if path.exists():
                    prior = self.get_private(value['brief_id'])
                    public = {key: item for key, item in prior.items() if key != '_artifact_seal'}
                    if public != value or prior['_artifact_seal']['owner'] != owner:
                        raise ArtifactConflict('Artifact briefs are immutable; create a new request.')
                else:
                    private = {**value, '_artifact_seal': {'version': 1,
                        'seal_secret': secrets.token_hex(32), 'owner': owner}}
                    _size(private, MAX_BRIEF_RECORD_BYTES)
                    atomic_json(path, private)
        except (OSError, LaunchError):
            raise ArtifactUnavailable('Artifact brief write did not complete.') from None
        return value['brief_id']

    def get_private(self, brief_id):
        path = self._path(brief_id)
        try:
            value = read_bounded_json(path, MAX_BRIEF_RECORD_BYTES)
            if not isinstance(value, dict):
                raise ValueError('Not an object')
            private = value.get('_artifact_seal')
            public = {key: item for key, item in value.items() if key != '_artifact_seal'}
            validate_brief(public)
            if public['brief_id'] != brief_id:
                raise ValueError('Different brief')
            _fields(private, ('version', 'seal_secret', 'owner'))
            if type(private['version']) is not int or private['version'] != 1:
                raise ValueError('Unknown authority version')
            _hex(private['seal_secret'], 64)
            self._owner_matches(public, validate_owner(private['owner']))
            return deepcopy(value)
        except (OSError, ValueError, TypeError, KeyError, RecursionError):
            raise ArtifactUnavailable('Artifact brief is unavailable; no source fallback is permitted.') from None
