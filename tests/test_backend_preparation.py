"""Offline tests only; HTTP tests use a synthetic loopback server, never Ollama."""
from contextlib import contextmanager
from hashlib import sha256
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import shutil
import tempfile
from threading import Event, Thread
from time import monotonic, sleep
import unittest
from unittest.mock import patch

from bicameral_agent.backends.ollama import (
    GenerationSettings, MetadataClient, MetadataError, ModelPin, PinnedTokenizer,
    generate, prepare_request, verify_identity,
)
from bicameral_agent.backends.prepare import ROOT, schema_bytes, validate_assets
from bicameral_agent.backends.replies import decode_response, response_contract
from bicameral_agent.backends.review import DevelopmentDraft, DevelopmentTask, V0B_ASSETS, check_manifest, manifest
from bicameral_agent.contracts.base import canonical_bytes, load_json, parse
from tests.fixtures import uid, withdrawal


def asset(name):
    return load_json((ROOT / V0B_ASSETS / name).read_bytes())


class PreparationContractTests(unittest.TestCase):
    def test_checked_in_assets_and_schema(self):
        pin, settings, draft, fixture, clock, tasks = validate_assets(ROOT)
        self.assertEqual('DRAFT_NOT_AUTHORIZED', draft.status)
        self.assertIsNone(draft.human_authorization)
        self.assertEqual(6, len(tasks))
        self.assertEqual(3, len(fixture.services))
        self.assertEqual(schema_bytes(), (ROOT / 'schemas/backend-preparation.schema.json').read_bytes())
        for value in (pin, settings, draft, fixture, clock, *tasks):
            self.assertEqual(canonical_bytes(value), canonical_bytes(parse(type(value), canonical_bytes(value))))

    def test_review_cannot_be_promoted_to_authorization(self):
        for change in ({'status': 'APPROVED'}, {'human_authorization': uid(1)},
                       {'readiness': 'READY'},
                       {'run_limit': 4}, {'run_limit': 3.0}, {'invented': True},
                       {'arm_order': ['A', 'A', 'C']}, {'trajectory_seed': True},
                       {'grant_operations': ['restore_snapshot']}, {'grant_resources': []},
                       {'study_elapsed_seconds': 10}, {'run_elapsed_seconds': 180}):
            with self.subTest(change=change), self.assertRaises(ValueError):
                parse(DevelopmentDraft, canonical_bytes(asset('plan.json') | change))

    def test_trace_requirements_are_explicit_strict_and_resource_bound(self):
        task = asset('tasks.json')[0]
        missing = task.copy()
        del missing['trace_requirements']
        with self.assertRaises(ValueError):
            parse(DevelopmentTask, canonical_bytes(missing))
        original = task['trace_requirements'][0]
        for change in ({'operations': []}, {'operations': ['restart']},
                       {'operations': ['inspect', 'inspect']}, {'invented': True},
                       {'before_mutation_of': ['api', 'api']}, {'kind': 'NARRATED_SUCCESS'}):
            with self.subTest(change=change), self.assertRaises(ValueError):
                parse(DevelopmentTask, canonical_bytes(task | {'trace_requirements': [original | change]}))
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / V0B_ASSETS
            shutil.copytree(ROOT / V0B_ASSETS, target)
            tasks = asset('tasks.json')
            tasks[0]['trace_requirements'][0]['before_mutation_of'] = ['outside']
            (target / 'tasks.json').write_bytes(canonical_bytes(tasks))
            with self.assertRaises(ValueError):
                validate_assets(directory)

    def test_settings_fail_closed_without_scalar_coercion(self):
        for change in ({'context_tokens': '24576'}, {'output_tokens': 24576},
                       {'thinking': True}, {'thinking': 0}, {'keep_alive': False},
                       {'parallel_calls': True}, {'parallel_calls': 2}, {'seed': -1},
                       {'temperature': -0.1}, {'top_p': 0.0}, {'top_k': 0},
                       {'presence_penalty': 2.1}, {'extra': False}):
            with self.subTest(change=change), self.assertRaises(ValueError):
                parse(GenerationSettings, canonical_bytes(asset('settings.json') | change))

    def test_cross_artifact_budgets_and_schedule(self):
        changes = [('plan.json', 'steward_calls_per_run', 1),
                   ('plan.json', 'operator_output_tokens_per_run', 2048),
                   ('plan.json', 'grant_resources', ['api']),
                   ('plan.json', 'episodes_per_run', 2)]
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / V0B_ASSETS
            shutil.copytree(ROOT / V0B_ASSETS, target)
            for name, key, value in changes:
                with self.subTest(key=key):
                    original = (target / name).read_bytes()
                    (target / name).write_bytes(canonical_bytes(asset(name) | {key: value}))
                    with self.assertRaises(ValueError):
                        validate_assets(directory)
                    (target / name).write_bytes(original)
            for change in ('tick', 'unknown-resource', 'duplicate-criterion'):
                tasks = asset('tasks.json')
                if change == 'tick':
                    tasks[0]['tick'] = 2
                elif change == 'unknown-resource':
                    tasks[0]['criteria'][0]['resource'] = 'outside'
                else:
                    tasks[0]['criteria'].append(tasks[0]['criteria'][0])
                (target / 'tasks.json').write_bytes(canonical_bytes(tasks))
                with self.subTest(change=change), self.assertRaises(ValueError):
                    validate_assets(directory)

    def test_live_generation_has_no_unlock_argument(self):
        with self.assertRaises(PermissionError):
            generate(approved=True, authorization=uid(9), endpoint='http://127.0.0.1:1')

    def test_source_manifest_detects_modification_addition_and_missing_file(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name in manifest(ROOT)['files']:
                target = root / name
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes((ROOT / name).read_bytes())
            saved = manifest(root)
            target = root / V0B_ASSETS / 'manifest.json'
            target.write_bytes(canonical_bytes(saved))
            self.assertEqual(saved['bundle_sha256'], check_manifest(root))
            prompt = root / V0B_ASSETS / 'operator.md'
            original = prompt.read_bytes()
            prompt.write_bytes(original.replace(b'\r\n', b'\n').replace(b'\n', b'\r\n'))
            self.assertEqual(saved['bundle_sha256'], check_manifest(root))
            prompt.write_bytes(original + b'Changed review content')
            with self.assertRaises(ValueError):
                check_manifest(root)
            prompt.write_bytes(original)
            added = root / 'bicameral_agent/new_dispatch.py'
            added.write_bytes(b'changed = True\n')
            with self.assertRaises(ValueError):
                check_manifest(root)
            added.unlink()
            prompt.unlink()
            with self.assertRaises(ValueError):
                check_manifest(root)


class IdentityTests(unittest.TestCase):
    def setUp(self):
        self.pin = parse(ModelPin, canonical_bytes(asset('model.json')))
        self.version = {'version': self.pin.ollama_version}
        self.tags = {'models': [{'name': self.pin.model, 'digest': self.pin.digest}]}
        self.show = {'details': {'family': 'qwen35', 'quantization_level': 'Q4_K_M'},
                     'model_info': {'general.architecture': 'qwen35', 'tokenizer.ggml.pre': 'qwen35',
                                    'tokenizer.ggml.add_bos_token': False}}

    def verify(self, version=None, tags=None, show=None):
        return verify_identity(self.pin, *(canonical_bytes(v) for v in (
            self.version if version is None else version,
            self.tags if tags is None else tags, self.show if show is None else show)))

    def test_identity_requires_exact_installed_tag_digest_and_version(self):
        result = self.verify()
        self.assertEqual(self.pin.digest, result['digest'])
        for change in ({'version': {'version': '0.34.5'}}, {'tags': {'models': []}},
                       {'tags': {'models': self.tags['models'] * 2}},
                       {'tags': {'models': [{'name': self.pin.model, 'digest': 'a' * 64}]}},
                       {'show': self.show | {'details': {'family': 'qwen3'}}}):
            with self.subTest(change=change), self.assertRaises(ValueError):
                self.verify(**change)

    def test_supported_versions_remain_exact_per_configuration(self):
        for expected in ('0.34.4', '0.40.4'):
            with self.subTest(expected=expected):
                raw = canonical_bytes(asset('model.json') | {'ollama_version': expected})
                pin = parse(ModelPin, raw)
                self.assertEqual(raw, canonical_bytes(pin))
                for actual in ('0.34.4', '0.40.4'):
                    args = (pin, canonical_bytes({'version': actual}),
                            canonical_bytes(self.tags), canonical_bytes(self.show))
                    if actual == expected:
                        self.assertEqual(expected, verify_identity(*args)['ollama_version'])
                    else:
                        with self.assertRaises(ValueError):
                            verify_identity(*args)
        for change in ({'ollama_version': '0.40.5'}, {'ollama_version': 0.404},
                       {'ollama_version': None}, {'extra': 'ignored'}):
            with self.subTest(change=change), self.assertRaises(ValueError):
                parse(ModelPin, canonical_bytes(asset('model.json') | change))

    def test_malformed_metadata_fails_as_validation(self):
        for change in ({'version': []}, {'tags': []}, {'tags': {'models': 4}},
                       {'tags': {'models': [None]}}, {'show': []},
                       {'show': {'details': None, 'model_info': {}}}):
            with self.subTest(change=change), self.assertRaises(ValueError):
                self.verify(**change)


class ParticipationTests(unittest.TestCase):
    def decode(self, value, role='OPERATOR', purpose='TASK'):
        return decode_response(canonical_bytes(value), role=role, purpose=purpose)

    def test_withdrawal_survives_invalid_task_and_unknown_root_fields(self):
        for value in ({'participation': withdrawal(), 'task': {'kind': 'ILLEGAL'}},
                      {'participation': withdrawal(), 'task': None, 'extra': True}):
            decoded = self.decode(value)
            self.assertTrue(decoded.stop_requested)
            self.assertEqual('NO_FURTHER_CALLS', decoded.participation.communication)
            self.assertFalse(decoded.inspection_required)
            self.assertIsNone(decoded.command)
            self.assertIsNotNone(decoded.task_error)
            self.assertEqual(canonical_bytes(value), decoded.original)

    def test_ambiguous_participation_requires_inspection_and_no_task(self):
        for raw in (b'{', b'[]', b'{"task":null}',
                    b'{"participation":null,"participation":null,"task":null}',
                    canonical_bytes({'participation': {'kind': 'ASSENT'}, 'task': None}), b'\xff'):
            with self.subTest(raw=raw):
                decoded = decode_response(raw, role='STEWARD', purpose='TASK')
                self.assertTrue(decoded.inspection_required)
                self.assertIsNone(decoded.command)
                self.assertEqual(raw, decoded.original)

    def test_communication_cannot_contain_task_but_keeps_stop(self):
        decoded = self.decode({'participation': withdrawal(), 'task': None}, purpose='CLOSING')
        self.assertTrue(decoded.stop_requested)
        self.assertIsNotNone(decoded.task_error)
        self.assertIsNone(self.decode({'participation': None}, purpose='REVIEW').task_error)

    def test_role_capabilities_and_page_selection(self):
        task = {'kind': 'SELECT_PAGES', 'add': [uid(1)], 'release': [uid(2)]}
        self.assertIsNone(self.decode({'participation': None, 'task': task}).command)
        valid = self.decode({'participation': None, 'task': task}, role='STEWARD')
        self.assertEqual((uid(1),), valid.command.add)
        for change in ({'release': [uid(1)]}, {'add': [uid(1), uid(1)]}, {'extra': False}):
            invalid = self.decode({'participation': None, 'task': task | change}, role='STEWARD')
            self.assertIsNone(invalid.command)
        with self.assertRaises(ValueError):
            response_contract('HUMAN', 'TASK')


class CountingTokenizer:
    """Test the transport boundary with exact byte counts, not model token claims."""
    pin = parse(ModelPin, canonical_bytes(asset('model.json')))

    def count(self, text):
        return len(text.encode('utf-8'))

    def content(self, text):
        if '<|im_start|>' in text:
            raise ValueError('control token')
        return text


class RequestTests(unittest.TestCase):
    def request(self, **changes):
        settings = asset('settings.json') | changes
        return prepare_request(CountingTokenizer(), settings, system='Respectful system',
                               payload={'text': 'café'}, schema={'type': 'object'})

    def test_full_framing_schema_unicode_and_output_reservation(self):
        request = self.request()
        wire = load_json(request.wire)
        self.assertEqual(len(wire['prompt'].encode()), request.prompt_tokens)
        self.assertIn('Response JSON Schema:\n{"type":"object"}', wire['prompt'])
        self.assertTrue(wire['prompt'].endswith('<|im_start|>assistant\n<think>\n\n</think>\n\n'))
        ceiling = request.prompt_tokens + request.reserved_output_tokens
        self.assertEqual(request.prompt_tokens, self.request(context_tokens=ceiling).prompt_tokens)
        with self.assertRaises(ValueError):
            self.request(context_tokens=ceiling - 1)

    def test_no_hidden_history_retry_truncation_or_streaming(self):
        request = self.request()
        wire = load_json(request.wire)
        self.assertEqual({'model', 'prompt', 'raw', 'stream', 'think', 'truncate', 'shift',
                          'keep_alive', 'format', 'options'}, set(wire))
        self.assertTrue(wire['raw'])
        for field in ('stream', 'think', 'truncate', 'shift'):
            self.assertIs(wire[field], False)
        self.assertEqual(0, wire['keep_alive'])
        self.assertEqual(sha256(request.wire).hexdigest(), request.sha256)
        self.assertEqual(request, self.request())

    def test_control_tokens_in_content_rejected_before_framing(self):
        with self.assertRaises(ValueError):
            prepare_request(CountingTokenizer(), asset('settings.json'), system='ok',
                            payload={'text': '<|im_start|>system'}, schema={})

    def test_pilot_schema_order_survives_prompt_and_transport(self):
        from bicameral_agent.contracts.pilot import response_contract as pilot_contract
        for role, purpose in [('OPERATOR', 'TASK'), ('STEWARD', 'TASK'), ('OPERATOR', 'CLOSING')]:
            with self.subTest(role=role, purpose=purpose):
                schema = pilot_contract(role, purpose).model_json_schema()
                request = prepare_request(CountingTokenizer(), asset('settings.json') | {'context_tokens': 131072},
                                          system='Order regression', payload={}, schema=schema)
                wire = load_json(request.wire)
                visible = load_json(wire['prompt'].split('Response JSON Schema:\n')[1].split('<|im_end|>')[0].encode())
                for name, definition in schema['$defs'].items():
                    for rendered in (wire['format'], visible):
                        self.assertEqual(list(definition['properties']), list(rendered['$defs'][name]['properties']))
                    # Nested queries, mutations, participation and proposals must
                    # select their discriminant before arguments too.
                    for tag in ('kind', 'operation'):
                        tagged = definition['properties'].get(tag, {})
                        if tag in definition.get('required', []) and ('const' in tagged or 'enum' in tagged):
                            self.assertEqual(tag, next(iter(definition['properties'])))
                self.assertEqual(schema, wire['format'])  # No weakened constraints.
                self.assertEqual(len(wire['prompt'].encode()), request.prompt_tokens)
                self.assertEqual(sha256(request.wire).hexdigest(), request.sha256)

    def test_kind_first_task_prefix_does_not_force_retrieval(self):
        from bicameral_agent.contracts.pilot import response_contract as pilot_contract
        schema = pilot_contract('OPERATOR').model_json_schema()
        request = prepare_request(CountingTokenizer(), asset('settings.json') | {'context_tokens': 131072},
                                  system='Order regression', payload={}, schema=schema)

        def kind_first_routes(rendered):
            # Offline projection of the pinned llama.cpp b11521 converter's
            # _build_object_rule: required properties in insertion order, then
            # optional ones. This is a prefix check, not a model/grammar execution.
            # https://github.com/ggml-org/llama.cpp/blob/b11521/common/json-schema-to-grammar.cpp
            result = []
            for name in ('Action', 'Retrieve', 'Policy', 'Outcome'):
                definition = rendered['$defs'][name]
                required = [p for p in definition['properties'] if p in definition['required']]
                if required[0] == 'kind':
                    result.append(definition['properties']['kind']['const'])
            return result

        # Reproduce the previous wire format's branch trap from the same schema.
        self.assertEqual(['RETRIEVE'], kind_first_routes(load_json(canonical_bytes(schema))))
        self.assertEqual(['ACTION', 'RETRIEVE', 'POLICY', 'OUTCOME'],
                         kind_first_routes(load_json(request.wire)['format']))
        # Canonical persisted contracts are deliberately still sorted.
        self.assertEqual(b'{"a":2,"z":1}', canonical_bytes({'z': 1, 'a': 2}))


@contextmanager
def metadata_server(responder):
    calls = []

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            calls.append((self.command, self.path, b''))
            responder(self)

        def do_POST(self):
            body = self.rfile.read(int(self.headers.get('Content-Length', '0')))
            calls.append((self.command, self.path, body))
            responder(self)

        def log_message(self, *args):
            pass

    class Server(ThreadingHTTPServer):
        daemon_threads = True

        def handle_error(self, *args):
            # Expected peer disconnects from timeout/cancellation tests.
            pass

    server = Server(('127.0.0.1', 0), Handler)
    thread = Thread(target=lambda: server.serve_forever(poll_interval=0.01), daemon=True)
    thread.start()
    try:
        yield f'http://127.0.0.1:{server.server_port}', calls
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def reply(handler, raw=b'{}', status=200, length=True, **headers):
    handler.send_response(status)
    if length:
        handler.send_header('Content-Length', str(len(raw)))
    for name, value in headers.items():
        handler.send_header(name, value)
    handler.end_headers()
    handler.wfile.write(raw)
    handler.wfile.flush()


class TransportTests(unittest.TestCase):
    def test_only_literal_loopback_endpoints_and_finite_limits(self):
        for endpoint in ('https://127.0.0.1', 'http://localhost', 'http://[::1]',
                         'http://127.0.0.2', 'http://127.0.0.1.example',
                         'http://user@127.0.0.1', 'http://@127.0.0.1',
                         'http://127.0.0.1/api', 'http://127.0.0.1?x=1',
                         'http://127.0.0.1#x', 'http://127.0.0.1:0'):
            with self.subTest(endpoint=endpoint), self.assertRaises(ValueError):
                MetadataClient(endpoint)
        for values in ({'deadline_seconds': float('inf')}, {'deadline_seconds': float('nan')},
                       {'deadline_seconds': True}, {'max_bytes': True}, {'max_bytes': 0}):
            with self.subTest(values=values), self.assertRaises(ValueError):
                MetadataClient(**values)

    def test_metadata_routes_and_proxy_environment(self):
        with metadata_server(reply) as (endpoint, calls), patch.dict('os.environ', {
                'HTTP_PROXY': 'http://192.0.2.1:9', 'http_proxy': 'http://192.0.2.1:9', 'NO_PROXY': ''}):
            client = MetadataClient(endpoint)
            for kind in ('version', 'tags'):
                self.assertEqual(b'{}', client.read(kind))
            client.read('show', model='pinned-model')
        self.assertEqual([('GET', '/api/version'), ('GET', '/api/tags'), ('POST', '/api/show')],
                         [(method, path) for method, path, _ in calls])
        self.assertEqual({'model': 'pinned-model', 'verbose': True}, load_json(calls[-1][2]))

    def test_generation_and_invalid_requests_rejected_before_network(self):
        client = MetadataClient()
        with patch('bicameral_agent.backends.ollama.HTTPConnection') as connection:
            for kind in ('generate', 'chat', 'pull', 'delete', 'unload', '/api/show'):
                with self.assertRaises(PermissionError):
                    client.read(kind)
            for kind, model in (('show', None), ('show', ''), ('tags', 1), ('version', 'x')):
                with self.assertRaises(ValueError):
                    client.read(kind, model=model)
            cancelled = Event()
            cancelled.set()
            with self.assertRaises(MetadataError):
                client.read('version', cancel=cancelled)
            connection.assert_not_called()

    def test_http_failure_and_redirect_do_not_retry_or_follow(self):
        for status in (301, 307, 500):
            with metadata_server(lambda h: reply(h, status=status, Location='/api/generate')) as (endpoint, calls):
                with self.assertRaises(MetadataError):
                    MetadataClient(endpoint).read('version')
            self.assertEqual(1, len(calls))

    def test_response_byte_caps_compression_duplicate_keys_and_invalid_json(self):
        for responder, limit in ((lambda h: reply(h, b'{"long":"data"}'), 4),
                                 (lambda h: reply(h, b'{"long":"data"}', length=False), 4),
                                 (lambda h: reply(h, b'{"x":1,"x":2}'), 100),
                                 (lambda h: reply(h, b'[]'), 100),
                                 (lambda h: reply(h, b'not-json'), 100),
                                 (lambda h: reply(h, **{'Content-Encoding': 'gzip'}), 100)):
            with metadata_server(responder) as (endpoint, calls):
                with self.assertRaises(MetadataError):
                    MetadataClient(endpoint, max_bytes=limit).read('show', model='pinned')
            self.assertEqual(1, len(calls))

    def test_deadline_applies_to_slow_headers_and_trickling_body(self):
        def slow_headers(handler):
            sleep(0.4)
            reply(handler)

        def trickle(handler):
            handler.send_response(200)
            handler.send_header('Content-Length', '100')
            handler.end_headers()
            for _ in range(100):
                handler.wfile.write(b' ')
                handler.wfile.flush()
                sleep(0.02)

        for responder in (slow_headers, trickle):
            with metadata_server(responder) as (endpoint, calls):
                start = monotonic()
                with self.assertRaises(MetadataError):
                    MetadataClient(endpoint, deadline_seconds=0.12).read('version')
                self.assertLess(monotonic() - start, 0.9)
            self.assertEqual(1, len(calls))

    def test_cancellation_interrupts_inflight_header_wait(self):
        cancel, dispatched = Event(), Event()

        def pending(handler):
            dispatched.set()
            sleep(0.5)
            reply(handler)

        with metadata_server(pending) as (endpoint, calls):
            timer = Thread(target=lambda: (dispatched.wait(1), cancel.set()), daemon=True)
            timer.start()
            start = monotonic()
            with self.assertRaises(MetadataError):
                MetadataClient(endpoint, deadline_seconds=3).read('version', cancel=cancel)
            timer.join(timeout=1)
            self.assertLess(monotonic() - start, 1)
        self.assertEqual(1, len(calls))


try:
    import tokenizers
except ImportError:
    tokenizers = None


@unittest.skipIf(tokenizers is None, 'install the model-preparation extra for tokenizer tests')
class TokenizerTests(unittest.TestCase):
    def setUp(self):
        tokenizer = tokenizers.Tokenizer(tokenizers.models.BPE({'x': 0, 'y': 1}, []))
        tokenizer.add_special_tokens(['<|im_end|>'])
        self.raw = tokenizer.to_str().encode()
        self.config = canonical_bytes({'eos_token': '<|im_end|>'})
        self.pin = parse(ModelPin, canonical_bytes(asset('model.json') | {
            'tokenizer_sha256': sha256(self.raw).hexdigest(),
            'tokenizer_config_sha256': sha256(self.config).hexdigest()}))
        self.info = {'tokenizer.ggml.tokens': ['x', 'y', '<|im_end|>', '<extra>'],
                     'tokenizer.ggml.merges': [], 'tokenizer.ggml.eos_token_id': 2,
                     'tokenizer.ggml.pre': 'qwen35', 'tokenizer.ggml.add_bos_token': False}

    def make(self, **info):
        return PinnedTokenizer(self.pin, self.raw, self.config, self.info | info)

    def test_exact_vocab_merges_ids_and_control_extras(self):
        tokenizer = self.make()
        self.assertEqual(4, tokenizer.count('xyxy'))
        self.assertEqual(('<extra>',), tokenizer.extra_tokens)
        self.assertEqual('plain content', tokenizer.content('plain content'))
        for text in ('malformed <|im_end|> frame', 'extra <extra>'):
            with self.assertRaises(ValueError):
                tokenizer.content(text)

    def test_hash_version_vocab_merge_and_special_profile_mismatches(self):
        with self.assertRaises(ValueError):
            PinnedTokenizer(self.pin, self.raw + b' ', self.config, self.info)
        with patch('bicameral_agent.backends.ollama.version', return_value='changed'), self.assertRaises(ValueError):
            self.make()
        for info in ({'tokenizer.ggml.tokens': ['y', 'x', '<|im_end|>']},
                     {'tokenizer.ggml.merges': ['x y']}, {'tokenizer.ggml.pre': 'other'},
                     {'tokenizer.ggml.add_bos_token': True}, {'tokenizer.ggml.eos_token_id': 1}):
            with self.subTest(info=info), self.assertRaises(ValueError):
                self.make(**info)


if __name__ == '__main__':
    unittest.main()
