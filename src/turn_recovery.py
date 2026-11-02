"""Bounded recovery policy shared by run creation and operator actions."""
import math

from turn_events import EventValidationError


DEFAULT_POLICY = {'ack_timeout': 30, 'response_timeout': 900, 'monitor_interval': 1}
FAILURE_CATEGORIES = frozenset(('provider_timeout', 'http_error', 'transport_closed', 'process_crash',
                              'malformed_session_response', 'provider_failure', 'local_delivery_failure', 'empty_completion'))


def positive_seconds(value, label):
    if type(value) not in (int, float) or not math.isfinite(value) or value <= 0:
        raise EventValidationError(f'{label} must be a positive finite number of seconds.')
    return value


def recovery_policy(overrides=None):
    if overrides is None:
        return dict(DEFAULT_POLICY)
    if not isinstance(overrides, dict) or overrides.keys() - DEFAULT_POLICY.keys():
        raise EventValidationError('Recovery policy accepts acknowledgement, response and monitor limits only.')
    result = dict(DEFAULT_POLICY)
    for key, value in overrides.items():
        result[key] = positive_seconds(value, key)
    return result
