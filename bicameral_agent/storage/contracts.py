"""Closed storage records. These shapes confer no transport or human authority."""
from typing import Annotated, Literal

from pydantic import Field, TypeAdapter, model_validator

from ..contracts.base import Contract, Identifier, Positive, Nonnegative, PayloadReference, Text
from ..contracts.governance import WelfareHold, WelfareReview, InterventionRecord, BoundaryDiscussion, RetentionRecord
from ..contracts.resolution import Binding
from ..contracts.semantics import ItchCreate, InvariantCreate, InvariantRevise, CommitmentCreate, ObjectType, Mutation

class RunState(Contract):
    kind: Literal["RUN"]
    status: Literal["CREATED", "ACTIVE", "PAUSED", "COMPLETED", "TERMINATED"]
    objective_id: Identifier | None
    task_tick: Nonnegative

class ObjectiveState(Contract):
    kind: Literal["OBJECTIVE"]
    statement: Text
    status: Literal["ACTIVE", "SATISFIED", "FAILED", "CANCELLED", "SUPERSEDED"]
    authority_event_id: Identifier

class EpisodeState(Contract):
    kind: Literal["EPISODE"]
    objective_id: Identifier
    phase: Literal["OPEN", "CONSOLIDATING", "RECOVERY_REQUIRED", "CLOSED"]
    disposition: Literal["BASELINE", "ACCEPTED", "HUMAN_CORRECTED", "SKIPPED"] | None

    @model_validator(mode="after")
    def closure(self):
        if (self.phase == "CLOSED") != (self.disposition is not None):
            raise ValueError("closed Episode requires a disposition")
        return self

Control = RunState | ObjectiveState | EpisodeState | WelfareHold | WelfareReview | InterventionRecord | BoundaryDiscussion | RetentionRecord
CONTROL = TypeAdapter(Control)

Content = Annotated[ItchCreate | InvariantCreate | InvariantRevise | CommitmentCreate, Field(discriminator="kind")]

class StoredObject(Contract):
    object_id: Identifier
    run_id: Identifier
    object_type: ObjectType
    objective_id: Identifier | None
    revision: Positive
    family_id: Identifier | None
    predecessor_id: Identifier | None
    status: Literal["OPEN", "INVESTIGATING", "RESOLVED", "DISMISSED", "ARCHIVED",
                    "TENTATIVE", "ACTIVE", "CHALLENGED", "RETIRED", "PENDING",
                    "TRIGGERED", "IN_PROGRESS", "BLOCKED", "FULFILLED", "CANCELLED",
                    "SUPERSEDED", "EXPIRED", "FAMILY"]
    content: Content
    commitment_links: tuple[Identifier, ...]

    @model_validator(mode="after")
    def shape(self):
        states = {
            "ITCH": {"OPEN", "INVESTIGATING", "RESOLVED", "DISMISSED", "ARCHIVED"},
            "INVARIANT_FAMILY": {"FAMILY"},
            "INVARIANT_VERSION": {"TENTATIVE", "ACTIVE", "CHALLENGED", "RETIRED"},
            "COMMITMENT": {"PENDING", "TRIGGERED", "IN_PROGRESS", "BLOCKED", "FULFILLED", "CANCELLED", "SUPERSEDED", "EXPIRED"},
        }
        content_types = {"ITCH": (ItchCreate,), "INVARIANT_FAMILY": (InvariantCreate,),
                         "INVARIANT_VERSION": (InvariantCreate, InvariantRevise), "COMMITMENT": (CommitmentCreate,)}
        if self.status not in states[self.object_type] or not isinstance(self.content, content_types[self.object_type]):
            raise ValueError("object content/status disagrees with type")
        if (self.object_type == "INVARIANT_VERSION") != (self.family_id is not None):
            raise ValueError("only Invariant versions have a family")
        if self.object_type in ("ITCH", "COMMITMENT") and self.objective_id is None:
            raise ValueError("owned semantic object needs an Objective")
        if self.object_type != "COMMITMENT" and self.commitment_links:
            raise ValueError("only Commitments have dependency links")
        if self.object_type != "INVARIANT_VERSION" and self.predecessor_id is not None:
            raise ValueError("only Invariant versions have a predecessor")
        return self

class ChamberKey(Contract):
    run_id: Identifier
    role: Literal["OPERATOR", "STEWARD"]
    request_id: Identifier
    episode_id: Identifier | None

class Receipt(Contract):
    request_id: Identifier
    status: Literal["RECORDED", "ACCEPTED", "REJECTED"]
    state_id: Identifier | None
    bindings: tuple[Binding, ...]
    error_code: Literal["INVALID_TASK", "INSPECTION_REQUIRED", "WITHDRAWAL", "VALIDATION_FAILED"] | None
    diagnostics: PayloadReference | None

    @model_validator(mode="after")
    def consistency(self):
        if (self.status == "ACCEPTED") != (self.state_id is not None):
            raise ValueError("only acceptance has a semantic state")
        if self.status != "ACCEPTED" and self.bindings:
            raise ValueError("unaccepted allocation has no durable binding")
        if (self.status == "REJECTED") != (self.error_code is not None):
            raise ValueError("rejection requires an error code")
        if (self.status == "REJECTED") != (self.diagnostics is not None):
            raise ValueError("rejection requires retained diagnostics")
        return self

class ObjectChange(Contract):
    object_id: Identifier
    before: Identifier | None
    after: Identifier

class MutationEntry(Contract):
    mutation: Mutation
    changes: Annotated[tuple[ObjectChange, ...], Field(min_length=1)]

class StorageContracts(Contract):
    mutation_entry: MutationEntry
    chamber_key: ChamberKey
    control: Control
    object: StoredObject
    receipt: Receipt
