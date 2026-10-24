"""Explicit channel catalog setup for partial application unit fixtures."""
from unittest.mock import Mock, patch

import app
from channel_lifecycle import ChannelStore
from channel_service import ChannelService
from jobs import JobStore
from schedules import ScheduleStore
from summaries import SummaryStore


def initialize_app_channels(case, root, channels, *, enter_context=None):
    catalog = ChannelStore(root / 'fixture_channels.json')
    catalog.initialize(channels)
    service = ChannelService(catalog, engine=app.session_engine, messages=app.store,
        jobs=app.jobs if app.jobs is not None else JobStore(str(root / 'fixture_jobs.json')),
        schedules=ScheduleStore(str(root / 'fixture_schedules.json')),
        summaries=SummaryStore(str(root / 'fixture_summaries.json')), queue=app.agents.queue,
        settings={'channels': list(channels)}, save_settings=Mock(), migrate_cursors=Mock(),
        router=app.router, migrate_last_active=Mock())
    (enter_context or case.enterContext)(patch.object(app, 'channel_service', service))
    app.agents.queue.bind_channel_policy(lambda: service)
    return service
