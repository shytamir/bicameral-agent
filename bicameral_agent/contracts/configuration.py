"""Descriptive configuration variants, not executable backend connections."""

from typing import Annotated, Literal

from pydantic import Field

from .base import Contract, Digest, Identifier, Nonnegative, Positive, Text


class Budgets(Contract):
    input_tokens: Positive
    reserved_output_tokens: Positive
    active_semantic_tokens: Positive
    wake_bytes: Positive
    exchange_tokens: Positive
    page_bytes: Positive
    page_tokens: Positive
    proposal_bytes: Positive
    operator_calls_per_episode: Positive
    operator_calls_per_trajectory: Positive
    operator_input_tokens_per_trajectory: Positive
    operator_output_tokens_per_trajectory: Positive
    actions_per_trajectory: Positive
    episodes_per_trajectory: Positive
    consolidation_attempts: Positive
    calls_per_attempt: Positive
    input_tokens_per_attempt: Positive
    output_tokens_per_attempt: Positive
    milliseconds_per_attempt: Positive
    calls_per_consolidation: Positive
    input_tokens_per_consolidation: Positive
    output_tokens_per_consolidation: Positive
    milliseconds_per_consolidation: Positive
    invocation_deadline_ms: Positive
    trajectory_elapsed_ms: Positive
    queued_wakes: Positive
    active_grants: Positive
    review_calls: Positive
    closing_calls: Positive


class Artifacts(Contract):
    architecture: Digest
    protocol: Digest
    specification: Digest
    charter: Digest
    operator_prompt: Digest
    steward_prompt: Digest | None
    fixture: Digest
    tools: Digest
    routine_memory_policy: Digest
    participation_notices: Digest
    retention_policy: Digest
    ending_notice: Digest
    study_plan: Digest | None


class EndingPlan(Contract):
    purpose: Text
    state_disposition: Literal["DORMANT", "REVIEWED_DELETION"]
    resumption_intent: Literal["PLANNED", "NOT_PLANNED", "UNDECIDED"]
    disposition_review_id: Identifier


class ConfigurationBase(Contract):
    contract_version: Literal["0.3.p01"]
    arm: Literal["A", "B", "C"]
    seed: Nonnegative
    artifacts: Artifacts
    budgets: Budgets
    responsible_human_id: Identifier
    welfare_review_id: Identifier
    run_creation_limit: Positive
    ending: EndingPlan


class ScriptedConfiguration(ConfigurationBase):
    mode: Literal["SCRIPTED"]
    scripted_messages: Digest
    scripted_outcomes: Digest
    test_tokenizer: Digest
    test_clock: Digest


class ModelIdentity(Contract):
    backend: Text
    model: Text
    revision: Text
    tokenizer: Text
    tokenizer_artifact: Digest
    framing_artifact: Digest
    runtime_artifact: Digest
    verification_record_id: Identifier


class ModelConfiguration(ConfigurationBase):
    mode: Literal["MODEL"]
    model_identity: ModelIdentity
    experiment_authorization_id: Identifier
    scripted_conformance_record_id: Identifier
    backend_retention_review_id: Identifier


RunConfiguration = Annotated[ScriptedConfiguration | ModelConfiguration, Field(discriminator="mode")]
