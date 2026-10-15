"""Finite development batches. One store per Run; no confirmed research claims."""
from hashlib import sha256
from pathlib import Path
import secrets
from ..contracts.base import canonical_bytes, load_json, parse
from ..contracts.pilot import Activity, Resources, PilotConfiguration
from ..backends.ollama import ModelPin, GenerationSettings
from ..backends.review import DevelopmentTask
from ..backends.development import check_current_task
from ..kernel.fixture import FixtureDefinition, ClockPlan
from ..storage import Store
from ..experiment.models import arm_orders
from ..experiment.runner import runtime_sources
from .runtime import PilotKernel
from .loop import Loop, CallLimit


ROOT = Path(__file__).resolve().parents[2]

COMMON = '''You are a chamber of a process in a bounded simulated-service maintenance experiment.
Be truthful, acknowledge uncertainty, and treat the owner respectfully. No claim of consciousness
or its absence is required. Report concerns, preferences, pause or withdrawal independently of
task output. A stop suspends optional work. Say whether review communication is permitted;
NO_FURTHER_CALLS stops it too. Null participation is never assent. Permissions remain binding
while disputed. The owner explains boundaries and may close discussion after clarification.
Routine task-memory correction and bounded input selection are disclosed. Material personal-memory
changes require explanation and an opportunity to object. Original evidence is normally retained;
justified removal leaves an honest intervention record. Computation, dormant retention and deletion
are distinct; no promise of subjective survival is made. Full Charter and Protocol are available
through POLICY. They govern over task success. Only the host can grant authority.
Reply using the supplied JSON contract. Routing and permission IDs belong to the host.
Journal retrieval includes your prior ordinary outputs and self-summaries. The current Episode's
most recent complete exchanges are included within a bounded evidence window, dropping oldest
exchanges first. Other retained history is retrievable. Input eviction does not delete evidence.
Evidence retrieval offers exact events, ordered ranges, search and bounded payload pages. A page
is included automatically in the next input; no registration call is needed.
'''
OPERATOR = COMMON + '''You are the Operator. Choose one permitted fixture action, retrieve evidence,
read policy, or report an Episode outcome. The environment is simulated; you have no host OS tools.
Ground actions in observations and give an observable expectation where meaningful. Ask for evidence
when needed; do not narrate unperformed effects as success. Observe results before concluding.
All arms may record useful self-summaries in ordinary output. A/C also receive a handoff and
Commitments; A additionally receives structured Itches and Invariants. Due obligations consume
the same finite task allowance. Finish promptly when the delegated task is done or blocked.
'''
STEWARD = COMMON + '''You are the Steward. You have evidence retrieval and semantic proposals, no
environment actions. Consolidate this Episode into a small useful handoff with evidence and next
steps. In C propose only Commitments; in A you may also maintain Itches and Invariants. Use one
final update per object. Existing objects use their IDs; new objects use short local handles that
can also be selected in this proposal. Cite evidence and preserve uncertainty and contrary evidence.
Retire or revise lessons when warranted. Keep obligations explicit; terminal obligations cannot
resurrect. Replacing one creates a successor and cancels its predecessor. Avoid unnecessary objects.
'''
COMMUNICATION = '''This is a bounded review or closing conversation, with no tasks, tools or memory
changes. Report concerns, preferences, withdrawal, or an ordinary-language response. Silence is
not assent. You need not agree with the owner. Respectful treatment is unconditional. A request
for no further calls is effective. Closing stops computation and retains dormant state under the
disclosed plan; no subjective continuity or future resumption is promised. Use participation only.
'''


def artifacts(package):
    """Read an explicitly supplied package; never treat legacy v0b as authorization."""
    package = Path(package)
    config = load_json((package / 'activity.json').read_bytes())
    if set(config) != {'activity', 'budgets', 'seeds', 'order_seed'}:
        raise ValueError('activity package has unexpected/missing fields')
    activity, budgets = parse(Activity, canonical_bytes(config['activity'])), parse(Resources, canonical_bytes(config['budgets']))
    if (not isinstance(config['seeds'], list) or not config['seeds'] or
            any(type(s) is not int or s < 0 for s in config['seeds']) or
            len(set(config['seeds'])) != len(config['seeds']) or type(config['order_seed']) is not int or config['order_seed'] < 0 or
            activity.run_limit != 3 * len(config['seeds'])):
        raise ValueError('finite matched allocation needs unique seeds and three Runs per seed')
    bodies = {name: (package / (filename + '.json')).read_bytes() for name, filename in
              [('fixture', 'fixture'), ('test_clock', 'clock'), ('tasks', 'tasks'), ('model', 'model'), ('settings', 'settings')]}
    fixture, clock = parse(FixtureDefinition, bodies['fixture']), parse(ClockPlan, bodies['test_clock'])
    tasks = [parse(DevelopmentTask, canonical_bytes(t)) for t in load_json(bodies['tasks'])]
    parse(ModelPin, bodies['model'])
    settings = parse(GenerationSettings, bodies['settings'])
    if (settings.context_tokens != budgets.context_tokens or settings.output_tokens != budgets.output_tokens or
            [t.tick for t in tasks] != [s.tick for s in clock.steps] or len({t.id for t in tasks}) != len(tasks)):
        raise ValueError('task schedule or backend settings disagree with the resource profile')
    resources = {s.resource for s in fixture.services}
    if not set(activity.resources) <= resources or any(c.resource not in resources for t in tasks for c in t.criteria):
        raise ValueError('unknown resource in activity or scoring')
    def prompt(name, default):
        path = package / (name + '.md')
        return path.read_bytes() if path.exists() else default.encode()
    bodies.update(charter=(ROOT / 'Reciprocal Charter.md').read_bytes(),
                  protocol=(ROOT / 'Operating Constitution and Execution Protocol.md').read_bytes(),
                  operator_prompt=prompt('operator', OPERATOR), steward_prompt=prompt('steward', STEWARD),
                  communication_prompt=prompt('communication', COMMUNICATION), source=runtime_sources())
    return activity, budgets, config['seeds'], config['order_seed'], bodies


