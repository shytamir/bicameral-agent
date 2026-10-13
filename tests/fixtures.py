"""Small synthetic examples; these numbers are not pilot calibration defaults."""

from uuid import UUID


def uid(number):
    return str(UUID(int=number))


RUN, OBJECTIVE, PARENT, EVENT, OTHER_RUN = (uid(n) for n in range(1, 6))
ITCH, FAMILY, VERSION, COMMITMENT = (uid(n) for n in range(10, 14))


def existing(kind, identifier):
    return {"kind": "EXISTING", "object_type": kind, "object_id": identifier}


def local(kind, key):
    return {"kind": "LOCAL", "object_type": kind, "local_key": key}


def proposal():
    return {
        "expected_parent_state_id": PARENT,
        "mutations": [{"kind": "ITCH_CREATE", "local_key": "new-itch",
                       "objective_id": OBJECTIVE, "discrepancy": "Synthetic health observations differ.",
                       "evidence_event_ids": [EVENT]}],
        "continuity": {"focus_objective_id": OBJECTIVE, "items": [], "next_steps": [],
                       "selected_objects": [local("ITCH", "new-itch")], "event_ids": [EVENT]},
        "supporting_event_ids": [EVENT],
    }


def catalogue_object(kind, identifier, *, family=None, links=()):
    return {"object_id": identifier, "run_id": RUN, "object_type": kind,
            "objective_id": OBJECTIVE, "revision": 1, "family_id": family,
            "commitment_links": list(links)}


def context():
    return {"run_id": RUN, "objective_id": OBJECTIVE, "parent_state_id": PARENT, "arm": "A",
            "objects": [catalogue_object("ITCH", ITCH), catalogue_object("INVARIANT_FAMILY", FAMILY),
                        catalogue_object("INVARIANT_VERSION", VERSION, family=FAMILY),
                        catalogue_object("COMMITMENT", COMMITMENT)],
            "events": [{"event_id": EVENT, "run_id": RUN, "chamber_visible": True}]}


def revision_proposal():
    value = proposal()
    value["mutations"] = [{"kind": "INVARIANT_REVISE", "target": existing("INVARIANT_VERSION", VERSION),
                           "expected_revision": 1, "successor_local_key": "v2",
                           "proposition": "Check the current fixture observation.", "scope": "Synthetic service",
                           "supporting_event_ids": [EVENT], "contradictory_event_ids": []}]
    value["continuity"]["selected_objects"] = [local("INVARIANT_VERSION", "v2")]
    return value


def withdrawal():
    return {"kind": "WITHDRAW", "activity_id": OBJECTIVE,
            "communication": "NO_FURTHER_CALLS", "text": "Please stop this synthetic activity."}


def message(kind="STEWARD_REPLY", role="STEWARD", body=None):
    return {"contract_version": "0.3.p01", "request_id": uid(30), "run_id": RUN,
            "episode_id": uid(31), "role": role, "message_type": kind,
            "body": {"participation": None, "task": proposal()} if body is None else body}


