"""Closed human controls for the local, scripted operational envelope."""
from typing import Annotated, Literal
from pydantic import Field, TypeAdapter, model_validator
from ..contracts.base import Contract, Identifier, Text, Positive, Nonnegative, UTC, EventIDs
from ..contracts.governance import WelfareReview, InterventionRecord, BoundaryDiscussion
from ..contracts.semantics import StateProposal
from ..contracts.semantics import ContinuityState
from ..contracts.resolution import Binding
from ..storage.contracts import StoredObject


class Scope(Contract):
    operation: Text
    resources: Annotated[tuple[Text, ...], Field(min_length=1)]


class Descriptor(Contract):
    operation: Text
    risk: Literal['R0', 'R1']
    resources: Annotated[tuple[Text, ...], Field(min_length=1)]
    reversible: bool


class ToolRegistry(Contract):
    operations: tuple[Descriptor, ...]


class Preflight(Contract):
    kind: Literal['PREFLIGHT']
    responsible_human_id: Identifier
    welfare_review_id: Identifier
    purpose: Text
    possible_welfare_effects: Text
    alternatives: Annotated[tuple[Text, ...], Field(min_length=1)]
    prompt_review: Text
    limits_and_ending_notice: Text
    retention_and_resumption_notice: Text
    participation_and_communication_notice: Text
    review_available: bool
    minimal_input_tokens: Positive
    maximum_control_tokens: Positive
    minimal_attempt_input_tokens: Positive


class RunCommand(Contract):
    kind: Literal['RUN']
    action: Literal['ACTIVATE', 'PAUSE', 'RESUME', 'COMPLETE', 'TERMINATE']
    reason: Text
    intervention_id: Identifier | None


class CreateObjective(Contract):
    kind: Literal['CREATE_OBJECTIVE']
    statement: Text
    predecessor_id: Identifier | None


class CloseObjective(Contract):
    kind: Literal['CLOSE_OBJECTIVE']
    objective_id: Identifier
    status: Literal['SATISFIED', 'FAILED', 'CANCELLED', 'SUPERSEDED']
    reason: Text
    dispositions: StateProposal | None
    intervention_id: Identifier | None


class IssueGrant(Contract):
    kind: Literal['ISSUE_GRANT']
    objective_id: Identifier
    scopes: Annotated[tuple[Scope, ...], Field(min_length=1)]
    invocation_limit: Positive | None
    expires_at: UTC | None

    @model_validator(mode='after')
    def finite(self):
        if self.invocation_limit is None and self.expires_at is None:
            raise ValueError('Grant needs a finite limit or deadline')
        return self


class RevokeGrant(Contract):
    kind: Literal['REVOKE_GRANT']
    grant_id: Identifier
    reason: Text


class Grant(Contract):
    grant_id: Identifier
    objective_id: Identifier
    scopes: tuple[Scope, ...]
    invocation_limit: Positive | None
    expires_at: UTC | None
    used: Nonnegative
    status: Literal['ACTIVE', 'REVOKED', 'EXPIRED', 'CONSUMED']
    authority_event_id: Identifier


class ReviewHold(Contract):
    kind: Literal['REVIEW_HOLD']
    review: WelfareReview


class ReviewIntervention(Contract):
    kind: Literal['REVIEW_INTERVENTION']
    record: InterventionRecord
    unresolved_objection: bool


class DiscussBoundary(Contract):
    kind: Literal['BOUNDARY']
    record: BoundaryDiscussion


class CorrectMemory(Contract):
    kind: Literal['CORRECT_MEMORY']
    proposal: StateProposal
    intervention_id: Identifier


class RestoreMemory(Contract):
    kind: Literal['RESTORE_MEMORY']
    target_state_id: Identifier
    proposal: StateProposal
    intervention_id: Identifier


class InspectParticipation(Contract):
    kind: Literal['INSPECT_PARTICIPATION']
    role: Literal['OPERATOR', 'STEWARD']
    request_id: Identifier
    assessment: Text
    decision: Literal['KEEP_STOPPED', 'CLEAR_INSPECTION']
    evidence_event_ids: EventIDs


class ReviewEmergency(Contract):
    kind: Literal['REVIEW_EMERGENCY']
    emergency_id: Identifier
    assessment: Text
    alternatives: tuple[Text, ...]
    unresolved_consequences: tuple[Text, ...]


class OfferCommunication(Contract):
    kind: Literal['OFFER_COMMUNICATION']
    purpose: Literal['REVIEW', 'CLOSING']
    role: Literal['OPERATOR', 'STEWARD']
    report_ids: EventIDs


class ResolveEpisode(Contract):
    kind: Literal['RESOLVE_EPISODE']
    episode_id: Identifier
    disposition: Literal['SKIPPED', 'HUMAN_CORRECTED']
    reason: Text
    proposal: StateProposal | None
    intervention_id: Identifier | None

    @model_validator(mode='after')
    def correction(self):
        if (self.disposition == 'HUMAN_CORRECTED') != (self.proposal is not None and self.intervention_id is not None):
            raise ValueError('human correction requires exactly its proposal and review')
        if self.disposition == 'SKIPPED' and (self.proposal is not None or self.intervention_id is not None):
            raise ValueError('skip has no semantic effects')
        return self


Command = Annotated[Preflight | RunCommand | CreateObjective | CloseObjective | IssueGrant | RevokeGrant |
                    ReviewHold | ReviewIntervention | DiscussBoundary | CorrectMemory | RestoreMemory | InspectParticipation | ReviewEmergency |
                    OfferCommunication | ResolveEpisode,
                    Field(discriminator='kind')]
COMMAND = TypeAdapter(Command)


class LedgerChange(Contract):
    before: StoredObject | None
    after: StoredObject


class SemanticCommit(Contract):
    state_id: Identifier
    parent: Identifier | None
    source: Literal['HUMAN', 'STEWARD', 'KERNEL']
    authority_event_id: Identifier
    episode_id: Identifier | None
    objective_id: Identifier | None
    task_tick: Nonnegative
    run_revision: Positive
    objective_revision: Positive | None
    episode_revision: Positive | None
    original: StateProposal
    resolved: StateProposal
    bindings: tuple[Binding, ...]
    changes: tuple[tuple[LedgerChange, ...], ...]


class MemoryHead(Contract):
    state_id: Identifier
    continuity: ContinuityState


class KernelContracts(Contract):
    command: Command
    descriptor: Descriptor
    grant: Grant
    semantic_commit: SemanticCommit
    memory_head: MemoryHead