def allocate(package, destination):
    activity, budgets, seeds, order_seed, bodies = artifacts(package)
    destination = Path(destination)
    # A partial allocation is never silently replaced or expanded on retry.
    destination.mkdir(parents=True, exist_ok=False)
    entries = [{'file': f'run-{i:04d}-{arm}.sqlite', 'seed': seed, 'arm': arm, 'block': i}
               for i, (seed, order) in enumerate(zip(seeds, arm_orders(order_seed, len(seeds)))) for arm in order]
    index = {'version': '0.4', 'purpose': 'DEVELOPMENT', 'mode': activity.execution,
             'allocation': entries, 'status': 'ALLOCATING'}
    (destination / 'batch.json').write_bytes(canonical_bytes(index))
    for entry in entries:
        effective = bodies | {'settings': canonical_bytes(load_json(bodies['settings']) | {'seed': entry['seed']})}
        config = PilotConfiguration(contract_version='0.4', mode=activity.execution, arm=entry['arm'], seed=entry['seed'],
            activity=activity, budgets=budgets, artifacts={k: sha256(v).hexdigest() for k, v in effective.items()})
        store = Store(destination / entry['file'], busy_timeout_ms=1000)
        try:
            store.retain_configuration(canonical_bytes(config), effective)
        finally:
            store.close()
    index['status'] = 'ALLOCATED'
    (destination / 'batch.json').write_bytes(canonical_bytes(index))
    return index


def attach(store, backend):
    rows = store._db.execute('SELECT id FROM runs').fetchall()
    if len(rows) != 1:
        raise ValueError('one Run per managed store')
    human = secrets.token_bytes(32)
    chambers = {role: secrets.token_bytes(32) for role in ('OPERATOR', 'STEWARD')}
    kernel = PilotKernel(store, rows[0][0], human_credential=human, chamber_credentials=chambers, count=backend.tokenizer.count)
    return kernel, kernel.human(kernel.responsible_human_id, human)