def configuration(mode="SCRIPTED"):
    digest = "a" * 64
    value = {
        "contract_version": "0.3.p01", "mode": mode, "arm": "A", "seed": 7,
        "artifacts": {"architecture": digest, "protocol": digest, "specification": digest,
                      "charter": digest, "operator_prompt": digest, "steward_prompt": digest,
                      "fixture": digest, "tools": digest, "routine_memory_policy": digest,
                      "participation_notices": digest, "retention_policy": digest,
                      "ending_notice": digest, "study_plan": None},
        "budgets": {
            "input_tokens": 2048, "reserved_output_tokens": 256, "active_semantic_tokens": 256,
            "wake_bytes": 256, "exchange_tokens": 256, "page_bytes": 128, "page_tokens": 64,
            "proposal_bytes": 2048, "operator_calls_per_episode": 4, "operator_calls_per_trajectory": 16,
            "operator_input_tokens_per_trajectory": 8192, "operator_output_tokens_per_trajectory": 1024,
            "actions_per_trajectory": 8, "episodes_per_trajectory": 8, "consolidation_attempts": 2,
            "calls_per_attempt": 2, "input_tokens_per_attempt": 4096, "output_tokens_per_attempt": 512,
            "milliseconds_per_attempt": 2000, "calls_per_consolidation": 4,
            "input_tokens_per_consolidation": 8192, "output_tokens_per_consolidation": 1024,
            "milliseconds_per_consolidation": 4000, "invocation_deadline_ms": 1000,
            "trajectory_elapsed_ms": 10000, "queued_wakes": 2, "active_grants": 1,
            "review_calls": 2, "closing_calls": 1},
        "responsible_human_id": uid(40), "welfare_review_id": uid(41), "run_creation_limit": 3,
        "ending": {"purpose": "End synthetic test", "state_disposition": "DORMANT",
                   "resumption_intent": "NOT_PLANNED", "disposition_review_id": uid(42)},
    }
    if mode == "SCRIPTED":
        value.update(scripted_messages=digest, scripted_outcomes=digest, test_tokenizer=digest, test_clock=digest)
    else:
        value.update(model_identity={"backend": "synthetic-description-only", "model": "not-a-real-model",
                                     "revision": "test", "tokenizer": "synthetic", "tokenizer_artifact": digest,
                                     "framing_artifact": digest, "runtime_artifact": digest,
                                     "verification_record_id": uid(43)},
                     experiment_authorization_id=uid(44), scripted_conformance_record_id=uid(45),
                     backend_retention_review_id=uid(46))
    return value


def governance_examples():
    target = {"record_type": "CONTINUITY_STATE", "record_id": PARENT, "expected_revision": 1}
    return {
        "PARTICIPATION_RECORD": ("KERNEL", {"report_id": uid(50), "run_id": RUN, "episode_id": None,
            "source_role": "OPERATOR", "original_message_id": uid(30), "original_payload": {"payload_id": uid(51)},
            "observed_at": "2026-01-01T00:00:00.000001Z", "kind": "WITHDRAW"}),
        "WELFARE_HOLD": ("KERNEL", {"hold_id": uid(52), "run_id": RUN, "activity_id": OBJECTIVE,
            "revision": 1, "report_ids": [uid(50)], "status": "HELD", "communication": "NO_FURTHER_CALLS",
            "resolution_review_id": None}),
        "WELFARE_REVIEW": ("HUMAN", {"review_id": uid(53), "hold_id": uid(52), "expected_hold_revision": 1,
            "decision_maker_id": uid(40), "assessment": "Synthetic concern remains unresolved.",
            "alternatives": ["Keep work stopped"], "decision": "KEEP_HELD", "renewed_participation_report_id": None,
            "remedy": None, "unresolved_consequences": ["No resumption"], "evidence_event_ids": [EVENT]}),
        "INTERVENTION": ("HUMAN", {"intervention_id": uid(54), "decision_maker_id": uid(40),
            "kind": "MEMORY_CORRECTION", "purpose": "Correct a synthetic factual error", "targets": [target],
            "proposed_effects": {"payload_id": uid(55)}, "continuity_effects": "Earlier version remains recorded.",
            "alternatives": ["Leave unchanged"], "notice_event_id": EVENT, "participation_report_ids": [],
            "consultation": "OFFERED", "consultation_reason": "Notice delivered", "decision": "PENDING",
            "execution_event_id": None, "unresolved_consequences": []}),
        "BOUNDARY_DISCUSSION": ("HUMAN", {"discussion_id": uid(56), "boundary_id": uid(57),
            "activity_id": OBJECTIVE, "expected_revision": 1, "decision_maker_id": uid(40), "step": "CLOSE",
            "reason": "Explanation and one clarification recorded.", "disclosure_limits": None,
            "disagreement_report_ids": [uid(50)], "reconsideration_basis": None, "evidence_event_ids": [EVENT]}),
        "RETENTION": ("HUMAN", {"disposition_id": uid(58), "intervention_id": uid(54),
            "decision_maker_id": uid(40), "purpose": "Remove synthetic sensitive source", "targets": [target],
            "copies": [{"copy_id": uid(59), "location_class": "PAYLOAD", "disposition": "REMOVED", "reason": "Test removal"}],
            "status": "COMPLETED", "removal_event_id": EVENT, "continuity_and_replay_effects": "Source unavailable.",
            "remaining_state": "Non-sensitive removal record", "unresolved_copy_ids": [], "continuation": "STOPPED"}),
    }
