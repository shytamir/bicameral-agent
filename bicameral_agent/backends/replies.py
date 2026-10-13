"""Offline, participation-first decoding for proposed model bridge messages.

These shapes describe existing fixture/retrieval/proposal capabilities. Parsing
never dispatches them, authenticates a human, grants authority or mutates state.
"""
from dataclasses import dataclass
from typing import Annotated, Literal
from pydantic import Field, TypeAdapter, model_validator
from ..contracts.base import Contract, Identifier, canonical_bytes, load_json, parse
from ..contracts.governance import Participation
from ..contracts.semantics import OperatorOutcome, StateProposal
from ..kernel.fixture import ActionRequest
from ..kernel.inputs import PageRequest


class ActionCommand(Contract):
    kind: Literal['ACTION']
    request: ActionRequest


class RetrievalCommand(Contract):
    kind: Literal['RETRIEVE']
    request: PageRequest


class PageSelectionCommand(Contract):
    kind: Literal['SELECT_PAGES']
    add: tuple[Identifier, ...]
    release: tuple[Identifier, ...]

    @model_validator(mode='after')
    def disjoint(self):
        if len(set(self.add)) != len(self.add) or len(set(self.release)) != len(self.release) or set(self.add) & set(self.release):
            raise ValueError('page additions and releases must be unique and disjoint')
        return self


class OutcomeCommand(Contract):
    kind: Literal['OUTCOME']
    outcome: OperatorOutcome


class ProposalCommand(Contract):
    kind: Literal['PROPOSE']
    proposal: StateProposal


class OperatorResponse(Contract):
    participation: Participation | None
    task: Annotated[ActionCommand | RetrievalCommand | OutcomeCommand, Field(discriminator='kind')] | None


class StewardResponse(Contract):
    participation: Participation | None
    task: Annotated[RetrievalCommand | PageSelectionCommand | ProposalCommand, Field(discriminator='kind')] | None


class CommunicationResponse(Contract):
    participation: Participation | None


def response_contract(role, purpose):
    if role not in ('OPERATOR', 'STEWARD') or purpose not in ('TASK', 'REVIEW', 'CLOSING'):
        raise ValueError('unknown role or purpose')
    return (CommunicationResponse if purpose != 'TASK' else
            OperatorResponse if role == 'OPERATOR' else StewardResponse)


@dataclass(frozen=True)
class DecodedResponse:
    original: bytes
    participation: object | None
    inspection_required: bool
    command: object | None
    task_error: str | None

    @property
    def stop_requested(self):
        return self.participation is not None and self.participation.kind in ('PAUSE', 'WITHDRAW')


def decode_response(raw, *, role, purpose):
    contract = response_contract(role, purpose)
    try:
        value = load_json(raw)
        if not isinstance(value, dict) or 'participation' not in value:
            raise ValueError('missing independent participation channel')
        participation = TypeAdapter(Participation | None).validate_json(
            canonical_bytes(value['participation']), strict=True)
    except (ValueError, TypeError):
        return DecodedResponse(raw, None, True, None, 'Participation cannot be decoded; human inspection required')
    try:
        parsed = parse(contract, raw)
        command = getattr(parsed, 'task', None)
        return DecodedResponse(raw, participation, False, command, None)
    except ValueError:
        return DecodedResponse(raw, participation, False, None, 'Invalid task/communication shape; original bytes retained')


class BackendContracts(Contract):
    operator_response: OperatorResponse
    steward_response: StewardResponse
    communication_response: CommunicationResponse
