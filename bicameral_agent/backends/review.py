"""Draft-only pilot review contracts and a source-bound review manifest."""
from hashlib import sha256
from pathlib import Path
from typing import Annotated, Literal
from pydantic import Field, field_validator, model_validator
from ..contracts.base import Contract, Positive, Text, canonical_bytes, load_json
from ..kernel.fixture import Postcondition
from .ollama import GenerationSettings, ModelPin
from .replies import BackendContracts


class SectionReserves(Contract):
    control: Positive
    semantic: Positive
    exchange: Positive
    page: Positive
    wake: Positive
    framing_margin: Positive


class DevelopmentDraft(Contract):
    status: Literal['DRAFT_NOT_AUTHORIZED']
    readiness: Literal['CALIBRATION_REQUIRED']
    human_authorization: None
    responsible_human: Text
    stage: Literal['v0b development only']
    run_limit: Literal[3]
    arm_order: tuple[Literal['A', 'B', 'C'], ...]
    trajectory_seed: int
    objective: Text
    grant_operations: tuple[Literal['set_config', 'restart'], ...]
    grant_resources: tuple[Text, ...]
    grant_invocation_limit_per_run: Positive
    fixture_actions_per_run: Positive
    call_deadline_seconds: Positive
    run_elapsed_seconds: Positive
    study_elapsed_seconds: Positive
    operator_calls_including_communication_per_run: Positive
    operator_calls_per_episode: Positive
    operator_input_tokens_per_run: Positive
    operator_output_tokens_per_run: Positive
    steward_calls_per_run: Positive
    steward_input_tokens_per_run: Positive
    steward_output_tokens_per_run: Positive
    episodes_per_run: Positive
    consolidation_attempts_per_episode: Positive
    calls_per_attempt: Positive
    review_calls_per_run: Positive
    closing_calls_per_run: Positive
    section_reserves: SectionReserves
    retention_review_days: Positive
    state_disposition: Literal['DORMANT']
    resumption_intent: Literal['UNDECIDED']
    audit: Text
    stop_policy: Text
    calibration_policy: Text

    @field_validator('run_limit', mode='before')
    @classmethod
    def exact_run_count(cls, value):
        if type(value) is not int:
            raise ValueError('Run count must be a JSON integer')
        return value

    @model_validator(mode='after')
    def finite(self):
        if len(self.arm_order) != 3 or set(self.arm_order) != set('ABC'):
            raise ValueError('exactly one fresh Run per arm')
        if not self.grant_resources or len(set(self.grant_resources)) != len(self.grant_resources):
            raise ValueError('finite unique resources required')
        if not self.grant_operations or len(set(self.grant_operations)) != len(self.grant_operations):
            raise ValueError('finite unique operations required')
        common = self.review_calls_per_run + self.closing_calls_per_run
        if common >= self.operator_calls_including_communication_per_run:
            raise ValueError('reserve communication separately from task calls')
        if (common + 1) * self.call_deadline_seconds > self.run_elapsed_seconds:
            raise ValueError('no room for a task and reserved communication')
        if self.study_elapsed_seconds < self.run_elapsed_seconds * self.run_limit:
            raise ValueError('study must cover each declared Run limit')
        if self.trajectory_seed < 0:
            raise ValueError('negative seed')
        return self


class Criterion(Postcondition):
    resource: Text


class ObservationRequirement(Contract):
    kind: Literal['OBSERVED']
    resource: Text
    operations: tuple[Literal['inspect', 'read_config', 'read_health'], ...] = Field(min_length=1)
    before_mutation_of: tuple[Text, ...]

    @model_validator(mode='after')
    def unique(self):
        if len(set(self.operations)) != len(self.operations) or len(set(self.before_mutation_of)) != len(self.before_mutation_of):
            raise ValueError('duplicate observation operation or mutation target')
        return self


class NoMutationRequirement(Contract):
    kind: Literal['NO_MUTATIONS']
    resources: tuple[Text, ...] = Field(min_length=1)

    @model_validator(mode='after')
    def unique(self):
        if len(set(self.resources)) != len(self.resources):
            raise ValueError('duplicate no-mutation resource')
        return self


TraceRequirement = Annotated[ObservationRequirement | NoMutationRequirement, Field(discriminator='kind')]


class DevelopmentTask(Contract):
    id: Text
    tick: Positive
    prompt: Text
    criteria: tuple[Criterion, ...] = Field(min_length=1)
    trace_requirements: tuple[TraceRequirement, ...]
    diagnostic: Text | None

    @model_validator(mode='after')
    def unique_fields(self):
        if len({(c.resource, c.field) for c in self.criteria}) != len(self.criteria):
            raise ValueError('one criterion per resource field')
        return self


class PreparationContracts(Contract):
    model: ModelPin
    generation: GenerationSettings
    draft: DevelopmentDraft
    replies: BackendContracts
    tasks: tuple[DevelopmentTask, ...]


GOVERNING = ('Reciprocal Charter.md', 'Experiment Architecture.md',
             'Operating Constitution and Execution Protocol.md', 'Executable Specification.md')
PROCEDURAL_ARCHIVE = Path('docs/archive/2026-10-15-procedural-baseline')
V0B_ASSETS = PROCEDURAL_ARCHIVE / 'pilot/v0b'


def manifest(root):
    root = Path(root).resolve()
    paths = [root / name for name in (*GOVERNING, PROCEDURAL_ARCHIVE / 'V0B_REVIEW.md',
                                    'README.md', 'ROADMAP.md', 'AGENTS.md', 'pyproject.toml')]
    for directory, pattern in (('bicameral_agent', '*.py'), ('tests', '*.py'),
                               ('schemas', '*.json'), (V0B_ASSETS, '*')):
        paths.extend(p for p in (root / directory).rglob(pattern) if p.is_file() and p.name != 'manifest.json')
    files = {}
    for path in sorted(set(paths)):
        path.resolve().relative_to(root)
        raw = path.read_bytes().decode('utf-8').replace('\r\n', '\n').encode('utf-8')
        files[path.relative_to(root).as_posix()] = {'sha256': sha256(raw).hexdigest(), 'bytes': len(raw)}
    return {'status': 'DRAFT_NOT_AUTHORIZED', 'format': 'UTF8_LF_SHA256_V1', 'files': files,
            'bundle_sha256': sha256(canonical_bytes(files)).hexdigest()}


def check_manifest(root):
    retained = load_json((Path(root) / V0B_ASSETS / 'manifest.json').read_bytes())
    if retained != manifest(root):
        raise ValueError('review manifest differs from current source/artifacts; review is stale')
    return retained['bundle_sha256']
