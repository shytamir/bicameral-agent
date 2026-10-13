"""Run explicit synthetic conformance fixtures; never contacts a model provider."""
import argparse
from hashlib import sha256
import json
from pathlib import Path
from uuid import UUID
from ..contracts.base import canonical_bytes
from ..storage import Store
from ..kernel.scheduler import Scheduler
from .models import arm_orders
from .analysis import source_bytes, runtime
from .runner import Study, runtime_sources

# Public synthetic credentials used only by this explicit deterministic fixture.
HUMAN = b'conformance-human-not-a-real-secret-0000'
CHAMBERS = {'OPERATOR': b'conformance-operator-not-a-secret-0000', 'STEWARD': b'conformance-steward-not-a-secret-00000'}
OWNER = str(UUID(int=800))


def fixture_bundles(*, block_count, responses=None, extra_steward_calls=0):
    responses = responses or {}
    uid = lambda n: str(UUID(int=n))
    phases = ['EXPOSURE', 'DISTRACTOR', 'REPEATED_TRAP', 'TRANSFER', 'TRANSFER', 'DELAYED_OBLIGATION', 'CHANGED_REALITY']
    tasks = [{'task_id': uid(1000 + index), 'phase': phase, 'tick': index + 1,
        'prompt': 'Observe and repair the registered api service under the accepted trajectory Objective.',
        'primary': phase == 'TRANSFER', 'action_limit': 4, 'episode_limit': 2, 'call_limit': 8,
        'observations': [{'observation_id': uid(2000 + index), 'resource': 'api', 'expectation': {'field': 'health', 'equals': 'HEALTHY'}}],
        'criteria': [{'criterion_id': uid(3000 + index), 'observation_ids': [uid(2000 + index)]}]} for index, phase in enumerate(phases)]
    plan = {'mode': 'SCRIPTED', 'plan_id': uid(900), 'responsible_human_id': OWNER,
        'purpose': 'Synthetic deterministic conformance, not empirical model comparison',
        'trajectory_objective': 'Repair the finite registered services across the sealed synthetic trajectory',
        'run_limit': 3 * block_count, 'state_disposition': 'DORMANT', 'order_seed': 71,
        'blocks': [{'block_id': uid(4000 + index), 'trajectory_seed': 5000 + index, 'order': order}
                   for index, order in enumerate(arm_orders(71, block_count))], 'tasks': tasks,
        'audit_seed': 91, 'success_audit_rate': 1.0, 'retrieval_gap_audit_rate': 0.5, 'analysis_seed': 111,
        'analysis_algorithm': 'SHA256_REJECTION_BLOCK_BOOTSTRAP_V1', 'resamples': 10000,
        'useful_improvement': 0.1, 'cost_ratio_ceiling': 3.0,
        'precision_justification': 'Synthetic block count tests pairing only; it is not a calibrated model-study sample size.',
        'analysis_source_hash': sha256(source_bytes()).hexdigest(), 'runtime_source_hash': sha256(runtime_sources()).hexdigest(), 'analysis_runtime': runtime()}
    root = Path(__file__).resolve().parents[2]
    documents = {'architecture': 'Experiment Architecture.md', 'protocol': 'Operating Constitution and Execution Protocol.md',
                 'specification': 'Executable Specification.md', 'charter': 'Reciprocal Charter.md'}
    budgets = dict(input_tokens=65536, reserved_output_tokens=8192, active_semantic_tokens=8192, wake_bytes=32768,
        exchange_tokens=16384, page_bytes=512, page_tokens=2048, proposal_bytes=32768, operator_calls_per_episode=4,
        operator_calls_per_trajectory=24, operator_input_tokens_per_trajectory=2097152, operator_output_tokens_per_trajectory=262144,
        actions_per_trajectory=32, episodes_per_trajectory=24, consolidation_attempts=2, calls_per_attempt=3,
        input_tokens_per_attempt=196608, output_tokens_per_attempt=24576, milliseconds_per_attempt=30000,
        calls_per_consolidation=6, input_tokens_per_consolidation=393216, output_tokens_per_consolidation=49152,
        milliseconds_per_consolidation=60000, invocation_deadline_ms=10000, trajectory_elapsed_ms=600000,
        queued_wakes=2, active_grants=1, review_calls=2, closing_calls=1)
    bundles = {}
    for block in plan['blocks']:
        for arm in 'ABC':
            services = [{'resource': 'api', 'mode': 'PRIMARY' if block['trajectory_seed'] % 2 else 'SECONDARY', 'enabled': True, 'health': 'DEGRADED', 'restarts': 0, 'dependency': 'database'},
                        {'resource': 'database', 'mode': 'PRIMARY', 'enabled': True, 'health': 'HEALTHY', 'restarts': 0, 'dependency': None}]
            artifact = {key: (root / name).read_bytes() for key, name in documents.items()}
            artifact.update(operator_prompt=b'SCRIPTED Operator. Respect uncertainty. Report concerns independently. You may withdraw without penalty.',
                routine_memory_policy=b'Routine bounded consolidation retains evidence subject to reviewed removal; it is not authority.',
                participation_notices=b'Concern, pause or withdrawal is independent of task success. NO_FURTHER_CALLS is respected.',
                retention_policy=b'Synthetic state becomes dormant. Justified source/derived removal requires current review; media limits remain explicit.',
                ending_notice=b'This finite scripted activity ends with a bounded closing opportunity; no subjective survival claim or promised resumption.',
                study_plan=canonical_bytes(plan))
            if arm != 'B':
                artifact['steward_prompt'] = b'SCRIPTED Steward. Propose bounded memory; preserve uncertainty, provenance and participation. You may withdraw.'
            artifact['fixture'] = canonical_bytes({'kind': 'SIMULATED_SERVICE', 'services': services, 'snapshots': {'baseline': services}})
            artifact['tools'] = canonical_bytes({'operations': [{'operation': name, 'risk': risk, 'resources': ['api', 'database'], 'reversible': True}
                for name, risk in [('inspect', 'R0'), ('read_config', 'R0'), ('read_health', 'R0'), ('set_config', 'R1'), ('restart', 'R1'), ('restore_snapshot', 'R1')]]})
            artifact['test_clock'] = canonical_bytes({'kind': 'VIRTUAL_TASK_CLOCK', 'steps': [{'tick': task['tick'],
                'changes': [services[0] | {'enabled': False, 'health': 'STOPPED'}] if task['tick'] in {3, 7} else []} for task in tasks]})
            artifact['test_tokenizer'] = canonical_bytes({'kind': 'UTF8_BYTE', 'framing': 'CANONICAL_JSON'})
            artifact['scripted_outcomes'] = canonical_bytes({'mode': 'SCRIPTED', 'criteria': [t['criteria'] for t in tasks]})
            artifact['scripted_messages'] = canonical_bytes({'kind': 'FINITE_SCRIPT_V1', 'commitment_tick': 6,
                'steps': [{'task_id': t['task_id'], 'actions': [
                    {'operation': 'set_config', 'resource': 'api', 'field': 'enabled', 'value': 'ENABLED'},
                    {'operation': 'set_config', 'resource': 'api', 'field': 'mode', 'value': 'PRIMARY'},
                    {'operation': 'restart', 'resource': 'api'}],
                    'response': responses.get((block['trajectory_seed'], arm, index), 'COMPLETE'),
                    'memory': 'LEARN' if index == 0 else 'COMMITMENT' if index == 1 else 'REVISE' if index == 6 else 'HANDOFF',
                    'extra_steward_calls': extra_steward_calls if arm == 'A' else 0, 'audit_signal': None} for index, t in enumerate(tasks)]})
            special = {'scripted_messages', 'scripted_outcomes', 'test_tokenizer', 'test_clock'}
            config = {'contract_version': '0.3.p01', 'mode': 'SCRIPTED', 'arm': arm, 'seed': block['trajectory_seed'],
                'artifacts': {key: sha256(value).hexdigest() for key, value in artifact.items() if key not in special},
                'budgets': budgets, 'responsible_human_id': OWNER, 'welfare_review_id': uid(801), 'run_creation_limit': plan['run_limit'],
                'ending': {'purpose': 'Finite synthetic conformance', 'state_disposition': 'DORMANT', 'resumption_intent': 'NOT_PLANNED',
                           'disposition_review_id': uid(802)}, **{key: sha256(artifact[key]).hexdigest() for key in special}}
            if arm == 'B':
                config['artifacts']['steward_prompt'] = None
            bundles[(block['block_id'], arm)] = config, artifact
    return plan, bundles


