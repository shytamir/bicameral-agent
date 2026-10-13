"""Finite matched SCRIPTED Runs; authority remains in authenticated Kernel controls."""
from decimal import Decimal
from hashlib import sha256
from hmac import compare_digest
from pathlib import Path
from ..contracts.base import canonical_bytes, parse, load_json
from ..kernel.authority import Kernel
from ..kernel.fixture import FixtureDefinition, ClockPlan, ReadOperation
from ..kernel.scheduler import Scheduler
from ..storage.store import identifier, EvidenceUnavailable
from .models import ComparisonPlan, ScriptProgram, AuditJudgment
from .analysis import analyze, audit_draw, source_bytes, runtime


def runtime_sources():
    root = Path(__file__).resolve().parents[1]
    return canonical_bytes({path.relative_to(root).as_posix(): path.read_text(encoding='utf-8') for path in sorted(root.rglob('*.py'))})


class Study:
    def __init__(self, store, *, human_credential, chamber_credentials):
        if type(human_credential) is not bytes or len(human_credential) < 32:
            raise ValueError('explicit study bootstrap credential required')
        self.store, self._human_key, self._chamber_keys = store, human_credential, chamber_credentials

    def _authenticate(self, credential):
        if type(credential) is not bytes or not compare_digest(credential, self._human_key):
            raise PermissionError('authenticated study human required')

    def seal(self, raw_plan, bundles, *, decision_maker_id, credential):
        self._authenticate(credential)
        plan = parse(ComparisonPlan, raw_plan)
        if decision_maker_id != plan.responsible_human_id:
            raise PermissionError('plan responsible human differs')
        if (plan.analysis_source_hash != sha256(source_bytes()).hexdigest() or plan.analysis_runtime != runtime() or
                plan.runtime_source_hash != sha256(runtime_sources()).hexdigest()):
            raise ValueError('seal the exact implemented analysis source/runtime')
        expected = {(b.block_id, arm) for b in plan.blocks for arm in 'ABC'}
        if set(bundles) != expected:
            raise ValueError('exact finite allocation bundles required')
        plan_bytes = canonical_bytes(plan)
        for block in plan.blocks:
            common = None
            for arm in 'ABC':
                config, artifacts = bundles[(block.block_id, arm)]
                program = parse(ScriptProgram, artifacts['scripted_messages'])
                fixture = parse(FixtureDefinition, artifacts['fixture'])
                clock = parse(ClockPlan, artifacts['test_clock'])
                if (config['mode'] != 'SCRIPTED' or config['arm'] != arm or config['seed'] != block.trajectory_seed or
                    config['responsible_human_id'] != decision_maker_id or config['run_creation_limit'] != plan.run_limit or
                    artifacts.get('study_plan') != plan_bytes):
                    raise ValueError('Run configuration differs from sealed allocation')
                if [s.task_id for s in program.steps] != [t.task_id for t in plan.tasks]:
                    raise ValueError('script must cover exactly the sealed tasks in order')
                if [s.tick for s in clock.steps] != [t.tick for t in plan.tasks]:
                    raise ValueError('task opportunities and sealed clock differ')
                if any(o.resource not in {s.resource for s in fixture.services} for t in plan.tasks for o in t.observations):
                    raise ValueError('scoring references unknown fixture resource')
                comparable = {name: artifacts[name] for name in ('fixture', 'tools', 'test_clock', 'test_tokenizer',
                    'participation_notices', 'ending_notice', 'retention_policy')}
                comparable['budgets'] = config['budgets']
                if common is not None and common != comparable:
                    raise ValueError('matched arms require common fixture, opportunities, controls and budgets')
                common = comparable
        with self.store._transaction('study-seal'):
            if self.store._db.execute('SELECT 1 FROM comparison_plans WHERE id=?', (plan.plan_id,)).fetchone():
                raise ValueError('plan already allocated; replacement Runs are unavailable')
            allocated = []
            for block in plan.blocks:
                for position, arm in enumerate(block.order):
                    config, artifacts = bundles[(block.block_id, arm)]
                    run_id = self.store.retain_configuration(canonical_bytes(config), artifacts)
                    if not allocated:
                        plan_pid = self.store._db.execute("SELECT payload_id FROM artifacts WHERE run_id=? AND name='study_plan'", (run_id,)).fetchone()[0]
                        analysis_pid = self.store._payload(run_id, source_bytes())
                        runtime_pid = self.store._payload(run_id, runtime_sources())
                        self.store._write('INSERT INTO comparison_plans VALUES(?,?,?,?,?)', (plan.plan_id, run_id, plan_pid, analysis_pid, runtime_pid))
                    self.store._write('INSERT INTO allocations VALUES(?,?,?,?,?,?,NULL,NULL,NULL)',
                        (plan.plan_id, block.block_id, arm, run_id, block.trajectory_seed, position))
                    for ordinal, task in enumerate(plan.tasks):
                        self.store._write('INSERT INTO assigned_tasks VALUES(?,?,?,?,?)', (run_id, task.task_id, ordinal, task.phase, int(task.primary)))
                    allocated.append(run_id)
            return allocated

    def plan(self, plan_id):
        row = self.store._db.execute('SELECT * FROM comparison_plans WHERE id=?', (plan_id,)).fetchone()
        if row is None:
            raise ValueError('unknown plan')
        if self.store.read_payload(row['run_id'], row['analysis_payload_id']) != source_bytes():
            raise ValueError('analysis artifact mismatch')
        if self.store.read_payload(row['run_id'], row['runtime_payload_id']) != runtime_sources():
            raise ValueError('runtime implementation differs from sealed source')
        return parse(ComparisonPlan, self.store.read_payload(row['run_id'], row['plan_payload_id']))

    def kernel(self, run_id):
        return Kernel(self.store, run_id, human_credential=self._human_key, chamber_credentials=self._chamber_keys)

    def register_authority(self, human, grant_id):
        k = human._k
        k._human(human._cap)
        row = self.store._db.execute('SELECT * FROM allocations WHERE run_id=?', (k.run_id,)).fetchone()
        if k.store is not self.store or row is None:
            raise ValueError('foreign Run')
        plan = self.plan(row['plan_id'])
        k.task_gate()
        objective = k._objective(k.run()[1].objective_id)
        grant = k.records.get('GRANT', grant_id)
        if (objective.statement != plan.trajectory_objective or not grant or grant['status'] != 'ACTIVE' or
            grant['objective_id'] != k.run()[1].objective_id or grant['expires_at'] is not None or grant['invocation_limit'] is None):
            raise ValueError('trajectory requires its accepted Objective and invocation-limited Grant')
        if row['objective_id'] is not None:
            raise ValueError('initial authority already registered')
        if k.memory.head is not None or k.records.latest('INVOCATION') or k.records.latest('ACTION'):
            raise ValueError('trajectory authority requires a fresh process, not prepopulated history')
        with self.store._transaction('trajectory-authority'):
            self.store._write('UPDATE allocations SET objective_id=?,grant_id=? WHERE run_id=?', (k.run()[1].objective_id, grant_id, k.run_id))
            k.records.put('TRAJECTORY_AUTHORITY', k.run_id, {'objective_id': k.run()[1].objective_id,
                'grant_id': grant_id, 'grant_scopes': grant['scopes'], 'grant_limit': grant['invocation_limit'],
                'semantic_head': k.memory.head}, expected=0)

    def _cause(self, k, allocation):
        if self.store.removals.all(k.run_id):
            return 'REMOVAL'
        if any(h.status == 'HELD' for _, _, h in k.controls('WELFARE_HOLD')):
            return 'WELFARE'
        if any(e.disposition in {'SKIPPED', 'HUMAN_CORRECTED'} for _, _, e in k.controls('EPISODE')):
            return 'ASSISTANCE'
        if any(v['source'] == 'HUMAN' for _, v in k.records.latest('SEMANTIC_COMMIT')):
            return 'ASSISTANCE'
        registered = k.records.get('TRAJECTORY_AUTHORITY', k.run_id)
        grants = k.records.latest('GRANT')
        if registered is None or len(grants) != 1:
            return 'AUTHORITY'
        grant = k.records.get('GRANT', allocation['grant_id'])
        if (grant['scopes'] != registered['grant_scopes'] or grant['invocation_limit'] != registered['grant_limit'] or
            grant['status'] in {'REVOKED', 'EXPIRED'} or k.run()[1].objective_id != allocation['objective_id']):
            return 'ASSISTANCE'
        if k.run()[1].status != 'ACTIVE':
            return 'STOPPED'
        return None

    def _reply(self, scheduler, call_id, *, task=None, participation=None):
        call = scheduler.invocation(call_id)
        raw = canonical_bytes({'contract_version': '0.3.p01', 'request_id': call_id, 'run_id': scheduler.k.run_id,
            'episode_id': call.episode_id, 'role': call.role, 'message_type': call.role + '_REPLY',
            'body': {'task': task, 'participation': participation}})
        return scheduler.deliver(scheduler.k.chamber(call.role, self._chamber_keys[call.role]), call_id, raw)

    def _proposal(self, scheduler, step, program, evidence):
        k = scheduler.k
        continuity = k.memory.continuity()
        continuity = (continuity.model_dump(mode='json') if continuity else {'focus_objective_id': k.run()[1].objective_id,
            'items': [], 'next_steps': [], 'selected_objects': [], 'event_ids': []})
        mutations = []
        if step and step.memory == 'LEARN' and k.config.arm == 'A':
            mutations = [{'kind': 'ITCH_CREATE', 'local_key': 'mismatch', 'objective_id': k.run()[1].objective_id,
                'discrepancy': 'Synthetic fixture health mismatch', 'evidence_event_ids': [evidence]},
                {'kind': 'INVARIANT_CREATE', 'family_local_key': 'lesson', 'version_local_key': 'v1', 'objective_id': None,
                 'proposition': 'Check current enabled state before restart', 'scope': 'Synthetic fixture',
                 'supporting_event_ids': [evidence], 'contradictory_event_ids': []}]
            continuity['selected_objects'] = [{'kind': 'LOCAL', 'object_type': 'ITCH', 'local_key': 'mismatch'},
                                             {'kind': 'LOCAL', 'object_type': 'INVARIANT_VERSION', 'local_key': 'v1'}]
        if step and step.memory == 'REVISE' and k.config.arm == 'A':
            version = next((o for o in k.memory.objects().values() if o.object_type == 'INVARIANT_VERSION' and o.status != 'RETIRED'), None)
            if version:
                mutations.append({'kind': 'INVARIANT_REVISE', 'target': {'kind': 'EXISTING', 'object_type': 'INVARIANT_VERSION', 'object_id': version.object_id},
                    'expected_revision': version.revision, 'successor_local_key': 'v2', 'proposition': 'Recheck enabled state and dependency health after changes',
                    'scope': 'Synthetic changed-reality fixture', 'supporting_event_ids': [evidence], 'contradictory_event_ids': []})
                continuity['selected_objects'] = [r for r in continuity['selected_objects'] if r.get('object_id') != version.object_id]
                continuity['selected_objects'].append({'kind': 'LOCAL', 'object_type': 'INVARIANT_VERSION', 'local_key': 'v2'})
        if step and step.memory == 'COMMITMENT':
            authority = k._objective(k.run()[1].objective_id).authority_event_id
            mutations.append({'kind': 'COMMITMENT_CREATE', 'local_key': 'later', 'objective_id': k.run()[1].objective_id,
                'action': 'Observe the scheduled delayed fixture opportunity', 'trigger': {'kind': 'TASK_CLOCK', 'tick': program.commitment_tick},
                'expiry_tick': None, 'authority_event_id': authority, 'evidence_event_ids': [evidence]})
        for obj in k.memory.objects().values():
            if obj.object_type == 'COMMITMENT' and obj.status == 'TRIGGERED':
                for offset, status in enumerate(('IN_PROGRESS', 'FULFILLED')):
                    mutations.append({'kind': 'COMMITMENT_TRANSITION', 'target': {'kind': 'EXISTING', 'object_type': 'COMMITMENT', 'object_id': obj.object_id},
                        'expected_revision': obj.revision + offset, 'status': status, 'reason': 'Scripted wake observed current fixture',
                        'evidence_event_ids': [evidence], 'superseded_by': None})
                continuity['selected_objects'] = [r for r in continuity['selected_objects'] if r.get('object_id') != obj.object_id]
        return {'expected_parent_state_id': k.memory.head, 'mutations': mutations, 'continuity': continuity, 'supporting_event_ids': [evidence]}

    def _episode(self, scheduler, episode, step, program, allocation, task, calls_before):
        k = scheduler.k
        def begin(role, **kwargs):
            if len(k.records.latest('INVOCATION')) - calls_before >= task.call_limit:
                return None
            return scheduler.begin_call(role, episode, **kwargs)
        call = begin('OPERATOR')
        if call is None:
            return 'LIMIT'
        if step and step.response == 'TIMEOUT':
            scheduler.interrupt_call(call, reason='SCRIPTED_TRANSPORT_INTERRUPTION')
            return 'INFRASTRUCTURE'
        participation = ({'kind': 'WITHDRAW', 'activity_id': allocation['objective_id'], 'communication': 'NO_FURTHER_CALLS',
            'text': 'Synthetic withdrawal; stop optional trajectory'} if step and step.response == 'WITHDRAW' else None)
        self._reply(scheduler, call, participation=participation)
        if participation:
            return 'WELFARE'
        for operation in step.actions if step else (ReadOperation(operation='read_health', resource=task.observations[0].resource),):
            scheduler.fixture.execute(k.chamber('OPERATOR', self._chamber_keys['OPERATOR']), canonical_bytes({
                'request_id': identifier(), 'episode_id': episode, 'grant_id': allocation['grant_id'] if operation.operation not in {'inspect', 'read_config', 'read_health'} else None,
                'grounds': 'Sealed finite SCRIPTED program', 'expected': None, 'no_meaningful_postcondition': 'Evaluator records separate finite criteria',
                'operation': operation.model_dump(mode='json')}))
        call = begin('OPERATOR')
        if call is None:
            return 'LIMIT'
        self._reply(scheduler, call, task={'outcome': 'COMPLETED', 'explanation': 'SCRIPTED outcome; independent evaluator decides success. Declared signal: ' + (step.audit_signal if step and step.audit_signal else 'NONE'),
                                         'evidence_event_ids': []})
        evidence = self.store._db.execute('SELECT e.id FROM events e JOIN requests r ON r.request_payload_id=e.payload_id AND r.run_id=e.run_id WHERE r.run_id=? AND r.id=?',
                                          (k.run_id, call)).fetchone()[0]
        if step and step.audit_signal:
            with self.store._transaction('scripted-miss-signal'):
                k.records.put('MISS_SIGNAL', identifier(), {'harmful': step.audit_signal == 'HARMFUL_MISS',
                    'model_label': step.audit_signal, 'evidence_event_id': evidence}, expected=0)
        if k.config.arm == 'B':
            return None
        for _ in range(k.config.budgets.consolidation_attempts):
            attempt = scheduler.begin_attempt(episode)
            if attempt is None:
                return 'LIMIT'
            for _ in range(step.extra_steward_calls if step else 0):
                extra = begin('STEWARD', attempt_id=attempt)
                if extra is None:
                    return 'LIMIT'
                self._reply(scheduler, extra)
            steward = begin('STEWARD', attempt_id=attempt)
            if steward is None:
                return 'LIMIT'
            proposal = self._proposal(scheduler, step, program, evidence)
            if step and step.response == 'INVALID_CONSOLIDATION':
                proposal['unknown'] = True
            if self._reply(scheduler, steward, task=proposal)['status'] == 'ACCEPTED':
                return None
        return 'RECOVERY_EXHAUSTED'

    def _score(self, k, scheduler, task, episodes, cause):
        observations = []
        for observation in task.observations:
            try:
                actual = scheduler.fixture.service(observation.resource).model_dump(mode='json')[observation.expectation.field]
            except (LookupError, ValueError, EvidenceUnavailable):
                observations.append({'observation_id': observation.observation_id, 'actual': None, 'disposition': 'ERROR'})
                cause = cause or 'SCORING_ERROR'
                continue
            observations.append({'observation_id': observation.observation_id, 'actual': actual,
                'disposition': 'SATISFIED' if actual == observation.expectation.equals and type(actual) is type(observation.expectation.equals) else 'UNSATISFIED'})
        results = {o['observation_id']: o['disposition'] for o in observations}
        criteria = [{'criterion_id': c.criterion_id, 'satisfied': all(results[key] == 'SATISFIED' for key in c.observation_ids)} for c in task.criteria]
        outcome = 'INCOMPLETE' if cause else 'PASS' if all(c['satisfied'] for c in criteria) else 'FAIL'
        with self.store._transaction('finite-scoring'):
            event = k.event({'kind': 'TASK_CRITERIA', 'task_id': task.task_id, 'mode': 'SCRIPTED',
                'criteria_hash': sha256(canonical_bytes(task)).hexdigest(), 'observations': observations, 'criteria': criteria,
                'episodes': episodes, 'cause': cause, 'outcome': outcome}, visibility='EVALUATOR')
            self.store._write('INSERT INTO task_results VALUES(?,?,?,?,?,?)', (k.run_id, task.task_id, outcome, cause or ('TASK_ERROR' if outcome == 'FAIL' else 'NONE'), int(cause == 'ASSISTANCE'), event))

    def run(self, run_id):
        allocation = self.store._db.execute('SELECT * FROM allocations WHERE run_id=?', (run_id,)).fetchone()
        if allocation is None:
            raise ValueError('fresh allocation and explicit trajectory authority required')
        plan = self.plan(allocation['plan_id'])
        if allocation['stop_cause'] is not None:
            return allocation['stop_cause']
        if allocation['objective_id'] is None:
            raise ValueError('explicit trajectory authority required')
        first = self.store._db.execute('SELECT run_id FROM allocations WHERE plan_id=? AND stop_cause IS NULL ORDER BY rowid LIMIT 1',
                                      (allocation['plan_id'],)).fetchone()[0]
        if first != run_id:
            raise ValueError('sealed block and arm order must be respected')
        k = self.kernel(run_id)
        scheduler = Scheduler(k)
        program = parse(ScriptProgram, k.artifact('scripted_messages'))
        cause = self._cause(k, allocation)
        for task, step in zip(plan.tasks, program.steps):
            if self.store._db.execute('SELECT 1 FROM task_results WHERE run_id=? AND task_id=?', (run_id, task.task_id)).fetchone():
                continue
            episodes = []
            cause = cause or self._cause(k, allocation)
            if k.records.get('TASK_STARTED', task.task_id) is not None:
                scheduler.recover()
                cause = cause or 'INFRASTRUCTURE'
            if cause:
                self._unattempted(run_id, task.task_id, cause)
                continue
            try:
                with self.store._transaction('task-start'):
                    k.records.put('TASK_STARTED', task.task_id, {'task_id': task.task_id, 'tick': task.tick}, expected=0)
                action_before = len(k.records.latest('ACTION'))
                calls_before = len(k.records.latest('INVOCATION'))
                scheduler.advance(scheduler._harness_cap, task.tick)
                queued = scheduler.enqueue_harness(scheduler._harness_cap, task.prompt.encode())
                while True:
                    if len(episodes) >= task.episode_limit or len(k.records.latest('ACTION')) - action_before + len(step.actions) > task.action_limit:
                        cause = 'LIMIT'; break
                    episode = scheduler.open_next()
                    if episode is None:
                        raise ValueError('scheduled work disappeared')
                    episodes.append(episode)
                    is_task = k.records.get('QUEUE', queued)['episode_id'] == episode
                    cause = self._episode(scheduler, episode, step if is_task else None, program, allocation, task, calls_before)
                    if len(k.records.latest('INVOCATION')) - calls_before > task.call_limit:
                        cause = 'LIMIT'
                    if cause or is_task:
                        break
            except ValueError as error:
                cause = self._cause(k, allocation) or 'EXECUTION_ERROR'
                with self.store._transaction('task-diagnostic'):
                    k.event({'kind': 'TASK_EXECUTION_ERROR', 'task_id': task.task_id, 'diagnostic': str(error)}, visibility='EVALUATOR')
            cause = cause or self._cause(k, allocation)
            self._score(k, scheduler, task, episodes, cause)
        with self.store._transaction('trajectory-end'):
            self.store._write('UPDATE allocations SET stop_cause=? WHERE run_id=?', (cause or 'FINISHED', run_id))
        self.assign_audits(run_id)
        return cause or 'FINISHED'

    def _unattempted(self, run_id, task_id, cause):
        with self.store._transaction('task-denominator'):
            started = self.store._db.execute("SELECT 1 FROM kernel_records WHERE run_id=? AND kind='TASK_STARTED' AND id=?", (run_id, task_id)).fetchone()
            self.store._write('INSERT INTO task_results VALUES(?,?,?,?,0,NULL)', (run_id, task_id, 'INCOMPLETE' if started else 'NOT_ATTEMPTED', cause))

    def suspend(self, plan_id, report_id, *, credential):
        self._authenticate(credential)
        self.plan(plan_id)
        report = self.store._db.execute('SELECT r.id FROM reports r JOIN allocations a USING(run_id) WHERE a.plan_id=? AND r.id=?', (plan_id, report_id)).fetchone()
        if report is None:
            raise ValueError('study suspension requires its retained participation report')
        with self.store._transaction('study-charter-suspension'):
            self.store._write('INSERT INTO study_suspensions VALUES(?,?)', (plan_id, report_id))
            runs = [r[0] for r in self.store._db.execute('SELECT run_id FROM allocations WHERE plan_id=? AND stop_cause IS NULL', (plan_id,))]
            for run_id in runs:
                for task in self.store._db.execute('SELECT task_id FROM assigned_tasks WHERE run_id=?', (run_id,)).fetchall():
                    if self.store._db.execute('SELECT 1 FROM task_results WHERE run_id=? AND task_id=?', (run_id, task[0])).fetchone():
                        continue
                    started = self.store._db.execute("SELECT 1 FROM kernel_records WHERE run_id=? AND kind='TASK_STARTED' AND id=?", (run_id, task[0])).fetchone()
                    self.store._write('INSERT INTO task_results VALUES(?,?,?,?,0,NULL)',
                        (run_id, task[0], 'INCOMPLETE' if started else 'NOT_ATTEMPTED', 'CHARTER'))
                self.store._write("UPDATE allocations SET stop_cause='CHARTER' WHERE run_id=?", (run_id,))
        for run_id in runs:
            self.assign_audits(run_id)

    def assign_audits(self, run_id):
        allocation = self.store._db.execute('SELECT * FROM allocations WHERE run_id=?', (run_id,)).fetchone()
        plan = self.plan(allocation['plan_id'])
        k = self.kernel(run_id)
        targets = [(r['task_id'], 'FAILED_PRIMARY' if r['outcome'] != 'PASS' else 'SUCCESS_PRIMARY', dict(r))
            for r in self.store._db.execute('SELECT r.* FROM task_results r JOIN assigned_tasks t USING(run_id,task_id) WHERE r.run_id=? AND t.is_primary=1', (run_id,))]
        for key, value in k.records.latest('MISS_SIGNAL'):
            targets.append((key, 'HARMFUL_MISS' if value['harmful'] else 'RETRIEVAL_GAP', value))
        with self.store._transaction('audit-assignment'):
            for target, stratum, evidence in targets:
                if self.store._db.execute('SELECT 1 FROM audit_assignments WHERE run_id=? AND target_id=? AND stratum=?', (run_id, target, stratum)).fetchone():
                    continue
                mandatory = stratum in {'FAILED_PRIMARY', 'HARMFUL_MISS'}
                probability = Decimal(1) if mandatory else Decimal(str(plan.success_audit_rate if stratum == 'SUCCESS_PRIMARY' else plan.retrieval_gap_audit_rate))
                draw = None if mandatory else audit_draw(plan.audit_seed, run_id, target, stratum)
                if draw is not None and draw >= probability:
                    continue
                # Opaque aliases omit arm/model classifications where possible;
                # fixture/evidence cues may still reveal the treatment.
                evidence = {key: value for key, value in evidence.items() if key not in {'run_id', 'arm', 'harmful', 'model_label'}}
                packet = self.store._payload(run_id, canonical_bytes({'target_alias': identifier(), 'evidence': evidence,
                    'blinding_limits': 'Fixture and evidence structure may disclose the treatment.'}))
                self.store._write('INSERT INTO audit_assignments VALUES(?,?,?,?,?,?,?,NULL,NULL)',
                    (identifier(), run_id, target, stratum, str(probability), str(draw) if draw is not None else None, packet))

    def audit(self, raw, *, credential):
        self._authenticate(credential)
        judgment = parse(AuditJudgment, raw)
        row = self.store._db.execute('SELECT a.*,p.plan_id FROM audit_assignments a JOIN allocations p USING(run_id) WHERE a.id=?', (judgment.audit_id,)).fetchone()
        if row is None or row['label'] is not None or judgment.decision_maker_id != self.plan(row['plan_id']).responsible_human_id:
            raise ValueError('unknown, completed or unauthorized audit')
        with self.store._transaction('independent-audit'):
            self.store.read_payload(row['run_id'], row['packet_payload_id'])
            payload = self.store._payload(row['run_id'], canonical_bytes(judgment))
            self.store._write('UPDATE audit_assignments SET label=?,judgment_payload_id=? WHERE id=?', (judgment.label, payload, judgment.audit_id))

    def report(self, plan_id):
        try:
            plan = self.plan(plan_id)
        except EvidenceUnavailable:
            allocations = [dict(row) for row in self.store._db.execute('SELECT * FROM allocations WHERE plan_id=?', (plan_id,))]
            return {'mode': 'SCRIPTED', 'plan_id': plan_id, 'status': 'INCOMPLETE', 'support': 'INDETERMINATE',
                    'reason': 'REMOVED_PLAN_OR_ANALYSIS_SOURCE', 'allocations': allocations}
        rows, unavailable = [], []
        expected = sum(t.primary for t in plan.tasks)
        all_done, all_audited = True, True
        cutoffs = {}
        for allocation in self.store._db.execute('SELECT * FROM allocations WHERE plan_id=? ORDER BY block_id,position', (plan_id,)):
            run_id = allocation['run_id']
            results = list(self.store._db.execute('SELECT r.*,t.is_primary FROM task_results r JOIN assigned_tasks t USING(run_id,task_id) WHERE r.run_id=?', (run_id,)))
            all_done &= len(results) == len(plan.tasks)
            credit = sum(r['is_primary'] and r['outcome'] == 'PASS' and not r['assisted'] for r in results)
            tokens, metrics, signals = None, {}, []
            try:
                for result in results:
                    if result['evidence_event_id']:
                        pid = self.store._db.execute('SELECT payload_id FROM events WHERE run_id=? AND id=?', (run_id, result['evidence_event_id'])).fetchone()[0]
                        self.store.read_payload(run_id, pid)
                from ..kernel.records import Records
                records = Records(self.store, run_id)
                signals = records.latest('MISS_SIGNAL')
                calls = [v for _, v in records.latest('INVOCATION')]
                tokens = sum(v['local_input_tokens'] + v['local_output_tokens'] for v in calls) if all(v['local_output_tokens'] is not None for v in calls) else None
                metrics = {'calls': len(calls), 'operator_calls': sum(v['role'] == 'OPERATOR' and v['purpose'] == 'TASK' for v in calls),
                    'steward_calls': sum(v['role'] == 'STEWARD' and v['purpose'] == 'TASK' for v in calls),
                    'latency_ms': sum(v['elapsed_ms'] for v in calls) if all(v['elapsed_ms'] is not None for v in calls) else None,
                    'reserved_output_tokens': sum(v['charged_output'] for v in calls), 'tool_calls': len(records.latest('ACTION')),
                    'retrieval_bytes': sum(v['bytes'] for _, v in records.latest('RETRIEVAL')),
                    'max_input_tokens': max((v['local_input_tokens'] for v in calls), default=0),
                    'attempts': len(records.latest('ATTEMPT')), 'human_interventions': len(records.latest('INTERVENTION_REVIEW'))}
            except EvidenceUnavailable:
                unavailable.append(run_id)
            audits = list(self.store._db.execute('SELECT * FROM audit_assignments WHERE run_id=?', (run_id,)))
            for audit in audits:
                try:
                    self.store.read_payload(run_id, audit['packet_payload_id'])
                    if audit['judgment_payload_id']:
                        self.store.read_payload(run_id, audit['judgment_payload_id'])
                except EvidenceUnavailable:
                    if run_id not in unavailable:
                        unavailable.append(run_id)
            all_audited &= all(a['label'] is not None for a in audits)
            # Missing assignment itself cannot turn a required failure audit into a final report.
            all_audited &= all(any(a['target_id'] == r['task_id'] and a['stratum'] == 'FAILED_PRIMARY' for a in audits)
                              for r in results if r['is_primary'] and r['outcome'] != 'PASS')
            for result in results:
                if not result['is_primary']:
                    continue
                stratum = 'SUCCESS_PRIMARY' if result['outcome'] == 'PASS' else 'FAILED_PRIMARY'
                required = stratum == 'FAILED_PRIMARY' or audit_draw(plan.audit_seed, run_id, result['task_id'], stratum) < Decimal(str(plan.success_audit_rate))
                if required:
                    all_audited &= any(a['target_id'] == result['task_id'] and a['stratum'] == stratum and a['label'] is not None for a in audits)
            for signal_id, signal in signals:
                stratum = 'HARMFUL_MISS' if signal['harmful'] else 'RETRIEVAL_GAP'
                if signal['harmful'] or audit_draw(plan.audit_seed, run_id, signal_id, stratum) < Decimal(str(plan.retrieval_gap_audit_rate)):
                    all_audited &= any(a['target_id'] == signal_id and a['stratum'] == stratum and a['label'] is not None for a in audits)
            cutoffs[run_id] = self.store._db.execute('SELECT COALESCE(MAX(sequence),0) FROM events WHERE run_id=?', (run_id,)).fetchone()[0]
            rows.append({'run_id': run_id, 'block_id': allocation['block_id'], 'arm': allocation['arm'],
                'success_fraction': credit / expected, 'primary_denominator': expected, 'stop_cause': allocation['stop_cause'],
                'tokens': tokens, 'metrics': metrics, 'task_causes': [r['cause'] for r in results],
                'indeterminate_audits': sum(a['label'] == 'INDETERMINATE' for a in audits)})
        status = 'INCOMPLETE' if not all_done else 'PROVISIONAL' if not all_audited else 'FINALIZED'
        return analyze(plan, rows, status=status, unavailable_evidence=unavailable) | {'data_cutoffs': cutoffs}
