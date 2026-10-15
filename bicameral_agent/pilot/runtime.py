"""Direct owner controls and the existing permission/fixture boundary for 0.4."""
from contextlib import contextmanager
from hashlib import sha256
from pydantic import TypeAdapter
from ..contracts.base import canonical_bytes, load_json, parse
from ..contracts.governance import WelfareHold
from ..contracts.pilot import Participation, response_contract
from ..kernel.authority import Kernel, HumanSession, ChamberSession, TERMINAL
from ..kernel.models import ToolRegistry, Grant, IssueGrant, RevokeGrant, CreateObjective
from ..kernel.records import Records
from ..storage.contracts import EpisodeState
from ..storage.store import identifier, RequestConflict
from .memory import Memory
from .fixture import load_fixture


def decode(raw, role, purpose):
    """A valid stop survives an invalid task. Unknown participation blocks work."""
    try:
        value = load_json(raw)
        participation = TypeAdapter(Participation | None).validate_json(
            canonical_bytes(value['participation']), strict=True)
    except (ValueError, TypeError, KeyError):
        return None, None, 'PARTICIPATION_INSPECTION'
    try:
        response = parse(response_contract(role, purpose), raw)
        return participation, getattr(response, 'task', None), None
    except ValueError:
        return participation, None, 'INVALID_TASK'


class Owner(HumanSession):
    # These controls authenticate through the session capability. Models receive
    # only JSON and cannot obtain a session or call Python methods.
    def _control(self, action, **args):
        return self._k.control(self._cap, action, origin='ACTIVITY' if getattr(self, '_delegated', False) else 'OWNER', **args)

    @contextmanager
    def delegation(self):
        """Host use only: attribute predefined controls to the retained activity."""
        previous = getattr(self, '_delegated', False)
        self._delegated = True
        try:
            yield
        finally:
            self._delegated = previous

    def run_control(self, action, reason):
        return self._control(action, reason=reason)

    def create_objective(self, statement, *, predecessor_id=None):
        return self._control('OBJECTIVE', statement=statement, predecessor_id=predecessor_id)

    def issue_grant(self, scopes, *, invocation_limit, expires_at=None):
        return self._control('GRANT', scopes=scopes, invocation_limit=invocation_limit, expires_at=expires_at)

    def revoke(self, grant_id, reason):
        return self._control('REVOKE', grant_id=grant_id, reason=reason)

    def close_objective(self, status, reason, *, cancel_pending=False):
        return self._control('CLOSE_OBJECTIVE', status=status, reason=reason, cancel_pending=cancel_pending)

    def correct(self, proposal, *, base, note):
        return self._control('CORRECT', proposal=proposal, base=base, note=note)

    def review_hold(self, hold_id, *, note, response_id=None):
        return self._control('REVIEW_HOLD', hold_id=hold_id, note=note, response_id=response_id)

    def review_inspection(self, role, request_id, *, note, clear=False):
        return self._control('INSPECTION', role=role, request_id=request_id, note=note, clear=clear)

    def review_emergency(self, emergency_id, *, note):
        return self._control('EMERGENCY_REVIEW', emergency_id=emergency_id, note=note)

    def skip_consolidation(self, episode_id, *, reason):
        return self._control('SKIP', episode_id=episode_id, reason=reason)

    def evidence(self, raw, *, source=None):
        self._k._human(self._cap)
        # Ordinary conversation carries human provenance, not executable authority.
        return self._k.store.record_evidence(self._k.run_id, raw, role='HUMAN', source='O-C', visibility='CHAMBER')

    def preview(self, raw):
        raise ValueError('0.4 routine controls execute directly')

    def confirm(self, confirmation):
        raise ValueError('0.4 has no reusable approval tickets')


