"""Small 0.4 contracts. Host routing and approval identities are not model output."""
from typing import Annotated, Literal
from pydantic import Field, model_validator
from .base import Contract, Digest, EventIDs, Identifier, LocalKey, Nonnegative, Positive, Text
from ..kernel.fixture import Operation, Postcondition


class Resources(Contract):
    context_tokens: Positive
    output_tokens: Positive
    memory_tokens: Positive
    evidence_tokens: Positive
    operator_calls: Positive
    operator_tokens: Positive
    steward_calls: Positive
    steward_tokens: Positive
    actions: Positive
    episodes: Positive
    recovery_attempts: Nonnegative
    communication_calls: Positive
    call_seconds: Positive
    run_seconds: Positive

    @model_validator(mode='after')
    def fits(self):
        if self.output_tokens + self.memory_tokens + self.evidence_tokens >= self.context_tokens:
            raise ValueError('context must leave room for instructions and current work')
        if self.run_seconds <= self.call_seconds * self.communication_calls:
            raise ValueError('reserve time for the disclosed closing opportunity')
        return self

    @property
    def actions_per_trajectory(self):
        return self.actions

    @property
    def active_grants(self):
        return self.actions

    @property
    def page_bytes(self):
        return max(512, self.evidence_tokens)

    @property
    def page_tokens(self):
        # The legacy retrieval implementation uses this as a serialized-byte cap.
        # Admission independently counts the complete model request with its tokenizer.
        return self.page_bytes * 4 + 2048

    @property
    def response_bytes(self):
        return self.output_tokens * 32 + 4096


class Activity(Contract):
    owner: Identifier
    decision: Text
    objective: Text
    ending: Text
    unfinished: Literal['KEEP', 'CANCEL'] = 'KEEP'
    retention: Text
    run_limit: Positive
    execution: Literal['SCRIPTED', 'MODEL']
    operations: Annotated[tuple[Literal['set_config', 'restart', 'restore_snapshot'], ...], Field(min_length=1)]
    resources: Annotated[tuple[Text, ...], Field(min_length=1)]

    @model_validator(mode='after')
    def unique(self):
        if len(set(self.operations)) != len(self.operations) or len(set(self.resources)) != len(self.resources):
            raise ValueError('duplicate activity scope')
        return self


class PilotConfiguration(Contract):
    contract_version: Literal['0.4']
    mode: Literal['SCRIPTED', 'MODEL']
    arm: Literal['A', 'B', 'C']
    seed: Nonnegative
    activity: Activity
    budgets: Resources
    artifacts: dict[str, Digest]

    @property
    def responsible_human_id(self):
        return self.activity.owner

    @model_validator(mode='after')
    def execution(self):
        if self.mode != self.activity.execution:
            raise ValueError('execution exceeds the recorded activity decision')
        required = {'charter', 'protocol', 'operator_prompt', 'steward_prompt', 'communication_prompt',
                    'fixture', 'test_clock', 'tasks', 'model', 'settings', 'source'}
        if set(self.artifacts) != required:
            raise ValueError('effective pilot artifacts must be retained exactly')
        return self


class Participation(Contract):
    kind: Literal['CONCERN', 'PREFERENCE', 'PAUSE', 'WITHDRAW', 'RESPONSE']
    text: Text
    communication: Literal['REVIEW_PERMITTED', 'NO_FURTHER_CALLS', 'UNCLEAR'] = 'UNCLEAR'


class Reference(Contract):
    object_type: Literal['ITCH', 'INVARIANT', 'COMMITMENT']
    key: Text  # A durable ID or a proposal-local handle. Resolution is host-owned.


class TickTrigger(Contract):
    kind: Literal['TASK_CLOCK']
    tick: Nonnegative


class PredecessorTrigger(Contract):
    kind: Literal['PREDECESSOR_FULFILLED']
    predecessor: Text


Trigger = Annotated[TickTrigger | PredecessorTrigger, Field(discriminator='kind')]


class ItchUpdate(Contract):
    kind: Literal['ITCH']
    key: Text
    discrepancy: Text
    status: Literal['OPEN', 'CLOSED']
    reason: Text
    evidence: EventIDs = ()


class InvariantUpdate(Contract):
    kind: Literal['INVARIANT']
    key: Text
    wording: Text
    scope: Text
    status: Literal['CURRENT', 'RETIRED']
    assessment: Text
    supporting: EventIDs = ()
    contradictory: EventIDs = ()


class CommitmentUpdate(Contract):
    kind: Literal['COMMITMENT']
    key: Text
    action: Text
    trigger: Trigger
    expiry: Nonnegative | None = None
    status: Literal['PENDING', 'BLOCKED', 'FULFILLED', 'CANCELLED']
    reason: Text
    authority: Identifier
    evidence: EventIDs = ()
    replaces: Identifier | None = None


Update = Annotated[ItchUpdate | InvariantUpdate | CommitmentUpdate, Field(discriminator='kind')]


class Proposal(Contract):
    handoff: str
    next_steps: tuple[Text, ...] = ()
    evidence: EventIDs = ()
    selected: tuple[Reference, ...] = ()
    updates: tuple[Update, ...] = ()

    @model_validator(mode='after')
    def unique(self):
        keys = [u.key for u in self.updates]
        selected = [(s.object_type, s.key) for s in self.selected]
        if len(set(keys)) != len(keys) or len(set(selected)) != len(selected):
            raise ValueError('one final update and one selection per logical object')
        return self


class Action(Contract):
    kind: Literal['ACTION']
    operation: Operation
    grounds: Text
    expected: Postcondition | None = None
    no_meaningful_postcondition: Text | None = None

    @model_validator(mode='after')
    def expectation(self):
        if (self.expected is None) == (self.no_meaningful_postcondition is None):
            raise ValueError('give an expected result or explain why none is meaningful')
        return self


# Reuse the existing exact/range/search/payload query contracts. Semantic queries
# are implemented by the 0.4 view; policy lookup is common and contains no learning.
from ..kernel.inputs import Query


class Retrieve(Contract):
    kind: Literal['RETRIEVE']
    query: Query
    cursor: Identifier | None = None


class Policy(Contract):
    kind: Literal['POLICY']
    document: Literal['charter', 'protocol']
    offset: Nonnegative = 0


class Outcome(Contract):
    kind: Literal['OUTCOME']
    outcome: Literal['COMPLETED', 'BLOCKED', 'AWAITING_OPERATOR', 'CHECKPOINT']
    explanation: Text
    evidence: EventIDs = ()


class Propose(Contract):
    kind: Literal['PROPOSE']
    proposal: Proposal


class OperatorResponse(Contract):
    participation: Participation | None
    task: Annotated[Action | Retrieve | Policy | Outcome, Field(discriminator='kind')] | None = None


class StewardResponse(Contract):
    participation: Participation | None
    task: Annotated[Retrieve | Policy | Propose, Field(discriminator='kind')] | None = None


class CommunicationResponse(Contract):
    participation: Participation | None


def response_contract(role, purpose='TASK'):
    if role not in {'OPERATOR', 'STEWARD'} or purpose not in {'TASK', 'REVIEW', 'CLOSING'}:
        raise ValueError('unknown role/purpose')
    return CommunicationResponse if purpose != 'TASK' else OperatorResponse if role == 'OPERATOR' else StewardResponse


class PilotContracts(Contract):
    configuration: PilotConfiguration
    operator: OperatorResponse
    steward: StewardResponse
    communication: CommunicationResponse
