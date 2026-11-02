"""Shared limits for session design, independent of execution concurrency."""

DEFAULT_POLICY = {'max_roles': 16, 'max_participants_per_phase': 16,
                  'max_phases': 12, 'max_prompt_chars': 1000, 'max_total_turns': 128}
LEGACY_POLICY = {'max_roles': 6, 'max_participants_per_phase': 4,
                 'max_phases': 6, 'max_prompt_chars': 200, 'max_total_turns': 24}


def capacity_policy(overrides=None):
    if overrides is None:
        return dict(DEFAULT_POLICY)
    if not isinstance(overrides, dict) or overrides.keys() - DEFAULT_POLICY.keys():
        raise ValueError('Session capacity must contain only declared limit settings.')
    result = dict(DEFAULT_POLICY)
    for key, value in overrides.items():
        if type(value) is not int or value < 1:
            raise ValueError(f'{key} must be a positive integer.')
        result[key] = value
    ceilings = {'max_roles': 256, 'max_participants_per_phase': 256, 'max_phases': 64,
                'max_prompt_chars': 10000, 'max_total_turns': 1024}
    for key, ceiling in ceilings.items():
        if result[key] > ceiling:
            raise ValueError(f'{key} cannot exceed {ceiling}.')
    if result['max_total_turns'] < result['max_participants_per_phase']:
        raise ValueError('max_total_turns must cover max_participants_per_phase.')
    return result


def policy_description(policy=None):
    limits = capacity_policy(policy)
    return (f"Limits: {limits['max_roles']} roles, {limits['max_participants_per_phase']} participants per phase, "
            f"{limits['max_phases']} phases, {limits['max_prompt_chars']} characters per phase prompt, "
            f"{limits['max_total_turns']} total logical turns. "
            'Count every participant occurrence, including the output phase. '
            'Turns execute sequentially; concurrency never removes members. '
            'Keep full task context and source in review inputs. Do not truncate or split rounds to fit.')


def public_capacity(policy=None):
    limits = capacity_policy(policy)
    return {'policy': limits, 'limits_text': policy_description(limits),
            'execution': {'mode': 'sequential', 'active_turns_per_session': 1}}