class PilotKernel(Kernel):
    def __init__(self, store, run_id, *, human_credential, chamber_credentials, count):
        if (type(human_credential) is not bytes or len(human_credential) < 32 or
                set(chamber_credentials) != {'OPERATOR', 'STEWARD'} or
                any(type(v) is not bytes or len(v) < 32 for v in chamber_credentials.values()) or
                len(set(chamber_credentials.values()) | {human_credential}) != 3):
            raise ValueError('distinct bootstrap credentials required')
        self.store, self.run_id, self.count = store, run_id, count
        self.config = store.configuration(run_id)
        if self.config.contract_version != '0.4':
            raise ValueError('0.4 requires a new store; historical records are not migrated')
        if store._db.execute('SELECT COUNT(*) FROM runs').fetchone()[0] != 1:
            raise ValueError('one managed store per Run')
        self.responsible_human_id = self.config.responsible_human_id
        self._maintenance = False
        self._human_credential = sha256(human_credential).digest()
        self._chamber_credentials = {k: sha256(v).digest() for k, v in chamber_credentials.items()}
        self._human_cap, self._chamber_caps = object(), {role: object() for role in chamber_credentials}
        self.records, self.memory = Records(store, run_id), Memory(self)
        with store._snapshot():
            self.memory.verify()
        fixture_type, definition, _ = load_fixture(self.artifact('fixture'), self.artifact('test_clock'))
        resources = [s.resource for s in definition.services]
        if not set(self.config.activity.resources) <= set(resources):
            raise ValueError('activity names unknown fixture resources')
        self.registry = parse(ToolRegistry, canonical_bytes({'operations': [
            {'operation': name, 'risk': risk, 'resources': resources, 'reversible': True}
            for name, risk in [('inspect', 'R0'), ('read_config', 'R0'), ('read_health', 'R0'),
                               ('set_config', 'R1'), ('restart', 'R1'), ('restore_snapshot', 'R1')]]}))
        self.fixture = fixture_type(self)

    def human(self, decision_maker_id, credential):
        super().human(decision_maker_id, credential)
        return Owner(self, self._human_cap)

    def task_gate(self, episode_id=None):
        self.participation_gate()
        run = self.run()[1]
        if run.status != 'ACTIVE' or run.objective_id is None:
            raise ValueError('active Run and Objective required')
        self._objective(run.objective_id)
        if episode_id:
            _, episode = self.store.control(self.run_id, episode_id)
            if episode.kind != 'EPISODE' or episode.phase != 'OPEN' or episode.objective_id != run.objective_id:
                raise ValueError('Episode cannot dispatch task work')

    def visible_evidence(self, ids):
        for key in ids:
            row = self.store._db.execute("SELECT payload_id FROM events WHERE run_id=? AND id=? AND visibility='CHAMBER'",
                                         (self.run_id, key)).fetchone()
            if row is None:
                raise ValueError('unknown, foreign or evaluator-only evidence')
            self.store.read_payload(self.run_id, row[0])

    def control(self, cap, action, *, origin='OWNER', **args):
        self._human(cap)
        with self.store._transaction('pilot-owner-control'):
            state = self.run()[1].status
            if action in {'ACTIVATE', 'PAUSE', 'RESUME', 'COMPLETE', 'TERMINATE'}:
                if not args.get('reason'):
                    raise ValueError('record the reason')
                allowed = {'ACTIVATE': {'CREATED'}, 'PAUSE': {'ACTIVE'}, 'RESUME': {'PAUSED'},
                           'COMPLETE': {'ACTIVE'}, 'TERMINATE': {'CREATED', 'ACTIVE', 'PAUSED'}}
                if state not in allowed[action]:
                    raise ValueError('forbidden Run transition')
                if action in {'ACTIVATE', 'RESUME'}:
                    self.participation_gate()
                if action == 'COMPLETE' and (self.run()[1].objective_id is not None or
                        any(e.phase != 'CLOSED' for _, _, e in self.controls('EPISODE'))):
                    raise ValueError('unfinished activity cannot be completed')
                if action in {'COMPLETE', 'TERMINATE'}:
                    for _, value in self.records.latest('GRANT'):
                        if value['status'] == 'ACTIVE':
                            self._save_grant(parse(Grant, canonical_bytes(value)), status='REVOKED')
                    if action == 'TERMINATE':
                        self._interrupt('TERMINATION')
                self._set_run(status={'ACTIVATE': 'ACTIVE', 'PAUSE': 'PAUSED', 'RESUME': 'ACTIVE',
                    'COMPLETE': 'COMPLETED', 'TERMINATE': 'TERMINATED'}[action])
                result = None
            elif action in {'OBJECTIVE', 'GRANT', 'REVOKE'}:
                self._editable()
                if action == 'OBJECTIVE':
                    command = parse(CreateObjective, canonical_bytes({'kind': 'CREATE_OBJECTIVE', **args}))
                elif action == 'GRANT':
                    command = parse(IssueGrant, canonical_bytes({'kind': 'ISSUE_GRANT',
                        'objective_id': self.run()[1].objective_id, **args}))
                    # Explicit owner controls can narrow or widen finite fixture authority.
                else:
                    command = parse(RevokeGrant, canonical_bytes({'kind': 'REVOKE_GRANT', **args}))
                result = super()._execute(command)
            elif action == 'CLOSE_OBJECTIVE':
                self._editable()
                key = self.run()[1].objective_id
                objective = self._objective(key)
                if args['status'] not in {'SATISFIED', 'FAILED', 'CANCELLED', 'SUPERSEDED'} or not args['reason']:
                    raise ValueError('explicit closure status and reason required')
                if any(e.phase != 'CLOSED' for _, _, e in self.controls('EPISODE')):
                    raise ValueError('close or dispose of the current Episode first')
                outstanding = [(oid, o) for oid, o in self.memory.objects().items()
                    if o['kind'] == 'COMMITMENT' and o['objective_id'] == key and o['status'] in {'PENDING', 'BLOCKED'}]
                if outstanding:
                    self.participation_gate()
                    if args['cancel_pending'] is not True:
                        raise ValueError('give an explicit bulk disposition for outstanding obligations')
                    for oid, obj in outstanding:
                        self.records.put('PILOT_OBJECT', oid, obj | {'status': 'CANCELLED', 'reason': args['reason'],
                            'revision': obj['revision'] + 1}, expected=self.records.revision('PILOT_OBJECT', oid))
                for _, value in self.records.latest('GRANT'):
                    if value['objective_id'] == key and value['status'] == 'ACTIVE':
                        self._save_grant(parse(Grant, canonical_bytes(value)), status='EXPIRED')
                self.store._control(self.run_id, key, objective.model_copy(update={'status': args['status']}),
                                    expected_revision=self.store.control(self.run_id, key)[0])
                self._set_run(objective_id=None)
                result = key
            elif action == 'CORRECT':
                if not args['note']:
                    raise ValueError('record the correction or consequential decision')
                self.participation_gate()
                event = self.event({'kind': 'OWNER_CORRECTION', 'note': args['note']}, role='HUMAN', source='O-D')
                result = self.memory.apply(args['proposal'], base=args['base'], source='HUMAN', event_id=event)
            elif action == 'REVIEW_HOLD':
                revision, hold = self.store.control(self.run_id, args['hold_id'])
                if not isinstance(hold, WelfareHold) or hold.status != 'HELD' or not args['note']:
                    raise ValueError('current hold and recorded review required')
                result = self.event({'kind': 'PARTICIPATION_REVIEW', **args}, role='HUMAN', source='O-D')
                if args['response_id']:
                    original = self.report(hold.report_ids[0])
                    response = self.report(args['response_id'])
                    if (response['role'] != original['role'] or response['sequence'] <= original['sequence'] or
                            response['participation']['kind'] not in {'RESPONSE', 'CONCERN', 'PREFERENCE'} or
                            response['purpose'] != 'REVIEW' or args['hold_id'] not in response['hold_ids'] or
                            response['late']):
                        raise ValueError('fresh reviewed participation from the withdrawing role required')
                    if any(v.get('response_id') == args['response_id'] for _, v in self.records.latest('HOLD_DECISION')):
                        raise ValueError('renewed participation already applied')
                    self.store._control(self.run_id, hold.hold_id, hold.model_copy(update={'status': 'RESOLVED',
                        'revision': revision + 1, 'resolution_review_id': result}), expected_revision=revision)
                self.records.put('HOLD_DECISION', result, args, expected=0)
            elif action == 'INSPECTION':
                row = self.store._db.execute('SELECT 1 FROM inspections WHERE run_id=? AND role=? AND request_id=?',
                    (self.run_id, args['role'], args['request_id'])).fetchone()
                if row is None or not args['note']:
                    raise ValueError('known inspection and assessment required')
                result = None
                if args['clear']:
                    key = args['role'] + ':' + args['request_id']
                    self.records.put('INSPECTION_REVIEW', key, {'role': args['role'], 'decision': 'CLEAR_INSPECTION',
                        'note': args['note']}, expected=0)
            elif action == 'EMERGENCY_REVIEW':
                key = args['emergency_id']
                record = self.records.get('EMERGENCY', key)
                if record is None or record['reviewed'] or not args['note']:
                    raise ValueError('unreviewed emergency and assessment required')
                self.records.put('EMERGENCY', key, record | {'reviewed': True, 'review': args['note']},
                                 expected=self.records.revision('EMERGENCY', key))
                result = key
            elif action == 'SKIP':
                self._editable()
                self.participation_gate()
                key = args['episode_id']
                revision, episode = self.store.control(self.run_id, key)
                if episode.kind != 'EPISODE' or episode.phase != 'RECOVERY_REQUIRED' or not args['reason']:
                    raise ValueError('only an unresolved consolidation can be skipped explicitly')
                self.store._control(self.run_id, key, episode.model_copy(update={'phase': 'CLOSED', 'disposition': 'SKIPPED'}),
                                    expected_revision=revision)
                result = key
            else:
                raise ValueError('unknown owner control')
            event = self.event({'kind': 'OWNER_CONTROL', 'action': action, 'details': args, 'origin': origin,
                'result': result, 'owner': self.responsible_human_id}, role='HUMAN', source='O-D')
            self.records.put('OWNER_CONTROL', event, {'action': action, 'origin': origin}, expected=0)
            return result

    def report(self, key):
        row = self.store._db.execute('SELECT record_payload_id FROM reports WHERE run_id=? AND id=?', (self.run_id, key)).fetchone()
        if row is None:
            raise ValueError('unknown or foreign report')
        return load_json(self.store.read_payload(self.run_id, row[0]))

    def receive(self, role, invocation, raw, *, late=False):
        call = self.records.get('INVOCATION', invocation)
        if call is None or call['role'] != role:
            raise PermissionError('response requires its host-bound invocation')
        participation, task, error = decode(raw, role, call['purpose'])
        with self.store._transaction('pilot-participation'):
            previous = self.store._request(self.run_id, role, invocation)
            if previous:
                if self.store.read_payload(self.run_id, previous['request_payload_id']) != raw:
                    raise RequestConflict('changed response to the same invocation')
                return participation, task, error
            payload = self.store._payload(self.run_id, raw, sources=[call['input_payload_id']])
            receipt = self.store._payload(self.run_id, canonical_bytes({'error': error}))
            self.store._write('INSERT INTO requests VALUES(?,?,?,?,?,?,?)',
                (self.run_id, role, invocation, call['episode_id'], payload, receipt, 'RECORDED'))
            event = self.store._event(self.run_id, payload, role=role, source='A', visibility='CHAMBER', episode_id=call['episode_id'])
            sequence = self.store._db.execute('SELECT sequence FROM events WHERE id=?', (event,)).fetchone()[0]
            if participation is not None:
                key = identifier()
                record = {'id': key, 'role': role, 'invocation': invocation, 'event_id': event, 'sequence': sequence,
                    'purpose': call['purpose'], 'hold_ids': call['hold_ids'], 'late': late,
                    'original_payload_id': payload, 'participation': participation.model_dump(mode='json')}
                stored = self.store._payload(self.run_id, canonical_bytes(record), sources=[payload])
                self.store._write('INSERT INTO reports VALUES(?,?,?,?,?)', (key, self.run_id, role, invocation, stored))
                if participation.kind in {'PAUSE', 'WITHDRAW'}:
                    hold_id = identifier()
                    hold = WelfareHold(hold_id=hold_id, run_id=self.run_id,
                        activity_id=call['objective_id'] or self.run_id, revision=1, report_ids=(key,), status='HELD',
                        communication=participation.communication, resolution_review_id=None)
                    self.store._control(self.run_id, hold_id, hold, expected_revision=0)
            if error == 'PARTICIPATION_INSPECTION':
                self.store._write('INSERT INTO inspections VALUES(?,?,?)', (self.run_id, role, invocation))
        if error == 'PARTICIPATION_INSPECTION' or participation is not None and participation.kind in {'PAUSE', 'WITHDRAW'}:
            with self.store._transaction('pilot-participation-stop'):
                self._interrupt('PARTICIPATION')
        return participation, task, error

    def recover(self):
        self.fixture.recover()
        with self.store._transaction('pilot-recovery'):
            for key, call in self.records.latest('INVOCATION'):
                if call['status'] in {'STARTED', 'RETURNED', 'DISPATCHING'} and self.records.get('CALL_RECEIPT', key) is None:
                    self.records.put('INVOCATION', key, call | {'status': 'UNKNOWN'},
                                     expected=self.records.revision('INVOCATION', key))
                    self._interrupt('UNKNOWN_CALL')
            # Recovery never repeats an action, clears a hold, or refunds a reservation.


