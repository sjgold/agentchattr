"""Worker-owned HTTP-error resources; buffered callback doubles, no network."""
import io
import unittest
import urllib.error

import artifact_worker as worker
from artifact_delivery import ArtifactOutbox
from tests import test_artifact_admission as fixture


class ArtifactWorkerHTTPTests(unittest.TestCase):
    def scope(self, api=False):
        case = fixture.ArtifactAdmissionTests()
        self.addCleanup(case.doCleanups)
        case.setUp()
        case.setup_authority()
        instance, attempt = case.instance, case.attempt
        if api:
            instance, attempt, _ = case.launch_binding('api')
        audit, consumer = case.claimed(instance=instance)
        record = case.trigger.queue.owned(instance, audit['dispatch_id'])
        return case, instance, audit, record, {'runtime_path': attempt['snapshot'].parent,
            'manifest': attempt['effective']['wrapper_protocol'], 'consumer_id': consumer}

    def error(self, code):
        body = io.BytesIO(b'PRIVATE_RESPONSE_BODY')
        error = urllib.error.HTTPError('http://PRIVATE_BEARER', code, 'PRIVATE_ERROR', {}, body)
        self.addCleanup(error.close)
        return error, body

    @staticmethod
    def forbidden(*args, **kwargs):
        raise AssertionError('Forbidden callback ran')

    def test_cli_first_brief_errors_close_the_response_body(self):
        _, _, _, record, owned = self.scope()
        for code, action in ((403, 'reject'), (409, 'reject'), (503, 'wait')):
            with self.subTest(code=code):
                error, body = self.error(code)
                def fetch(*args):
                    raise error
                result = worker.preflight_cli_artifact(record, **owned, fetch_brief=fetch, submit_saved=self.forbidden)
                self.assertEqual(result['action'], action)
                self.assertTrue(body.closed, 'Handled HTTPError still owns an open body')

    def test_api_delivery_parent_and_rejection_errors_close_the_response_body(self):
        for stage in ('delivery', 'parent', 'rejection'):
            with self.subTest(stage=stage):
                case, instance, audit, record, owned = self.scope(api=True)
                error, body = self.error(503)
                def failed(*args):
                    raise error
                callbacks = {'fetch_delivery': lambda brief: case.authority.get_delivery(brief, instance),
                    'fetch_parent': lambda brief: case.authority.get_parent(brief, instance),
                    'generate': self.forbidden, 'submit_saved': self.forbidden,
                    'reject_response': self.forbidden, 'cancel_requested': lambda dispatch: False}
                if stage == 'delivery':
                    callbacks['fetch_delivery'] = failed
                elif stage == 'parent':
                    callbacks['fetch_parent'] = failed
                else:
                    callbacks['generate'] = lambda messages, dispatch: {'content': 'not JSON', 'confirmed_model': None}
                    callbacks['reject_response'] = failed
                result = worker.complete_api_artifact(record, **owned, **callbacks)
                self.assertEqual(result['status'], 'held')
                self.assertTrue(body.closed, 'Handled API HTTPError still owns an open body')

    def test_each_saved_result_send_error_is_closed_before_another_retry(self):
        case, _, audit, record, owned = self.scope()
        private = case.briefs.get_private(audit['brief_id'])
        signed = case.sealed_fixture_record(audit, owned['consumer_id'])
        ArtifactOutbox(owned['runtime_path']).save(signed['payload'], private['_artifact_seal']['seal_secret'])
        bodies = []
        open_at_next_retry = []
        def send(*args):
            open_at_next_retry.extend(not body.closed for body in bodies)
            error, body = self.error(503)
            bodies.append(body)
            raise error
        result = worker.preflight_cli_artifact(record, **owned, fetch_brief=self.forbidden, submit_saved=send)
        self.assertEqual(result['action'], 'hold')
        self.assertEqual(len(bodies), 3)
        self.assertFalse(any(open_at_next_retry), 'Previous HTTP response was still open on retry')
        self.assertTrue(all(body.closed for body in bodies))


if __name__ == '__main__':
    unittest.main()
