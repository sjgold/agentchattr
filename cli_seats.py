"""Explicit CLI launch contracts. No command is probed or launched on import/save."""
from copy import deepcopy
import os
from pathlib import Path
import re
import math
import string
import subprocess

from api_seats import SeatError


def cli_templates(config):
    return {name: deepcopy(cfg) for name, cfg in config.get('agents', {}).items()
            if cfg.get('type') != 'api' and isinstance(cfg.get('command'), str)}


def _arguments(value, field):
    if not isinstance(value, list) or any(not isinstance(v, str) or not v or
            any(ord(c) < 32 for c in v) for v in value):
        raise SeatError(f'{field} must be a list of nonempty arguments without control characters.')
    return value


def _setting_args(template, setting, value):
    mapping = template.get(f'cli_{setting}_args')
    if mapping is None:
        if value is not None:
            raise SeatError(f'This CLI template does not declare a {setting} argument contract.')
        return []
    mapping = _arguments(mapping, f'cli_{setting}_args')
    fields = []
    try:
        for argument in mapping:
            for _, name, spec, conversion in string.Formatter().parse(argument):
                if name is not None:
                    if name != setting or spec or conversion:
                        raise ValueError('Unsupported placeholder')
                    fields.append(name)
    except ValueError:
        raise SeatError(f'CLI {setting} mapping must contain exactly one {{{setting}}} placeholder.') from None
    if fields != [setting]:
        raise SeatError(f'CLI {setting} mapping must contain exactly one {{{setting}}} placeholder.')
    return [arg.format(**{setting: value}) for arg in mapping] if value is not None else []


def build_cli_args(seat, template):
    result = list(_arguments(template.get('cli_args', []), 'cli_args'))
    for setting in ('model', 'reasoning'):
        value = seat[setting]
        if value is not None and (not isinstance(value, str) or not value.strip() or
                len(value) > 256 or value.startswith('-') or any(ord(c) < 32 for c in value)):
            raise SeatError(f'CLI {setting} must be a nonempty value without leading dash or control characters.')
        if setting == 'reasoning' and value is not None and value not in template.get('reasoning_efforts', []):
            raise SeatError('This CLI template does not declare the selected reasoning effort.')
        result.extend(_setting_args(template, setting, value))
    return result

def build_fresh_context_args(template, context_id):
    """Expand an explicitly verified adapter contract, never inferred flags."""
    if template.get('cli_fresh_context_verified') is not True or not template.get('cli_fresh_context_args'):
        raise SeatError('unsupported_clean_context: this adapter has no verified fresh-context launch contract.')
    if not isinstance(context_id, str) or not re.fullmatch(r'[A-Za-z0-9_.-]{1,128}', context_id):
        raise SeatError('Fresh context ID must be a bounded plain identifier.')
    mapping = _arguments(template['cli_fresh_context_args'], 'cli_fresh_context_args')
    fields = []
    try:
        for argument in mapping:
            for _, name, spec, conversion in string.Formatter().parse(argument):
                if name is not None:
                    if name != 'context_id' or spec or conversion:
                        raise ValueError('Unsupported placeholder')
                    fields.append(name)
    except ValueError:
        raise SeatError('Fresh-context arguments require exactly one {context_id} placeholder.') from None
    if fields != ['context_id']:
        raise SeatError('Fresh-context arguments require exactly one {context_id} placeholder.')
    return [argument.format(context_id=context_id) for argument in mapping]


def validate_cli_seat(seat, template):
    if template.get('type') == 'api' or not isinstance(template.get('command'), str) or not template['command'].strip():
        raise SeatError('Select a configured CLI client template.')
    if seat['launch_profile'] != 'standard' or seat['secret_ref'] != '':
        raise SeatError('CLI seats use the standard launch profile and existing native login; secret_ref must be empty.')
    if not isinstance(template.get('cwd', '.'), str):
        raise SeatError('CLI working directory must be a path string.')
    from wrapper import _resolve_mcp_inject, _VALID_INJECT_MODES
    injection = _resolve_mcp_inject('', template)
    if injection.get('mcp_inject') not in _VALID_INJECT_MODES:
        raise SeatError('This client requires a declared, supported MCP identity injection contract.')
    if injection.get('mcp_inject') in ('env', 'env_content'):
        if not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*', injection.get('mcp_env_var', '')):
            raise SeatError('CLI MCP environment-variable name is invalid.')
    strip = template.get('strip_env', [])
    if not isinstance(strip, list) or any(not isinstance(v, str) or not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*', v) for v in strip):
        raise SeatError('CLI strip_env must be a list of environment-variable names.')
    delay = template.get('inject_delay', 0.3)
    if isinstance(delay, bool) or not isinstance(delay, (int, float)) or not math.isfinite(delay) or not 0 <= delay <= 5:
        raise SeatError('CLI inject_delay must be a finite number between zero and five seconds.')
    if template.get('enter_backend', 'console_input') not in ('console_input', 'wm_setfocus'):
        raise SeatError('Unsupported Windows console input backend.')
    efforts = template.get('reasoning_efforts', [])
    if not isinstance(efforts, list) or any(not isinstance(v, str) or not v for v in efforts):
        raise SeatError('CLI reasoning_efforts must be a list of supported strings.')
    build_cli_args(seat, template)
    if 'cli_version_args' in template:
        _arguments(template['cli_version_args'], 'cli_version_args')
    return deepcopy(seat)


def config_resource(template, project_dir):
    from wrapper import _resolve_mcp_inject
    cfg = _resolve_mcp_inject('', template)
    if cfg.get('mcp_inject') != 'settings_file':
        return None
    raw = cfg.get('mcp_settings_path')
    if not isinstance(raw, str) or not raw:
        raise SeatError('A settings-file client requires mcp_settings_path.')
    target = Path(raw).expanduser()
    if not target.is_absolute():
        target = Path(project_dir) / target
    return os.path.normcase(str(target.resolve()))


def probe_version(command, arguments, timeout=15):
    """Only called by an explicit Launch and only for a declared version contract."""
    if not arguments:
        return None
    options = {'timeout': timeout, 'stdin': subprocess.DEVNULL, 'stdout': subprocess.PIPE,
               'stderr': subprocess.DEVNULL, 'text': True, 'encoding': 'utf-8', 'errors': 'replace'}
    if os.name == 'nt':
        options['creationflags'] = subprocess.CREATE_NO_WINDOW
    try:
        result = subprocess.run([command, *_arguments(arguments, 'cli_version_args')], **options)
        # Persist a version number only, never arbitrary CLI output or diagnostics.
        match = re.search(r'\b\d+\.\d+(?:\.\d+)?(?:[-+][A-Za-z0-9.]+)?\b', result.stdout or '')
        return match.group(0) if result.returncode == 0 and match else None
    except (OSError, subprocess.TimeoutExpired):
        return None
