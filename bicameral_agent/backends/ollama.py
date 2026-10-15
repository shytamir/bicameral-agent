"""Bounded loopback transport and exact Ollama request preparation.

Legacy ``generate`` remains disabled. The separate 0.4 GenerationClient is used
only by the authorized pilot host after admission. Metadata probes cannot load
or unload a model, and importing this module performs no network operations.
"""
from dataclasses import dataclass
from hashlib import sha256
from http.client import HTTPConnection, HTTPException
from importlib.metadata import version
import socket
import math
import json
from threading import Event, Thread
from time import monotonic
from typing import Literal
from urllib.parse import urlsplit

from pydantic import Field, field_validator, model_validator
from ..contracts.base import Contract, Digest, Positive, canonical_bytes, load_json, parse


class ModelPin(Contract):
    model: Literal['qwen3.5:4b-q4_K_M']
    digest: Digest
    ollama_version: Literal['0.34.4', '0.40.4']
    tokenizer_sha256: Digest
    tokenizer_config_sha256: Digest
    tokenizer_revision: str = Field(pattern=r'^[0-9a-f]{40}$')
    tokenizer_library: Literal['0.23.3']


class GenerationSettings(Contract):
    context_tokens: Positive
    output_tokens: Positive
    temperature: float = Field(ge=0, le=2)
    top_p: float = Field(gt=0, le=1)
    top_k: Positive
    presence_penalty: float = Field(ge=-2, le=2)
    seed: int = Field(ge=0, le=2147483647)
    thinking: Literal[False]
    keep_alive: Literal[0]
    parallel_calls: Literal[1]

    @field_validator('thinking', 'keep_alive', 'parallel_calls', mode='before')
    @classmethod
    def exact_literals(cls, value, info):
        expected = bool if info.field_name == 'thinking' else int
        if type(value) is not expected:
            raise ValueError('literal setting must have its exact JSON scalar type')
        return value

    @model_validator(mode='after')
    def room(self):
        if self.output_tokens >= self.context_tokens:
            raise ValueError('output reservation must leave input room')
        return self


class MetadataError(RuntimeError):
    def __init__(self, message, *, raw=b''):
        super().__init__(message)
        self.raw = raw


class MetadataClient:
    """No redirects, proxy environment, DNS lookup, retries, or generation routes.

    A cancellation watchdog and absolute deadline bound slow streaming too.
    Exact response bytes are available for a caller's evidence retention.
    """
    def __init__(self, endpoint='http://127.0.0.1:11434', *, deadline_seconds=10, max_bytes=32_000_000):
        url = urlsplit(endpoint)
        if (url.scheme != 'http' or url.hostname != '127.0.0.1' or url.username is not None or url.password is not None
                or url.path not in ('', '/') or url.query or url.fragment):
            raise ValueError('only a literal IPv4 loopback Ollama endpoint is allowed')
        self.port = url.port if url.port is not None else 80
        if (not 1 <= self.port <= 65535 or type(deadline_seconds) not in (int, float)
                or not math.isfinite(deadline_seconds) or deadline_seconds <= 0
                or type(max_bytes) is not int or max_bytes <= 0):
            raise ValueError('positive bounded transport settings required')
        self.deadline_seconds, self.max_bytes = deadline_seconds, max_bytes

    def read(self, kind, *, model=None, cancel=None):
        paths = {'version': ('GET', '/api/version'), 'tags': ('GET', '/api/tags'),
                 'show': ('POST', '/api/show')}
        if kind not in paths:
            raise PermissionError('only metadata routes are available; generation is disabled')
        if ((kind == 'show' and (type(model) is not str or not model))
                or (kind != 'show' and model is not None)):
            raise ValueError('only show takes an explicit model name')
        method, path = paths[kind]
        body = canonical_bytes({'model': model, 'verbose': True}) if kind == 'show' else None
        return self._request(method, path, body, cancel=cancel)

    def _request(self, method, path, body, *, cancel=None):
        """Shared bounded HTTP transport. Public metadata routes remain unchanged."""
        cancel = cancel if cancel is not None else Event()
        if cancel.is_set():
            raise MetadataError('cancelled before dispatch')
        deadline = monotonic() + self.deadline_seconds
        connection = HTTPConnection('127.0.0.1', self.port, timeout=self.deadline_seconds)
        finished = Event()
        retained_socket = [None]

        def watchdog():
            while not finished.wait(0.01):
                if cancel.is_set() or monotonic() >= deadline:
                    active = connection.sock or retained_socket[0]
                    if active is not None:
                        try:
                            active.shutdown(socket.SHUT_RDWR)
                        except OSError:
                            pass
                    return

        watcher = Thread(target=watchdog, daemon=True)
        watcher.start()
        response_bytes = bytearray()
        response = None
        try:
            # Header/connect timeout is fail-closed; it does not trigger a retry.
            connection.request(method, path, body=body, headers={'Content-Type': 'application/json', 'Connection': 'close'})
            retained_socket[0] = connection.sock
            response = connection.getresponse()
            if response.status != 200:
                raise MetadataError(f'metadata HTTP status {response.status}; no redirect or retry')
            if response.getheader('Content-Encoding', 'identity') != 'identity':
                raise MetadataError('compressed metadata is outside the bounded wire envelope')
            length = response.getheader('Content-Length')
            if length is not None and (not length.isdigit() or int(length) > self.max_bytes):
                raise MetadataError('metadata byte limit')
            while True:
                if cancel.is_set():
                    raise MetadataError('cancelled; connection closed')
                if monotonic() >= deadline:
                    raise MetadataError('absolute metadata deadline')
                chunk = response.read1(min(65536, self.max_bytes + 1 - len(response_bytes)))
                if not chunk:
                    break
                response_bytes.extend(chunk)
                if len(response_bytes) > self.max_bytes:
                    raise MetadataError('metadata byte limit')
            if cancel.is_set() or monotonic() >= deadline:
                raise MetadataError('cancelled or deadline exceeded')
            if length is not None and len(response_bytes) != int(length):
                raise MetadataError('incomplete metadata body')
            raw = bytes(response_bytes)
            value = load_json(raw)
            if not isinstance(value, dict):
                raise MetadataError('metadata must be a JSON object')
            return raw
        except (OSError, HTTPException, ValueError, MetadataError) as error:
            raise MetadataError('bounded transport failure; no retry', raw=bytes(response_bytes)) from error
        finally:
            finished.set()
            if response is not None:
                response.close()
            connection.close()
            watcher.join(timeout=0.1)


