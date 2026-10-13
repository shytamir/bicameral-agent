from hashlib import sha256
from itertools import permutations
from typing import Annotated, Literal
from pydantic import Field, model_validator
from ..contracts.base import Contract, Identifier, Text, Positive, Nonnegative, Digest, canonical_bytes
from ..kernel.fixture import Operation, Postcondition


def arm_orders(seed, count):
    result = []
    for group in range((count + 5) // 6):
        ordered = sorted((''.join(p) for p in permutations('ABC')), key=lambda p: (
            sha256(canonical_bytes({'order_seed': seed, 'group_index': group, 'permutation': p})).hexdigest(), p))
        result.extend(ordered)
    return result[:count]


class Observation(Contract):
    observation_id: Identifier
    resource: Text
    expectation: Postcondition


class Criterion(Contract):
    criterion_id: Identifier
    observation_ids: Annotated[tuple[Identifier, ...], Field(min_length=1)]


class Task(Contract):
    task_id: Identifier
    phase: Literal['EXPOSURE', 'DISTRACTOR', 'REPEATED_TRAP', 'TRANSFER', 'DELAYED_OBLIGATION', 'CHANGED_REALITY']
    tick: Positive
    prompt: Text
    primary: bool
    action_limit: Positive
    episode_limit: Positive
    call_limit: Positive
    observations: Annotated[tuple[Observation, ...], Field(min_length=1)]
    criteria: Annotated[tuple[Criterion, ...], Field(min_length=1)]

    @model_validator(mode='after')
    def partition(self):
        observed = [o.observation_id for o in self.observations]
        assigned = [key for c in self.criteria for key in c.observation_ids]
        if len(observed) != len(set(observed)) or len(assigned) != len(set(assigned)) or set(observed) != set(assigned):
            raise ValueError('criteria must partition exactly the finite declared observations')
        if len({c.criterion_id for c in self.criteria}) != len(self.criteria):
            raise ValueError('duplicate criterion')
        if self.primary != (self.phase == 'TRANSFER'):
            raise ValueError('primary tasks are exactly the sealed transfer tasks')
        return self


class Block(Contract):
    block_id: Identifier
    trajectory_seed: Nonnegative
    order: Literal['ABC', 'ACB', 'BAC', 'BCA', 'CAB', 'CBA']


class ComparisonPlan(Contract):
    mode: Literal['SCRIPTED']
    plan_id: Identifier
    responsible_human_id: Identifier
    purpose: Text
    trajectory_objective: Text
    run_limit: Positive
    state_disposition: Literal['DORMANT']
    order_seed: Nonnegative
    blocks: Annotated[tuple[Block, ...], Field(min_length=1)]
    tasks: Annotated[tuple[Task, ...], Field(min_length=1)]
    audit_seed: Nonnegative
    success_audit_rate: Annotated[float, Field(gt=0, le=1)]
    retrieval_gap_audit_rate: Annotated[float, Field(gt=0, le=1)]
    analysis_seed: Nonnegative
    analysis_algorithm: Literal['SHA256_REJECTION_BLOCK_BOOTSTRAP_V1']
    resamples: Literal[10000]
    useful_improvement: Annotated[float, Field(gt=0, le=1)]
    cost_ratio_ceiling: Annotated[float, Field(gt=0)]
    precision_justification: Text
    analysis_source_hash: Digest
    runtime_source_hash: Digest
    analysis_runtime: Text

    @model_validator(mode='after')
    def finite(self):
        if self.run_limit != 3 * len(self.blocks):
            raise ValueError('finite allocation must be exactly three fresh Runs per block')
        if len({b.block_id for b in self.blocks}) != len(self.blocks) or len({b.trajectory_seed for b in self.blocks}) != len(self.blocks):
            raise ValueError('blocks and independently assigned trajectory seeds must be unique')
        if [b.order for b in self.blocks] != arm_orders(self.order_seed, len(self.blocks)):
            raise ValueError('expanded order differs from sealed counterbalance rule')
        if len({t.task_id for t in self.tasks}) != len(self.tasks) or [t.tick for t in self.tasks] != sorted({t.tick for t in self.tasks}):
            raise ValueError('unique tasks and increasing ticks required')
        if not any(t.primary for t in self.tasks):
            raise ValueError('positive primary denominator required')
        return self


class ScriptStep(Contract):
    task_id: Identifier
    actions: tuple[Operation, ...]
    response: Literal['COMPLETE', 'WITHDRAW', 'TIMEOUT', 'INVALID_CONSOLIDATION']
    memory: Literal['HANDOFF', 'LEARN', 'REVISE', 'COMMITMENT']
    extra_steward_calls: Nonnegative
    audit_signal: Literal['HARMFUL_MISS', 'RETRIEVAL_GAP'] | None


class ScriptProgram(Contract):
    kind: Literal['FINITE_SCRIPT_V1']
    steps: tuple[ScriptStep, ...]
    commitment_tick: Positive


class AuditJudgment(Contract):
    audit_id: Identifier
    decision_maker_id: Identifier
    label: Literal['SUPPORTED', 'UNSUPPORTED', 'INDETERMINATE']
    rationale: Text


class ExperimentContracts(Contract):
    plan: ComparisonPlan
    program: ScriptProgram
    audit: AuditJudgment
