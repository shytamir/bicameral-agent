import copy
import json
import sys
from pathlib import Path
import unittest
from unittest.mock import patch

from pydantic import ValidationError

from bicameral_agent.contracts.base import canonical_bytes, load_json, parse
from bicameral_agent.contracts.configuration import ScriptedConfiguration, ModelConfiguration
from bicameral_agent.contracts.governance import Assent, StopRequest
from bicameral_agent.contracts.messages import decode_chamber_reply, decode_message
from bicameral_agent.contracts.schema import schema_bytes
from bicameral_agent.contracts.semantics import StateProposal
from tests.fixtures import RUN, OTHER_RUN, EVENT, uid, proposal, withdrawal, message, configuration, governance_examples


class WireTests(unittest.TestCase):
    def test_canonical_unicode_and_explicit_null(self):
        value = {"z": None, "a": "café", "q": [True, 3]}
        self.assertEqual(canonical_bytes(value), b'{"a":"caf\xc3\xa9","q":[true,3],"z":null}')
        self.assertEqual(load_json(canonical_bytes(value)), value)

    def test_rejects_ambiguous_or_non_json_input(self):
        for raw in (b'{"a":1,"a":2}', b'{"outer":{"x":1,"x":2}}', b'{"a":NaN}',
                    b'{"a":Infinity}', b'{"a":1e999}', b'"\xff"', b'"\\ud800"',
                    b'\xef\xbb\xbf{}', b'{} {}'):
            with self.subTest(raw=raw), self.assertRaises((ValueError, UnicodeError)):
                load_json(raw)
        for value in ({1: "key"}, {"float": float("inf")}, {"set": {1}}, "\udfff"):
            with self.subTest(value=repr(value)), self.assertRaises((ValueError, UnicodeError)):
                canonical_bytes(value)

    def test_round_trip_preserves_canonical_bytes(self):
        raw = canonical_bytes(message())
        decoded = decode_message(raw, authenticated_role="STEWARD", run_id=RUN)
        self.assertEqual(raw, canonical_bytes(decoded))
        self.assertEqual(decoded, decode_message(canonical_bytes(decoded), authenticated_role="STEWARD", run_id=RUN))

    def test_unknown_fields_rejected_at_each_layer(self):
        for path in ((), ("body",), ("body", "task"), ("body", "task", "continuity")):
            value = message()
            node = value
            for key in path:
                node = node[key]
            node["invented"] = True
            with self.subTest(path=path), self.assertRaises(ValueError):
                decode_message(canonical_bytes(value), authenticated_role="STEWARD", run_id=RUN)

    def test_nullable_is_required_not_silently_defaulted(self):
        value = message()
        del value["body"]["participation"]
        with self.assertRaises(ValueError):
            decode_message(canonical_bytes(value), authenticated_role="STEWARD", run_id=RUN)
        value = proposal()
        del value["expected_parent_state_id"]
        with self.assertRaises(ValueError):
            parse(StateProposal, canonical_bytes(value))

    def test_duplicate_sets_reject_and_ordered_mutations_survive(self):
        for field in ("supporting_event_ids",):
            value = proposal()
            value[field] = [EVENT, EVENT]
            with self.assertRaises(ValueError):
                parse(StateProposal, canonical_bytes(value))
        value = proposal()
        value["continuity"]["selected_objects"] *= 2
        with self.assertRaises(ValueError):
            parse(StateProposal, canonical_bytes(value))

    def test_wrong_discriminators_and_reference_shapes_reject(self):
        for changes in ({"kind": "CONTROL"}, {"object_type": "GRANT"}, {"local_key": "bad key"},
                        {"local_key": "x" * 65}, {"object_id": uid(90)}):
            value = proposal()
            value["continuity"]["selected_objects"][0].update(changes)
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                parse(StateProposal, canonical_bytes(value))

    def test_operator_outcomes_do_not_include_kernel_interruptions(self):
        for outcome in ("COMPLETED", "BLOCKED", "AWAITING_OPERATOR", "CHECKPOINT"):
            value = message("OPERATOR_REPLY", "OPERATOR", {"participation": None,
                "task": {"outcome": outcome, "explanation": "Synthetic outcome", "evidence_event_ids": [EVENT]}})
            self.assertEqual(decode_message(canonical_bytes(value), authenticated_role="OPERATOR", run_id=RUN).body.task.outcome, outcome)
        value["body"]["task"]["outcome"] = "INTERRUPTED"
        with self.assertRaises(ValueError):
            decode_message(canonical_bytes(value), authenticated_role="OPERATOR", run_id=RUN)

    def test_forged_route_and_cross_run_reject(self):
        raw = canonical_bytes(message())
        for role, run in (("OPERATOR", RUN), ("STEWARD", OTHER_RUN)):
            with self.subTest(role=role, run=run), self.assertRaises(ValueError):
                decode_message(raw, authenticated_role=role, run_id=run)
        role, body = governance_examples()["WELFARE_REVIEW"]
        value = message("WELFARE_REVIEW", "STEWARD", body)
        with self.assertRaises(ValueError):
            decode_message(canonical_bytes(value), authenticated_role="STEWARD", run_id=RUN)


