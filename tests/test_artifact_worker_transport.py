"""Loopback callback codec, buffered HTTP doubles only; no sockets."""
import io
import json
import unittest
from unittest.mock import patch

import artifact_worker as worker


class ArtifactWorkerTransportTests(unittest.TestCase):
    def test_owned_bearer_paths_bodies_deadlines_and_response_closure(self):
        client = worker.ArtifactHTTP(18300, lambda: 'CONTROLLED_BEARER')
        seen, responses = [], []
        def opened(request, *, timeout):
            seen.append((request, timeout))
            response = io.BytesIO(b'{"fixture":true}')
            responses.append(response)
            return response
        brief = 'a' * 32
        report = {'content': None, 'received_truncated': True}
        saved = {'payload': {'fixture': 'codec only, not admission evidence'}, 'seal': 'b' * 64}
        with patch('urllib.request.urlopen', side_effect=opened):
            client.fetch_brief(brief)
            client.fetch_delivery(brief)
            client.fetch_parent(brief)
            client.submit_saved(saved)
            client.reject_response(brief, report)
        expected = [('/api/artifact-briefs/' + brief, 'GET', None),
            ('/api/artifact-briefs/' + brief + '/delivery', 'GET', None),
            ('/api/artifact-briefs/' + brief + '/parent', 'GET', None),
            ('/api/artifact-results', 'POST', saved),
            ('/api/artifact-briefs/' + brief + '/reject', 'POST', report)]
        for (request, timeout), (path, method, body) in zip(seen, expected):
            self.assertEqual(request.full_url, 'http://127.0.0.1:18300' + path)
            self.assertEqual(request.get_method(), method)
            self.assertEqual(request.get_header('Authorization'), 'Bearer CONTROLLED_BEARER')
            self.assertEqual(json.loads(request.data) if request.data else None, body)
            self.assertEqual(timeout, 10)
        self.assertTrue(all(response.closed for response in responses))

    def test_response_json_is_bounded_strict_and_path_ids_never_escape_owned_routes(self):
        client = worker.ArtifactHTTP(18300, lambda: 'CONTROLLED_BEARER')
        for raw in (b'{"a":1,"a":2}', b'{"n":NaN}', b'{"n":1e999}', b'\xff',
                    b'x' * (worker.MAX_ACK_BYTES + 1)):
            with self.subTest(raw_length=len(raw)):
                response = io.BytesIO(raw)
                with patch('urllib.request.urlopen', return_value=response):
                    with self.assertRaises(worker.ArtifactWorkerError):
                        client.submit_saved({'fixture': 'codec only'})
                self.assertTrue(response.closed)
        with patch('urllib.request.urlopen') as opened:
            for brief in ('../private', 'a' * 31, None):
                with self.subTest(brief=brief), self.assertRaises(worker.ArtifactWorkerError):
                    client.fetch_parent(brief)
            opened.assert_not_called()


if __name__ == '__main__':
    unittest.main()