def verify_identity(pin, version_bytes, tags_bytes, show_bytes):
    """Treat tags as mutable selectors; require the pinned digest every time."""
    server, tags, show = (load_json(raw) for raw in (version_bytes, tags_bytes, show_bytes))
    if not all(isinstance(v, dict) for v in (server, tags, show)):
        raise ValueError('metadata roots must be objects')
    if server.get('version') != pin.ollama_version:
        raise ValueError('Ollama version differs from reviewed pin')
    models = tags.get('models', [])
    if not isinstance(models, list) or any(not isinstance(m, dict) for m in models):
        raise ValueError('model listing must contain objects')
    matches = [m for m in models if m.get('name') == pin.model]
    if len(matches) != 1 or matches[0].get('digest') != pin.digest:
        raise ValueError('installed model missing, ambiguous, or digest changed')
    details, info = show.get('details', {}), show.get('model_info', {})
    if not isinstance(details, dict) or not isinstance(info, dict):
        raise ValueError('model details and tokenizer metadata must be objects')
    if (details.get('family') != 'qwen35' or details.get('quantization_level') != 'Q4_K_M'
            or info.get('general.architecture') != 'qwen35'
            or info.get('tokenizer.ggml.pre') != 'qwen35'
            or info.get('tokenizer.ggml.add_bos_token') is not False):
        raise ValueError('model/tokenizer architecture differs from reviewed envelope')
    return {'model': pin.model, 'digest': pin.digest, 'ollama_version': pin.ollama_version,
            'metadata_sha256': sha256(show_bytes).hexdigest()}


