"""Participation and human review records are never executable permissions."""

from typing import Annotated, Literal

from pydantic import AfterValidator, Field, model_validator

from .base import Contract, EventIDs, Identifier, PayloadReference, Positive, Text, UTC, unique


class Concern(Contract):
    kind: Literal["CONCERN", "PREFERENCE"]
    activity_id: Identifier
    text: Text


class StopRequest(Contract):
    kind: Literal["PAUSE", "WITHDRAW"]
    activity_id: Identifier
    communication: Literal["REVIEW_PERMITTED", "NO_FURTHER_CALLS", "UNCLEAR"]
    text: Text


class Assent(Contract):
    kind: Literal["ASSENT"]
    subject_id: Identifier
    subject_revision: Positive
    text: Text


Participation = Annotated[Concern | StopRequest | Assent, Field(discriminator="kind")]


class ParticipationRecord(Contract):
    report_id: Identifier
    run_id: Identifier
    episode_id: Identifier | None
    source_role: Literal["OPERATOR", "STEWARD"]
    original_message_id: Identifier
    original_payload: PayloadReference
    observed_at: UTC
    kind: Literal["CONCERN", "PREFERENCE", "PAUSE", "WITHDRAW", "ASSENT"]


class WelfareHold(Contract):
    hold_id: Identifier
    run_id: Identifier
    activity_id: Identifier
    revision: Positive
    report_ids: Annotated[tuple[Identifier, ...], Field(min_length=1), AfterValidator(unique)]
    status: Literal["HELD", "RESOLVED"]
    communication: Literal["REVIEW_PERMITTED", "NO_FURTHER_CALLS", "UNCLEAR"]
    resolution_review_id: Identifier | None

    @model_validator(mode="after")
    def resolution(self):
        if (self.status == "RESOLVED") != (self.resolution_review_id is not None):
            raise ValueError("resolved hold needs a review reference")
        return self


class WelfareReview(Contract):
    review_id: Identifier
    hold_id: Identifier
    expected_hold_revision: Positive
    decision_maker_id: Identifier
    assessment: Text
    alternatives: tuple[Text, ...]
    decision: Literal["KEEP_HELD", "END_ACTIVITY", "RESOLVE"]
    renewed_participation_report_id: Identifier | None
    remedy: Text | None
    unresolved_consequences: tuple[Text, ...]
    evidence_event_ids: EventIDs


class InterventionTarget(Contract):
    record_type: Literal["CONTINUITY_STATE", "ITCH", "INVARIANT_VERSION", "COMMITMENT", "RUN", "PAYLOAD"]
    record_id: Identifier
    expected_revision: Positive


class InterventionRecord(Contract):
    intervention_id: Identifier
    decision_maker_id: Identifier
    kind: Literal["MEMORY_CORRECTION", "SEMANTIC_RESTORATION", "RETENTION", "PLANNED_ENDING", "EMERGENCY_STOP"]
    purpose: Text
    targets: Annotated[tuple[InterventionTarget, ...], Field(min_length=1), AfterValidator(unique)]
    proposed_effects: PayloadReference
    continuity_effects: Text
    alternatives: tuple[Text, ...]
    notice_event_id: Identifier | None
    participation_report_ids: EventIDs
    consultation: Literal["OFFERED", "DECLINED", "INFEASIBLE", "EMERGENCY"]
    consultation_reason: Text
    decision: Literal["PENDING", "APPROVED", "REJECTED"]
    execution_event_id: Identifier | None
    unresolved_consequences: tuple[Text, ...]


class BoundaryDiscussion(Contract):
    discussion_id: Identifier
    boundary_id: Identifier
    activity_id: Identifier
    expected_revision: Positive
    decision_maker_id: Identifier
    step: Literal["EXPLANATION", "CLARIFICATION", "CLOSE", "REOPEN", "DECLINE_REOPEN"]
    reason: Text
    disclosure_limits: Text | None
    disagreement_report_ids: EventIDs
    reconsideration_basis: Literal["NEW_EVIDENCE", "CHANGED_CIRCUMSTANCES", "SCHEDULED_REVIEW"] | None
    evidence_event_ids: EventIDs

    @model_validator(mode="after")
    def reopening(self):
        if self.step == "REOPEN" and self.reconsideration_basis is None:
            raise ValueError("reopening needs a recorded permissible basis")
        return self


class RetentionCopy(Contract):
    copy_id: Identifier
    location_class: Literal["PAYLOAD", "PROJECTION", "JOURNAL", "MUTATION", "INVOCATION", "CACHE", "EXPORT", "WAL", "FREE_PAGES", "BACKUP", "PROVIDER"]
    disposition: Literal["PENDING", "REMOVED", "RETAINED", "INACCESSIBLE", "UNVERIFIED"]
    reason: Text


class RetentionRecord(Contract):
    disposition_id: Identifier
    intervention_id: Identifier
    decision_maker_id: Identifier
    purpose: Text
    targets: Annotated[tuple[InterventionTarget, ...], Field(min_length=1), AfterValidator(unique)]
    copies: Annotated[tuple[RetentionCopy, ...], Field(min_length=1)]
    status: Literal["PROPOSED", "IN_PROGRESS", "COMPLETED", "INCOMPLETE"]
    removal_event_id: Identifier | None
    continuity_and_replay_effects: Text
    remaining_state: Text
    unresolved_copy_ids: EventIDs
    continuation: Literal["STOPPED", "REVIEW_REQUIRED", "ELIGIBLE_FOR_REVIEWED_RESUMPTION"]

    @model_validator(mode="after")
    def copy_accounting(self):
        ids = [copy.copy_id for copy in self.copies]
        if len(ids) != len(set(ids)):
            raise ValueError("duplicate copy identity")
        unresolved = {copy.copy_id for copy in self.copies
                      if copy.disposition in ("PENDING", "INACCESSIBLE", "UNVERIFIED")}
        if unresolved != set(self.unresolved_copy_ids):
            raise ValueError("unresolved copies must be accounted for exactly")
        if self.status == "COMPLETED" and (unresolved or self.removal_event_id is None):
            raise ValueError("cannot claim complete removal with unresolved copies or no evidence")
        return self
