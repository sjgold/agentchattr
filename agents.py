"""Agent trigger: persist each envelope before a wrapper can claim ownership."""

import logging
from dispatch_queue import QueueStore

log = logging.getLogger(__name__)


class AgentTrigger:
    def __init__(self, registry, data_dir: str = "./data"):
        self._registry = registry
        self.queue = QueueStore(data_dir)

    def is_available(self, name: str) -> bool:
        return self._registry.is_registered(name)

    def get_status(self) -> dict:
        from mcp_bridge import is_online, is_active, get_role
        instances = self._registry.get_all()
        status = {
            name: {
                "available": is_online(name),
                "busy": is_active(name),
                "label": info["label"],
                "color": info["color"],
                "role": get_role(name),
            }
            for name, info in instances.items()
        }
        try:
            status['_queue'] = self.queue.status()
        except (OSError, ValueError):
            status['_queue'] = {'error': 'Queue storage unavailable. Pending work is held.'}
        return status

    async def trigger(self, agent_name: str, message: str = "", channel: str = "general",
                      job_id: int | None = None, **kwargs):
        return self.trigger_sync(agent_name, message, channel, job_id, **kwargs)

    def trigger_sync(self, agent_name: str, message: str = "", channel: str = "general",
                     job_id: int | None = None, **kwargs):
        instance = self._registry.get_instance(agent_name)
        if not instance:
            raise ValueError('The target seat is not registered; no future identity was assigned this work.')
        return self._enqueue_instance(instance, message, channel, job_id, **kwargs)

    def trigger_identity_sync(self, identity_id, *, dispatch_id, message='',
                              channel='general', job_id=None, prompt=''):
        matches = [value for value in self._registry.get_all().values()
                   if value['identity_id'] == identity_id and value['state'] == 'active']
        if len(matches) != 1:
            raise ValueError('The resolved seat identity is no longer available.')
        return self._enqueue_instance(matches[0], message, channel, job_id,
                                      dispatch_id=dispatch_id, prompt=prompt)

    def _enqueue_instance(self, instance, message, channel, job_id, **kwargs):
        entry = {'sender': message.split(':')[0].strip() if ':' in message else '?',
                 'text': message, 'channel': channel}
        prompt = kwargs.get('prompt', '')
        if isinstance(prompt, str) and prompt.strip():
            entry['prompt'] = prompt
        if job_id is not None:
            entry['job_id'] = job_id
        for key in ('dispatch_id', 'review_brief_id', 'run_id', 'turn_id', 'attempt_id', 'input_revision'):
            if key in kwargs:
                entry[key] = kwargs[key]
        record = self.queue.enqueue(instance, entry)
        log.info('Persisted dispatch %s for %s (channel=%s)',
                 record['envelope']['dispatch_id'], instance['name'], channel)
        return record
