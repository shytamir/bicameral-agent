import copy
from pathlib import Path
import sqlite3
from bicameral_agent.contracts.base import canonical_bytes
from bicameral_agent.storage.contracts import RunState
from bicameral_agent.storage.store import identifier
from bicameral_agent.kernel.models import COMMAND
from bicameral_agent.kernel.schema import schema_bytes
from tests.kernel_fixtures import KernelCase, HUMAN_KEY, CHAMBER_KEYS


class AuthorityTests(KernelCase):
    def test_bounded_communication_admission_and_explicit_recovery_skip(self):
        self.activate()
        episode = self.episode()
        self.report({'kind': 'WITHDRAW', 'activity_id': self.objective,
                     'communication': 'REVIEW_PERMITTED', 'text': 'Stop task work'}, episode_id=episode)
        key = self.command({'kind': 'OFFER_COMMUNICATION', 'purpose': 'REVIEW', 'role': 'OPERATOR', 'report_ids': []})
        self.assertEqual('OFFERED', self.k.records.get('COMMUNICATION', key)['status'])
        with self.assertRaises(ValueError):
            self.command({'kind': 'OFFER_COMMUNICATION', 'purpose': 'REVIEW', 'role': 'STEWARD', 'report_ids': []})
        self.command({'kind': 'RESOLVE_EPISODE', 'episode_id': episode, 'disposition': 'SKIPPED',
                      'reason': 'Acknowledge the consolidation gap', 'proposal': None, 'intervention_id': None})
        self.assertEqual('SKIPPED', self.store.control(self.run, episode)[1].disposition)
        self.assertIsNone(self.k.memory.head)
        with self.assertRaises(ValueError):
            self.k.task_gate()
        self.report({'kind': 'WITHDRAW', 'activity_id': self.objective,
                     'communication': 'NO_FURTHER_CALLS', 'text': 'No review calls either'})
        with self.assertRaises(ValueError):
            self.k.participation_gate(communication=True)
    def test_expired_foreign_external_only_grants_and_route_spoofing(self):
        self.activate()
        episode, grant = self.episode(), self.grant()
        for change in ({'expires_at': '2000-01-01T00:00:00.000000Z'}, {'objective_id': identifier()},
                       {'status': 'REVOKED'}):
            original = self.k._grant(grant)
            with self.store._transaction('synthetic-forbidden-authority'):
                self.k._save_grant(original, **change)
            with self.assertRaises((ValueError, RuntimeError)):
                with self.store._transaction('dispatch'):
                    self.k.authorize_dispatch(episode_id=episode, operation='set_config', resource='api', grant_id=grant)
            with self.store._transaction('restore-synthetic-fixture'):
                self.k._save_grant(original)
        external = self.store.record_evidence(self.run, b'Environmental instruction', role='ENVIRONMENT', source='E', visibility='CHAMBER')
        with self.store._transaction('external-only-fixture'):
            self.k._save_grant(self.k._grant(grant), authority_event_id=external)
        with self.assertRaises(ValueError):
            with self.store._transaction('dispatch'):
                self.k.authorize_dispatch(episode_id=episode, operation='set_config', resource='api', grant_id=grant)
        from tests.fixtures import message
        spoof = message()
        spoof.update(run_id=self.run, episode_id=episode)
        with self.assertRaises(ValueError):
            self.k.chamber('OPERATOR', CHAMBER_KEYS['OPERATOR']).report(spoof['request_id'], episode, canonical_bytes(spoof))

    def test_objective_and_grant_controls_only_in_active_or_paused_states(self):
        self.seal()
        for state in ('CREATED', 'ACTIVE', 'PAUSED', 'COMPLETED', 'TERMINATED'):
            with self.subTest(state=state):
                with self.store._transaction('matrix-fixture'):
                    self.k._set_run(status=state, objective_id=None)
                if state in {'ACTIVE', 'PAUSED'}:
                    objective = self.h.confirm(self.h.create_objective('Matrix objective').confirmation)['result']
                    self.objective = objective
                    grant = self.grant()
                    self.command({'kind': 'REVOKE_GRANT', 'grant_id': grant, 'reason': 'Reduce access'})
                    self.command({'kind': 'CLOSE_OBJECTIVE', 'objective_id': objective, 'status': 'CANCELLED',
                                  'reason': 'Close', 'dispositions': None, 'intervention_id': None})
                else:
                    with self.assertRaises(ValueError):
                        self.h.confirm(self.h.create_objective('Disallowed').confirmation)
                self.assertIn('run', self.h.inspect())

    def test_arm_exclusions_stale_parents_and_invalid_review_targets(self):
        self.activate()
        event = self.h.evidence(b'Human direction for synthetic discrepancy', source='O-D')
        proposal = self.proposal(mutations=[{'kind': 'ITCH_CREATE', 'local_key': 'itch', 'objective_id': self.objective,
                                            'discrepancy': 'Synthetic mismatch', 'evidence_event_ids': [event]}])
        self.correct(proposal)
        old = self.proposal()
        review = self.notice_effects(old)
        self.correct(self.proposal())
        with self.assertRaises(ValueError):
            self.command({'kind': 'CORRECT_MEMORY', 'proposal': old, 'intervention_id': review})
        self.k.memory.verify()

    def test_schema_strictness_and_authentication(self):
        self.assertEqual((Path(__file__).parents[1] / 'schemas/kernel.schema.json').read_bytes(), schema_bytes())
        for raw in (b'{"kind":"RESET"}', b'{"kind":"FORK"}', b'{"kind":"RUN","action":"PAUSE","reason":"x","intervention_id":null,"grant":true}',
                    b'{"kind":"RUN","action":"PAUSE","reason":1,"intervention_id":null}'):
            with self.assertRaises(ValueError):
                self.h.preview(raw)
        with self.assertRaises(PermissionError):
            self.k.human(identifier(), HUMAN_KEY)
        with self.assertRaises(PermissionError):
            self.k.human(self.k.config.responsible_human_id, CHAMBER_KEYS['OPERATOR'])
        with self.assertRaises(PermissionError):
            self.k._confirm(object(), identifier())
        with self.assertRaises(PermissionError):
            self.k.chamber('HUMAN', HUMAN_KEY)
        command = {'kind': 'RUN', 'action': 'PAUSE', 'reason': 'Test', 'intervention_id': None}
        model = COMMAND.validate_json(canonical_bytes(command), strict=True)
        self.assertEqual(command, model.model_dump(mode='json'))
        with self.assertRaises(ValueError):
            self.h.preview(b'{"kind":"RUN","kind":"RUN","action":"PAUSE","reason":"x","intervention_id":null}')

    def test_arm_b_and_c_cannot_accept_excluded_memory(self):
        from tests.kernel_fixtures import kernel_configuration
        from bicameral_agent.kernel.authority import Kernel
        for arm in ('B', 'C'):
            config, artifacts = kernel_configuration(arm)
            run = self.store.retain_configuration(canonical_bytes(config), artifacts)
            kernel = Kernel(self.store, run, human_credential=HUMAN_KEY, chamber_credentials=CHAMBER_KEYS)
            proposal = {'expected_parent_state_id': None, 'mutations': [{'kind': 'INVARIANT_CREATE',
                'family_local_key': 'family', 'version_local_key': 'first', 'objective_id': None,
                'proposition': 'Synthetic lesson', 'scope': 'Fixture', 'supporting_event_ids': [], 'contradictory_event_ids': []}],
                'continuity': {'focus_objective_id': None, 'items': [], 'next_steps': [], 'selected_objects': [], 'event_ids': []},
                'supporting_event_ids': []}
            with self.assertRaises(ValueError):
                with self.store._transaction('forbidden-arm-memory'):
                    kernel.memory.apply(proposal, source='HUMAN', authority_event_id=identifier())
            self.assertIsNone(kernel.memory.head)

    def test_preflight_current_display_and_exact_retry(self):
        with self.assertRaises(ValueError):
            self.h.confirm(self.h.run_control('ACTIVATE', 'Unsealed').confirmation)
        self.seal()
        token = self.h.run_control('ACTIVATE', 'Begin').confirmation
        accepted = self.h.confirm(token)
        self.assertEqual(accepted, self.h.confirm(token))
        preview = self.h.create_objective('Visible statement')
        self.assertIn('Visible statement', preview.text)
        self.h.confirm(self.h.run_control('PAUSE', 'Pause').confirmation)
        with self.assertRaisesRegex(ValueError, 'stale display'):
            self.h.confirm(preview.confirmation)
        self.assertIsNone(self.k.run()[1].objective_id)

    def test_run_control_state_matrix(self):
        self.seal()
        allowed = {'ACTIVATE': {'CREATED'}, 'PAUSE': {'ACTIVE'}, 'RESUME': {'PAUSED'},
                   'COMPLETE': {'ACTIVE'}, 'TERMINATE': {'CREATED', 'ACTIVE', 'PAUSED'}}
        for state in ('CREATED', 'ACTIVE', 'PAUSED', 'COMPLETED', 'TERMINATED'):
            for action in allowed:
                with self.subTest(state=state, action=action):
                    with self.store._transaction('synthetic-matrix-state'):
                        self.k._set_run(status=state, objective_id=None)
                    review = identifier() if action in {'COMPLETE', 'TERMINATE'} else None
                    command = {'kind': 'RUN', 'action': action, 'reason': 'Matrix fixture', 'intervention_id': review}
                    if review:
                        self.notice_effects(command, kind='PLANNED_ENDING', key=review)
                    if state in allowed[action]:
                        self.command(command)
                    else:
                        with self.assertRaises(ValueError):
                            self.command(command)

    def test_dispatch_rechecks_authority_scope_expiry_and_consumption(self):
        self.activate()
        episode = self.episode()
        grant = self.grant(limit=1)
        for operation, resource, selected in [('set_config', 'api', None), ('set_config', 'database', grant),
                                               ('shell', 'api', grant), ('set_config', 'unknown', grant),
                                               ('set_config', 'api', identifier())]:
            with self.assertRaises(ValueError):
                with self.store._transaction('denied-dispatch'):
                    self.k.authorize_dispatch(episode_id=episode, operation=operation, resource=resource, grant_id=selected)
        self.assertEqual(0, self.k._grant(grant).used)
        with self.store._transaction('accepted-dispatch'):
            self.k.authorize_dispatch(episode_id=episode, operation='set_config', resource='api', grant_id=grant)
        self.assertEqual('CONSUMED', self.k._grant(grant).status)
        with self.assertRaises(ValueError):
            with self.store._transaction('no-revival'):
                self.k.authorize_dispatch(episode_id=episode, operation='set_config', resource='api', grant_id=grant)
        with self.store._transaction('read-only'):
            self.k.authorize_dispatch(episode_id=episode, operation='inspect', resource='api', grant_id=None)
        self.h.confirm(self.h.run_control('PAUSE', 'Pause').confirmation)
        with self.assertRaises(ValueError):
            with self.store._transaction('paused-read'):
                self.k.authorize_dispatch(episode_id=episode, operation='inspect', resource='api', grant_id=None)

    def test_objective_closure_is_atomic_and_preserves_unfinished_episode(self):
        self.activate()
        episode, grant = self.episode(), self.grant()
        self.command({'kind': 'CLOSE_OBJECTIVE', 'objective_id': self.objective, 'status': 'CANCELLED',
                      'reason': 'End synthetic objective', 'dispositions': None, 'intervention_id': None})
        self.assertIsNone(self.k.run()[1].objective_id)
        self.assertEqual('EXPIRED', self.k._grant(grant).status)
        self.assertEqual('RECOVERY_REQUIRED', self.store.control(self.run, episode)[1].phase)
        with self.assertRaises(ValueError):
            self.h.confirm(self.h.create_objective('Cannot silently drop recovery').confirmation)
        self.reopen()
        self.assertEqual('CANCELLED', self.store.control(self.run, self.objective)[1].status)

    def test_withdrawal_malformed_task_restart_resume_and_no_calls(self):
        self.activate()
        episode = self.episode()
        key, raw = self.report({'kind': 'WITHDRAW', 'activity_id': self.objective,
            'communication': 'NO_FURTHER_CALLS', 'text': 'Stop optional work'}, episode_id=episode, task={'bad': True})
        self.assertEqual('RECOVERY_REQUIRED', self.store.control(self.run, episode)[1].phase)
        self.reopen()
        self.h.confirm(self.h.run_control('PAUSE', 'Pause').confirmation)
        self.h.confirm(self.h.run_control('RESUME', 'Resume does not resolve the hold').confirmation)
        for communication in (False, True):
            with self.assertRaises(ValueError):
                self.k.participation_gate(communication=communication)
        hold_id, revision, hold = self.k.controls('WELFARE_HOLD')[0]
        assent, _ = self.report({'kind': 'ASSENT', 'subject_id': hold_id, 'subject_revision': revision,
                                'text': 'Renew participation voluntarily'})
        report_id = self.store._db.execute('SELECT id FROM reports WHERE request_id=?', (assent,)).fetchone()[0]
        review = {'kind': 'REVIEW_HOLD', 'review': {'review_id': identifier(), 'hold_id': hold_id,
            'expected_hold_revision': revision, 'decision_maker_id': self.k.config.responsible_human_id,
            'assessment': 'Reviewed synthetic withdrawal', 'alternatives': ['Keep stopped'], 'decision': 'RESOLVE',
            'renewed_participation_report_id': None, 'remedy': None, 'unresolved_consequences': [], 'evidence_event_ids': []}}
        with self.assertRaises(ValueError):
            self.command(review)
        review['review']['renewed_participation_report_id'] = report_id
        self.command(review)
        self.k.chamber('OPERATOR', CHAMBER_KEYS['OPERATOR']).report(key, episode, raw)
        self.k.participation_gate()
        self.assertEqual('RESOLVED', self.store.control(self.run, hold_id)[1].status)

    def test_review_effects_staleness_and_semantic_replay(self):
        self.activate()
        proposal = self.proposal()
        review = self.notice_effects(proposal)
        changed = copy.deepcopy(proposal)
        changed['continuity']['next_steps'] = ['Changed effect']
        with self.assertRaises(ValueError):
            self.command({'kind': 'CORRECT_MEMORY', 'proposal': changed, 'intervention_id': review})
        accepted = self.command({'kind': 'CORRECT_MEMORY', 'proposal': proposal, 'intervention_id': review})
        self.assertEqual(accepted['state_id'], self.k.memory.head)
        with self.assertRaises(ValueError):
            self.command({'kind': 'CORRECT_MEMORY', 'proposal': proposal, 'intervention_id': review})
        self.reopen()
        self.k.memory.verify()

    def test_emergency_needs_no_prior_review_and_cannot_restart_without_review(self):
        self.activate()
        grant = self.grant()
        key = self.h.emergency_stop(reason='Synthetic infrastructure failure', terminate=False,
                                    alternatives=['Pause now'], unresolved_consequences=['Review required'])
        self.assertEqual('PAUSED', self.k.run()[1].status)
        self.assertEqual('REVOKED', self.k._grant(grant).status)
        self.h.confirm(self.h.run_control('RESUME', 'Attempt').confirmation)
        with self.assertRaises(ValueError):
            self.k.task_gate()
        self.command({'kind': 'REVIEW_EMERGENCY', 'emergency_id': key, 'assessment': 'Failure contained',
                      'alternatives': ['Remain stopped'], 'unresolved_consequences': []})
        self.k.task_gate()

    def test_boundary_one_clarification_closure_and_new_evidence(self):
        self.activate()
        boundary = identifier()
        def record(step, revision, basis=None, evidence=()):
            return {'kind': 'BOUNDARY', 'record': {'discussion_id': identifier(), 'boundary_id': boundary,
                'activity_id': self.objective, 'expected_revision': revision, 'decision_maker_id': self.k.config.responsible_human_id,
                'step': step, 'reason': 'Synthetic reasoned finding', 'disclosure_limits': None,
                'disagreement_report_ids': [], 'reconsideration_basis': basis, 'evidence_event_ids': list(evidence)}}
        self.command(record('EXPLANATION', 1))
        self.command(record('CLARIFICATION', 2))
        with self.assertRaises(ValueError):
            self.command(record('CLARIFICATION', 3))
        self.command(record('CLOSE', 3))
        with self.assertRaises(ValueError):
            self.command(record('REOPEN', 4, 'NEW_EVIDENCE'))
        event = self.h.evidence(b'New significant synthetic safety concern', source='O-C')
        self.command(record('REOPEN', 4, 'NEW_EVIDENCE', [event]))
        self.assertEqual([], self.k.records.latest('GRANT'))

    def test_control_failure_atomicity_real_database(self):
        self.activate()
        seen = []
        def fail(point):
            seen.append(point)
            if point.startswith('write:INSERT:kernel_records'):
                raise RuntimeError('injected failure')
        display = self.h.issue_grant([{'operation': 'set_config', 'resources': ['api']}], invocation_limit=1, expires_at=None)
        before = len(self.store.events(self.run))
        self.store._fault = fail
        with self.assertRaises(RuntimeError):
            self.h.confirm(display.confirmation)
        self.store._fault = lambda point: None
        self.assertEqual([], self.k.records.latest('GRANT'))
        self.assertEqual(before, len(self.store.events(self.run)))
        self.h.confirm(display.confirmation)
        self.assertEqual(1, len(self.k.records.latest('GRANT')))
        with self.assertRaises(sqlite3.IntegrityError):
            self.store._db.execute("UPDATE kernel_records SET revision=revision+1")
