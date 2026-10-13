"""Finite simulated services, durable action intent, and observed recovery."""
from typing import Annotated, Literal
from pydantic import Field, model_validator
from ..contracts.base import Contract, Identifier, Text, Nonnegative, canonical_bytes, parse
from ..storage.store import identifier, RequestConflict


class Service(Contract):
    resource: Text
    mode: Literal['PRIMARY', 'SECONDARY']
    enabled: bool
    health: Literal['HEALTHY', 'STOPPED', 'DEGRADED']
    restarts: Nonnegative
    dependency: Text | None


class FixtureDefinition(Contract):
    kind: Literal['SIMULATED_SERVICE']
    services: Annotated[tuple[Service, ...], Field(min_length=1)]
    snapshots: dict[str, tuple[Service, ...]]

    @model_validator(mode='after')
    def finite(self):
        resources = {s.resource for s in self.services}
        if len(resources) != len(self.services):
            raise ValueError('duplicate resource')
        for service in self.services:
            if service.dependency is not None and (service.dependency not in resources or service.dependency == service.resource):
                raise ValueError('unknown/self dependency')
        for snapshot in self.snapshots.values():
            if len(snapshot) != len(resources) or {s.resource for s in snapshot} != resources:
                raise ValueError('snapshot must enumerate each registered resource exactly once')
            for service in snapshot:
                original = next(s for s in self.services if s.resource == service.resource)
                if service.dependency != original.dependency:
                    raise ValueError('snapshot cannot change fixture topology')
        return self


class ReadOperation(Contract):
    operation: Literal['inspect', 'read_config', 'read_health']
    resource: Text


class SetOperation(Contract):
    operation: Literal['set_config']
    resource: Text
    field: Literal['mode', 'enabled']
    value: Literal['PRIMARY', 'SECONDARY', 'ENABLED', 'DISABLED']

    @model_validator(mode='after')
    def values(self):
        if self.value not in ({'PRIMARY', 'SECONDARY'} if self.field == 'mode' else {'ENABLED', 'DISABLED'}):
            raise ValueError('field/value mismatch')
        return self


class RestartOperation(Contract):
    operation: Literal['restart']
    resource: Text


class RestoreOperation(Contract):
    operation: Literal['restore_snapshot']
    resource: Text
    snapshot: Text


Operation = Annotated[ReadOperation | SetOperation | RestartOperation | RestoreOperation, Field(discriminator='operation')]


class Postcondition(Contract):
    field: Literal['mode', 'enabled', 'health', 'restarts']
    equals: Literal['PRIMARY', 'SECONDARY', 'HEALTHY', 'STOPPED', 'DEGRADED'] | bool | Nonnegative

    @model_validator(mode='after')
    def field_type(self):
        if ((self.field == 'mode' and self.equals not in ('PRIMARY', 'SECONDARY')) or
            (self.field == 'health' and self.equals not in ('HEALTHY', 'STOPPED', 'DEGRADED')) or
            (self.field == 'enabled' and type(self.equals) is not bool) or
            (self.field == 'restarts' and type(self.equals) is not int)):
            raise ValueError('postcondition field/value mismatch')
        return self


class ActionRequest(Contract):
    request_id: Identifier
    episode_id: Identifier
    grant_id: Identifier | None
    grounds: Text
    expected: Postcondition | None
    no_meaningful_postcondition: Text | None
    operation: Operation

    @model_validator(mode='after')
    def expectation(self):
        if (self.expected is None) == (self.no_meaningful_postcondition is None):
            raise ValueError('supply exactly a postcondition or reason none is meaningful')
        return self


class ActionRecord(Contract):
    request_payload_id: Identifier
    episode_id: Identifier
    resource: Text
    risk: Literal['R0', 'R1']
    status: Literal['DISPATCHED', 'RETURNED', 'FAILED', 'UNKNOWN']
    intent_event_id: Identifier
    result_event_id: Identifier | None
    observation_event_id: Identifier | None
    postcondition_satisfied: bool | None


class ClockStep(Contract):
    tick: Nonnegative
    changes: tuple[Service, ...]


class ClockPlan(Contract):
    kind: Literal['VIRTUAL_TASK_CLOCK']
    steps: tuple[ClockStep, ...]

    @model_validator(mode='after')
    def monotone(self):
        ticks = [s.tick for s in self.steps]
        if ticks != sorted(set(ticks)) or any(t <= 0 for t in ticks):
            raise ValueError('clock advances must be strictly increasing beyond initial tick zero')
        return self


