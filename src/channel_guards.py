"""Enter channel policy before a synchronous store method takes its own lock."""
from functools import wraps
from inspect import signature


def channel_write(resolve_channels):
    def decorate(method):
        parameters = signature(method)
        @wraps(method)
        def guarded(self, *args, **kwargs):
            getter = self._channel_policy_getter
            if getter is None:
                return method(self, *args, **kwargs)  # Standalone store algorithm.
            policy = getter()  # Configured runtime binds even when unavailable.
            with policy._boundary():
                policy.catalog.snapshot()
                bound = parameters.bind(self, *args, **kwargs)
                bound.apply_defaults()
                for channel in set(resolve_channels(self, bound.arguments)):
                    policy.require_active(channel)
                return method(self, *args, **kwargs)
        return guarded
    return decorate
