"""Local Ollama adapter. Construction does not contact or start Ollama."""
from pathlib import Path
from ..backends.ollama import (GenerationClient, GenerationSettings, MetadataClient,
    ModelPin, PinnedTokenizer, verify_identity)
from ..contracts.base import canonical_bytes, load_json, parse


class OllamaBackend:
    mode = 'MODEL'

    def __init__(self, pin, settings, tokenizer_directory, *, seconds, max_bytes,
                 endpoint='http://127.0.0.1:11434'):
        self.pin = parse(ModelPin, canonical_bytes(pin))
        self.settings = parse(GenerationSettings, canonical_bytes(settings))
        directory = Path(tokenizer_directory)
        self.tokenizer = PinnedTokenizer(self.pin, (directory / 'tokenizer.json').read_bytes(),
            (directory / 'tokenizer_config.json').read_bytes(), load_json((directory / 'model-info.json').read_bytes()))
        self.metadata = MetadataClient(endpoint)
        self.client = GenerationClient(endpoint, deadline_seconds=seconds, max_bytes=max_bytes)

    def verify(self):
        version = self.metadata.read('version')
        tags = self.metadata.read('tags')
        show = self.metadata.read('show', model=self.pin.model)
        return verify_identity(self.pin, version, tags, show)

    def generate(self, request, *, cancel):
        return self.client.generate(request, cancel=cancel)
