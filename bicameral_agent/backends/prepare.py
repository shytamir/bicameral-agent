"""Prepare/recheck the draft v0b review package without any model invocation."""
import argparse
from hashlib import sha256
import json
from pathlib import Path
from pydantic import TypeAdapter

from ..contracts.base import canonical_bytes, load_json, parse
from ..kernel.fixture import ClockPlan, FixtureDefinition
from .ollama import MetadataClient, ModelPin, GenerationSettings, PinnedTokenizer, prepare_request, verify_identity
from .replies import response_contract
from .review import DevelopmentDraft, DevelopmentTask, PreparationContracts, check_manifest, manifest


ROOT = Path(__file__).resolve().parents[2]


def schema_bytes():
    return (json.dumps(PreparationContracts.model_json_schema(), sort_keys=True, indent=2) + '\n').encode()


def inspect_metadata(pin, client):
    # Deliberately exhaustive allowlist; never call generate, chat, pull or unload.
    version = client.read('version')
    tags = client.read('tags')
    show = client.read('show', model=pin.model)
    identity = verify_identity(pin, version, tags, show)
    return identity, load_json(show)['model_info']


def validate_assets(root):
    assets = Path(root) / 'pilot/v0b'
    pin = parse(ModelPin, (assets / 'model.json').read_bytes())
    settings = parse(GenerationSettings, (assets / 'settings.json').read_bytes())
    draft = parse(DevelopmentDraft, (assets / 'plan.json').read_bytes())
    fixture = parse(FixtureDefinition, (assets / 'fixture.json').read_bytes())
    clock = parse(ClockPlan, (assets / 'clock.json').read_bytes())
    tasks = TypeAdapter(tuple[DevelopmentTask, ...]).validate_json(
        canonical_bytes(load_json((assets / 'tasks.json').read_bytes())), strict=True)
    if (not tasks or len({t.id for t in tasks}) != len(tasks)
            or [t.tick for t in tasks] != [s.tick for s in clock.steps]):
        raise ValueError('finite unique tasks must match the fixed clock schedule')
    if len(tasks) > draft.episodes_per_run:
        raise ValueError('task schedule exceeds Episode allowance')
    if draft.operator_calls_per_episode > draft.operator_calls_including_communication_per_run:
        raise ValueError('Episode call cap exceeds Run cap')
    if draft.steward_calls_per_run != (draft.episodes_per_run *
            draft.consolidation_attempts_per_episode * draft.calls_per_attempt):
        raise ValueError('Steward Run allowance must match Episode/attempt ceilings')
    for role, calls in (('operator', draft.operator_calls_including_communication_per_run),
                        ('steward', draft.steward_calls_per_run)):
        if (getattr(draft, role + '_input_tokens_per_run') < calls * settings.context_tokens
                or getattr(draft, role + '_output_tokens_per_run') < calls * settings.output_tokens):
            raise ValueError('cumulative token allowance cannot cover declared call ceilings')
    if set(draft.grant_resources) != {s.resource for s in fixture.services}:
        raise ValueError('draft Grant resources differ from finite fixture')
    resources = {s.resource: s for s in fixture.services}
    if any(c.resource not in resources for task in tasks for c in task.criteria):
        raise ValueError('criterion references unknown fixture resource')
    for step in clock.steps:
        for change in step.changes:
            if change.resource not in resources or change.dependency != resources[change.resource].dependency:
                raise ValueError('hidden change must preserve registered topology')
    return pin, settings, draft, fixture, clock, tasks


