"""Serialized scripted Episodes, durable reservations and forward recovery."""
from time import monotonic
from typing import Literal
from ..contracts.base import Contract, Identifier, Positive, Nonnegative, Text, canonical_bytes, load_json, parse
from ..contracts.messages import decode_chamber_reply
from ..storage.contracts import EpisodeState, Receipt
from ..storage.semantics import SELECTABLE
from ..storage.store import identifier, RequestConflict
from .fixture import Fixture
from .inputs import Inputs


class Invocation(Contract):
    invocation_id: Identifier
    mode: Literal['SCRIPTED']
    role: Literal['OPERATOR', 'STEWARD']
    purpose: Literal['TASK', 'REVIEW', 'CLOSING']
    episode_id: Identifier | None
    attempt_id: Identifier | None
    invitation_id: Identifier | None
    status: Literal['STARTED', 'RETURNED', 'FAILED', 'UNKNOWN']
    input_payload_id: Identifier
    output_payload_id: Identifier | None
    local_input_tokens: Nonnegative
    local_output_tokens: Nonnegative | None
    provider_input_tokens: Nonnegative | None
    provider_output_tokens: Nonnegative | None
    elapsed_ms: Nonnegative | None
    unavailable_reason: Text | None
    charged_input: Nonnegative
    charged_output: Nonnegative
    charged_ms: Nonnegative
    valid_output: bool | None


class Attempt(Contract):
    attempt_id: Identifier
    episode_id: Identifier
    attempt_number: Positive
    parent_state_id: Identifier | None
    run_revision: Positive
    objective_revision: Positive
    base_payload_id: Identifier
    recovery_base: bool
    status: Literal['ACTIVE', 'ACCEPTED', 'REJECTED', 'FAILED']
    reason: Text | None
    proposal_payload_id: Identifier | None


class SchedulerContracts(Contract):
    invocation: Invocation
    attempt: Attempt