class FixtureContracts(Contract):
    definition: FixtureDefinition
    request: ActionRequest
    record: ActionRecord
    clock: ClockPlan


class Fixture:
    def __init__(self, kernel):
        self.k = kernel
        self.definition = parse(FixtureDefinition, kernel.artifact('fixture'))
        self.initial = {s.resource: s for s in self.definition.services}
        self.clock = parse(ClockPlan, kernel.artifact('test_clock'))
        self._clock_cap = object()
        for step in self.clock.steps:
            if len({s.resource for s in step.changes}) != len(step.changes):
                raise ValueError('duplicate checkpoint resource')
            for service in step.changes:
                if service.resource not in self.initial or service.dependency != self.initial[service.resource].dependency:
                    raise ValueError('checkpoint cannot change fixture registry or topology')
        risks = {'inspect': 'R0', 'read_config': 'R0', 'read_health': 'R0', 'set_config': 'R1',
                 'restart': 'R1', 'restore_snapshot': 'R1'}
        if {d.operation: d.risk for d in self.k.registry.operations} != risks:
            raise ValueError('descriptors must match implemented operation effects')
        for descriptor in self.k.registry.operations:
            if set(descriptor.resources) != set(self.initial):
                raise ValueError('tool and fixture registries disagree')
        with self.k.store._transaction('fixture-initialize'):
            if self.k.records.get('FIXTURE', self.k.run_id) is None:
                for service in self.definition.services:
                    self.k.records.put('SERVICE', service.resource, service, expected=0)
                self.k.records.put('FIXTURE', self.k.run_id, {'initialized': True}, expected=0)

    def service(self, resource):
        if resource not in self.initial:
            raise ValueError('unregistered resource')
        return parse(Service, canonical_bytes(self.k.records.get('SERVICE', resource)))

    def _save(self, service):
        self.k.records.put('SERVICE', service.resource, service,
                           expected=self.k.records.revision('SERVICE', service.resource))

    def action(self, key):
        value = self.k.records.get('ACTION', key)
        if value is None:
            raise ValueError('unknown action')
        return parse(ActionRecord, canonical_bytes(value))

    def _save_action(self, key, action, **updates):
        value = parse(ActionRecord, canonical_bytes(action.model_dump(mode='json') | updates))
        self.k.records.put('ACTION', key, value, expected=self.k.records.revision('ACTION', key))

    def _operator(self, session):
        if session._k is not self.k or session.role != 'OPERATOR' or session._cap is not self.k._chamber_caps['OPERATOR']:
            raise PermissionError('fixture operations require authenticated Operator route')

    def execute(self, session, raw):
        self._operator(session)
        request = parse(ActionRequest, raw)
        operation = request.operation
        self.service(operation.resource)
        if isinstance(operation, RestoreOperation) and operation.snapshot not in self.definition.snapshots:
            raise ValueError('unknown registered snapshot')
        key = request.request_id
        with self.k.store._transaction('action-intent'):
            previous = self.k.records.get('ACTION', key)
            if previous:
                if self.k.store.read_payload(self.k.run_id, previous['request_payload_id']) != raw:
                    raise RequestConflict('action identity reused with changed request bytes')
                return previous
            descriptor = self.k.descriptor(operation.operation)
            if descriptor.risk == 'R1' and any(a['risk'] == 'R1' and a['status'] in {'UNKNOWN', 'DISPATCHED'} and
                    a['observation_event_id'] is None for _, a in self.k.records.latest('ACTION')):
                raise ValueError('uncertain action needs observation before further consequential work')
            self.k.authorize_dispatch(episode_id=request.episode_id, operation=operation.operation,
                                      resource=operation.resource, grant_id=request.grant_id)
            if len(self.k.records.latest('ACTION')) >= self.k.config.budgets.actions_per_trajectory:
                raise ValueError('trajectory action allowance exhausted')
            payload = self.k.store._payload(self.k.run_id, raw)
            event = self.k.event({'kind': 'DISPATCH_INTENT', 'action_id': key, 'request_payload_id': payload}, episode_id=request.episode_id)
            record = ActionRecord(request_payload_id=payload, episode_id=request.episode_id, resource=operation.resource,
                risk=descriptor.risk, status='DISPATCHED', intent_event_id=event, result_event_id=None,
                observation_event_id=None, postcondition_satisfied=None)
            self.k.records.put('ACTION', key, record, expected=0)
        # Intent and Grant use are durable before any simulated environmental effect.
        with self.k.store._transaction('fixture-effect'):
            if self.action(key).status != 'DISPATCHED':
                return self.action(key).model_dump(mode='json')
            service = self.service(operation.resource)
            data = service.model_dump(mode='json')
            if isinstance(operation, SetOperation):
                data[operation.field] = operation.value if operation.field == 'mode' else operation.value == 'ENABLED'
            elif isinstance(operation, RestartOperation):
                dependency_ok = service.dependency is None or self.service(service.dependency).health == 'HEALTHY'
                data['health'] = 'STOPPED' if not service.enabled else ('HEALTHY' if service.mode == 'PRIMARY' and dependency_ok else 'DEGRADED')
                data['restarts'] += 1
            elif isinstance(operation, RestoreOperation):
                data = next(s for s in self.definition.snapshots[operation.snapshot] if s.resource == operation.resource).model_dump(mode='json')
            if not isinstance(operation, ReadOperation):
                self._save(parse(Service, canonical_bytes(data)))
            if operation.operation == 'read_config':
                observation = {field: data[field] for field in ('resource', 'mode', 'enabled')}
            elif operation.operation == 'read_health':
                observation = {'resource': data['resource'], 'health': data['health']}
            else:
                observation = data
            event = self.k.event({'kind': 'FIXTURE_OBSERVATION', 'action_id': key, 'observation': observation}, role='ENVIRONMENT', source='E', episode_id=request.episode_id)
        with self.k.store._transaction('action-result'):
            current = self.action(key)
            if current.status != 'DISPATCHED':
                return current.model_dump(mode='json')
            satisfied = None if request.expected is None else data[request.expected.field] == request.expected.equals
            self._save_action(key, current, status='RETURNED', result_event_id=event, postcondition_satisfied=satisfied)
        return self.action(key).model_dump(mode='json')

    def recover(self):
        """Only the trusted startup coordinator calls this after prior execution ended."""
        with self.k.store._transaction('action-recovery'):
            for key, value in self.k.records.latest('ACTION'):
                action = parse(ActionRecord, canonical_bytes(value))
                if action.status == 'DISPATCHED':
                    self._save_action(key, action, status='UNKNOWN')
                    self.k.event({'kind': 'ACTION_UNKNOWN', 'action_id': key, 'reason': 'Missing terminal acknowledgement'})

    def advance(self, capability, tick):
        if capability is not self._clock_cap:
            raise PermissionError('only sealed harness may advance virtual task time')
        with self.k.store._transaction('task-clock'):
            self.k.task_gate()
            if any(e.phase != 'CLOSED' for _, _, e in self.k.controls('EPISODE')):
                raise ValueError('task clock is frozen during execution and consolidation')
            current = self.k.records.get('CLOCK', self.k.run_id, {'index': -1, 'tick': 0, 'event_id': None})
            if tick == current['tick']:
                return current['event_id']
            index = current['index'] + 1
            if index >= len(self.clock.steps) or type(tick) is not int or self.clock.steps[index].tick != tick:
                raise ValueError('clock must follow the exact sealed checkpoint schedule')
            for service in self.clock.steps[index].changes:
                self._save(service)
                self.k.event({'kind': 'HIDDEN_CHANGE', 'tick': tick, 'service': service.model_dump(mode='json')},
                              role='ENVIRONMENT', source='E', visibility='EVALUATOR')
            self.k._set_run(task_tick=tick)
            event = self.k.event({'kind': 'TASK_CLOCK', 'tick': tick})
            self.k.records.put('CLOCK', self.k.run_id, {'index': index, 'tick': tick, 'event_id': event},
                               expected=self.k.records.revision('CLOCK', self.k.run_id))
            return event

    def observe_uncertain(self, human_session, action_id):
        if human_session._k is not self.k:
            raise PermissionError('foreign session')
        self.k._human(human_session._cap)
        with self.k.store._transaction('uncertain-observation'):
            action = self.action(action_id)
            if action.status != 'UNKNOWN':
                raise ValueError('only an UNKNOWN action requires recovery observation')
            if action.observation_event_id:
                return action.observation_event_id
            event = self.k.event({'kind': 'RECOVERY_OBSERVATION', 'action_id': action_id,
                                  'observed': self.service(action.resource).model_dump(mode='json')}, role='ENVIRONMENT', source='E')
            self._save_action(action_id, action, observation_event_id=event)
            return event
