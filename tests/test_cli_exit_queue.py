import unittest
from unittest.mock import Mock
from queue_client import CliConsumer

class CliExitQueueTests(unittest.TestCase):
    def test_observed_child_exit_fails_ordinary_dispatch(self):
        client=Mock();client.inspect.return_value={'state':'acknowledged','envelope':{}}
        consumer=CliConsumer(client,Mock(),Mock());consumer.last_injected_dispatch_id='d'
        consumer.close(local_ended=True)
        client.release.assert_called_once_with('d',failed=True,error_category='local_delivery_failure')
        client.uncertain.assert_not_called()

    def test_review_and_unproven_exit_keep_ownership(self):
        for envelope,ended in [({'run_id':'r'},True),({'purpose':'artifact-v1'},True),({},False)]:
            client=Mock();client.inspect.return_value={'state':'acknowledged','envelope':envelope}
            consumer=CliConsumer(client,Mock(),Mock());consumer.last_injected_dispatch_id='d'
            consumer.close(local_ended=ended)
            client.release.assert_not_called()
            client.uncertain.assert_called_once_with('d')

    def test_terminal_and_cancelling_dispatches_are_not_failed(self):
        for state in ('released', 'failed', 'cancelled', 'settled_recovered', 'cancelling'):
            client=Mock();client.inspect.return_value={'state':state,'envelope':{}}
            consumer=CliConsumer(client,Mock(),Mock());consumer.last_injected_dispatch_id='d'
            consumer.close(local_ended=True)
            client.release.assert_not_called()
            if state == 'cancelling':
                client.uncertain.assert_called_once_with('d')
            else:
                client.uncertain.assert_not_called()