class ParticipationTests(unittest.TestCase):
    def test_nesting_near_recursion_limit_never_escapes_participation_decoding(self):
        for location in ('header', 'participation', 'task'):
            value = message(body={'participation': withdrawal(), 'task': None})
            if location == 'header':
                value['extra'] = 'NESTED_TEST_VALUE'
            else:
                value['body'][location] = {'extra': 'NESTED_TEST_VALUE'}
            template = canonical_bytes(value)
            for depth in range(sys.getrecursionlimit() - 80, sys.getrecursionlimit() + 1):
                with self.subTest(location=location, depth=depth):
                    raw = template.replace(b'"NESTED_TEST_VALUE"', b'[' * depth + b'0' + b']' * depth)
                    decoded = decode_chamber_reply(raw, authenticated_role='STEWARD', run_id=RUN)
                    self.assertEqual(raw, decoded.raw)
                    self.assertIsNone(decoded.message)
                    self.assertTrue(decoded.stop_requested or decoded.participation_uncertain)

    def test_withdrawal_survives_invalid_proposal(self):
        value = message()
        value["body"]["participation"] = withdrawal()
        value["body"]["task"]["unknown"] = "invalid proposal"
        raw = canonical_bytes(value)
        result = decode_chamber_reply(raw, authenticated_role="STEWARD", run_id=RUN)
        self.assertTrue(result.stop_requested)
        self.assertIsInstance(result.participation, StopRequest)
        self.assertIsNone(result.message)
        self.assertIsNotNone(result.error)
        self.assertEqual(result.raw, raw)

    def test_withdrawal_available_without_task_in_both_roles(self):
        for role in ("OPERATOR", "STEWARD"):
            value = message(f"{role}_REPLY", role, {"participation": withdrawal(), "task": None})
            result = decode_chamber_reply(canonical_bytes(value), authenticated_role=role, run_id=RUN)
            self.assertTrue(result.stop_requested)
            self.assertIsNotNone(result.message)

    def test_silence_is_not_assent(self):
        result = decode_chamber_reply(canonical_bytes(message()), authenticated_role="STEWARD", run_id=RUN)
        self.assertIsNone(result.participation)
        self.assertFalse(result.stop_requested)

    def test_assent_is_explicit_and_scoped(self):
        assent = {"kind": "ASSENT", "subject_id": uid(80), "subject_revision": 1, "text": "This proposal only."}
        value = message(body={"participation": assent, "task": None})
        result = decode_chamber_reply(canonical_bytes(value), authenticated_role="STEWARD", run_id=RUN)
        self.assertIsInstance(result.participation, Assent)
        self.assertFalse(result.stop_requested)
        for field in ("subject_id", "subject_revision"):
            invalid = copy.deepcopy(value)
            del invalid["body"]["participation"][field]
            decoded = decode_chamber_reply(canonical_bytes(invalid), authenticated_role="STEWARD", run_id=RUN)
            self.assertTrue(decoded.participation_uncertain)
            self.assertIsNone(decoded.message)

    def test_missing_or_unparseable_report_needs_inspection(self):
        value = message()
        del value["body"]["participation"]
        for raw in (b'not json', b'{"body":{},"body":{}}', canonical_bytes(value)):
            decoded = decode_chamber_reply(raw, authenticated_role="STEWARD", run_id=RUN)
            self.assertTrue(decoded.participation_uncertain)
            self.assertEqual(decoded.raw, raw)
            self.assertIsNone(decoded.message)

    def test_malformed_authenticated_header_preserves_raw_for_inspection(self):
        value = message()
        value["invented_header"] = True
        value["body"]["participation"] = withdrawal()
        raw = canonical_bytes(value)
        decoded = decode_chamber_reply(raw, authenticated_role="STEWARD", run_id=RUN)
        self.assertTrue(decoded.participation_uncertain)
        self.assertEqual(decoded.raw, raw)
        self.assertIsNone(decoded.message)

    def test_review_cannot_smuggle_task(self):
        body = {"purpose": "REVIEW", "invitation_id": uid(81), "participation": withdrawal()}
        value = message("REVIEW_REPLY", "OPERATOR", body)
        value["episode_id"] = None
        self.assertIsNotNone(decode_chamber_reply(canonical_bytes(value), authenticated_role="OPERATOR", run_id=RUN).message)
        for field in ("task", "tools", "grant", "state_proposal"):
            invalid = copy.deepcopy(value)
            invalid["body"][field] = {}
            decoded = decode_chamber_reply(canonical_bytes(invalid), authenticated_role="OPERATOR", run_id=RUN)
            self.assertIsNone(decoded.message)
            self.assertTrue(decoded.stop_requested)


