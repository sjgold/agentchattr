"""App-owned wrapper source declarations; no registration or launch authority."""
from copy import deepcopy
import hashlib
from pathlib import Path
import re


# Enabled only by the separately reviewed wrapper-purpose implementation.
SUPPORTED_CAPABILITIES = ()
SOURCE_FILES = {
    'cli': ('api_invocation.py', 'api_seats.py', 'artifact_delivery.py', 'artifact_protocol.py', 'artifact_store.py', 'artifact_worker.py',
        'channel_guards.py', 'channel_lifecycle.py', 'cli_seats.py', 'cli_worker.py', 'config_loader.py',
        'invocation_evidence.py', 'launcher.py', 'mcp_proxy.py', 'process_identity.py', 'queue_client.py',
        'runtime_ownership.py', 'runtime_protocol.py', 'sealed_result_io.py', 'turn_events.py', 'turn_recovery.py',
        'wrapper.py', 'wrapper_unix.py', 'wrapper_windows.py'),
    'openai-compatible': ('api_invocation.py', 'api_seats.py', 'artifact_delivery.py', 'artifact_protocol.py',
        'artifact_store.py', 'artifact_worker.py', 'channel_guards.py', 'channel_lifecycle.py',
        'cli_result_recovery.py', 'cli_seats.py', 'config_loader.py', 'document_inputs.py',
        'invocation_evidence.py', 'launcher.py', 'mcp_proxy.py', 'participant_replacement_store.py',
        'process_identity.py', 'queue_client.py', 'result_delivery.py', 'result_outbox.py',
        'review_brief.py', 'runtime_ownership.py', 'runtime_protocol.py', 'sealed_result_io.py',
        'session_capacity.py', 'session_store.py', 'turn_events.py', 'turn_recovery.py',
        'wrapper.py', 'wrapper_api.py', 'wrapper_unix.py', 'wrapper_windows.py'),
}


def validate_manifest(value, adapter):
    if (not isinstance(adapter, str) or adapter not in SOURCE_FILES or not isinstance(value, dict)
            or set(value) != {'version', 'adapter', 'capabilities', 'sources'}
            or type(value['version']) is not int or value['version'] != 1
            or value['adapter'] != adapter or value['capabilities'] not in ([], ['artifact-v1'])
            or not isinstance(value['sources'], dict) or set(value['sources']) != set(SOURCE_FILES[adapter])
            or any(not isinstance(digest, str) or not re.fullmatch('[0-9a-f]{64}', digest)
                   for digest in value['sources'].values())):
        raise ValueError('Wrapper protocol declaration is malformed or unsupported.')
    return deepcopy(value)


def _source_hashes(root, adapter):
    root = Path(root).resolve()
    result = {}
    for name in SOURCE_FILES[adapter]:
        source = root / name
        if source.resolve().parent != root:
            raise ValueError('Wrapper source is outside the owned checkout.')
        result[name] = hashlib.sha256(source.read_bytes()).hexdigest()
    return result


def build_manifest(root, adapter):
    if not isinstance(adapter, str) or adapter not in SOURCE_FILES:
        raise ValueError('Unsupported wrapper adapter.')
    try:
        sources = _source_hashes(root, adapter)
    except (OSError, ValueError):
        return None
    return validate_manifest({'version': 1, 'adapter': adapter,
        'capabilities': list(SUPPORTED_CAPABILITIES), 'sources': sources}, adapter)


def sources_match(root, manifest):
    try:
        value = validate_manifest(manifest, manifest.get('adapter') if isinstance(manifest, dict) else None)
        return _source_hashes(root, value['adapter']) == value['sources']
    except (OSError, ValueError):
        return False