class PinnedTokenizer:
    def __init__(self, pin, tokenizer_bytes, config_bytes, model_info):
        if (sha256(tokenizer_bytes).hexdigest() != pin.tokenizer_sha256
                or sha256(config_bytes).hexdigest() != pin.tokenizer_config_sha256):
            raise ValueError('tokenizer artifact hash mismatch')
        if version('tokenizers') != pin.tokenizer_library:
            raise ValueError('tokenizer runtime version mismatch')
        from tokenizers import Tokenizer
        data, config = load_json(tokenizer_bytes), load_json(config_bytes)
        vocab = data['model']['vocab'] | {t['content']: t['id'] for t in data['added_tokens']}
        tokens = model_info['tokenizer.ggml.tokens']
        if any(i >= len(tokens) or tokens[i] != token for token, i in vocab.items()):
            raise ValueError('GGUF vocabulary mismatch')
        merges = [' '.join(m) if isinstance(m, list) else m for m in data['model']['merges']]
        if merges != model_info['tokenizer.ggml.merges']:
            raise ValueError('GGUF merge rules mismatch')
        if (model_info.get('tokenizer.ggml.pre') != 'qwen35'
                or model_info.get('tokenizer.ggml.add_bos_token') is not False
                or tokens[model_info['tokenizer.ggml.eos_token_id']] != config['eos_token']):
            raise ValueError('GGUF special-token or pre-tokenizer profile mismatch')
        ids = set(vocab.values())
        self.extra_tokens = tuple(t for i, t in enumerate(tokens) if i not in ids)
        self.control_tokens = tuple(t['content'] for t in data['added_tokens'] if t.get('special'))
        self._tokenizer = Tokenizer.from_str(tokenizer_bytes.decode('utf-8'))
        self._tokenizer.no_truncation()
        self._tokenizer.no_padding()
        self.pin = pin

    def count(self, text):
        return len(self._tokenizer.encode(text, add_special_tokens=False).ids)

    def content(self, text):
        if any(t in text for t in self.control_tokens + self.extra_tokens):
            raise ValueError('literal tokenizer control/extra tokens in content require explicit review')
        return text


@dataclass(frozen=True)
class PreparedRequest:
    wire: bytes
    prompt_tokens: int
    reserved_output_tokens: int
    context_tokens: int
    sha256: str


def prepare_request(tokenizer, settings, *, system, payload, schema):
    """A narrow text-only two-message Qwen frame, with thinking disabled.

    No provider template, conversation ID, prior KV context, image or tool loop
    is supplied. The schema is both prompt-visible and a decoding constraint.
    Account the entire actual prompt, including role markers and schema.
    This is local accounting, not a claim about observed server token counts.
    """
    settings = parse(GenerationSettings, canonical_bytes(settings))
    # Schema property order is operational for constrained decoding: llama.cpp
    # emits required fields in that order. Sorting put grounds before kind in
    # ACTION, leaving only RETRIEVE reachable after a kind-first task prefix.
    # Keep strict JSON validation, but preserve the contract's declaration order
    # in both the visible schema and format. Storage canonicalization is unchanged.
    canonical_bytes(schema)
    schema_bytes = json.dumps(schema, ensure_ascii=False, separators=(',', ':'), allow_nan=False).encode('utf-8')
    system = tokenizer.content(system.strip() + '\n\nResponse JSON Schema:\n' + schema_bytes.decode())
    user = tokenizer.content(canonical_bytes(payload).decode())
    prompt = ('<|im_start|>system\n' + system + '<|im_end|>\n'
              '<|im_start|>user\n' + user + '<|im_end|>\n'
              '<|im_start|>assistant\n<think>\n\n</think>\n\n')
    count = tokenizer.count(prompt)
    if count + settings.output_tokens > settings.context_tokens:
        raise ValueError(f'full prompt ({count}) plus output reserve ({settings.output_tokens}) '
                         f'exceeds context ({settings.context_tokens}); no truncation')
    wire = json.dumps({'model': tokenizer.pin.model, 'prompt': prompt, 'raw': True,
        'stream': False, 'think': False, 'truncate': False, 'shift': False, 'keep_alive': 0,
        'format': schema, 'options': {'num_ctx': settings.context_tokens,
            'num_predict': settings.output_tokens, 'temperature': settings.temperature,
            'top_p': settings.top_p, 'top_k': settings.top_k,
            'presence_penalty': settings.presence_penalty, 'seed': settings.seed,
            'stop': ['<|im_end|>']}}, ensure_ascii=False, separators=(',', ':'), allow_nan=False).encode('utf-8')
    return PreparedRequest(wire, count, settings.output_tokens, settings.context_tokens, sha256(wire).hexdigest())


def generate(*args, **kwargs):
    raise PermissionError('Live generation is disabled in the preparation slice. '
                          'Human experiment review and governed MODEL integration are required.')


class GenerationClient(MetadataClient):
    """0.4 transport; the pilot host owns authorization, admission and recording.

    Closing the connection bounds the client wait. It does not establish that a
    server stopped computing; the host retains unknown cost and does not retry.
    """
    def generate(self, request, *, cancel=None):
        return self._request('POST', '/api/generate', request.wire, cancel=cancel)