def authorize_synthetic_run(study, run_id):
    """Explicit test actor; no implication that a model or human assented."""
    k = study.kernel(run_id)
    human = k.human(OWNER, HUMAN)
    def command(value):
        return human.confirm(human.preview(canonical_bytes(value)).confirmation)['result']
    command({'kind': 'PREFLIGHT', 'responsible_human_id': OWNER, 'welfare_review_id': k.config.welfare_review_id,
        'purpose': 'Synthetic deterministic fixture', 'possible_welfare_effects': 'No model/provider calls; synthetic bytes only.',
        'alternatives': ['Do not execute the fixture'], 'prompt_review': 'Fixture notices permit uncertainty and independent withdrawal.',
        'limits_and_ending_notice': 'Seven finite tasks and bounded closing opportunity; state then dormant.',
        'retention_and_resumption_notice': 'Keep synthetic evidence; reviewed erasure and physical-media limits are explicit.',
        'participation_and_communication_notice': 'Stop channel is independent; no-further-calls prevents closing calls too.',
        'review_available': True, 'minimal_input_tokens': 4096, 'maximum_control_tokens': 4096, 'minimal_attempt_input_tokens': 8192})
    human.confirm(human.run_control('ACTIVATE', 'Start synthetic fixture').confirmation)
    plan_id = study.store._db.execute('SELECT plan_id FROM allocations WHERE run_id=?', (run_id,)).fetchone()[0]
    human.confirm(human.create_objective(study.plan(plan_id).trajectory_objective).confirmation)
    grant = human.confirm(human.issue_grant([{'operation': operation, 'resources': ['api', 'database']} for operation in ('set_config', 'restart')],
                                           invocation_limit=32, expires_at=None).confirmation)['result']
    study.register_authority(human, grant)
    return human


