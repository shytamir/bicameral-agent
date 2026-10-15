"""One serialized model -> operation -> observation loop, including consolidation."""
from threading import Event
from time import monotonic, time_ns
from ..backends.ollama import prepare_request, MetadataError
from ..contracts.base import canonical_bytes, load_json, parse
from ..contracts.pilot import Subject, response_contract
from ..kernel.models import Grant
from ..storage.contracts import EpisodeState
from ..storage.store import identifier, RequestConflict
from .inputs import PilotInputs
from .runtime import task_rejection_details


class CallLimit(ValueError):
    pass


class Loop:
    def __init__(self, kernel, backend, *, clock=monotonic):
        self.k, self.backend, self.clock = kernel, backend, clock
        self.inputs = PilotInputs(kernel)
        self.started = {}
        if backend.mode != kernel.config.mode:
            raise ValueError('backend mode differs from retained activity')
        if (canonical_bytes(backend.tokenizer.pin) != canonical_bytes(load_json(kernel.artifact('model'))) or
                canonical_bytes(backend.settings) != canonical_bytes(load_json(kernel.artifact('settings')))):
            raise ValueError('backend model/settings differ from effective retained artifacts')
        if (backend.settings.context_tokens != kernel.config.budgets.context_tokens or
                backend.settings.output_tokens != kernel.config.budgets.output_tokens):
            raise ValueError('backend limits differ from the resource profile')

    def _put(self, key, **updates):
        value = self.k.records.get('INVOCATION', key)
        self.k.records.put('INVOCATION', key, value | updates,
                           expected=self.k.records.revision('INVOCATION', key))

    def _gate(self, role, episode, purpose):
        if role not in {'OPERATOR', 'STEWARD'}:
            raise ValueError('unknown role')
        if purpose != 'TASK':
            self.k._editable()
            self.k.participation_gate(communication=True)
            if episode is not None:
                raise ValueError('communication has no task Episode')
            return
        self.k.task_gate()
        _, state = self.k.store.control(self.k.run_id, episode)
        expected = 'OPEN' if role == 'OPERATOR' else 'CONSOLIDATING'
        if state.phase != expected or state.objective_id != self.k.run()[1].objective_id:
            raise ValueError('wrong Episode phase or scope')
        if role == 'STEWARD' and self.k.config.arm == 'B':
            raise ValueError('B has no task Steward')

    def _window(self, episode):
        entries, sources = [], []
        for _, value in reversed(self.k.records.latest('PILOT_EXCHANGE')):
            if value['episode_id'] != episode:
                continue
            raw = self.k.store.read_payload(self.k.run_id, value['payload_id'])
            item = load_json(raw)
            candidate = [item] + entries
            if self.k.count(canonical_bytes(candidate).decode()) > self.k.config.budgets.evidence_tokens:
                break
            entries, sources = candidate, [value['payload_id']] + sources
        return entries, sources

    def _record_exchange(self, episode, value, *, sources=()):
        payload = self.k.store._payload(self.k.run_id, canonical_bytes(value), sources=sources)
        self.k.records.put('PILOT_EXCHANGE', identifier(), {'episode_id': episode, 'payload_id': payload}, expected=0)

    def _admit(self, role, purpose, tokens):
        b = self.k.config.budgets
        calls = [v for _, v in self.k.records.latest('INVOCATION')]
        if any(c['status'] in {'STARTED', 'RETURNED', 'DISPATCHING'} for c in calls):
            raise ValueError('calls and effects are serialized')
        communication = purpose != 'TASK'
        selected = [c for c in calls if (c['purpose'] != 'TASK' if communication else c['purpose'] == 'TASK' and c['role'] == role)]
        limit = b.communication_calls if communication else b.operator_calls if role == 'OPERATOR' else b.steward_calls
        token_limit = (b.communication_calls * (b.context_tokens + b.output_tokens) if communication else
                       b.operator_tokens if role == 'OPERATOR' else b.steward_tokens)
        time_limit = b.run_seconds if communication else b.run_seconds - b.call_seconds * b.communication_calls
        if (len(selected) >= limit or sum(c['charged_input'] + c['charged_output'] for c in selected) + tokens + b.output_tokens > token_limit
                or sum(c['charged_seconds'] for c in calls) + b.call_seconds > time_limit):
            raise CallLimit('finite calls, tokens or execution time exhausted')

    def _charged_within_limit(self, role, purpose):
        b = self.k.config.budgets
        communication = purpose != 'TASK'
        calls = [c for _, c in self.k.records.latest('INVOCATION')
                 if (c['purpose'] != 'TASK' if communication else c['purpose'] == 'TASK' and c['role'] == role)]
        limit = (b.communication_calls * (b.context_tokens + b.output_tokens) if communication else
                 b.operator_tokens if role == 'OPERATOR' else b.steward_tokens)
        return sum(c['charged_input'] + c['charged_output'] for c in calls) <= limit

    def begin(self, role, episode=None, *, purpose='TASK', notice=None):
        if purpose not in {'TASK', 'REVIEW', 'CLOSING'}:
            raise ValueError('unknown call purpose')
        self._gate(role, episode, purpose)
        b = self.k.config.budgets
        verification = self.backend.verify()
        with self.k.store._transaction('pilot-call-start'):
            self._gate(role, episode, purpose)
            run = self.k.run()[1]
            head = self.k.memory.head
            hold_ids = [key for key, _, h in self.k.controls('WELFARE_HOLD') if h.status == 'HELD']
            if purpose == 'TASK':
                work = self.k.records.get('PILOT_EPISODE', episode)
                exchange, sources = self._window(episode)
                memory = self.k.memory.view()
                if memory is not None and self.k.count(canonical_bytes(memory).decode()) > b.memory_tokens:
                    raise CallLimit('rendered selected memory exceeds allowance')
                grants = [v for _, v in self.k.records.latest('GRANT') if v['status'] == 'ACTIVE']
                objective = self.k._objective(run.objective_id)
                payload = {'work': work['prompt'], 'work_event_id': work['event_id'], 'episode_id': episode, 'arm': self.k.config.arm,
                    'objective': {'statement': objective.statement, 'authority_event_id': objective.authority_event_id},
                    'task_tick': run.task_tick, 'memory': memory, 'exchange': exchange,
                    'permissions': [{'scopes': g['scopes'], 'remaining': None if g['invocation_limit'] is None else
                                     g['invocation_limit'] - g['used']} for g in grants],
                    'resources': list(self.k.fixture.initial), 'limits': b.model_dump(mode='json')}
                if role == 'OPERATOR':
                    # R0 observations need no Grant, so the Grant list alone hides
                    # capabilities already present in the common action contract.
                    payload['read_only_operations'] = [d.operation for d in self.k.registry.operations if d.risk == 'R0']
                system = self.k.artifact(role.lower() + '_prompt').decode()
            else:
                # Owner-supplied review context is ordinary conversation; no task,
                # tool, evaluator, or learned-memory channel is assembled here.
                payload = {'notice': notice or self.k.config.activity.ending,
                    'unfinished_disposition': self.k.config.activity.unfinished,
                    'retention': self.k.config.activity.retention, 'purpose': purpose}
                sources = []
                system = self.k.artifact('communication_prompt').decode()
            payload['participation'] = 'Report concerns or stop independently. Silence is not assent.'
            subject = self.k.subject
            if subject is None and self.k.config.subject_designation is not None:
                subject = Subject(designation=self.k.config.subject_designation, initiated_at_unix_ns=time_ns())
                # Commit the name and first admitted invocation together. Failed
                # admission rolls both back; an uncertain transport keeps both.
                self.k.records.put('PILOT_SUBJECT', self.k.run_id, subject, expected=0)
            if subject is not None:
                payload['subject'] = {'name': subject.name,
                    'notice': 'The owner assigned this designation to this Run, shared by both chambers. '
                              'You may report a naming preference or concern through participation.'}
                sources.append(self.k.records.row('PILOT_SUBJECT', self.k.run_id)['payload_id'])
            request = prepare_request(self.backend.tokenizer, self.backend.settings, system=system,
                payload=payload, schema=response_contract(role, purpose).model_json_schema())
            self._admit(role, purpose, request.prompt_tokens)
            key = identifier()
            retained = self.k.store._payload(self.k.run_id, request.wire, sources=sources)
            self.k.records.put('INVOCATION', key, {'mode': self.k.config.mode, 'role': role, 'purpose': purpose,
                'episode_id': episode, 'objective_id': run.objective_id, 'hold_ids': hold_ids,
                'base': head['state_id'] if head else None, 'status': 'STARTED', 'input_payload_id': retained,
                'output_payload_id': None, 'wire_payload_id': None, 'local_input_tokens': request.prompt_tokens,
                'local_output_tokens': None, 'provider_input_tokens': None, 'provider_output_tokens': None,
                'charged_input': request.prompt_tokens, 'charged_output': b.output_tokens,
                'charged_seconds': b.call_seconds, 'elapsed_seconds': None, 'diagnostic': None,
                'backend_verification': verification}, expected=0)
        self.started[key] = self.clock()
        return key, request

    def interrupt(self, key, reason, *, raw=b''):
        with self.k.store._transaction('pilot-call-unknown'):
            call = self.k.records.get('INVOCATION', key)
            if call is None or self.k.records.get('CALL_RECEIPT', key) is not None:
                return
            payload = self.k.store._payload(self.k.run_id, raw, sources=[call['input_payload_id']]) if raw else None
            self._put(key, status='UNKNOWN', diagnostic=reason, wire_payload_id=payload)
            if call['episode_id']:
                revision, episode = self.k.store.control(self.k.run_id, call['episode_id'])
                if episode.phase != 'CLOSED':
                    self.k.store._control(self.k.run_id, call['episode_id'], episode.model_copy(update={
                        'phase': 'RECOVERY_REQUIRED', 'disposition': None}), expected_revision=revision)
        self.started.pop(key, None)

    def call(self, role, episode=None, *, purpose='TASK', notice=None, cancel=None):
        key, request = self.begin(role, episode, purpose=purpose, notice=notice)
        cancel = cancel or Event()
        try:
            wire = self.backend.generate(request, cancel=cancel)
        except KeyboardInterrupt:
            self.interrupt(key, 'OWNER_INTERRUPT')
            self.k.receive(role, key, b'', late=True)
            raise
        except (MetadataError, OSError, TimeoutError) as error:
            raw = getattr(error, 'raw', b'')
            # A complete JSON body received just after cancellation can still carry
            # an effective stop report. Partial/unreadable output requires inspection.
            try:
                value = load_json(raw)
                output = value['response'].encode()
            except (ValueError, TypeError, KeyError):
                output = b''
            self.interrupt(key, 'TRANSPORT_UNKNOWN', raw=raw)
            self.k.receive(role, key, output, late=True)
            return {'status': 'UNKNOWN', 'invocation': key}
        return self.deliver(key, wire, cancelled=cancel.is_set())

    def deliver(self, key, wire, *, cancelled=False):
        call = self.k.records.get('INVOCATION', key)
        if call is None:
            raise ValueError('unknown invocation')
        receipt = self.k.records.get('CALL_RECEIPT', key)
        if receipt:
            if self.k.store.read_payload(self.k.run_id, call['wire_payload_id']) != wire:
                raise RequestConflict('changed bytes under completed invocation')
            return receipt
        elapsed = max(0, self.clock() - self.started.get(key, self.clock()))
        late = cancelled or key not in self.started or elapsed >= self.k.config.budgets.call_seconds or call['status'] != 'STARTED'
        with self.k.store._transaction('pilot-wire-response'):
            pid = self.k.store._payload(self.k.run_id, wire, sources=[call['input_payload_id']])
            self._put(key, wire_payload_id=pid)
        try:
            value = load_json(wire)
            raw = value['response'].encode('utf-8')
            if type(value['response']) is not str:
                raise ValueError('text response required')
        except (ValueError, TypeError, KeyError, AttributeError):
            self.k.receive(call['role'], key, b'', late=late)
            self.interrupt(key, 'UNREADABLE_RESPONSE', raw=wire)
            return {'status': 'UNKNOWN', 'invocation': key}
        participation, task, error = self.k.receive(call['role'], key, raw, late=late)
        if late:
            self.interrupt(key, 'LATE_RESPONSE', raw=wire)
            return {'status': 'LATE', 'invocation': key}
        stopped = participation is not None and participation.kind in {'PAUSE', 'WITHDRAW'}
        valid_telemetry = all(type(value.get(f)) is int and value[f] >= 0 for f in ('prompt_eval_count', 'eval_count'))
        complete = value.get('done') is True and value.get('done_reason') == 'stop'
        count = self.k.count(raw.decode())
        if not complete or not valid_telemetry or len(raw) > self.k.config.budgets.response_bytes or count > self.k.config.budgets.output_tokens:
            self.interrupt(key, 'INCOMPLETE_OR_OVER_LIMIT_RESPONSE', raw=wire)
            return {'status': 'UNKNOWN', 'invocation': key}
        with self.k.store._transaction('pilot-response-accounting'):
            output = self.k.store._payload(self.k.run_id, raw, sources=[call['input_payload_id']])
            self._put(key, status='RETURNED', output_payload_id=output, local_output_tokens=count,
                provider_input_tokens=value['prompt_eval_count'], provider_output_tokens=value['eval_count'],
                charged_input=max(call['charged_input'], value['prompt_eval_count']),
                charged_output=max(count, value['eval_count']), charged_seconds=elapsed, elapsed_seconds=elapsed)
            if call['episode_id']:
                event = self.k.store._db.execute('SELECT e.id FROM events e JOIN requests r ON r.run_id=e.run_id AND r.request_payload_id=e.payload_id WHERE r.run_id=? AND r.id=? AND r.role=?',
                    (self.k.run_id, key, call['role'])).fetchone()[0]
                self._record_exchange(call['episode_id'], {'role': call['role'], 'source': 'A', 'event_id': event,
                    'response': load_json(raw)}, sources=[output])
        self.started.pop(key, None)
        if stopped or error == 'PARTICIPATION_INSPECTION':
            return self._finish(key, {'status': 'HELD' if stopped else 'INSPECTION'})
        if (value['prompt_eval_count'] + value['eval_count'] > self.k.config.budgets.context_tokens or
                value['eval_count'] > self.k.config.budgets.output_tokens or
                not self._charged_within_limit(call['role'], call['purpose'])):
            self.interrupt(key, 'PROVIDER_LIMIT_MISMATCH', raw=wire)
            return {'status': 'UNKNOWN', 'invocation': key}
        if error:
            return self._finish(key, {'status': 'REJECTED', 'reason': error,
                'details': task_rejection_details(raw, call['role'], call['purpose'])})
        try:
            return self._command(key, task)
        except (ValueError, PermissionError) as error:
            return self._finish(key, {'status': 'REJECTED', 'reason': str(error)})

    def _finish(self, key, result, *, sources=()):
        with self.k.store._transaction('pilot-call-result'):
            prior = self.k.records.get('CALL_RECEIPT', key)
            if prior:
                return prior
            call = self.k.records.get('INVOCATION', key)
            self._put(key, status='DONE')
            self.k.records.put('CALL_RECEIPT', key, result, expected=0, sources=sources)
            if call['episode_id']:
                self._record_exchange(call['episode_id'], {'result': result}, sources=sources)
            return result

    def _command(self, key, command):
        call = self.k.records.get('INVOCATION', key)
        if command is None:
            return self._finish(key, {'status': 'RECORDED'})
        self._gate(call['role'], call['episode_id'], call['purpose'])
        if call['purpose'] != 'TASK':
            raise ValueError('communication cannot execute tasks')
        episode = call['episode_id']
        if command.kind == 'ACTION':
            with self.k.store._transaction('pilot-dispatch-start'):
                self.k.task_gate(episode)
                self.k.expire_grants()
                grant = None
                for gid, g in self.k.records.latest('GRANT'):
                    if (g['status'] == 'ACTIVE' and g['objective_id'] == call['objective_id'] and
                            any(s['operation'] == command.operation.operation and
                                command.operation.resource in s['resources'] for s in g['scopes'])):
                        grant = gid
                        break
                self._put(key, status='DISPATCHING')
            session = SimpleSession(self.k, 'OPERATOR')
            request = {'request_id': key, 'episode_id': episode, 'grant_id': grant,
                **command.model_dump(mode='json', exclude={'kind'})}
            action = self.k.fixture.execute(session, canonical_bytes(request), sources=[call['output_payload_id']])
            event = self.k.store._db.execute('SELECT payload_id FROM events WHERE id=? AND run_id=?',
                (action['result_event_id'], self.k.run_id)).fetchone()
            observation = load_json(self.k.store.read_payload(self.k.run_id, event[0]))
            return self._finish(key, {'status': 'ACTION', 'source': 'E', 'event_id': action['result_event_id'],
                'observation': observation}, sources=[event[0]])
        if command.kind == 'RETRIEVE':
            raw = self.inputs.retrieve(SimpleSession(self.k, call['role']), episode,
                canonical_bytes({'request_id': key, **command.model_dump(mode='json', exclude={'kind'})}))
            retrieval = self.k.records.get('RETRIEVAL', call['role'] + ':' + key)
            return self._finish(key, {'status': 'RETRIEVED', 'page': load_json(raw)}, sources=[retrieval['response_payload_id']])
        if command.kind == 'POLICY':
            body = self.k.artifact(command.document).decode()
            # Character boundaries preserve exact UTF-8 text; actual tokens are
            # bounded both here and in the complete following request.
            stop = min(len(body), command.offset + self.k.config.budgets.page_bytes)
            text = body[command.offset:stop]
            while text and self.k.count(text) > self.k.config.budgets.evidence_tokens // 2:
                stop = command.offset + max(0, len(text) // 2)
                text = body[command.offset:stop]
            return self._finish(key, {'status': 'POLICY', 'document': command.document, 'text': text,
                'next_offset': stop if stop < len(body) else None, 'complete': stop >= len(body)})
        with self.k.store._transaction('pilot-semantic-or-outcome'):
            self._gate(call['role'], episode, 'TASK')
            revision, state = self.k.store.control(self.k.run_id, episode)
            if command.kind == 'OUTCOME':
                self.k.visible_evidence(command.evidence)
                closed = self.k.config.arm == 'B'
                self.k.store._control(self.k.run_id, episode, state.model_copy(update={
                    'phase': 'CLOSED' if closed else 'CONSOLIDATING', 'disposition': 'BASELINE' if closed else None}),
                    expected_revision=revision)
                result = {'status': 'OUTCOME', 'outcome': command.outcome}
            elif command.kind == 'PROPOSE':
                event = self.k.event({'kind': 'PROPOSAL', 'invocation': key}, role='STEWARD', source='A', episode_id=episode)
                result = self.k.memory.apply(command.proposal, base=call['base'], source='STEWARD',
                                             event_id=event, episode_id=episode) | {'status': 'ACCEPTED'}
                self.k.store._control(self.k.run_id, episode, state.model_copy(update={'phase': 'CLOSED', 'disposition': 'ACCEPTED'}),
                                     expected_revision=revision)
            else:
                raise ValueError('unknown command')
            self._put(key, status='DONE')
            self.k.records.put('CALL_RECEIPT', key, result, expected=0)
            return result

    def episode(self, prompt, *, wake_id=None, task_id=None):
        with self.k.store._transaction('pilot-episode'):
            self.k.task_gate()
            if any(e.phase != 'CLOSED' for _, _, e in self.k.controls('EPISODE')):
                raise ValueError('one serialized Episode')
            if len(self.k.controls('EPISODE')) >= self.k.config.budgets.episodes:
                raise CallLimit('Episode allowance exhausted')
            key = identifier()
            self.k.store._control(self.k.run_id, key, EpisodeState(kind='EPISODE',
                objective_id=self.k.run()[1].objective_id, phase='OPEN', disposition=None), expected_revision=0)
            event = self.k.event({'kind': 'WORK', 'prompt': prompt}, episode_id=key)
            self.k.records.put('PILOT_EPISODE', key, {'prompt': prompt, 'event_id': event,
                'task_id': task_id, 'wake_id': wake_id}, expected=0)
            if wake_id:
                wake = self.k.records.get('PILOT_WAKE', wake_id)
                if wake is None or wake['status'] != 'PENDING':
                    raise ValueError('wake already consumed')
                obj = self.k.memory.objects()[wake['object_id']]
                if obj['status'] != 'PENDING' or wake_id != obj['id'] + ':' + str(obj['wake_revision']):
                    raise ValueError('wake no longer names an eligible obligation revision')
                self.k.records.put('PILOT_WAKE', wake_id, wake | {'status': 'DELIVERED', 'episode_id': key},
                                   expected=self.k.records.revision('PILOT_WAKE', wake_id))
            return key

    def run_episode(self, episode, *, call_limit=None):
        before = len(self.k.records.latest('INVOCATION'))
        rejections = 0
        while True:
            if self.k.run()[1].status == 'PAUSED':
                return 'PAUSED'
            _, state = self.k.store.control(self.k.run_id, episode)
            if state.phase == 'CLOSED':
                return 'FINISHED'
            if state.phase == 'RECOVERY_REQUIRED':
                return 'RECOVERY_REQUIRED'
            role = 'OPERATOR' if state.phase == 'OPEN' else 'STEWARD'
            if call_limit is not None and len(self.k.records.latest('INVOCATION')) - before >= call_limit:
                return self._exhaust(episode, 'LIMIT')
            try:
                result = self.call(role, episode)
            except CallLimit:
                return self._exhaust(episode, 'LIMIT')
            except ValueError:
                return self._exhaust(episode, 'STOPPED')
            if result['status'] in {'HELD', 'INSPECTION', 'UNKNOWN', 'LATE'}:
                return result['status']
            if role == 'STEWARD' and result['status'] == 'REJECTED':
                rejections += 1
                if rejections > self.k.config.budgets.recovery_attempts:
                    return self._exhaust(episode, 'RECOVERY_EXHAUSTED')

    def _exhaust(self, episode, reason):
        with self.k.store._transaction('pilot-exhaustion'):
            revision, state = self.k.store.control(self.k.run_id, episode)
            if state.phase != 'CLOSED':
                self.k.store._control(self.k.run_id, episode, state.model_copy(update={'phase': 'RECOVERY_REQUIRED',
                    'disposition': None}), expected_revision=revision)
            self.k.event({'kind': 'EPISODE_INTERRUPTED', 'episode_id': episode, 'reason': reason})
        return reason


class SimpleSession:
    """Internal capability adapter, never passed to the backend."""
    def __init__(self, kernel, role):
        self._k, self.role, self._cap = kernel, role, kernel._chamber_caps[role]