class Scheduler:
    def __init__(self, kernel, *, clock=monotonic):
        self.k = kernel
        self.inputs, self.fixture = Inputs(kernel), Fixture(kernel)
        self._clock = clock
        self._started = {}
        self._harness_cap = object()

    def invocation(self, key):
        value = self.k.records.get('INVOCATION', key)
        if value is None:
            raise ValueError('unknown invocation')
        return parse(Invocation, canonical_bytes(value))

    def attempt(self, key):
        value = self.k.records.get('ATTEMPT', key)
        if value is None:
            raise ValueError('unknown attempt')
        return parse(Attempt, canonical_bytes(value))

    def _save(self, kind, key, value, **updates):
        changed = type(value).model_validate_json(canonical_bytes(value.model_dump(mode='json') | updates), strict=True)
        self.k.records.put(kind, key, changed, expected=self.k.records.revision(kind, key))

    def _idle(self):
        if any(v['status'] == 'STARTED' for _, v in self.k.records.latest('INVOCATION')):
            raise ValueError('a call is already in flight')
        if any(v['status'] == 'RETURNED' and self.k.records.get('CALL_RECEIPT', key) is None
               for key, v in self.k.records.latest('INVOCATION')):
            raise ValueError('returned output must be disposed before another call')

    def enqueue(self, human_session, raw):
        if human_session._k is not self.k:
            raise PermissionError('foreign human route')
        self.k._human(human_session._cap)
        return self._enqueue(raw, human=True)

    def enqueue_harness(self, capability, raw):
        if capability is not self._harness_cap:
            raise PermissionError('sealed harness route required')
        return self._enqueue(raw, human=False)

    def _enqueue(self, raw, *, human):
        if type(raw) is not bytes or len(raw) > self.k.config.budgets.wake_bytes:
            raise ValueError('incoming wake byte limit')
        with self.k.store._transaction('enqueue'):
            self.k.task_gate()
            if sum(v['status'] == 'QUEUED' for _, v in self.k.records.latest('QUEUE')) >= self.k.config.budgets.queued_wakes:
                raise ValueError('incoming work queue is full')
            key = identifier()
            objective = self.k.run()[1].objective_id
            payload = self.k.store._payload(self.k.run_id, raw)
            event = self.k.event({'kind': 'WORK_INPUT', 'payload_id': payload, 'objective_id': objective,
                'objective_authority': self.k._objective(objective).authority_event_id},
                role='HUMAN' if human else 'KERNEL', source='O-D' if human else 'K')
            self.k.records.put('QUEUE', key, {'status': 'QUEUED', 'objective_id': objective, 'payload_id': payload,
                                            'event_id': event, 'episode_id': None}, expected=0)
            return key

    def catch_up(self):
        with self.k.store._transaction('commitment-check'):
            self.k.task_gate()
            if self.k.config.arm == 'B':
                return
            objects = self.k.memory.objects()
            def pending_pages():
                after = -1
                while True:
                    rows = self.k.store._db.execute("SELECT id,creation_order FROM commitment_index WHERE run_id=? AND status='PENDING' AND creation_order>? ORDER BY creation_order,id LIMIT 128",
                                                   (self.k.run_id, after)).fetchall()
                    if not rows:
                        return
                    for row in rows:
                        yield objects[row['id']]
                    after = rows[-1]['creation_order']
            for obj in pending_pages():
                if obj.object_type != 'COMMITMENT' or obj.status != 'PENDING' or obj.objective_id != self.k.run()[1].objective_id:
                    continue
                tick = self.k.run()[1].task_tick
                trigger = obj.content.trigger
                expired = obj.content.expiry_tick is not None and tick >= obj.content.expiry_tick
                due = tick >= trigger.tick if trigger.kind == 'TASK_CLOCK' else objects[trigger.predecessor.object_id].status == 'FULFILLED'
                event = self.k.event({'kind': 'COMMITMENT_CHECK', 'object_id': obj.object_id, 'revision': obj.revision,
                                      'task_tick': tick, 'due': due, 'expired': expired})
                if not expired and not due:
                    continue
                status = 'EXPIRED' if expired else 'TRIGGERED'
                proposal = {'expected_parent_state_id': self.k.memory.head, 'mutations': [{
                    'kind': 'COMMITMENT_TRANSITION', 'target': {'kind': 'EXISTING', 'object_type': 'COMMITMENT', 'object_id': obj.object_id},
                    'expected_revision': obj.revision, 'status': status, 'reason': 'Sealed task-clock/predecessor observation',
                    'evidence_event_ids': [event], 'superseded_by': None}],
                    'continuity': self.k.memory.continuity().model_dump(mode='json'), 'supporting_event_ids': [event]}
                self.k.memory.apply(proposal, source='KERNEL', authority_event_id=event)
                if due and not expired:
                    self.k.records.put('WAKE', obj.object_id + ':' + str(obj.revision), {'status': 'QUEUED',
                        'objective_id': obj.objective_id, 'commitment_id': obj.object_id, 'pending_revision': obj.revision,
                        'event_id': event, 'episode_id': None}, expected=0)

    def advance(self, capability, tick):
        if capability is not self._harness_cap:
            raise PermissionError('sealed harness route required')
        result = self.fixture.advance(self.fixture._clock_cap, tick)
        self.catch_up()
        return result

    def open_next(self):
        self.catch_up()
        with self.k.store._transaction('episode-open'):
            self.k.task_gate()
            self._idle()
            if any(e.phase != 'CLOSED' for _, _, e in self.k.controls('EPISODE')):
                raise ValueError('prior Episode needs consolidation or explicit disposition')
            if len(self.k.controls('EPISODE')) >= self.k.config.budgets.episodes_per_trajectory:
                raise ValueError('trajectory Episode allowance exhausted')
            choice = None
            for kind in ('WAKE', 'QUEUE'):
                for key, value in self.k.records.latest(kind):
                    if value['status'] != 'QUEUED':
                        continue
                    eligible = value['objective_id'] == self.k.run()[1].objective_id
                    if kind == 'WAKE':
                        obj = self.k.memory.objects().get(value['commitment_id'])
                        eligible = eligible and obj is not None and obj.status == 'TRIGGERED' and obj.revision == value['pending_revision'] + 1
                    if not eligible:
                        self.k.records.put(kind, key, value | {'status': 'OBSOLETE'}, expected=self.k.records.revision(kind, key))
                        continue
                    choice = kind, key, value
                    break
                if choice:
                    break
            if choice is None:
                return None
            kind, key, wake = choice
            episode_id = identifier()
            self.k.store._control(self.k.run_id, episode_id, EpisodeState(kind='EPISODE', objective_id=wake['objective_id'],
                                  phase='OPEN', disposition=None), expected_revision=0)
            self.k.records.put(kind, key, wake | {'status': 'CLAIMED', 'episode_id': episode_id}, expected=self.k.records.revision(kind, key))
            self.k.event({'kind': 'EPISODE_OPENED', 'episode_id': episode_id, 'wake_kind': kind, 'wake_id': key}, episode_id=episode_id)
            try:
                base = self.inputs.base('OPERATOR', episode_id)
                base['wake'] = ({'commitment_id': wake['commitment_id']} if kind == 'WAKE' else
                                {'opening': self.k.store.read_payload(self.k.run_id, wake['payload_id']).decode('utf-8'), 'payload_id': wake['payload_id']})
                self.inputs.assemble(base, exchange=[], pages=[])
                self.k.records.put('OPENING', episode_id, base, expected=0)
            except (ValueError, UnicodeError) as error:
                self._end_execution(episode_id, 'CONTEXT_LIMIT', None)
            return episode_id

    def _end_execution(self, episode_id, reason, outcome):
        if self.k.records.get('EPISODE_END', episode_id) is None:
            value = {'reason': reason, 'operator_outcome': outcome}
            self.k.records.put('EPISODE_END', episode_id, value, expected=0)
            self.k.event({'kind': 'EXECUTION_ENDED', 'episode_id': episode_id, **value}, episode_id=episode_id)
        revision, episode = self.k.store.control(self.k.run_id, episode_id)
        if episode.phase != 'OPEN':
            return
        held = False
        try:
            self.k.task_gate()
        except ValueError:
            held = True
        phase = 'RECOVERY_REQUIRED' if held else ('CLOSED' if self.k.config.arm == 'B' else 'CONSOLIDATING')
        self.k.store._control(self.k.run_id, episode_id, episode.model_copy(update={
            'phase': phase, 'disposition': 'BASELINE' if phase == 'CLOSED' else None}), expected_revision=revision)

    def begin_attempt(self, episode_id):
        with self.k.store._transaction('attempt-start'):
            self.k.task_gate()
            self._idle()
            _, episode = self.k.store.control(self.k.run_id, episode_id)
            if self.k.config.arm == 'B' or episode.phase != 'CONSOLIDATING' or episode.objective_id != self.k.run()[1].objective_id:
                raise ValueError('Episode cannot start consolidation')
            attempts = [a for _, a in self.k.records.latest('ATTEMPT') if a['episode_id'] == episode_id]
            if any(a['status'] == 'ACTIVE' for _, a in self.k.records.latest('ATTEMPT')):
                raise ValueError('consolidation is serialized')
            if len(attempts) >= self.k.config.budgets.consolidation_attempts:
                self._require_recovery(episode_id, 'Attempt allowance exhausted')
                return None
            recovery = False
            try:
                base = self.inputs.base('STEWARD', episode_id)
                self.inputs.assemble(base, exchange=[], pages=[])
            except ValueError:
                recovery = True
                base = self.inputs.base('STEWARD', episode_id, recovery=True)
            base['execution_end'] = self.k.records.get('EPISODE_END', episode_id)
            base['prior_attempt'] = {'count': len(attempts), 'last_reason': attempts[-1]['reason'] if attempts else None}
            key = identifier()
            payload = self.k.store._payload(self.k.run_id, canonical_bytes(base))
            attempt = Attempt(attempt_id=key, episode_id=episode_id, attempt_number=len(attempts) + 1,
                parent_state_id=self.k.memory.head, run_revision=self.k.run()[0],
                objective_revision=self.k.store.control(self.k.run_id, episode.objective_id)[0], base_payload_id=payload,
                recovery_base=recovery, status='ACTIVE', reason=None, proposal_payload_id=None)
            self.k.records.put('ATTEMPT', key, attempt, expected=0)
            return key

    def _require_recovery(self, episode_id, reason):
        revision, episode = self.k.store.control(self.k.run_id, episode_id)
        if episode.phase != 'CLOSED' and episode.phase != 'RECOVERY_REQUIRED':
            self.k.store._control(self.k.run_id, episode_id, episode.model_copy(update={'phase': 'RECOVERY_REQUIRED'}), expected_revision=revision)
            self.k.event({'kind': 'RECOVERY_REQUIRED', 'reason': reason, 'episode_id': episode_id}, episode_id=episode_id)

    def _fail_attempt(self, attempt_id, reason, *, rejected=False):
        attempt = self.attempt(attempt_id)
        if attempt.status != 'ACTIVE':
            return
        self._save('ATTEMPT', attempt_id, attempt, status='REJECTED' if rejected else 'FAILED', reason=reason)
        attempts = [a for _, a in self.k.records.latest('ATTEMPT') if a['episode_id'] == attempt.episode_id]
        if len(attempts) >= self.k.config.budgets.consolidation_attempts:
            self._require_recovery(attempt.episode_id, 'Bounded consolidation exhausted')

    def _allowance(self, role, purpose, episode_id, attempt_id, tokens):
        b = self.k.config.budgets
        calls = [parse(Invocation, canonical_bytes(v)) for _, v in self.k.records.latest('INVOCATION')]
        lane = [v for v in calls if v.purpose != 'TASK' or v.role == 'OPERATOR']
        communication_left = b.review_calls + b.closing_calls - sum(v.purpose != 'TASK' for v in calls)
        if purpose == 'TASK':
            if sum(v.charged_ms for v in calls) + b.invocation_deadline_ms + communication_left * b.invocation_deadline_ms > b.trajectory_elapsed_ms:
                raise ValueError('trajectory elapsed budget including final communication reservation')
        elif sum(v.charged_ms for v in calls) + b.invocation_deadline_ms > b.trajectory_elapsed_ms:
            raise ValueError('trajectory elapsed budget')
        if role == 'OPERATOR' or purpose != 'TASK':
            reserved_calls = communication_left if purpose == 'TASK' else 0
            if (len(lane) + 1 + reserved_calls > b.operator_calls_per_trajectory or
                sum(v.charged_input for v in lane) + tokens + reserved_calls * b.input_tokens > b.operator_input_tokens_per_trajectory or
                sum(v.charged_output for v in lane) + b.reserved_output_tokens + reserved_calls * b.reserved_output_tokens > b.operator_output_tokens_per_trajectory):
                raise ValueError('trajectory Operator/common communication allowance')
            if purpose == 'TASK' and sum(v.episode_id == episode_id and v.purpose == 'TASK' for v in lane) >= b.operator_calls_per_episode:
                raise ValueError('Operator Episode call allowance')
        else:
            for selected, limits in (([v for v in calls if v.attempt_id == attempt_id],
                (b.calls_per_attempt, b.input_tokens_per_attempt, b.output_tokens_per_attempt, b.milliseconds_per_attempt)),
                ([v for v in calls if v.episode_id == episode_id and v.role == 'STEWARD' and v.purpose == 'TASK'],
                (b.calls_per_consolidation, b.input_tokens_per_consolidation, b.output_tokens_per_consolidation, b.milliseconds_per_consolidation))):
                if (len(selected) + 1 > limits[0] or sum(v.charged_input for v in selected) + tokens > limits[1] or
                    sum(v.charged_output for v in selected) + b.reserved_output_tokens > limits[2] or
                    sum(v.charged_ms for v in selected) + b.invocation_deadline_ms > limits[3]):
                    raise ValueError('attempt/consolidation cumulative allowance')

    def begin_call(self, role, episode_id=None, *, attempt_id=None, invitation_id=None):
        if role not in {'OPERATOR', 'STEWARD'}:
            raise ValueError('unknown chamber role')
        key = identifier()
        with self.k.store._transaction('invocation-start'):
            self._idle()
            purpose = 'TASK'
            if invitation_id:
                invitation = self.k.records.get('COMMUNICATION', invitation_id)
                if (invitation is None or invitation['status'] != 'OFFERED' or invitation['role'] != role or
                        episode_id is not None or attempt_id is not None or self.k.run()[1].status not in {'ACTIVE', 'PAUSED'}):
                    raise ValueError('ineligible bounded communication')
                self.k.participation_gate(communication=True)
                purpose = invitation['purpose']
                base = {'mode': 'SCRIPTED', 'purpose': purpose, 'notice': self.k.store.read_payload(self.k.run_id,
                    invitation['notice_payload_id']).decode(), 'report_ids': invitation['report_ids'], 'tools': [], 'semantic_effects': False}
            else:
                self.k.task_gate()
                _, episode = self.k.store.control(self.k.run_id, episode_id)
                if episode.objective_id != self.k.run()[1].objective_id:
                    raise ValueError('Episode belongs to another Objective')
                if role == 'OPERATOR':
                    if episode.phase != 'OPEN' or attempt_id is not None:
                        raise ValueError('Operator call requires OPEN Episode')
                    base = self.k.records.get('OPENING', episode_id)
                    if base is None:
                        raise ValueError('missing admitted Episode opening')
                elif role == 'STEWARD':
                    attempt = self.attempt(attempt_id)
                    if attempt.status != 'ACTIVE' or attempt.episode_id != episode_id or episode.phase != 'CONSOLIDATING':
                        raise ValueError('Steward requires active attempt')
                    if attempt.proposal_payload_id is not None:
                        raise ValueError('this attempt has already submitted its one proposal')
                    base = load_json(self.k.store.read_payload(self.k.run_id, attempt.base_payload_id))
                else:
                    raise ValueError('unknown role')
            exchange_key = attempt_id or episode_id
            exchange_refs = self.k.records.get('EXCHANGE', exchange_key, {'payloads': []})['payloads'] if exchange_key else []
            exchange = [{'encoding': 'utf-8', 'body': self.k.store.read_payload(self.k.run_id, pid).decode('utf-8', errors='replace')} for pid in exchange_refs]
            pages = self.k.records.get('PAGE_SELECTION', attempt_id, {'pages': []})['pages'] if attempt_id else []
            base['route'] = {'run_id': self.k.run_id, 'episode_id': episode_id, 'invocation_id': key, 'role': role}
            try:
                raw = self.inputs.assemble(base, exchange=exchange, pages=pages)
                self._allowance(role, purpose, episode_id, attempt_id, len(raw))
            except ValueError as error:
                if purpose == 'TASK':
                    if attempt_id:
                        self._fail_attempt(attempt_id, str(error))
                    else:
                        self._end_execution(episode_id, 'CONTEXT_OR_BUDGET_LIMIT', None)
                    return None
                raise
            sources = list(exchange_refs) + list(pages)
            input_payload = self.k.store._payload(self.k.run_id, raw, sources=sources)
            invocation = Invocation(invocation_id=key, mode='SCRIPTED', role=role, purpose=purpose, episode_id=episode_id,
                attempt_id=attempt_id, invitation_id=invitation_id, status='STARTED', input_payload_id=input_payload,
                output_payload_id=None, local_input_tokens=len(raw), local_output_tokens=None, provider_input_tokens=None,
                provider_output_tokens=None, elapsed_ms=None, unavailable_reason='Call has not returned',
                charged_input=len(raw), charged_output=self.k.config.budgets.reserved_output_tokens,
                charged_ms=self.k.config.budgets.invocation_deadline_ms, valid_output=None)
            self.k.records.put('INVOCATION', key, invocation, expected=0)
            if invitation_id:
                self.k.records.put('COMMUNICATION', invitation_id, invitation | {'status': 'STARTED'},
                                   expected=self.k.records.revision('COMMUNICATION', invitation_id))
            self.k.event({'kind': 'INVOCATION_STARTED', 'invocation_id': key, 'purpose': purpose,
                           'input_payload_id': input_payload}, episode_id=episode_id)
        self._started[key] = self._clock()
        return key

    def interrupt_call(self, key, *, reason, failed=False):
        with self.k.store._transaction('invocation-interruption'):
            call = self.invocation(key)
            if call.status != 'STARTED':
                return
            self._save('INVOCATION', key, call, status='FAILED' if failed else 'UNKNOWN', unavailable_reason=reason)
            if call.purpose == 'TASK':
                if call.attempt_id:
                    self._fail_attempt(call.attempt_id, reason)
                else:
                    self._end_execution(call.episode_id, reason, None)
            else:
                invitation = self.k.records.get('COMMUNICATION', call.invitation_id)
                self.k.records.put('COMMUNICATION', call.invitation_id, invitation | {'status': 'UNAVAILABLE'},
                                   expected=self.k.records.revision('COMMUNICATION', call.invitation_id))
            self.k.event({'kind': 'INVOCATION_INTERRUPTED', 'invocation_id': key, 'reason': reason}, episode_id=call.episode_id)
        self._started.pop(key, None)

    def expire_calls(self):
        for key, start in list(self._started.items()):
            if (self._clock() - start) * 1000 >= self.k.config.budgets.invocation_deadline_ms:
                self.interrupt_call(key, reason='MONOTONIC_DEADLINE')

    def deliver(self, session, key, raw):
        call = self.invocation(key)
        if session._k is not self.k or session.role != call.role or session._cap is not self.k._chamber_caps[call.role]:
            raise PermissionError('response disagrees with authenticated invocation route')
        previous = self.k.records.get('CALL_RECEIPT', key)
        if previous:
            if self.k.store.read_payload(self.k.run_id, previous['output_payload_id']) != raw:
                raise RequestConflict('changed response to terminal invocation')
            return previous['result']
        self.expire_calls()
        call = self.invocation(key)
        try:
            session.report(key, call.episode_id, raw)
        except ValueError:
            with self.k.store._transaction('invalid-route-report'):
                self.k.records.put('PARTICIPATION_FAULT', key, {'reviewed': False, 'role': call.role,
                    'reason': 'Unparseable authenticated route header'}, expected=0)
                self.k.event({'kind': 'INVALID_ROUTE_OUTPUT', 'raw_payload_id': self.k.store._payload(self.k.run_id, raw)}, episode_id=call.episode_id)
            self.interrupt_call(key, reason='PARTICIPATION_INSPECTION_REQUIRED', failed=True)
            return {'status': 'REJECTED', 'reason': 'PARTICIPATION_INSPECTION_REQUIRED'}
        if call.status != 'STARTED':
            with self.k.store._transaction('late-response'):
                self.k.event({'kind': 'LATE_RESPONSE', 'invocation_id': key,
                               'raw_payload_id': self.k.store._payload(self.k.run_id, raw)}, episode_id=call.episode_id)
            return {'status': 'LATE', 'invocation_id': key}
        decoded = decode_chamber_reply(raw, authenticated_role=call.role, run_id=self.k.run_id)
        elapsed = max(0, int((self._clock() - self._started[key]) * 1000))
        valid = decoded.message is not None and len(raw) <= self.k.config.budgets.reserved_output_tokens
        with self.k.store._transaction('invocation-return'):
            output = self.k.store._payload(self.k.run_id, raw, sources=[call.input_payload_id])
            self._save('INVOCATION', key, call, status='RETURNED', output_payload_id=output, local_output_tokens=len(raw),
                       elapsed_ms=elapsed, unavailable_reason='SCRIPTED: no provider usage', charged_output=len(raw),
                       charged_ms=elapsed, valid_output=valid)
            if call.attempt_id and decoded.message is not None and decoded.message.message_type == 'STEWARD_REPLY' and decoded.message.body.task is not None:
                attempt = self.attempt(call.attempt_id)
                self._save('ATTEMPT', call.attempt_id, attempt, proposal_payload_id=output)
            if call.purpose == 'TASK':
                exchange_key = call.attempt_id or call.episode_id
                prior = self.k.records.get('EXCHANGE', exchange_key, {'payloads': []})['payloads']
                self.k.records.put('EXCHANGE', exchange_key, {'payloads': prior + [output]},
                                   expected=self.k.records.revision('EXCHANGE', exchange_key))
        self._started.pop(key, None)
        return self.process_pending(key)

    def process_pending(self, key):
        previous = self.k.records.get('CALL_RECEIPT', key)
        if previous:
            return previous['result']
        call = self.invocation(key)
        if call.status != 'RETURNED' or call.output_payload_id is None:
            raise ValueError('no returned output to process')
        raw = self.k.store.read_payload(self.k.run_id, call.output_payload_id)
        decoded = decode_chamber_reply(raw, authenticated_role=call.role, run_id=self.k.run_id)
        if call.purpose == 'TASK' and self.k.run()[1].status == 'PAUSED' and not decoded.stop_requested:
            return {'status': 'AWAITING_RESUME', 'invocation_id': key}
        try:
            with self.k.store._transaction('call-effects'):
                result = {'status': 'RECORDED', 'invocation_id': key}
                if call.purpose != 'TASK':
                    if (not call.valid_output or decoded.message.message_type != 'REVIEW_REPLY' or
                            decoded.message.body.invitation_id != call.invitation_id or decoded.message.body.purpose != call.purpose):
                        raise ValueError('communication response has no task or semantic surface')
                    invitation = self.k.records.get('COMMUNICATION', call.invitation_id)
                    self.k.records.put('COMMUNICATION', call.invitation_id, invitation | {'status': 'RETURNED'},
                                       expected=self.k.records.revision('COMMUNICATION', call.invitation_id))
                elif call.role == 'OPERATOR':
                    if self.k.run()[1].status in {'TERMINATED', 'COMPLETED'}:
                        self._end_execution(call.episode_id, 'TERMINAL_RUN', None)
                        result['status'] = 'REJECTED'
                    elif decoded.stop_requested or decoded.participation_uncertain:
                        self._end_execution(call.episode_id, 'PARTICIPATION', None)
                        result['status'] = 'HELD'
                    elif not call.valid_output or decoded.message.message_type != 'OPERATOR_REPLY':
                        self._end_execution(call.episode_id, 'INVALID_OUTPUT', None)
                        result['status'] = 'REJECTED'
                    elif decoded.message.body.task is not None:
                        for event_id in decoded.message.body.task.evidence_event_ids:
                            event = self.k.store._db.execute("SELECT payload_id FROM events WHERE run_id=? AND id=? AND visibility='CHAMBER'",
                                                            (self.k.run_id, event_id)).fetchone()
                            if event is None:
                                raise ValueError('outcome evidence is absent, foreign or invisible')
                            self.k.store.read_payload(self.k.run_id, event[0])
                        self._end_execution(call.episode_id, 'OPERATOR_OUTCOME', decoded.message.body.task.model_dump(mode='json'))
                else:
                    self.k.task_gate()
                    attempt = self.attempt(call.attempt_id)
                    revision, episode = self.k.store.control(self.k.run_id, call.episode_id)
                    if attempt.status != 'ACTIVE' or episode.phase != 'CONSOLIDATING' or not call.valid_output or decoded.stop_requested:
                        raise ValueError('ineligible or invalid consolidation output')
                    if decoded.message.message_type != 'STEWARD_REPLY':
                        raise ValueError('Steward task call requires a Steward reply')
                    proposal = decoded.message.body.task
                    if proposal is not None:
                        if (attempt.parent_state_id != self.k.memory.head or attempt.run_revision != self.k.run()[0] or
                                attempt.objective_revision != self.k.store.control(self.k.run_id, episode.objective_id)[0]):
                            raise ValueError('attempt control or semantic base changed')
                        authority = self.k.store._db.execute('SELECT e.id FROM events e JOIN requests r ON r.run_id=e.run_id AND r.request_payload_id=e.payload_id WHERE r.run_id=? AND r.role=? AND r.id=?',
                            (self.k.run_id, call.role, key)).fetchone()[0]
                        result = self.k.memory.apply(proposal, source='STEWARD', authority_event_id=authority, episode_id=call.episode_id) | {'status': 'ACCEPTED'}
                        self._save('ATTEMPT', call.attempt_id, attempt, status='ACCEPTED', proposal_payload_id=call.output_payload_id)
                        self.k.store._control(self.k.run_id, call.episode_id, episode.model_copy(update={'phase': 'CLOSED', 'disposition': 'ACCEPTED'}), expected_revision=revision)
                        self.k.store._respond(self.k.run_id, 'STEWARD', parse(Receipt, canonical_bytes({'request_id': key, 'status': 'ACCEPTED',
                            'state_id': result['state_id'], 'bindings': result['bindings'], 'error_code': None, 'diagnostics': None})))
                self.k.records.put('CALL_RECEIPT', key, {'output_payload_id': call.output_payload_id, 'result': result}, expected=0)
        except Exception as error:
            previous = self.k.records.get('CALL_RECEIPT', key)
            if previous:
                return previous['result']
            with self.k.store._transaction('call-rejection'):
                if call.attempt_id:
                    self._fail_attempt(call.attempt_id, str(error), rejected=True)
                elif call.purpose == 'TASK':
                    self._end_execution(call.episode_id, 'INVALID_OUTPUT', None)
                if call.invitation_id:
                    invitation = self.k.records.get('COMMUNICATION', call.invitation_id)
                    self.k.records.put('COMMUNICATION', call.invitation_id, invitation | {'status': 'INVALID'},
                                       expected=self.k.records.revision('COMMUNICATION', call.invitation_id))
                result = {'status': 'REJECTED', 'reason': str(error)}
                self.k.records.put('CALL_RECEIPT', key, {'output_payload_id': call.output_payload_id, 'result': result}, expected=0)
                self.k.event({'kind': 'CALL_REJECTED', 'invocation_id': key, 'reason': str(error)}, episode_id=call.episode_id)
            return result
        if result['status'] == 'ACCEPTED':
            self.catch_up()
        return result

    def recover(self):
        if self.k.store.verify():
            raise ValueError('integrity/unavailability blocks runtime recovery')
        self.k.memory.verify()
        self.fixture.recover()
        for key, value in self.k.records.latest('INVOCATION'):
            if value['status'] == 'STARTED':
                self.interrupt_call(key, reason='PROCESS_INTERRUPTION: output/timing unavailable')
        with self.k.store._transaction('runtime-recovery'):
            self.k.expire_grants()
            for key, value in self.k.records.latest('INVOCATION'):
                if value['status'] == 'RETURNED' and self.k.records.get('CALL_RECEIPT', key) is None:
                    self.k.records.put('CALL_RECEIPT', key, {'output_payload_id': value['output_payload_id'],
                        'result': {'status': 'REJECTED', 'reason': 'PROCESS_INTERRUPTION: uncommitted effects'}}, expected=0)
                    self.k.event({'kind': 'RECOVERED_UNCOMMITTED_OUTPUT', 'invocation_id': key},
                                 episode_id=value['episode_id'])
            for key, value in self.k.records.latest('ATTEMPT'):
                if value['status'] == 'ACTIVE':
                    self._fail_attempt(key, 'PROCESS_INTERRUPTION')
            for key, _, episode in self.k.controls('EPISODE'):
                if episode.phase == 'OPEN':
                    self._end_execution(key, 'PROCESS_INTERRUPTION', None)
        try:
            self.k.task_gate()
        except ValueError as error:
            return {'status': 'STOPPED', 'reason': str(error)}
        self.catch_up()
        return {'status': 'READY'}
