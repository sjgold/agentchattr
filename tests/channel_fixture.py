"""Explicit channel catalog setup for partial application unit fixtures."""
from unittest.mock import Mock, patch

import app
import mcp_bridge
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
    (enter_context or case.enterContext)(patch.object(mcp_bridge, 'channel_policy_getter', lambda: service))
    app.agents.queue.bind_channel_policy(lambda: service)
    return service


def initialize_mcp_channels(case, root, channels, *, engine=None, enter_context=None):
    """Explicit policy for standalone MCP fixtures, without app.configure."""
    if engine is None:
        from agents import AgentTrigger
        from session_engine import SessionEngine
        from session_store import SessionStore
        engine = SessionEngine(SessionStore(str(root / 'fixture_mcp_sessions.json')),
            mcp_bridge.store, AgentTrigger(mcp_bridge.registry, str(root)), mcp_bridge.registry)
    catalog = ChannelStore(root / 'fixture_mcp_channels.json')
    catalog.initialize(channels)
    service = ChannelService(catalog, engine=engine, messages=mcp_bridge.store,
        jobs=JobStore(str(root / 'fixture_mcp_jobs.json')),
        schedules=ScheduleStore(str(root / 'fixture_mcp_schedules.json')),
        summaries=SummaryStore(str(root / 'fixture_mcp_summaries.json')), queue=engine._trigger.queue,
        settings={'channels': list(channels)}, save_settings=Mock(), migrate_cursors=Mock(),
        router=None, migrate_last_active=None)
    (enter_context or case.enterContext)(patch.object(mcp_bridge, 'channel_policy_getter', lambda: service))
    engine._trigger.queue.bind_channel_policy(lambda: service)
    return service
