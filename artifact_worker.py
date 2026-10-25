"""Temporary unrouted TDD scaffold; production capability stays disabled."""
from copy import deepcopy


class ArtifactWorkerError(ValueError):
    def __init__(self, code='artifact_invalid_dispatch'):
        super().__init__('Artifact dispatch is unavailable.')
        self.code = code


def validate_artifact_dispatch(record, *, runtime_path, manifest, consumer_id):
    return deepcopy(record['envelope'])


def preflight_cli_artifact(record, *, runtime_path, manifest, consumer_id,
                          fetch_brief, submit_saved, injected_dispatch_id=None, held_dispatch_id=None):
    return {'action': 'wait', 'prompt': None, 'admission': None, 'reason': None}
