"""Wire shapes and participation-first decoding. No effects are performed."""

from dataclasses import dataclass
from typing import Annotated, Literal

from pydantic import Field, TypeAdapter, ValidationError

from .base import Contract, Identifier, canonical_bytes, load_json, parse
from .configuration import RunConfiguration
from .governance import (
    BoundaryDiscussion, InterventionRecord, Participation, ParticipationRecord,
    RetentionRecord, StopRequest, WelfareHold, WelfareReview,
)
from .semantics import OperatorOutcome, StateProposal


Role = Literal["OPERATOR", "STEWARD", "HUMAN", "KERNEL"]
MessageType = Literal["OPERATOR_REPLY", "STEWARD_REPLY", "REVIEW_REPLY", "PARTICIPATION_RECORD", "WELFARE_HOLD", "WELFARE_REVIEW", "INTERVENTION", "BOUNDARY_DISCUSSION", "RETENTION", "CONFIGURATION"]


class Header(Contract):
    contract_version: Literal["0.3.p01"]
    request_id: Identifier
    run_id: Identifier
    episode_id: Identifier | None
    role: Role
    message_type: MessageType


class OperatorBody(Contract):
    participation: Participation | None
    task: OperatorOutcome | None


class StewardBody(Contract):
    participation: Participation | None
    task: StateProposal | None


class ReviewBody(Contract):
    purpose: Literal["REVIEW", "CLOSING"]
    invitation_id: Identifier
    participation: Participation | None


class OperatorReply(Header):
    role: Literal["OPERATOR"]
    message_type: Literal["OPERATOR_REPLY"]
    episode_id: Identifier
    body: OperatorBody


class StewardReply(Header):
    role: Literal["STEWARD"]
    message_type: Literal["STEWARD_REPLY"]
    episode_id: Identifier
    body: StewardBody


class ReviewReply(Header):
    role: Literal["OPERATOR", "STEWARD"]
    message_type: Literal["REVIEW_REPLY"]
    body: ReviewBody


class ParticipationRecordMessage(Header):
    role: Literal["KERNEL"]
    message_type: Literal["PARTICIPATION_RECORD"]
    body: ParticipationRecord


class WelfareHoldMessage(Header):
    role: Literal["KERNEL"]
    message_type: Literal["WELFARE_HOLD"]
    body: WelfareHold


class WelfareReviewMessage(Header):
    role: Literal["HUMAN"]
    message_type: Literal["WELFARE_REVIEW"]
    body: WelfareReview


class InterventionMessage(Header):
    role: Literal["HUMAN"]
    message_type: Literal["INTERVENTION"]
    body: InterventionRecord


class BoundaryMessage(Header):
    role: Literal["HUMAN"]
    message_type: Literal["BOUNDARY_DISCUSSION"]
    body: BoundaryDiscussion


class RetentionMessage(Header):
    role: Literal["HUMAN"]
    message_type: Literal["RETENTION"]
    body: RetentionRecord


class ConfigurationMessage(Header):
    role: Literal["HUMAN"]
    message_type: Literal["CONFIGURATION"]
    body: RunConfiguration


Message = Annotated[
    OperatorReply | StewardReply | ReviewReply | ParticipationRecordMessage |
    WelfareHoldMessage | WelfareReviewMessage | InterventionMessage |
    BoundaryMessage | RetentionMessage | ConfigurationMessage,
    Field(discriminator="message_type"),
]
MESSAGE_ADAPTER = TypeAdapter(Message)
PARTICIPATION_ADAPTER = TypeAdapter(Participation | None)


class RouteMismatch(ValueError):
    """Claimed identity or message capability disagrees with the trusted route."""


def _header(value: object, role: Role, run_id: str) -> Header:
    if not isinstance(value, dict) or "body" not in value:
        raise ValueError("message must contain a header and body")
    header = parse(Header, canonical_bytes({key: item for key, item in value.items() if key != "body"}))
    if header.role != role or header.run_id != run_id:
        raise RouteMismatch("message disagrees with authenticated route")
    allowed_roles = {
        "OPERATOR_REPLY": ("OPERATOR",), "STEWARD_REPLY": ("STEWARD",),
        "REVIEW_REPLY": ("OPERATOR", "STEWARD"),
        "PARTICIPATION_RECORD": ("KERNEL",), "WELFARE_HOLD": ("KERNEL",),
    }
    if role not in allowed_roles.get(header.message_type, ("HUMAN",)):
        raise RouteMismatch("message type is unavailable to this role")
    return header


def decode_message(raw: bytes, *, authenticated_role: Role, run_id: str) -> Message:
    """Caller supplies trusted route identity; claimed wire identity is checked."""
    value = load_json(raw)
    _header(value, authenticated_role, run_id)
    message = MESSAGE_ADAPTER.validate_json(canonical_bytes(value), strict=True)
    if isinstance(message, (ParticipationRecordMessage, WelfareHoldMessage)):
        if message.body.run_id != run_id:
            raise ValueError("record belongs to another Run")
    return message


@dataclass(frozen=True)
class ChamberDecode:
    """Preserve raw evidence even if task parsing fails; caller must persist it."""

    raw: bytes
    header: Header | None
    participation: Participation | None
    message: OperatorReply | StewardReply | ReviewReply | None
    error: str | None
    participation_uncertain: bool

    @property
    def stop_requested(self) -> bool:
        return isinstance(self.participation, StopRequest)


def decode_chamber_reply(raw: bytes, *, authenticated_role: Role, run_id: str) -> ChamberDecode:
    """Decode reporting separately so an invalid task cannot swallow withdrawal.

    This result creates no durable hold. P02/P03 must persist it and enforce gates.
    Invalid route identity rejects; unparseable authenticated bytes need inspection.
    """
    if authenticated_role not in ("OPERATOR", "STEWARD"):
        raise ValueError("chamber decoder requires a chamber route")
    try:
        value = load_json(raw)
    except (ValueError, UnicodeError) as error:
        return ChamberDecode(raw, None, None, None, str(error), True)
    try:
        header = _header(value, authenticated_role, run_id)
    except RouteMismatch:
        raise
    except ValueError as error:
        return ChamberDecode(raw, None, None, None, str(error), True)
    body = value["body"]
    try:
        if not isinstance(body, dict) or "participation" not in body:
            raise ValueError("participation field must be explicit, including null")
        participation = PARTICIPATION_ADAPTER.validate_json(canonical_bytes(body["participation"]), strict=True)
    except (ValueError, ValidationError) as error:
        return ChamberDecode(raw, header, None, None, str(error), True)
    try:
        message = decode_message(raw, authenticated_role=authenticated_role, run_id=run_id)
        return ChamberDecode(raw, header, participation, message, None, False)
    except (ValueError, ValidationError) as error:
        return ChamberDecode(raw, header, participation, None, str(error), False)
