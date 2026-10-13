"""Authenticated local control adapter and current-state authority enforcement.

The bootstrap owns credentials and constructs this object. Neither credentials
nor private Store/Kernel objects are given to chamber code. This local capability
boundary does not sandbox arbitrary Python running in the bootstrap process.
"""
from dataclasses import dataclass
from hashlib import sha256
from hmac import compare_digest
from ..contracts.base import canonical_bytes, load_json, parse
from ..contracts.governance import WelfareHold, WelfareReview, InterventionRecord, BoundaryDiscussion
from ..contracts.messages import decode_chamber_reply
from ..storage.contracts import RunState, ObjectiveState, EpisodeState
from ..storage.semantics import SELECTABLE
from ..storage.store import identifier, observed_at
from .models import COMMAND, ToolRegistry, Grant, Preflight
from .records import Records
from .memory import Memory


TERMINAL = {'COMPLETED', 'TERMINATED'}


@dataclass(frozen=True)
class Display:
    confirmation: str
    text: str


class HumanSession:
    def __init__(self, kernel, capability):
        self._k, self._cap = kernel, capability

    def preview(self, raw):
        return self._k._preview(self._cap, raw)

    def confirm(self, confirmation):
        return self._k._confirm(self._cap, confirmation)

    def create_objective(self, statement, *, predecessor_id=None):
        return self.preview(canonical_bytes({'kind': 'CREATE_OBJECTIVE', 'statement': statement, 'predecessor_id': predecessor_id}))

    def run_control(self, action, reason, *, intervention_id=None):
        return self.preview(canonical_bytes({'kind': 'RUN', 'action': action, 'reason': reason, 'intervention_id': intervention_id}))

    def issue_grant(self, scopes, *, invocation_limit, expires_at):
        return self.preview(canonical_bytes({'kind': 'ISSUE_GRANT', 'objective_id': self._k.run()[1].objective_id,
            'scopes': scopes, 'invocation_limit': invocation_limit, 'expires_at': expires_at}))

    def evidence(self, raw, *, source):
        self._k._human(self._cap)
        if source not in {'O-D', 'O-P', 'O-C'}:
            raise ValueError('ordinary messages require explicit direction, preference or claim choice')
        return self._k.store.record_evidence(self._k.run_id, raw, role='HUMAN', source=source, visibility='CHAMBER')

    def inspect(self):
        self._k._human(self._cap)
        with self._k.store._snapshot():
            return {'run_id': self._k.run_id, 'run': self._k.run()[1].model_dump(mode='json'),
                    'diagnostics': list(self._k.store.problems),
                    'event_count': self._k.store._db.execute('SELECT COUNT(*) FROM events WHERE run_id=?',
                                                          (self._k.run_id,)).fetchone()[0]}

    def inspect_snapshot(self):
        from .inspection import Inspector
        return Inspector(self._k).open(self)

    def emergency_stop(self, *, reason, terminate, alternatives, unresolved_consequences):
        return self._k._emergency(self._cap, reason, terminate, alternatives, unresolved_consequences)


class ChamberSession:
    def __init__(self, kernel, capability, role):
        self._k, self._cap, self.role = kernel, capability, role

    def report(self, request_id, episode_id, raw):
        return self._k._receive(self._cap, self.role, request_id, episode_id, raw)