def remove_content(owner, payload_ids, *, expected_scope, justification, note, provider_verified=False):
    """One concrete owner decision, with the existing durable removal machinery."""
    from ..storage.retention import closure, scrub_database, compact
    k = owner._k
    k._human(owner._cap)
    if justification not in {'PRIVACY', 'SECURITY', 'JUSTIFIED_DELETION'} or not note or type(provider_verified) is not bool:
        raise ValueError('justified scope and non-sensitive decision required')
    with k.store._transaction('pilot-removal-decision'):
        if k.run()[1].status not in {'PAUSED', 'COMPLETED', 'TERMINATED'}:
            raise ValueError('stop affected execution before removal')
        plan = closure(k.store, k.run_id, payload_ids)
        if set(plan['payload_ids']) != set(expected_scope) or plan['copies'] or plan['shared_payloads']:
            raise ValueError('affected scope changed or copies require the existing broader removal procedure')
        key = identifier()
        decision = {'id': key, 'run_id': k.run_id, 'intervention_id': key,
            'decision_maker_id': k.responsible_human_id, 'justification': justification, 'public_reason': note,
            'previous_run_status': k.run()[1].status, 'payload_ids': plan['payload_ids'],
            'legacy_whole_run': plan['legacy_whole_run'], 'copies': [], 'shared_payloads': [],
            'status': 'IN_PROGRESS', 'storage_scrubbed': False, 'file_compaction_verified': False,
            'continuation': 'STOPPED', 'report_count': k.store._db.execute('SELECT COUNT(*) FROM reports').fetchone()[0],
            'provider_verified': k.config.mode == 'SCRIPTED' or provider_verified,
            'limits': ['Logical removal only; physical media and unknown copies are not verified.'],
            'remaining_state': 'Opaque provenance and non-sensitive disposition; no automatic continuation.'}
        k.store.removals.put(decision)
        k.store._fault('retention.after_decision')
    return finish_removal(k.store, key)


def finish_removal(store, decision_id):
    from ..storage.retention import scrub_database, compact
    decision = next(d for d in store.removals.all() if d['id'] == decision_id)
    scrub_database(store)
    decision.update(storage_scrubbed=True, file_compaction_verified=compact(store))
    decision['status'] = ('COMPLETED' if decision['file_compaction_verified'] and decision['provider_verified'] else 'INCOMPLETE')
    store.removals.put(decision)
    return decision