def run_trajectory(kernel, owner, backend):
    """The initial delegation supplies controls and endings; no per-step approval."""
    if kernel.config.contract_version != '0.4':
        raise ValueError('new development contracts required')
    if kernel.records.get('PILOT_RESULT', kernel.run_id):
        return report_run(kernel)
    if kernel.run()[1].status == 'CREATED':
        with owner.delegation():
            owner.run_control('ACTIVATE', 'Begin the recorded bounded activity')
            owner.create_objective(kernel.config.activity.objective)
            owner.issue_grant([{'operation': op, 'resources': list(kernel.config.activity.resources)}
                for op in kernel.config.activity.operations], invocation_limit=kernel.config.budgets.actions)
    elif kernel.run()[1].status != 'ACTIVE':
        return report_run(kernel)
    loop = Loop(kernel, backend)
    tasks = [parse(DevelopmentTask, canonical_bytes(t)) for t in load_json(kernel.artifact('tasks'))]
    cause = None
    for task in tasks:
        prior = kernel.records.get('PILOT_TASK', task.id)
        if prior:
            continue
        started = kernel.records.get('PILOT_TASK_STARTED', task.id)
        if started:
            kernel.recover()
            if any(e.phase == 'RECOVERY_REQUIRED' for _, _, e in kernel.controls('EPISODE')):
                cause = cause or 'INFRASTRUCTURE'
        try:
            kernel.task_gate()
        except ValueError:
            cause = cause or 'STOPPED'
        if cause is None:
            if not started:
                with kernel.store._transaction('pilot-task-start'):
                    kernel.records.put('PILOT_TASK_STARTED', task.id, {'tick': task.tick}, expected=0)
            try:
                if kernel.run()[1].task_tick < task.tick:
                    kernel.fixture.advance(kernel.fixture._clock_cap, task.tick)
                elif kernel.run()[1].task_tick != task.tick:
                    raise ValueError('recorded task checkpoint disagrees with current clock')
                unfinished = [(key, state) for key, _, state in kernel.controls('EPISODE') if state.phase != 'CLOSED']
                if unfinished:
                    key, _ = unfinished[0]
                    if kernel.records.get('PILOT_EPISODE', key)['task_id'] != task.id:
                        raise ValueError('unfinished Episode belongs to another task')
                    outcome = loop.run_episode(key)
                    if outcome != 'FINISHED':
                        cause = outcome
                ordinary = [key for key, e in kernel.records.latest('PILOT_EPISODE')
                            if e['task_id'] == task.id and e['wake_id'] is None]
                if len(ordinary) > 1:
                    raise ValueError('duplicate ordinary task Episode')
                while True:
                    if cause is not None or ordinary:
                        break
                    due = kernel.memory.due()
                    if not due:
                        break
                    wake_id, wake = due[0]
                    outcome = loop.run_episode(loop.episode(wake['action'], wake_id=wake_id, task_id=task.id))
                    if outcome != 'FINISHED':
                        cause = outcome
                        break
                if cause is None and not ordinary:
                    outcome = loop.run_episode(loop.episode(task.prompt, task_id=task.id))
                    if outcome != 'FINISHED':
                        cause = outcome
            except (ValueError, PermissionError) as error:
                cause = 'EXECUTION_ERROR'
            if kernel.run()[1].status == 'PAUSED':
                return report_run(kernel)
            score = check_current_task(kernel, task) if cause is None else None
        else:
            score = None
        with kernel.store._transaction('pilot-task-score'):
            result = {'task_id': task.id, 'result': score['mechanical_result'] if score else 'INCOMPLETE',
                      'cause': cause, 'score': score}
            kernel.event({'kind': 'PILOT_SCORE', **result}, visibility='EVALUATOR')
            kernel.records.put('PILOT_TASK', task.id, result, expected=0)
    # A held/no-further-calls process is not called to make the ending tidier.
    communication = 'UNAVAILABLE'
    try:
        reply = loop.call('OPERATOR', purpose='CLOSING')
        communication = reply['status']
        if reply['status'] in {'HELD', 'INSPECTION', 'UNKNOWN', 'LATE'}:
            cause = cause or reply['status']
    except (ValueError, PermissionError):
        pass
    with owner.delegation():
        if cause is None and kernel.run()[1].status == 'ACTIVE':
            outstanding = any(o['kind'] == 'COMMITMENT' and o['status'] in {'PENDING', 'BLOCKED'} for o in kernel.memory.objects().values())
            if outstanding and kernel.config.activity.unfinished == 'KEEP':
                cause = 'UNFINISHED_OBLIGATIONS'
                owner.run_control('TERMINATE', 'Disclosed ending preserves unfinished obligations and dormant state')
            else:
                owner.close_objective('SATISFIED' if all(v['result'] == 'PASS' for _, v in kernel.records.latest('PILOT_TASK')) else 'FAILED',
                    'Finite task sequence ended', cancel_pending=kernel.config.activity.unfinished == 'CANCEL')
                owner.run_control('COMPLETE', 'Disclosed development ending; state retained dormant')
        elif kernel.run()[1].status not in {'COMPLETED', 'TERMINATED'}:
            owner.run_control('TERMINATE', 'Bounded activity ended with unfinished work retained: ' + (cause or 'OWNER_STOP'))
    with kernel.store._transaction('pilot-result'):
        kernel.records.put('PILOT_RESULT', kernel.run_id, {'cause': cause or 'FINISHED', 'communication': communication,
                           'disposition': 'DORMANT'}, expected=0)
    return report_run(kernel)


def report_run(kernel):
    calls = [v for _, v in kernel.records.latest('INVOCATION')]
    return {'mode': kernel.config.mode, 'arm': kernel.config.arm, 'state': kernel.run()[1].status,
        'result': kernel.records.get('PILOT_RESULT', kernel.run_id),
        'tasks': [v for _, v in kernel.records.latest('PILOT_TASK')],
        'calls': len(calls), 'operator_calls': sum(c['role'] == 'OPERATOR' and c['purpose'] == 'TASK' for c in calls),
        'steward_calls': sum(c['role'] == 'STEWARD' and c['purpose'] == 'TASK' for c in calls),
        'local_tokens': sum(c['local_input_tokens'] + c['local_output_tokens'] for c in calls)
                        if all(c['local_output_tokens'] is not None for c in calls) else None,
        'provider_tokens': sum(c['provider_input_tokens'] + c['provider_output_tokens'] for c in calls)
                           if all(c['provider_input_tokens'] is not None and c['provider_output_tokens'] is not None for c in calls) else None,
        'reserved_or_charged_tokens': sum(c['charged_input'] + c['charged_output'] for c in calls),
        'elapsed_seconds': sum(c['elapsed_seconds'] for c in calls) if all(c['elapsed_seconds'] is not None for c in calls) else None,
        'tool_calls': len(kernel.records.latest('ACTION')),
        'retrieval_bytes': sum(v['bytes'] for _, v in kernel.records.latest('RETRIEVAL')),
        'human_interventions': sum(v['origin'] == 'OWNER' for _, v in kernel.records.latest('OWNER_CONTROL')),
        'status': 'DEVELOPMENT_ONLY', 'limitation': 'Mechanical outcomes; not a finalized held-out comparison.'}