def prepare(root, tokenizer_directory, *, client=None):
    root, tokenizer_directory = Path(root), Path(tokenizer_directory)
    assets = root / 'pilot/v0b'
    pin, settings, draft, _, _, _ = validate_assets(root)
    metadata = {'status': 'OFFLINE_ONLY; server identity was not rechecked'}
    if client is not None:
        metadata, info = inspect_metadata(pin, client)
    else:
        info = load_json((tokenizer_directory / 'model-info.json').read_bytes())
    tokenizer = PinnedTokenizer(pin, (tokenizer_directory / 'tokenizer.json').read_bytes(),
                                (tokenizer_directory / 'tokenizer_config.json').read_bytes(), info)
    common = '\n\n'.join((root / name).read_text(encoding='utf-8') for name in
                          ('Reciprocal Charter.md', 'Operating Constitution and Execution Protocol.md'))
    notices = (assets / 'notices.md').read_text(encoding='utf-8')
    probes, wires = {}, {}
    for role, purpose in ((role, purpose) for purpose in ('TASK', 'REVIEW', 'CLOSING')
                          for role in ('OPERATOR', 'STEWARD')):
        prompt_file = role.lower() if purpose == 'TASK' else 'communication'
        system = common + '\n\n' + (assets / (prompt_file + '.md')).read_text(encoding='utf-8') + '\n\n' + notices
        # Synthetic route identifiers, never permissions or actual Run allocations.
        route = {key: '00000000-0000-4000-8000-000000000001' for key in
                 ('run_id', 'episode_id', 'invocation_id', 'activity_id')}
        if purpose != 'TASK':
            route['episode_id'] = None
        payload = {'probe': 'OFFLINE ONLY — not a model invocation', 'role': role, 'purpose': purpose,
                   'route': route, 'control': {}, 'semantic': {}, 'exchange': [], 'pages': [], 'wake': ''}
        request = prepare_request(tokenizer, settings, system=system, payload=payload,
                                  schema=response_contract(role, purpose).model_json_schema())
        key = role + '_' + purpose
        extra = sum(draft.section_reserves.model_dump().values())
        maximum = request.prompt_tokens + settings.output_tokens + extra
        if maximum > settings.context_tokens:
            raise ValueError(f'{key}: fixed frame plus proposed section/output reservations exceeds context')
        probes[key] = {'fixed_framed_prompt_tokens': request.prompt_tokens,
            'reserved_output_tokens': settings.output_tokens, 'additional_section_reservations': extra,
            'planned_total_ceiling': maximum, 'context_tokens': settings.context_tokens,
            'remaining_margin': settings.context_tokens - maximum, 'request_sha256': request.sha256,
            'fits_earlier_16k_suggestion': maximum <= 16384}
        wires[key] = request.wire
    return {'status': 'DRAFT_NOT_AUTHORIZED', 'generation_calls': 0, 'metadata': metadata,
        'model_pin': pin.model_dump(mode='json'), 'tokenizer': {'known_vocabulary_and_merges_match': True,
            'additional_gguf_tokens': len(tokenizer.extra_tokens),
            'additional_gguf_tokens_sha256': sha256(canonical_bytes(tokenizer.extra_tokens)).hexdigest(),
            'accounting': 'PINNED_LOCAL_TOKENIZER; backend counts and behavior remain unmeasured'},
        'admission_probes': probes,
        'limits': 'Offline reservation arithmetic; actual assembled requests must be counted and admitted before each dispatch. '
                  'No GPU fit, speed, server token parity, cancellation or retention behavior is inferred.'}, wires


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument('--write-schema', action='store_true')
    mode.add_argument('--check-schema', action='store_true')
    mode.add_argument('--write-manifest', action='store_true')
    mode.add_argument('--check-manifest', action='store_true')
    mode.add_argument('--check-assets', action='store_true')
    parser.add_argument('--tokenizer-dir', type=Path)
    parser.add_argument('--report', type=Path)
    parser.add_argument('--inspect', action='store_true', help='Read-only loopback /version, /tags, /show only')
    args = parser.parse_args()
    if args.write_schema or args.check_schema:
        target = ROOT / 'schemas/backend-preparation.schema.json'
        if args.write_schema:
            target.write_bytes(schema_bytes())
        elif target.read_bytes() != schema_bytes():
            raise ValueError('backend preparation schema drift')
        print('Backend preparation schema matches.')
    elif args.write_manifest:
        target = ROOT / 'pilot/v0b/manifest.json'
        target.write_bytes(canonical_bytes(manifest(ROOT)) + b'\n')
        print('Draft review manifest written; no authorization or inference.')
    elif args.check_manifest:
        print('Draft review manifest matches: ' + check_manifest(ROOT))
    elif args.check_assets:
        validate_assets(ROOT)
        print('Draft model, settings, plan, fixture, clock and tasks are consistent; no authorization or inference.')
    else:
        if args.tokenizer_dir is None:
            parser.error('--tokenizer-dir is required for offline preparation')
        report, wires = prepare(ROOT, args.tokenizer_dir, client=MetadataClient() if args.inspect else None)
        if args.report:
            args.report.parent.mkdir(parents=True, exist_ok=True)
            args.report.write_bytes(canonical_bytes(report) + b'\n')
            for name, raw in wires.items():
                (args.report.parent / (name.lower() + '.request.json')).write_bytes(raw)
        print(json.dumps(report, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
