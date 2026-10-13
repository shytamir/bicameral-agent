"""Semantic proposal shapes; lifecycle acceptance belongs to later slices."""

from typing import Annotated, Literal

from pydantic import AfterValidator, Field, model_validator

from .base import Contract, EventIDs, Identifier, LocalKey, Positive, Text, Nonnegative, unique


ObjectType = Literal["ITCH", "INVARIANT_FAMILY", "INVARIANT_VERSION", "COMMITMENT"]
ItchStatus = Literal["OPEN", "INVESTIGATING", "RESOLVED", "DISMISSED", "ARCHIVED"]
InvariantStatus = Literal["TENTATIVE", "ACTIVE", "CHALLENGED", "RETIRED"]
CommitmentStatus = Literal["PENDING", "TRIGGERED", "IN_PROGRESS", "BLOCKED", "FULFILLED", "CANCELLED", "SUPERSEDED", "EXPIRED"]


class ExistingReference(Contract):
    kind: Literal["EXISTING"]
    object_type: ObjectType
    object_id: Identifier


class LocalReference(Contract):
    kind: Literal["LOCAL"]
    object_type: ObjectType
    local_key: LocalKey


class ExistingItch(ExistingReference):
    object_type: Literal["ITCH"]


class LocalItch(LocalReference):
    object_type: Literal["ITCH"]


class ExistingVersion(ExistingReference):
    object_type: Literal["INVARIANT_VERSION"]


class LocalVersion(LocalReference):
    object_type: Literal["INVARIANT_VERSION"]


class ExistingCommitment(ExistingReference):
    object_type: Literal["COMMITMENT"]


class LocalCommitment(LocalReference):
    object_type: Literal["COMMITMENT"]


class ExistingSelected(ExistingReference):
    object_type: Literal["ITCH", "INVARIANT_VERSION", "COMMITMENT"]


class LocalSelected(LocalReference):
    object_type: Literal["ITCH", "INVARIANT_VERSION", "COMMITMENT"]


ItchReference = Annotated[ExistingItch | LocalItch, Field(discriminator="kind")]
VersionReference = Annotated[ExistingVersion | LocalVersion, Field(discriminator="kind")]
CommitmentReference = Annotated[ExistingCommitment | LocalCommitment, Field(discriminator="kind")]
SelectedReference = Annotated[ExistingSelected | LocalSelected, Field(discriminator="kind")]
Selection = Annotated[tuple[SelectedReference, ...], AfterValidator(unique)]


class EpistemicItem(Contract):
    kind: Literal["OBSERVATION", "INFERENCE", "ASSUMPTION", "UNRESOLVED_CLAIM", "CONTRADICTION"]
    text: Text
    evidence_event_ids: EventIDs


class ContinuityState(Contract):
    focus_objective_id: Identifier | None
    items: tuple[EpistemicItem, ...]
    next_steps: tuple[Text, ...]
    selected_objects: Selection
    event_ids: EventIDs

    @model_validator(mode="after")
    def unfocused(self):
        if self.focus_objective_id is None and self.next_steps:
            raise ValueError("unfocused handoff cannot contain task next steps")
        return self


class ItchCreate(Contract):
    kind: Literal["ITCH_CREATE"]
    local_key: LocalKey
    objective_id: Identifier
    discrepancy: Text
    evidence_event_ids: EventIDs


class ItchTransition(Contract):
    kind: Literal["ITCH_TRANSITION"]
    target: ItchReference
    expected_revision: Positive
    status: ItchStatus
    reason: Text
    evidence_event_ids: EventIDs


class InvariantCreate(Contract):
    kind: Literal["INVARIANT_CREATE"]
    family_local_key: LocalKey
    version_local_key: LocalKey
    objective_id: Identifier | None
    proposition: Text
    scope: Text
    supporting_event_ids: EventIDs
    contradictory_event_ids: EventIDs


class InvariantTransition(Contract):
    kind: Literal["INVARIANT_TRANSITION"]
    target: VersionReference
    expected_revision: Positive
    status: InvariantStatus
    reason: Text
    evidence_event_ids: EventIDs


class InvariantRevise(Contract):
    kind: Literal["INVARIANT_REVISE"]
    target: VersionReference
    expected_revision: Positive
    successor_local_key: LocalKey
    proposition: Text
    scope: Text
    supporting_event_ids: EventIDs
    contradictory_event_ids: EventIDs


class TaskClockTrigger(Contract):
    kind: Literal["TASK_CLOCK"]
    tick: Nonnegative


class PredecessorTrigger(Contract):
    kind: Literal["PREDECESSOR_FULFILLED"]
    predecessor: CommitmentReference


Trigger = Annotated[TaskClockTrigger | PredecessorTrigger, Field(discriminator="kind")]


class CommitmentCreate(Contract):
    kind: Literal["COMMITMENT_CREATE"]
    local_key: LocalKey
    objective_id: Identifier
    action: Text
    trigger: Trigger
    expiry_tick: Nonnegative | None
    authority_event_id: Identifier
    evidence_event_ids: EventIDs


class CommitmentTransition(Contract):
    kind: Literal["COMMITMENT_TRANSITION"]
    target: CommitmentReference
    expected_revision: Positive
    status: CommitmentStatus
    reason: Text
    evidence_event_ids: EventIDs
    superseded_by: CommitmentReference | None

    @model_validator(mode="after")
    def supersession(self):
        if (self.status == "SUPERSEDED") != (self.superseded_by is not None):
            raise ValueError("SUPERSEDED requires exactly one successor reference")
        return self


Mutation = Annotated[
    ItchCreate | ItchTransition | InvariantCreate | InvariantTransition |
    InvariantRevise | CommitmentCreate | CommitmentTransition,
    Field(discriminator="kind"),
]


class StateProposal(Contract):
    expected_parent_state_id: Identifier | None
    mutations: tuple[Mutation, ...]
    continuity: ContinuityState
    supporting_event_ids: EventIDs


class OperatorOutcome(Contract):
    outcome: Literal["COMPLETED", "BLOCKED", "AWAITING_OPERATOR", "CHECKPOINT"]
    explanation: Text
    evidence_event_ids: EventIDs
