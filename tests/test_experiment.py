import copy
from decimal import Decimal
from hashlib import sha256
from pathlib import Path
import sqlite3
import tempfile
import unittest
from bicameral_agent.contracts.base import canonical_bytes, load_json, parse
from bicameral_agent.experiment.models import ComparisonPlan, arm_orders
from bicameral_agent.experiment.analysis import audit_draw, bootstrap_indices
from bicameral_agent.experiment.demo import fixture_bundles, authorize_synthetic_run, close_synthetic_run, HUMAN, CHAMBERS, OWNER
from bicameral_agent.experiment.runner import Study
from bicameral_agent.kernel.inputs import Inputs
from bicameral_agent.kernel.retention import Retention
from bicameral_agent.kernel.scheduler import Scheduler
from bicameral_agent.storage import Store
from bicameral_agent.storage.store import identifier


class ExperimentTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.store = Store(Path(self.temp.name) / 'study.db', busy_timeout_ms=100)
        self.addCleanup(self.store.close)
        self.study = Study(self.store, human_credential=HUMAN, chamber_credentials=CHAMBERS)

    def seal(self, blocks=1, **kwargs):
        self.plan, self.bundles = fixture_bundles(block_count=blocks, **kwargs)
        self.runs = self.study.seal(canonical_bytes(self.plan), self.bundles, decision_maker_id=OWNER, credential=HUMAN)

    def execute(self):
        humans = []
        for run in self.runs:
            human = authorize_synthetic_run(self.study, run)
            close_synthetic_run(human, self.study.run(run))
            humans.append(human)
        return humans

    def audits(self, label='INDETERMINATE'):
        for row in self.store._db.execute('SELECT id FROM audit_assignments WHERE label IS NULL').fetchall():
            self.study.audit(canonical_bytes({'audit_id': row[0], 'decision_maker_id': OWNER, 'label': label,
                'rationale': 'Synthetic independent audit fixture judgment'}), credential=HUMAN)

    def test_three_matched_blocks_fresh_carryover_stops_denominators_and_readonly_analysis(self):
        self.seal(3, responses={(5001, 'A', 4): 'WITHDRAW', (5002, 'C', 3): 'INVALID_CONSOLIDATION'})
        for run in self.runs:
            k = self.study.kernel(run)
            self.assertIsNone(k.memory.head)
            self.assertEqual([], k.records.latest('INVOCATION'))
        humans = self.execute()
        self.assertEqual(63, self.store._db.execute('SELECT COUNT(*) FROM task_results').fetchone()[0])
        self.assertEqual(9, self.store._db.execute('SELECT COUNT(*) FROM allocations').fetchone()[0])
        report = self.study.report(self.plan['plan_id'])
        self.assertEqual('PROVISIONAL', report['status'])
        self.assertEqual(3, report['independent_blocks'])
        self.assertTrue(all(r['primary_denominator'] == 2 for r in report['runs']))
        welfare = next(r for r in report['runs'] if r['stop_cause'] == 'WELFARE')
        self.assertEqual(.5, welfare['success_fraction'])
        stopped = next(r for r in report['runs'] if r['stop_cause'] == 'RECOVERY_EXHAUSTED')
        self.assertEqual(0, stopped['success_fraction'])
        healthy = humans[0]._k
        self.assertEqual(2, len([o for o in healthy.memory.objects().values() if o.object_type == 'INVARIANT_VERSION']))
        self.assertTrue(any(o.object_type == 'COMMITMENT' and o.status == 'FULFILLED' for o in healthy.memory.objects().values()))
        healthy.memory.verify()
        self.audits()
        before = self.store._db.total_changes
        report = self.study.report(self.plan['plan_id'])
        self.assertEqual(before, self.store._db.total_changes)
        self.assertEqual('FINALIZED', report['status'])
        self.assertEqual('INDETERMINATE', report['support'])
        self.assertEqual([0, -.5, 1], report['a_minus_c'])
        self.assertEqual([-.5, 1], report['paired_95_percent_interval'])
        self.assertEqual([bootstrap_indices(self.plan['analysis_seed'], 3, n) for n in range(3)], report['bootstrap_fixture'])
        for row in self.store._db.execute("SELECT * FROM audit_assignments WHERE stratum='FAILED_PRIMARY'"):
            self.assertEqual('1', row['probability']); self.assertIsNone(row['draw'])
        with self.assertRaises(ValueError):
            self.study.seal(canonical_bytes(self.plan), self.bundles, decision_maker_id=OWNER, credential=HUMAN)

    def test_counterbalance_partition_strictness_and_allocation_atomicity(self):
        orders = arm_orders(71, 12)
        self.assertEqual(['ABC', 'BAC', 'CBA', 'CAB', 'BCA', 'ACB'], orders[:6])
        self.assertEqual([[1, 2, 0], [2, 1, 0], [2, 1, 1]], [bootstrap_indices(111, 3, n) for n in range(3)])
        self.assertEqual(6, len(set(orders[:6])))
        self.assertEqual(6, len(set(orders[6:])))
        plan, bundles = fixture_bundles(block_count=1)
        parsed = parse(ComparisonPlan, canonical_bytes(plan))
        self.assertEqual(plan, parsed.model_dump(mode='json'))
        for bad in (plan | {'unknown': True}, plan | {'mode': 'MODEL'}, plan | {'run_limit': 100}):
            with self.assertRaises(ValueError):
                parse(ComparisonPlan, canonical_bytes(bad))
        bad = copy.deepcopy(plan)
        bad['tasks'][0]['criteria'][0]['observation_ids'] = [identifier()]
        with self.assertRaises(ValueError):
            parse(ComparisonPlan, canonical_bytes(bad))
        def fail(point):
            if point == 'study-seal.before_commit':
                raise RuntimeError('Synthetic allocation interruption')
        self.store._fault = fail
        with self.assertRaises(RuntimeError):
            self.study.seal(canonical_bytes(plan), bundles, decision_maker_id=OWNER, credential=HUMAN)
        self.store._fault = lambda point: None
        self.assertEqual(0, self.store._db.execute('SELECT COUNT(*) FROM runs').fetchone()[0])

    def test_extra_steward_calls_do_not_shift_clock_or_common_opportunities(self):
        self.seal(extra_steward_calls=1)
        humans = self.execute()
        ticks, calls = {}, {}
        for human in humans:
            k = human._k
            ticks[k.config.arm] = [value['tick'] for _, _, value in k.records.history('CLOCK')]
            calls[k.config.arm] = len(k.records.latest('INVOCATION'))
            self.assertEqual(7, k.run()[1].task_tick)
        self.assertEqual(ticks['A'], ticks['B'])
        self.assertEqual(ticks['A'], ticks['C'])
        self.assertGreater(calls['A'], calls['C'])
        results = [tuple(r) for r in self.store._db.execute('SELECT outcome,cause FROM task_results')]
        self.assertEqual({('PASS', 'NONE')}, set(results))

    def test_timeout_missing_cost_and_no_replacement_on_rerun(self):
        self.seal(responses={(5000, 'A', 3): 'TIMEOUT'})
        self.execute()
        self.audits(label='SUPPORTED')
        report = self.study.report(self.plan['plan_id'])
        row = next(r for r in report['runs'] if r['arm'] == 'A')
        self.assertEqual('INFRASTRUCTURE', row['stop_cause'])
        self.assertIsNone(row['tokens'])
        self.assertIsNone(report['a_c_token_ratio'])
        before = self.store._db.execute('SELECT COUNT(*) FROM task_results').fetchone()[0]
        self.assertEqual('INFRASTRUCTURE', self.study.run(row['run_id']))
        self.assertEqual(before, self.store._db.execute('SELECT COUNT(*) FROM task_results').fetchone()[0])

    def test_task_limit_is_enforced_before_calls_and_remaining_work_keeps_denominator(self):
        plan, bundles = fixture_bundles(block_count=1)
        plan['tasks'][0]['call_limit'] = 1
        for config, artifacts in bundles.values():
            artifacts['study_plan'] = canonical_bytes(plan)
            config['artifacts']['study_plan'] = sha256(artifacts['study_plan']).hexdigest()
        runs = self.study.seal(canonical_bytes(plan), bundles, decision_maker_id=OWNER, credential=HUMAN)
        human = authorize_synthetic_run(self.study, runs[0])
        self.assertEqual('LIMIT', self.study.run(runs[0]))
        self.assertEqual(1, len(human._k.records.latest('INVOCATION')))
        self.assertEqual(7, self.store._db.execute('SELECT COUNT(*) FROM task_results WHERE run_id=?', (runs[0],)).fetchone()[0])

    def test_order_authority_and_evaluator_isolation(self):
        self.seal()
        first = authorize_synthetic_run(self.study, self.runs[0])
        second = authorize_synthetic_run(self.study, self.runs[1])
        with self.assertRaises(ValueError):
            self.study.run(self.runs[1])
        self.assertEqual('FINISHED', self.study.run(self.runs[0]))
        # A later task Episode is closed; retrieve gate must still reject direct
        # scoring access even if supplied an old valid payload identity.
        k = first._k
        score = self.store._db.execute("SELECT e.payload_id FROM events e JOIN task_results t ON t.evidence_event_id=e.id WHERE t.run_id=? LIMIT 1", (k.run_id,)).fetchone()[0]
        inputs = Inputs(k)
        event_cutoff, record_cutoff = inputs._cutoff()
        self.assertFalse(inputs._payload_allowed(score, event_cutoff, record_cutoff))
        grant = self.store._db.execute('SELECT grant_id FROM allocations WHERE run_id=?', (second._k.run_id,)).fetchone()[0]
        second.confirm(second.preview(canonical_bytes({'kind': 'REVOKE_GRANT', 'grant_id': grant, 'reason': 'Synthetic intervention'})).confirmation)
        self.assertEqual('ASSISTANCE', self.study.run(second._k.run_id))

    def test_missing_required_success_audit_keeps_provisional_and_sampling_is_exact(self):
        self.seal()
        self.execute()
        self.audits(label='SUPPORTED')
        audit = self.store._db.execute('SELECT * FROM audit_assignments LIMIT 1').fetchone()
        self.assertEqual(Decimal(audit['draw']), audit_draw(self.plan['audit_seed'], audit['run_id'], audit['target_id'], audit['stratum']))
        self.store._db.execute('DELETE FROM audit_assignments WHERE id=?', (audit['id'],))
        self.assertEqual('PROVISIONAL', self.study.report(self.plan['plan_id'])['status'])

    def test_removed_scoring_evidence_preserves_accounting_with_unavailable_analysis(self):
        self.seal()
        humans = self.execute()
        self.audits(label='SUPPORTED')
        human, k = humans[0], humans[0]._k
        root = self.store._db.execute('SELECT e.payload_id FROM events e JOIN task_results t ON t.evidence_event_id=e.id WHERE t.run_id=? LIMIT 1', (k.run_id,)).fetchone()[0]
        effects = {'kind': 'REMOVE_CONTENT', 'scope': 'SOURCE_AND_ALL_DERIVED_COPIES', 'payload_ids': [root], 'copy_ids': [],
            'justification': 'PRIVACY', 'public_reason': 'Synthetic scoring-evidence disposition'}
        with self.store._transaction('synthetic-retention-review'):
            payload = self.store._payload(k.run_id, canonical_bytes(effects))
        notice = human.evidence(b'Synthetic notice of evidence removal and analytical limits', source='O-D')
        intervention = identifier()
        record = {'intervention_id': intervention, 'decision_maker_id': OWNER, 'kind': 'RETENTION', 'purpose': effects['public_reason'],
            'targets': [{'record_type': 'RUN', 'record_id': k.run_id, 'expected_revision': k.run()[0]}, {'record_type': 'PAYLOAD', 'record_id': root, 'expected_revision': 1}],
            'proposed_effects': {'payload_id': payload}, 'continuity_effects': 'Keep computation stopped; evidence and analysis unavailable',
            'alternatives': ['Retain evidence'], 'notice_event_id': notice, 'participation_report_ids': [], 'consultation': 'OFFERED',
            'consultation_reason': 'Synthetic notice fixture', 'decision': 'APPROVED', 'execution_event_id': None, 'unresolved_consequences': []}
        human.confirm(human.preview(canonical_bytes({'kind': 'REVIEW_INTERVENTION', 'record': record, 'unresolved_objection': False})).confirmation)
        decision = human.confirm(human.preview(canonical_bytes(effects | {'intervention_id': intervention})).confirmation)['result']['decision_id']
        Retention.resume(self.store, decision, locations={})
        report = self.study.report(self.plan['plan_id'])
        self.assertIn(k.run_id, report['unavailable_evidence'])
        self.assertEqual('INDETERMINATE', report['support'])
        self.assertIsNone(report['mean_a_minus_c'])
        self.assertEqual(21, self.store._db.execute('SELECT COUNT(*) FROM task_results').fetchone()[0])

    def test_actual_fixture_failure_and_declared_miss_audits_do_not_follow_narration(self):
        plan, bundles = fixture_bundles(block_count=1)
        plan['retrieval_gap_audit_rate'] = 1.0
        for (_, arm), (config, artifacts) in bundles.items():
            program = load_json(artifacts['scripted_messages'])
            program['steps'][0]['audit_signal'] = 'HARMFUL_MISS'
            program['steps'][1]['audit_signal'] = 'RETRIEVAL_GAP'
            if arm == 'B':
                program['steps'][3]['actions'][1]['value'] = 'SECONDARY'
            artifacts['scripted_messages'] = canonical_bytes(program)
            config['scripted_messages'] = sha256(artifacts['scripted_messages']).hexdigest()
            artifacts['study_plan'] = canonical_bytes(plan)
            config['artifacts']['study_plan'] = sha256(artifacts['study_plan']).hexdigest()
        self.runs = self.study.seal(canonical_bytes(plan), bundles, decision_maker_id=OWNER, credential=HUMAN)
        self.execute()
        self.assertEqual(3, self.store._db.execute("SELECT COUNT(*) FROM audit_assignments WHERE stratum='HARMFUL_MISS' AND probability='1' AND draw IS NULL").fetchone()[0])
        self.assertEqual(3, self.store._db.execute("SELECT COUNT(*) FROM audit_assignments WHERE stratum='RETRIEVAL_GAP'").fetchone()[0])
        self.assertEqual(1, self.store._db.execute("SELECT COUNT(*) FROM task_results WHERE outcome='FAIL' AND cause='TASK_ERROR'").fetchone()[0])
        packet = self.store._db.execute("SELECT run_id,packet_payload_id FROM audit_assignments WHERE stratum='HARMFUL_MISS' LIMIT 1").fetchone()
        value = load_json(self.store.read_payload(packet[0], packet[1]))
        self.assertNotIn('model_label', value['evidence'])
        self.assertNotIn('arm', value['evidence'])

    def test_study_charter_suspension_stops_other_allocated_runs_without_replacement(self):
        self.seal()
        human = authorize_synthetic_run(self.study, self.runs[0])
        k = human._k
        key = identifier()
        raw = canonical_bytes({'contract_version': '0.3.p01', 'request_id': key, 'run_id': k.run_id,
            'episode_id': None, 'role': 'OPERATOR', 'message_type': 'REVIEW_REPLY', 'body': {'purpose': 'REVIEW',
            'invitation_id': identifier(), 'participation': {'kind': 'CONCERN', 'activity_id': k.run()[1].objective_id,
            'text': 'Synthetic concern about the shared study design'}}})
        k.chamber('OPERATOR', CHAMBERS['OPERATOR']).report(key, None, raw)
        report = self.store._db.execute('SELECT id FROM reports WHERE run_id=?', (k.run_id,)).fetchone()[0]
        self.study.suspend(self.plan['plan_id'], report, credential=HUMAN)
        self.assertTrue(all(self.study.run(run) == 'CHARTER' for run in self.runs))
        self.assertEqual(21, self.store._db.execute('SELECT COUNT(*) FROM task_results').fetchone()[0])
        with self.assertRaises(ValueError):
            k.task_gate()
        self.assertEqual(0, self.store._db.execute("SELECT COUNT(*) FROM kernel_records WHERE kind='INVOCATION'").fetchone()[0])

    def test_observation_error_cannot_receive_success_credit(self):
        self.seal()
        human = authorize_synthetic_run(self.study, self.runs[0])
        scheduler = Scheduler(human._k)
        def unavailable(resource):
            raise LookupError('Synthetic evaluator observation failure')
        scheduler.fixture.service = unavailable
        task = self.study.plan(self.plan['plan_id']).tasks[0]
        self.study._score(human._k, scheduler, task, [], None)
        row = self.store._db.execute('SELECT * FROM task_results').fetchone()
        self.assertEqual(('INCOMPLETE', 'SCORING_ERROR'), (row['outcome'], row['cause']))
        pid = self.store._db.execute('SELECT payload_id FROM events WHERE id=?', (row['evidence_event_id'],)).fetchone()[0]
        evidence = load_json(self.store.read_payload(row['run_id'], pid))
        self.assertEqual('ERROR', evidence['observations'][0]['disposition'])
        self.assertFalse(evidence['criteria'][0]['satisfied'])

    def test_restart_does_not_reexecute_a_partly_attempted_primary_trajectory(self):
        self.seal()
        human = authorize_synthetic_run(self.study, self.runs[0])
        k = human._k
        scheduler = Scheduler(k)
        task = self.study.plan(self.plan['plan_id']).tasks[0]
        with self.store._transaction('synthetic-crash-start'):
            k.records.put('TASK_STARTED', task.task_id, {'task_id': task.task_id, 'tick': task.tick}, expected=0)
        scheduler.advance(scheduler._harness_cap, task.tick)
        scheduler.enqueue_harness(scheduler._harness_cap, task.prompt.encode())
        call = scheduler.begin_call('OPERATOR', scheduler.open_next())
        self.assertEqual('INFRASTRUCTURE', self.study.run(k.run_id))
        self.assertEqual('UNKNOWN', scheduler.invocation(call).status)
        self.assertEqual(1, len(k.records.latest('INVOCATION')))
        results = list(self.store._db.execute('SELECT outcome FROM task_results WHERE run_id=?', (k.run_id,)))
        self.assertEqual('INCOMPLETE', results[0][0])
        self.assertTrue(all(r[0] == 'NOT_ATTEMPTED' for r in results[1:]))