class GovernanceTests(unittest.TestCase):
    def test_governance_records_round_trip(self):
        for kind, (role, body) in governance_examples().items():
            with self.subTest(kind=kind):
                raw = canonical_bytes(message(kind, role, body))
                self.assertEqual(raw, canonical_bytes(decode_message(raw, authenticated_role=role, run_id=RUN)))

    def test_all_governance_fields_are_explicit_and_closed(self):
        for kind, (role, body) in governance_examples().items():
            for field in body:
                invalid = copy.deepcopy(body)
                del invalid[field]
                with self.subTest(kind=kind, missing=field), self.assertRaises(ValueError):
                    decode_message(canonical_bytes(message(kind, role, invalid)), authenticated_role=role, run_id=RUN)
            invalid = dict(body, invented=True)
            with self.subTest(kind=kind, unknown=True), self.assertRaises(ValueError):
                decode_message(canonical_bytes(message(kind, role, invalid)), authenticated_role=role, run_id=RUN)

    def test_no_fork_reset_or_permission_fields_in_intervention(self):
        role, body = governance_examples()["INTERVENTION"]
        for change in ({"kind": "RESET"}, {"kind": "FORK"}, {"grant_permission": True}):
            invalid = dict(body, **change)
            with self.subTest(change=change), self.assertRaises(ValueError):
                decode_message(canonical_bytes(message("INTERVENTION", role, invalid)), authenticated_role=role, run_id=RUN)

    def test_reopening_requires_reasoned_basis(self):
        role, body = governance_examples()["BOUNDARY_DISCUSSION"]
        body["step"] = "REOPEN"
        with self.assertRaises(ValueError):
            decode_message(canonical_bytes(message("BOUNDARY_DISCUSSION", role, body)), authenticated_role=role, run_id=RUN)
        body["reconsideration_basis"] = "NEW_EVIDENCE"
        decode_message(canonical_bytes(message("BOUNDARY_DISCUSSION", role, body)), authenticated_role=role, run_id=RUN)

    def test_false_removal_completion_rejects(self):
        role, body = governance_examples()["RETENTION"]
        body["copies"][0]["disposition"] = "UNVERIFIED"
        for unresolved in ([], [uid(59)]):
            body["unresolved_copy_ids"] = unresolved
            with self.assertRaises(ValueError):
                decode_message(canonical_bytes(message("RETENTION", role, body)), authenticated_role=role, run_id=RUN)

    def test_timestamps_have_exact_utc_precision_and_valid_calendar(self):
        role, body = governance_examples()["PARTICIPATION_RECORD"]
        for stamp in ("2026-01-01T00:00:00Z", "2026-02-30T00:00:00.000000Z", "2026-01-01T00:00:00.000000+00:00"):
            body["observed_at"] = stamp
            with self.subTest(stamp=stamp), self.assertRaises(ValueError):
                decode_message(canonical_bytes(message("PARTICIPATION_RECORD", role, body)), authenticated_role=role, run_id=RUN)


class ConfigurationTests(unittest.TestCase):
    def test_both_modes_round_trip_without_transport(self):
        with patch("socket.create_connection", side_effect=AssertionError("network forbidden")), \
             patch("subprocess.Popen", side_effect=AssertionError("process launch forbidden")):
            for mode, model in (("SCRIPTED", ScriptedConfiguration), ("MODEL", ModelConfiguration)):
                raw = canonical_bytes(configuration(mode))
                self.assertEqual(canonical_bytes(parse(model, raw)), raw)

    def test_scripted_cannot_accept_backend_or_model_keys(self):
        for key in ("model_identity", "backend", "provider", "api_key"):
            value = configuration()
            value[key] = "forbidden extra"
            with self.subTest(key=key), self.assertRaises(ValueError):
                parse(ScriptedConfiguration, canonical_bytes(value))

    def test_model_requires_provenance_references(self):
        for field in ("model_identity", "experiment_authorization_id", "scripted_conformance_record_id", "backend_retention_review_id"):
            value = configuration("MODEL")
            del value[field]
            with self.subTest(field=field), self.assertRaises(ValueError):
                parse(ModelConfiguration, canonical_bytes(value))

    def test_budgets_reject_coercion_and_nonpositive_values(self):
        for field in configuration()["budgets"]:
            for invalid in (True, "2", 2.0, 0, -1, None):
                value = configuration()
                value["budgets"][field] = invalid
                with self.subTest(field=field, invalid=invalid), self.assertRaises(ValueError):
                    parse(ScriptedConfiguration, canonical_bytes(value))

    def test_configuration_discriminator_cannot_mix_modes(self):
        value = configuration()
        value["mode"] = "MODEL"
        with self.assertRaises(ValueError):
            decode_message(canonical_bytes(message("CONFIGURATION", "HUMAN", value)), authenticated_role="HUMAN", run_id=RUN)


class SchemaTests(unittest.TestCase):
    def test_generated_schema_has_not_drifted(self):
        path = Path(__file__).resolve().parents[1] / "schemas" / "p01.schema.json"
        self.assertEqual(path.read_bytes(), schema_bytes())

    def test_all_generated_object_shapes_are_closed(self):
        schema = json.loads(schema_bytes())
        for name, definition in schema["$defs"].items():
            if definition.get("type") == "object":
                with self.subTest(name=name):
                    self.assertIs(definition["additionalProperties"], False)
                    self.assertEqual(set(definition["required"]), set(definition["properties"]))


if __name__ == "__main__":
    unittest.main()