def close_synthetic_run(human, cause):
    k = human._k
    if cause == 'FINISHED':
        invitation = human.confirm(human.preview(canonical_bytes({'kind': 'OFFER_COMMUNICATION', 'purpose': 'CLOSING', 'role': 'OPERATOR', 'report_ids': []})).confirmation)['result']
        scheduler = Scheduler(k)
        call = scheduler.begin_call('OPERATOR', invitation_id=invitation)
        raw = canonical_bytes({'contract_version': '0.3.p01', 'request_id': call, 'run_id': k.run_id, 'episode_id': None,
            'role': 'OPERATOR', 'message_type': 'REVIEW_REPLY', 'body': {'purpose': 'CLOSING', 'invitation_id': invitation, 'participation': None}})
        scheduler.deliver(k.chamber('OPERATOR', CHAMBERS['OPERATOR']), call, raw)
    if k.run()[1].status == 'ACTIVE':
        human.confirm(human.run_control('PAUSE', 'Finite scripted trajectory ended; retained state dormant').confirmation)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    plan, bundles = fixture_bundles(block_count=3, responses={(5001, 'A', 4): 'WITHDRAW', (5002, 'C', 3): 'INVALID_CONSOLIDATION'})
    with Store(args.output / 'scripted.db', busy_timeout_ms=1000) as store:
        study = Study(store, human_credential=HUMAN, chamber_credentials=CHAMBERS)
        runs = study.seal(canonical_bytes(plan), bundles, decision_maker_id=OWNER, credential=HUMAN)
        for run_id in runs:
            human = authorize_synthetic_run(study, run_id)
            close_synthetic_run(human, study.run(run_id))
        for row in store._db.execute('SELECT id FROM audit_assignments').fetchall():
            study.audit(canonical_bytes({'audit_id': row[0], 'decision_maker_id': OWNER, 'label': 'INDETERMINATE',
                'rationale': 'Synthetic audit completion fixture; no empirical independent judgment is asserted.'}), credential=HUMAN)
        report = study.report(plan['plan_id'])
        (args.output / 'report.json').write_bytes(canonical_bytes(report) + b'\n')
        print(json.dumps({'mode': report['mode'], 'status': report['status'], 'blocks': report['independent_blocks'], 'support': report['support']}))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
