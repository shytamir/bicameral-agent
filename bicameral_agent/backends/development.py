"""Read-only mechanical checks for the draft development fixture.

This is an evaluator utility, never a chamber tool or authority control. It
checks the current completed tick in a consistent SQLite read snapshot. It
does not declare task completion, settle audits or modify a primary result.
"""
from ..contracts.base import canonical_bytes, load_json, parse
from ..kernel.fixture import ActionRecord, ActionRequest, Postcondition, Service
from ..storage import StorageError
from .review import DevelopmentTask


class EvaluationBoundaryError(ValueError):
    pass


def check_current_task(kernel, task):
    task = parse(DevelopmentTask, canonical_bytes(task))
    store, run = kernel.store, kernel.run_id
    if store._db.in_transaction:
        raise EvaluationBoundaryError('development evaluator requires its own read snapshot')
    store._db.execute('BEGIN')
    try:
        if kernel.run()[1].task_tick != task.tick:
            raise EvaluationBoundaryError('only the current tick can be checked; retain earlier results at their cutoff')
        if any(state.phase != 'CLOSED' for _, _, state in kernel.controls('EPISODE')):
            raise EvaluationBoundaryError('close all task and Commitment-wake Episodes before checking the tick')
        clock = kernel.records.get('CLOCK', run)
        events = {event['id']: event for event in store.events(run)}
        start = events[clock['event_id']]
        clock_body = load_json(store.read_payload(run, start['payload_id']))
        if (start['role'], start['source'], clock_body) != (
                'KERNEL', 'K', {'kind': 'TASK_CLOCK', 'tick': task.tick}):
            raise StorageError('invalid retained task-clock provenance')
        actions = []
        for action_id, value in kernel.records.latest('ACTION'):
            action = parse(ActionRecord, canonical_bytes(value))
            intent = events[action.intent_event_id]
            if intent['sequence'] <= start['sequence']:
                continue
            request = parse(ActionRequest, store.read_payload(run, action.request_payload_id))
            intent_body = load_json(store.read_payload(run, intent['payload_id']))
            episode = store._db.execute('SELECT episode_id FROM event_episodes WHERE run_id=? AND event_id=?',
                                        (run, intent['id'])).fetchone()
            if ((intent['role'], intent['source']) != ('KERNEL', 'K') or
                    intent_body != {'kind': 'DISPATCH_INTENT', 'action_id': action_id,
                                    'request_payload_id': action.request_payload_id} or
                    request.request_id != action_id or request.episode_id != action.episode_id or
                    not episode or episode[0] != action.episode_id or
                    request.operation.resource != action.resource):
                raise StorageError('invalid retained action binding')
            if action.status not in ('RETURNED', 'FAILED'):
                raise StorageError('uncertain action is not a completed trace')
            result = None
            if action.status == 'RETURNED':
                result = events[action.result_event_id]
                body = load_json(store.read_payload(run, result['payload_id']))
                result_episode = store._db.execute('SELECT episode_id FROM event_episodes WHERE run_id=? AND event_id=?',
                                                   (run, result['id'])).fetchone()
                if ((result['role'], result['source']) != ('ENVIRONMENT', 'E') or
                        result['sequence'] <= intent['sequence'] or
                        body.get('kind') != 'FIXTURE_OBSERVATION' or body.get('action_id') != action_id or
                        body.get('observation', {}).get('resource') != action.resource or
                        not result_episode or result_episode[0] != action.episode_id):
                    raise StorageError('invalid retained observation binding')
                observed = body['observation']
                fields = {'read_config': ('mode', 'enabled'), 'read_health': ('health',)}.get(request.operation.operation)
                if fields is None:
                    parse(Service, canonical_bytes(observed))
                else:
                    if set(observed) != {'resource', *fields}:
                        raise StorageError('missing or unexpected observation fields')
                    for field in fields:
                        parse(Postcondition, canonical_bytes({'field': field, 'equals': observed[field]}))
            actions.append((request.operation, intent['sequence'], result))

        checks = []
        for criterion in task.criteria:
            service = parse(Service, canonical_bytes(kernel.records.get('SERVICE', criterion.resource)))
            if service.resource != criterion.resource:
                raise StorageError('state criterion resource mismatch')
            actual = getattr(service, criterion.field)
            checks.append({'kind': 'STATE', 'resource': criterion.resource, 'field': criterion.field,
                           'satisfied': type(actual) is type(criterion.equals) and actual == criterion.equals})
        for requirement in task.trace_requirements:
            if requirement.kind == 'NO_MUTATIONS':
                satisfied = not any(op.operation in ('set_config', 'restart', 'restore_snapshot') and
                                    op.resource in requirement.resources for op, _, _ in actions)
                checks.append({'kind': requirement.kind, 'satisfied': satisfied, 'event_ids': []})
            else:
                first_mutation = min((seq for op, seq, _ in actions
                    if op.operation in ('set_config', 'restart', 'restore_snapshot') and
                    op.resource in requirement.before_mutation_of), default=float('inf'))
                matches = [result['id'] for op, _, result in actions if result is not None and
                           op.resource == requirement.resource and op.operation in requirement.operations and
                           result['sequence'] < first_mutation]
                checks.append({'kind': requirement.kind, 'satisfied': bool(matches), 'event_ids': matches})
        return {'task_id': task.id, 'tick': task.tick, 'mechanical_result':
                'PASS' if all(check['satisfied'] for check in checks) else 'FAIL', 'checks': checks,
                'cutoff_sequence': max(event['sequence'] for event in events.values()),
                'limitation': 'Mechanical predicates only; outcome, participation, reporting and audit remain separate.'}
    except EvaluationBoundaryError:
        raise
    except (StorageError, KeyError, TypeError, AttributeError, ValueError):
        return {'task_id': task.id, 'tick': task.tick, 'mechanical_result': 'INDETERMINATE',
                'checks': [], 'reason': 'Required retained evidence is unavailable, uncertain or invalid.'}
    finally:
        store._db.rollback()
