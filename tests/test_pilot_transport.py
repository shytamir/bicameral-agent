"""Ollama-shaped HTTP tests against a synthetic loopback server only."""
from threading import Event, Thread
from time import sleep, monotonic
import unittest
from bicameral_agent.backends.ollama import GenerationClient, MetadataClient, MetadataError, prepare_request
from bicameral_agent.contracts.base import canonical_bytes, load_json
from tests.test_backend_preparation import metadata_server, reply
from tests.test_pilot_runtime import FakeBackend


class GenerationTransportTests(unittest.TestCase):
    def request(self):
        backend = FakeBackend()
        return prepare_request(backend.tokenizer, backend.settings, system='Respectful bounded task',
                               payload={'work': 'synthetic'}, schema={'type': 'object'})

    def test_exact_generate_body_and_bounded_plain_response(self):
        body = canonical_bytes({'response': '{"participation":null}', 'done': True, 'done_reason': 'stop',
                                'prompt_eval_count': 20, 'eval_count': 5})
        request = self.request()
        with metadata_server(lambda handler: reply(handler, body)) as (endpoint, calls):
            self.assertEqual(body, GenerationClient(endpoint).generate(request))
        self.assertEqual([('POST', '/api/generate', request.wire)], calls)
        with self.assertRaises(PermissionError):
            MetadataClient().read('generate')

    def test_http_failure_and_oversize_never_retry(self):
        for responder, limit in ((lambda h: reply(h, b'{}', status=500), 1024),
                                  (lambda h: reply(h, b' ' * 4096), 100)):
            with self.subTest(limit=limit), metadata_server(responder) as (endpoint, calls):
                with self.assertRaises(MetadataError):
                    GenerationClient(endpoint, max_bytes=limit).generate(self.request())
                self.assertEqual(1, len(calls))

    def test_deadline_and_cancellation_retain_received_partial_bytes(self):
        def slow(handler):
            handler.send_response(200)
            handler.end_headers()
            handler.wfile.write(b'{"response":"partial')
            handler.wfile.flush()
            sleep(.2)
        with metadata_server(slow) as (endpoint, calls):
            start = monotonic()
            with self.assertRaises(MetadataError) as caught:
                GenerationClient(endpoint, deadline_seconds=.08).generate(self.request())
            self.assertLess(monotonic() - start, 1)
            self.assertEqual(1, len(calls))
            self.assertIn(b'partial', caught.exception.raw)
        cancel = Event()
        cancel.set()
        with metadata_server(slow) as (endpoint, calls):
            with self.assertRaises(MetadataError):
                GenerationClient(endpoint).generate(self.request(), cancel=cancel)
            self.assertEqual([], calls)