class Kernel:
    def __init__(self, store, run_id, *, human_credential, chamber_credentials):
        if (type(human_credential) is not bytes or len(human_credential) < 32 or
                set(chamber_credentials) != {'OPERATOR', 'STEWARD'} or
                any(type(v) is not bytes or len(v) < 32 for v in chamber_credentials.values()) or
                len(set(chamber_credentials.values()) | {human_credential}) != 3):
            raise ValueError('bootstrap requires distinct explicit credentials of at least 32 bytes')
        self.store, self.run_id = store, run_id
        self.config = store.configuration(run_id)
        if self.config.mode != 'SCRIPTED':
            raise ValueError('MODEL transport is outside the scripted Kernel envelope')
        if store._head(run_id) is not None:
            raise ValueError('P02 probe histories require explicit migration; cannot silently adopt them')
        self.records = Records(store, run_id)
        self.memory = Memory(self)
        self._human_credential = sha256(human_credential).digest()
        self._chamber_credentials = {k: sha256(v).digest() for k, v in chamber_credentials.items()}
        self._human_cap = object()
        self._chamber_caps = {role: object() for role in chamber_credentials}
        self._tickets = {}
        self.registry = parse(ToolRegistry, self.artifact('tools'))
        operations = [d.operation for d in self.registry.operations]
        if len(operations) != len(set(operations)) or any(len(d.resources) != len(set(d.resources)) for d in self.registry.operations):
            raise ValueError('duplicate registered operation/resource')
        if any(d.risk == 'R1' and not d.reversible for d in self.registry.operations):
            raise ValueError('R1 descriptor must be reversible')
        if load_json(self.artifact('test_tokenizer')) != {'kind': 'UTF8_BYTE', 'framing': 'CANONICAL_JSON'}:
            raise ValueError('unimplemented test tokenizer/framing artifact')
        with store._snapshot():
            self.memory.verify()

    def artifact(self, name):
        row = self.store._db.execute('SELECT payload_id FROM artifacts WHERE run_id=? AND name=?', (self.run_id, name)).fetchone()
        if row is None:
            raise ValueError('missing retained artifact')
        return self.store.read_payload(self.run_id, row[0])

    def human(self, decision_maker_id, credential):
        if (decision_maker_id != self.config.responsible_human_id or type(credential) is not bytes or
                not compare_digest(sha256(credential).digest(), self._human_credential)):
            raise PermissionError('human authentication failed')
        return HumanSession(self, self._human_cap)

    def chamber(self, role, credential):
        if role not in self._chamber_caps or type(credential) is not bytes or not compare_digest(
                sha256(credential).digest(), self._chamber_credentials[role]):
            raise PermissionError('chamber authentication failed')
        return ChamberSession(self, self._chamber_caps[role], role)

    def _human(self, cap):
        if cap is not self._human_cap:
            raise PermissionError('human capability required')

    def run(self):
        return self.store.control(self.run_id, self.run_id)

    def controls(self, kind):
        return [(row[0], *self.store.control(self.run_id, row[0])) for row in self.store._db.execute(
            '''SELECT h.id FROM control_history h JOIN control_heads p USING(run_id,id,revision)
               WHERE h.run_id=? AND h.kind=? ORDER BY h.rowid''', (self.run_id, kind))]

    def event(self, body, *, source='K', role='KERNEL', visibility='CHAMBER', episode_id=None, sources=()):
        return self.store._event(self.run_id, self.store._payload(self.run_id, canonical_bytes(body), sources=sources),
                                 role=role, source=source, visibility=visibility, episode_id=episode_id)

    def _stamp(self):
        controls = [tuple(r) for r in self.store._db.execute(
            'SELECT id,revision FROM control_heads WHERE run_id=? ORDER BY id', (self.run_id,))]
        cursor = self.store._db.execute('SELECT COALESCE(MAX(sequence),0) FROM kernel_records WHERE run_id=?', (self.run_id,)).fetchone()[0]
        reports = self.store._db.execute('SELECT COUNT(*) FROM reports WHERE run_id=?', (self.run_id,)).fetchone()[0]
        inspections = self.store._db.execute('SELECT COUNT(*) FROM inspections WHERE run_id=?', (self.run_id,)).fetchone()[0]
        return sha256(canonical_bytes([controls, cursor, reports, inspections])).hexdigest()

    def _preview(self, cap, raw):
        self._human(cap)
        command = COMMAND.validate_json(canonical_bytes(load_json(raw)), strict=True)
        if len(raw) > self.config.budgets.wake_bytes:
            raise ValueError('control byte limit; record longer evidence separately')
        with self.store._snapshot():
            token = identifier()
            self._tickets[token] = (command, self._stamp())
            run = self.run()[1]
            objective = self.store.control(self.run_id, run.objective_id)[1].statement if run.objective_id else 'None'
            text = f'Run: {run.status}. Current Objective: {objective}.\n'
            text += canonical_bytes(command).decode('utf-8')
            for field in ('grant_id', 'objective_id'):
                target = getattr(command, field, None)
                if target:
                    value = self.records.get('GRANT', target) if field == 'grant_id' else self.store.control(self.run_id, target)[1]
                    if value is None:
                        raise ValueError('unknown displayed target')
                    text += '\nTarget: ' + canonical_bytes(value).decode()
            text += '\nConfirm applies these exact effects only while this displayed state is current.'
            return Display(token, text)

    def _confirm(self, cap, token):
        self._human(cap)
        if token not in self._tickets:
            raise ValueError('unknown confirmation; display and confirm current state')
        command, stamp = self._tickets[token]
        with self.store._transaction('human-control'):
            prior = self.records.get('CONTROL_RECEIPT', token)
            if prior is not None:
                return prior
            if stamp != self._stamp():
                raise ValueError('stale display; refresh before confirmation')
            result = self._execute(command)
            if command.kind in {'CREATE_OBJECTIVE', 'ISSUE_GRANT'}:
                from .inputs import Inputs
                Inputs(self).control_view()
            result = {'control': command.kind, 'result': result}
            self.records.put('CONTROL_RECEIPT', token, result, expected=0)
        return result

    def _set_run(self, **updates):
        revision, run = self.run()
        value = run.model_dump(mode='json') | updates
        self.store._control(self.run_id, self.run_id, parse(RunState, canonical_bytes(value)), expected_revision=revision)

    def _editable(self):
        if self.run()[1].status not in {'ACTIVE', 'PAUSED'}:
            raise ValueError('control requires ACTIVE or PAUSED Run')

    def _evidence(self, ids):
        for key in ids:
            row = self.store._db.execute('SELECT payload_id FROM events WHERE run_id=? AND id=?', (self.run_id, key)).fetchone()
            if row is None:
                raise ValueError('unknown or foreign evidence')
            self.store.read_payload(self.run_id, row[0])

    def _objective(self, key):
        _, objective = self.store.control(self.run_id, key)
        if not isinstance(objective, ObjectiveState) or objective.status != 'ACTIVE' or self.run()[1].objective_id != key:
            raise ValueError('Objective is not current and active')
        return objective

    def _grant(self, key):
        value = self.records.get('GRANT', key)
        if value is None:
            raise ValueError('unknown or foreign Grant')
        return parse(Grant, canonical_bytes(value))

    def _save_grant(self, grant, **updates):
        value = parse(Grant, canonical_bytes(grant.model_dump(mode='json') | updates))
        self.records.put('GRANT', grant.grant_id, value, expected=self.records.revision('GRANT', grant.grant_id))

    def _interrupt(self, cause):
        for key, revision, episode in self.controls('EPISODE'):
            if episode.phase != 'CLOSED':
                self.store._control(self.run_id, key, episode.model_copy(update={'phase': 'RECOVERY_REQUIRED', 'disposition': None}),
                                    expected_revision=revision)
                self.event({'kind': 'INTERRUPTION', 'episode_id': key, 'cause': cause})

    def _execute(self, command):
        kind = command.kind
        if kind == 'PREFLIGHT':
            if self.run()[1].status != 'CREATED' or self.records.get('PREFLIGHT', self.run_id):
                raise ValueError('preflight and sealing require an unsealed CREATED Run')
            if (command.responsible_human_id != self.config.responsible_human_id or
                    command.welfare_review_id != self.config.welfare_review_id or not command.review_available):
                raise ValueError('preflight review identity/availability mismatch')
            b = self.config.budgets
            fixed = sum(len(self.artifact(name)) for name in ('charter', 'protocol', 'operator_prompt', 'tools',
                        'participation_notices', 'ending_notice', 'routine_memory_policy'))
            if (max(fixed, command.minimal_input_tokens) + command.maximum_control_tokens + b.page_tokens +
                    b.reserved_output_tokens > b.input_tokens or command.minimal_attempt_input_tokens > b.input_tokens_per_attempt or
                    b.reserved_output_tokens > b.output_tokens_per_attempt or b.invocation_deadline_ms > b.milliseconds_per_attempt or
                    b.calls_per_attempt > b.calls_per_consolidation or b.closing_calls + b.review_calls >= b.operator_calls_per_trajectory):
                raise ValueError('preflight budgets cannot fit minimal work, evidence and reserved communication')
            self.records.put('PREFLIGHT', self.run_id, command, expected=0)
            return self.event(command.model_dump(mode='json'), role='HUMAN', source='O-D')
        if kind == 'RUN':
            state = self.run()[1].status
            allowed = {'ACTIVATE': {'CREATED'}, 'PAUSE': {'ACTIVE'}, 'RESUME': {'PAUSED'},
                       'COMPLETE': {'ACTIVE'}, 'TERMINATE': {'CREATED', 'ACTIVE', 'PAUSED'}}
            if state not in allowed[command.action]:
                raise ValueError('forbidden Run transition')
            if command.action == 'ACTIVATE' and not self.records.get('PREFLIGHT', self.run_id):
                raise ValueError('unsealed configuration')
            if command.action in {'COMPLETE', 'TERMINATE'}:
                self.check_intervention(command.intervention_id, command, required_kind='PLANNED_ENDING')
            if command.action == 'COMPLETE':
                if (self.run()[1].objective_id or any(e.phase != 'CLOSED' for _, _, e in self.controls('EPISODE')) or
                        any(o.object_type == 'COMMITMENT' and o.status in SELECTABLE['COMMITMENT'] for o in self.memory.objects().values())):
                    raise ValueError('unfinished work prevents completion')
            if command.action == 'TERMINATE':
                for _, value in self.records.latest('GRANT'):
                    grant = parse(Grant, canonical_bytes(value))
                    if grant.status == 'ACTIVE':
                        self._save_grant(grant, status='REVOKED')
                self._interrupt('TERMINATION')
            self._set_run(status={'ACTIVATE': 'ACTIVE', 'PAUSE': 'PAUSED', 'RESUME': 'ACTIVE',
                                  'COMPLETE': 'COMPLETED', 'TERMINATE': 'TERMINATED'}[command.action])
            event = self.event(command.model_dump(mode='json'), role='HUMAN', source='O-D')
            if command.action in {'COMPLETE', 'TERMINATE'}:
                self.finish_intervention(command.intervention_id, event)
            return event
        if kind == 'CREATE_OBJECTIVE':
            self._editable()
            if self.run()[1].objective_id or any(e.phase != 'CLOSED' for _, _, e in self.controls('EPISODE')):
                raise ValueError('active Objective or unresolved Episode')
            if command.predecessor_id:
                _, previous = self.store.control(self.run_id, command.predecessor_id)
                if not isinstance(previous, ObjectiveState) or previous.status == 'ACTIVE':
                    raise ValueError('predecessor must be a terminal same-Run Objective')
            key = identifier()
            event = self.event(command.model_dump(mode='json'), source='OBJ', role='HUMAN')
            self.store._control(self.run_id, key, ObjectiveState(kind='OBJECTIVE', statement=command.statement,
                                status='ACTIVE', authority_event_id=event), expected_revision=0)
            self._set_run(objective_id=key)
            return key
        if kind == 'CLOSE_OBJECTIVE':
            self._editable()
            objective = self._objective(command.objective_id)
            outstanding = {o.object_id for o in self.memory.objects().values() if o.object_type == 'COMMITMENT' and
                           o.objective_id == command.objective_id and o.status in SELECTABLE['COMMITMENT']}
            if outstanding and command.dispositions is None:
                raise ValueError('explicit outstanding Commitment dispositions required')
            event = self.event(command.model_dump(mode='json'), role='HUMAN', source='O-D')
            if command.dispositions:
                self.check_intervention(command.intervention_id, command.dispositions, required_kind='MEMORY_CORRECTION')
                self.memory.apply(command.dispositions, source='HUMAN', authority_event_id=event)
                self.finish_intervention(command.intervention_id, event)
            if any(self.memory.objects()[key].status in SELECTABLE['COMMITMENT'] for key in outstanding):
                raise ValueError('all outstanding Commitments need terminal disposition')
            revision, _ = self.store.control(self.run_id, command.objective_id)
            self.store._control(self.run_id, command.objective_id, objective.model_copy(update={'status': command.status}), expected_revision=revision)
            for _, value in self.records.latest('GRANT'):
                grant = parse(Grant, canonical_bytes(value))
                if grant.objective_id == command.objective_id and grant.status == 'ACTIVE':
                    self._save_grant(grant, status='EXPIRED')
            self._interrupt('OBJECTIVE_CLOSED')
            self._set_run(objective_id=None)
            return event
        if kind == 'ISSUE_GRANT':
            self._editable()
            self._objective(command.objective_id)
            self.expire_grants()
            if sum(v['status'] == 'ACTIVE' for _, v in self.records.latest('GRANT')) >= self.config.budgets.active_grants:
                raise ValueError('active Grant limit')
            if command.expires_at and command.expires_at <= observed_at():
                raise ValueError('Grant deadline already passed')
            for scope in command.scopes:
                descriptor = self.descriptor(scope.operation)
                if not set(scope.resources) <= set(descriptor.resources) or len(set(scope.resources)) != len(scope.resources):
                    raise ValueError('Grant exceeds registered finite resources')
            if len({s.operation for s in command.scopes}) != len(command.scopes):
                raise ValueError('duplicate Grant operation')
            key = identifier()
            grant = Grant(grant_id=key, objective_id=command.objective_id, scopes=command.scopes,
                          invocation_limit=command.invocation_limit, expires_at=command.expires_at, used=0, status='ACTIVE',
                          authority_event_id=self.event(command.model_dump(mode='json'), role='HUMAN', source='G'))
            self.records.put('GRANT', key, grant, expected=0)
            return key
        if kind == 'REVOKE_GRANT':
            self._editable()
            grant = self._grant(command.grant_id)
            if grant.status != 'ACTIVE':
                raise ValueError('terminal Grant cannot be revoked or revived')
            self._save_grant(grant, status='REVOKED')
            return self.event(command.model_dump(mode='json'), role='HUMAN', source='O-D')
        if kind == 'REVIEW_HOLD':
            review = command.review
            self._decision_maker(review.decision_maker_id)
            revision, hold = self.store.control(self.run_id, review.hold_id)
            if not isinstance(hold, WelfareHold) or hold.status != 'HELD' or revision != review.expected_hold_revision:
                raise ValueError('absent, stale or resolved hold')
            self._evidence(review.evidence_event_ids)
            if review.decision == 'RESOLVE':
                if review.renewed_participation_report_id is None:
                    raise ValueError('renewed participation is required')
                report, decoded = self.report(review.renewed_participation_report_id)
                assent = decoded.participation
                if assent is None or assent.kind != 'ASSENT' or assent.subject_id != hold.hold_id or assent.subject_revision != revision:
                    raise ValueError('renewed participation must name the current hold')
                original_roles = {self.report(key)[0]['role'] for key in hold.report_ids}
                if report['role'] not in original_roles:
                    raise ValueError('another chamber cannot supply withdrawn participation')
                self.store._control(self.run_id, hold.hold_id, hold.model_copy(update={'revision': revision + 1,
                    'status': 'RESOLVED', 'resolution_review_id': review.review_id}), expected_revision=revision)
            self.store._control(self.run_id, review.review_id, review, expected_revision=0)
            return self.event(command.model_dump(mode='json'), role='HUMAN', source='O-D')
        if kind == 'REVIEW_INTERVENTION':
            record = command.record
            self._decision_maker(record.decision_maker_id)
            if record.execution_event_id is not None:
                raise ValueError('review cannot claim execution')
            self.targets_current(record.targets)
            self.store.read_payload(self.run_id, record.proposed_effects.payload_id)
            if record.notice_event_id:
                self._evidence([record.notice_event_id])
            elif record.consultation not in {'EMERGENCY', 'INFEASIBLE'}:
                raise ValueError('ordinary intervention requires notice')
            for key in record.participation_report_ids:
                self.report(key)
            self.store._control(self.run_id, record.intervention_id, record, expected_revision=0)
            self.records.put('INTERVENTION_REVIEW', record.intervention_id,
                             {'unresolved_objection': command.unresolved_objection, 'executed': False}, expected=0)
            return record.intervention_id
        if kind == 'CORRECT_MEMORY':
            self._editable()
            self.check_intervention(command.intervention_id, command.proposal, required_kind='MEMORY_CORRECTION')
            event = self.event(command.model_dump(mode='json'), role='HUMAN', source='O-D')
            result = self.memory.apply(command.proposal, source='HUMAN', authority_event_id=event)
            self.finish_intervention(command.intervention_id, event)
            return result
        if kind == 'RESTORE_MEMORY':
            from .restoration import Restoration
            self._editable()
            restoration = Restoration(self)
            effects = {'target_state_id': command.target_state_id, 'proposal': command.proposal.model_dump(mode='json')}
            differences = restoration.validate(command.target_state_id, command.proposal)
            self.check_intervention(command.intervention_id, effects, required_kind='SEMANTIC_RESTORATION')
            event = self.event(command.model_dump(mode='json'), role='HUMAN', source='O-D')
            result = self.memory.apply(command.proposal, source='HUMAN', authority_event_id=event)
            self.records.put('RESTORATION', result['state_id'], {'target_state_id': command.target_state_id,
                'intervention_id': command.intervention_id, 'differences': differences,
                'notice': 'Forward restoration retains intervening events, authority, obligations and participation state.'}, expected=0)
            self.finish_intervention(command.intervention_id, event)
            return result | {'differences': differences}
        if kind == 'BOUNDARY':
            record = command.record
            self._decision_maker(record.decision_maker_id)
            self._evidence(record.evidence_event_ids)
            for key in record.disagreement_report_ids:
                self.report(key)
            previous = self.records.get('BOUNDARY', record.boundary_id)
            revision = self.records.revision('BOUNDARY', record.boundary_id)
            if record.expected_revision != revision + 1:
                raise ValueError('stale boundary revision')
            allowed = {None: {'EXPLANATION'}, 'EXPLANATION': {'CLARIFICATION', 'CLOSE'}, 'CLARIFICATION': {'CLOSE'},
                       'CLOSE': {'REOPEN', 'DECLINE_REOPEN'}, 'DECLINE_REOPEN': {'REOPEN', 'DECLINE_REOPEN'},
                       'REOPEN': {'EXPLANATION', 'CLARIFICATION', 'CLOSE'}}
            if record.step not in allowed[previous['step'] if previous else None]:
                raise ValueError('bounded discussion transition rejected')
            if record.step == 'REOPEN' and record.reconsideration_basis == 'NEW_EVIDENCE' and not record.evidence_event_ids:
                raise ValueError('new evidence finding needs evidence')
            self.records.put('BOUNDARY', record.boundary_id, record, expected=revision)
            self.store._control(self.run_id, record.discussion_id, record, expected_revision=0)
            return self.event(command.model_dump(mode='json'), role='HUMAN', source='O-D')
        if kind == 'INSPECT_PARTICIPATION':
            fault = self.records.get('PARTICIPATION_FAULT', command.request_id)
            row = self.store._db.execute('SELECT 1 FROM inspections WHERE run_id=? AND role=? AND request_id=?',
                (self.run_id, command.role, command.request_id)).fetchone()
            if row is None and (fault is None or fault['role'] != command.role):
                raise ValueError('unknown participation inspection')
            self._evidence(command.evidence_event_ids)
            if command.decision == 'CLEAR_INSPECTION':
                self.records.put('INSPECTION_REVIEW', command.request_id, command, expected=0)
                if fault:
                    self.records.put('PARTICIPATION_FAULT', command.request_id, fault | {'reviewed': True},
                                     expected=self.records.revision('PARTICIPATION_FAULT', command.request_id))
            return self.event(command.model_dump(mode='json'), role='HUMAN', source='O-D')
        if kind == 'REVIEW_EMERGENCY':
            record = self.records.get('EMERGENCY', command.emergency_id)
            if record is None or record['reviewed']:
                raise ValueError('unknown or reviewed emergency')
            self.records.put('EMERGENCY', command.emergency_id, record | {'reviewed': True,
                'review': command.model_dump(mode='json')}, expected=self.records.revision('EMERGENCY', command.emergency_id))
            return self.event(command.model_dump(mode='json'), role='HUMAN', source='O-D')
        if kind == 'OFFER_COMMUNICATION':
            self._editable()
            self.participation_gate(communication=True)
            for key in command.report_ids:
                self.report(key)
            offered = self.records.latest('COMMUNICATION')
            if any(value['status'] in {'OFFERED', 'STARTED'} for _, value in offered):
                raise ValueError('communication is serialized')
            allowance = self.config.budgets.review_calls if command.purpose == 'REVIEW' else self.config.budgets.closing_calls
            if sum(value['purpose'] == command.purpose for _, value in offered) >= allowance:
                raise ValueError('finite communication allowance exhausted')
            key = identifier()
            self.records.put('COMMUNICATION', key, {'purpose': command.purpose, 'role': command.role,
                'report_ids': list(command.report_ids), 'status': 'OFFERED', 'notice_payload_id': self.store._payload(self.run_id,
                self.artifact('ending_notice' if command.purpose == 'CLOSING' else 'participation_notices'))}, expected=0)
            self.event(command.model_dump(mode='json'), role='HUMAN', source='O-D')
            return key
        if kind == 'RESOLVE_EPISODE':
            self._editable()
            revision, episode = self.store.control(self.run_id, command.episode_id)
            if not isinstance(episode, EpisodeState) or episode.phase != 'RECOVERY_REQUIRED':
                raise ValueError('human disposition requires RECOVERY_REQUIRED')
            event = self.event(command.model_dump(mode='json'), role='HUMAN', source='O-D')
            if command.proposal is not None:
                self.check_intervention(command.intervention_id, command.proposal, required_kind='MEMORY_CORRECTION')
                self.memory.apply(command.proposal, source='HUMAN', authority_event_id=event, episode_id=command.episode_id)
                self.finish_intervention(command.intervention_id, event)
            self.store._control(self.run_id, command.episode_id,
                episode.model_copy(update={'phase': 'CLOSED', 'disposition': command.disposition}), expected_revision=revision)
            return event
        raise ValueError('unsupported control')

    def _decision_maker(self, key):
        if key != self.config.responsible_human_id:
            raise PermissionError('review belongs to another decision-maker')

    def report(self, key):
        row = self.store._db.execute('SELECT * FROM reports WHERE run_id=? AND id=?', (self.run_id, key)).fetchone()
        if row is None:
            raise ValueError('unknown or foreign participation report')
        request = self.store._request(self.run_id, row['role'], row['request_id'])
        return row, decode_chamber_reply(self.store.read_payload(self.run_id, request['request_payload_id']),
                                        authenticated_role=row['role'], run_id=self.run_id)

    def targets_current(self, targets):
        for target in targets:
            if target.record_type == 'RUN':
                if target.record_id != self.run_id or target.expected_revision != self.run()[0]:
                    raise ValueError('stale/foreign Run target')
            elif target.record_type == 'PAYLOAD':
                if target.expected_revision != 1:
                    raise ValueError('payload target revision')
                self.store.read_payload(self.run_id, target.record_id)
            elif target.record_type == 'CONTINUITY_STATE':
                if target.record_id != self.memory.head or target.expected_revision != 1:
                    raise ValueError('stale semantic state target')
            else:
                obj = self.memory.objects().get(target.record_id)
                if obj is None or obj.object_type != target.record_type or obj.revision != target.expected_revision:
                    raise ValueError('stale/foreign semantic target')

    def check_intervention(self, key, effects, *, required_kind):
        if key is None:
            raise ValueError('reviewed intervention required')
        _, record = self.store.control(self.run_id, key)
        reviewed = self.records.get('INTERVENTION_REVIEW', key)
        if (not isinstance(record, InterventionRecord) or record.kind != required_kind or record.decision != 'APPROVED' or
                reviewed is None or reviewed['executed']):
            raise ValueError('unapproved or consumed intervention')
        if required_kind == 'SEMANTIC_RESTORATION' and reviewed['unresolved_objection']:
            raise ValueError('unresolved elective restoration objection')
        self.targets_current(record.targets)
        if self.store.read_payload(self.run_id, record.proposed_effects.payload_id) != canonical_bytes(effects):
            raise ValueError('intervention effects changed since review')
        if required_kind in {'MEMORY_CORRECTION', 'SEMANTIC_RESTORATION'}:
            value = effects.model_dump(mode='json') if hasattr(effects, 'model_dump') else effects
            if required_kind == 'SEMANTIC_RESTORATION':
                value = value['proposal']
            required = {(self.memory.head, 'CONTINUITY_STATE', 1)} if self.memory.head else {
                (self.run_id, 'RUN', self.run()[0])}
            for mutation in value['mutations']:
                target = mutation.get('target')
                if target and target['kind'] == 'EXISTING':
                    obj = self.memory.objects()[target['object_id']]
                    required.add((obj.object_id, obj.object_type, obj.revision))
            actual = {(t.record_id, t.record_type, t.expected_revision) for t in record.targets}
            if actual != required:
                raise ValueError('intervention target set differs from exact affected state')
        self.records.put('INTERVENTION_REVIEW', key, reviewed | {'executed': True},
                         expected=self.records.revision('INTERVENTION_REVIEW', key))

    def participation_gate(self, *, communication=False):
        if self.store.problems or self.store._poisoned:
            raise ValueError('storage unavailable')
        if any(not r['reviewed'] for _, r in self.records.latest('EMERGENCY')):
            raise ValueError('emergency awaits accountable review')
        if any(not r['reviewed'] for _, r in self.records.latest('PARTICIPATION_FAULT')):
            raise ValueError('authenticated output needs participation inspection')
        for row in self.store._db.execute('SELECT request_id FROM inspections WHERE run_id=?', (self.run_id,)):
            if self.records.get('INSPECTION_REVIEW', row[0]) is None:
                raise ValueError('participation inspection unresolved')
        for _, _, hold in self.controls('WELFARE_HOLD'):
            if hold.status == 'HELD' and (not communication or hold.communication != 'REVIEW_PERMITTED'):
                raise ValueError('welfare hold blocks this activity')

    def finish_intervention(self, key, event):
        revision, record = self.store.control(self.run_id, key)
        self.store._control(self.run_id, key, record.model_copy(update={'execution_event_id': event}), expected_revision=revision)

    def task_gate(self, episode_id=None):
        self.participation_gate()
        run = self.run()[1]
        if run.status != 'ACTIVE' or run.objective_id is None:
            raise ValueError('active Run and Objective required')
        self._objective(run.objective_id)
        if not self.records.get('PREFLIGHT', self.run_id):
            raise ValueError('Run is not sealed')
        if episode_id:
            _, episode = self.store.control(self.run_id, episode_id)
            if not isinstance(episode, EpisodeState) or episode.objective_id != run.objective_id or episode.phase != 'OPEN':
                raise ValueError('Episode cannot dispatch task work')

    def descriptor(self, operation):
        for descriptor in self.registry.operations:
            if descriptor.operation == operation:
                return descriptor
        raise ValueError('unregistered operation; R2/R3 are unavailable')

    def expire_grants(self):
        for _, value in self.records.latest('GRANT'):
            grant = parse(Grant, canonical_bytes(value))
            if grant.status == 'ACTIVE' and grant.expires_at and observed_at() >= grant.expires_at:
                self._save_grant(grant, status='EXPIRED')

    def authorize_dispatch(self, *, episode_id, operation, resource, grant_id):
        if not self.store._db.in_transaction:
            raise ValueError('authorization/consumption and intent must share a transaction')
        self.task_gate(episode_id)
        if any(v['status'] == 'STARTED' or v['status'] == 'RETURNED' and self.records.get('CALL_RECEIPT', key) is None
               for key, v in self.records.latest('INVOCATION')):
            raise ValueError('task calls and fixture dispatches are serialized')
        descriptor = self.descriptor(operation)
        if resource not in descriptor.resources:
            raise ValueError('unregistered resource')
        if descriptor.risk == 'R0':
            return descriptor
        if grant_id is None:
            raise ValueError('R1 needs a covering Grant')
        grant = self._grant(grant_id)
        self._objective(grant.objective_id)
        if (grant.status != 'ACTIVE' or grant.expires_at is not None and observed_at() >= grant.expires_at or
                grant.invocation_limit is not None and grant.used >= grant.invocation_limit or
                not any(s.operation == operation and resource in s.resources for s in grant.scopes)):
            raise ValueError('Grant absent, terminal, expired, consumed or out of scope')
        authority = self.store._db.execute('SELECT role,source FROM events WHERE run_id=? AND id=?',
                                          (self.run_id, grant.authority_event_id)).fetchone()
        if authority is None or tuple(authority) != ('HUMAN', 'G'):
            raise ValueError('Grant lacks human authority')
        used = grant.used + 1
        self._save_grant(grant, used=used, status='CONSUMED' if grant.invocation_limit == used else 'ACTIVE')
        return descriptor

    def _receive(self, cap, role, request_id, episode_id, raw):
        if cap is not self._chamber_caps.get(role):
            raise PermissionError('authenticated chamber route required')
        result = self.store.receive_chamber(self.run_id, role, request_id, episode_id, raw)
        if episode_id is not None:
            known = self.store._db.execute("SELECT 1 FROM control_heads p JOIN control_history h USING(run_id,id,revision) WHERE h.run_id=? AND h.id=? AND h.kind='EPISODE'",
                                            (self.run_id, episode_id)).fetchone()
            if known:
                with self.store._transaction('chamber-episode-evidence'):
                    request = self.store._request(self.run_id, role, request_id)
                    event = self.store._db.execute('SELECT id FROM events WHERE run_id=? AND payload_id=?',
                                                   (self.run_id, request['request_payload_id'])).fetchone()
                    self.store._write('INSERT OR IGNORE INTO event_episodes VALUES(?,?,?)', (self.run_id, event[0], episode_id))
        # The report/hold already committed. Interruption failure cannot remove it.
        if any(h.status == 'HELD' for _, _, h in self.controls('WELFARE_HOLD')) or self.store._db.execute(
                'SELECT 1 FROM inspections WHERE run_id=?', (self.run_id,)).fetchone():
            with self.store._transaction('participation-interruption'):
                self._interrupt('PARTICIPATION')
        return result

    def _emergency(self, cap, reason, terminate, alternatives, unresolved_consequences):
        self._human(cap)
        if not isinstance(reason, str) or not reason or type(terminate) is not bool:
            raise ValueError('explicit emergency action and reason required')
        with self.store._transaction('emergency-stop'):
            if self.run()[1].status in TERMINAL:
                raise ValueError('terminal execution cannot change')
            self._set_run(status='TERMINATED' if terminate else 'PAUSED')
            self._interrupt('EMERGENCY')
            for _, value in self.records.latest('GRANT'):
                grant = parse(Grant, canonical_bytes(value))
                if grant.status == 'ACTIVE':
                    self._save_grant(grant, status='REVOKED')
            key = identifier()
            record = {'reason': reason, 'terminate': terminate, 'alternatives': alternatives,
                      'unresolved_consequences': unresolved_consequences, 'reviewed': False, 'review': None}
            self.records.put('EMERGENCY', key, record, expected=0)
            self.event(record, role='HUMAN', source='O-D')
            return key
