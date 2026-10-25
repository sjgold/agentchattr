"""Real configure ordering with real owners; thread starts are recorded doubles."""
from contextlib import ExitStack
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch
import app
import mcp_bridge
from api_seat_runtime import SeatManager
from artifact_service import ArtifactService
from channel_lifecycle import ChannelStore

class ArtifactFactoryTests(unittest.TestCase):
    def test_real_factory_binds_before_catalog_recovers_before_threads_and_holds_corruption(self):
        for corrupt in (False,True):
            with self.subTest(corrupt=corrupt),tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parents[1]/'.audit-tmp') as directory,ExitStack() as stack:
                root=Path(directory)
                if corrupt:
                    (root/'artifacts').mkdir()
                    (root/'artifacts/index.json').write_bytes(b'BROKEN_SAVED_INDEX')
                for name in ('store','rules','summaries','jobs','schedules','router','agents','registry',
                        'session_store','session_engine','channel_service','config','api_seat_store','api_seat_manager',
                        '_event_loop','artifact_authority','artifacts','artifact_briefs','artifact_recovery'):
                    stack.enter_context(patch.object(app,name,None,create=True))
                stack.enter_context(patch.object(app,'room_settings',{'channels':['general'],'username':'operator','history_limit':'all'}))
                stack.enter_context(patch.object(app,'ws_clients',set()))
                stack.enter_context(patch.object(app,'agent_hats',{}))
                stack.enter_context(patch.object(app,'_install_security_middleware'))
                stack.enter_context(patch.object(mcp_bridge,'artifact_authority',None))
                stack.enter_context(patch.object(mcp_bridge,'channel_policy_getter',None))
                events=[]
                def manager(*args,**kwargs):
                    kwargs['monitor']=False
                    value=SeatManager(*args,**kwargs)
                    stack.callback(value.shutdown)
                    return value
                stack.enter_context(patch('api_seat_runtime.SeatManager',side_effect=manager))
                def thread(*args,**kwargs):
                    value=Mock();value.start.side_effect=lambda:events.append('thread')
                    return value
                stack.enter_context(patch.object(app.threading,'Thread',side_effect=thread))
                original=ChannelStore.initialize
                def initialize(catalog,names):
                    self.assertIsNotNone(app.artifacts)
                    self.assertIs(app.artifacts._channel_policy_getter,app._channels)
                    events.append('catalog')
                    return original(catalog,names)
                stack.enter_context(patch.object(ChannelStore,'initialize',initialize))
                recover=ArtifactService.recover_startup
                def recovery(service,**kwargs):
                    events.append('artifact_recovery')
                    return recover(service,**kwargs)
                stack.enter_context(patch.object(ArtifactService,'recover_startup',recovery))
                app.configure({'server':{'data_dir':directory,'port':18300},'images':{'upload_dir':str(root/'uploads')},'agents':{}},session_token='FIXTURE')
                self.assertIs(app.channel_service.authored_artifacts,app.artifacts)
                self.assertIs(app.channel_service.artifact_service_getter(),app.artifact_authority)
                self.assertIs(app.artifact_authority.store,app.artifacts)
                self.assertIs(app.artifact_authority.seats,app.api_seat_manager)
                self.assertIs(app.artifact_authority.agents,app.agents)
                self.assertIs(app.artifact_authority.registry,app.registry)
                self.assertLess(events.index('catalog'),events.index('artifact_recovery'))
                self.assertTrue(all(events.index('artifact_recovery')<i for i,event in enumerate(events) if event=='thread'))
                if corrupt:
                    self.assertEqual((root/'artifacts/index.json').read_bytes(),b'BROKEN_SAVED_INDEX')
                    self.assertEqual(app.artifact_recovery['held'][0]['reason'],'storage_unavailable')
                else:
                    self.assertFalse((root/'artifacts/index.json').exists())
                    self.assertEqual(app.artifact_recovery['scanned'],0)
                self.assertEqual(list(root.glob('api_seat_runtime/*/config.json')),[])
                count=len(events)
                app.api_seat_manager.start_monitor()
                self.assertEqual(len(events),count)

if __name__=='__main__':unittest.main()
