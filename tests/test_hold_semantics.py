"""Approved participation policy at the shared semantic commit boundary."""
from bicameral_agent.kernel.restoration import Restoration
from bicameral_agent.storage.store import identifier
from tests.kernel_fixtures import KernelCase, CHAMBER_KEYS


class HoldSemanticsTests(KernelCase):
    def setUp(self):
        super().setUp()
        self.activate()
        self.target = self.correct(self.proposal())['state_id']
        authority = self.k._objective(self.objective).authority_event_id
        created = self.correct(self.proposal(mutations=[{'kind': 'COMMITMENT_CREATE', 'local_key': 'c',
            'objective_id': self.objective, 'action': 'Keep outstanding obligation',
            'trigger': {'kind': 'TASK_CLOCK', 'tick': 99}, 'expiry_tick': None,
            'authority_event_id': authority, 'evidence_event_ids': [authority]}]))
        self.commitment = created['bindings'][0]['object_id']
        self.episode_id = self.episode()
        self.grant_id = self.grant()

    def stop(self, kind, communication='NO_FURTHER_CALLS'):
        if kind == 'HOLD':
            self.report({'kind': 'WITHDRAW', 'activity_id': self.objective,
                'communication': communication, 'text': 'Stop optional work'})
            return self.k.controls('WELFARE_HOLD')[0][0]
        key = identifier()
        self.k.chamber('OPERATOR', CHAMBER_KEYS['OPERATOR']).report(key, None, b'undecodable report')
        return key

    def commands(self):
        correction = self.proposal()
        correction['continuity']['next_steps'] = ['Reviewed correction']
        plan = Restoration(self.k).propose(self.h, self.target, evidence_event_ids=[])
        obj = self.k.memory.objects()[self.commitment]
        closure = self.proposal(mutations=[{'kind': 'COMMITMENT_TRANSITION',
            'target': {'kind': 'EXISTING', 'object_type': 'COMMITMENT', 'object_id': obj.object_id},
            'expected_revision': obj.revision, 'status': 'CANCELLED', 'reason': 'Reviewed disposition',
            'evidence_event_ids': [], 'superseded_by': None}])
        return [
            {'kind': 'CORRECT_MEMORY', 'proposal': correction, 'intervention_id': self.notice_effects(correction)},
            {'kind': 'RESTORE_MEMORY', **plan['effects'],
             'intervention_id': self.notice_effects(plan['effects'], kind='SEMANTIC_RESTORATION')},
            {'kind': 'RESOLVE_EPISODE', 'episode_id': self.episode_id, 'disposition': 'HUMAN_CORRECTED',
             'reason': 'Reviewed recovery', 'proposal': correction, 'intervention_id': self.notice_effects(correction)},
            {'kind': 'CLOSE_OBJECTIVE', 'objective_id': self.objective, 'status': 'CANCELLED',
             'reason': 'Reviewed closure', 'dispositions': closure, 'intervention_id': self.notice_effects(closure)}]

    def assert_blocked_controls(self, kind, communication='NO_FURTHER_CALLS'):
        self.stop(kind, communication)
        commands = self.commands()  # Proposal preparation and review remain available.
        for status in ('ACTIVE', 'PAUSED'):
            if status == 'PAUSED':
                self.h.confirm(self.h.run_control('PAUSE', 'Keep activity paused').confirmation)
            self.reopen()
            for command in commands:
                with self.subTest(status=status, control=command['kind']):
                    before = list(self.store._db.iterdump())
                    with self.assertRaisesRegex(ValueError, 'welfare hold|participation inspection'):
                        self.command(command)
                    self.assertEqual(before, list(self.store._db.iterdump()))
                    self.assertFalse(self.k.records.get('INTERVENTION_REVIEW', command['intervention_id'])['executed'])

    def test_hold_blocks_every_human_semantic_route_atomically_after_restart(self):
        self.assert_blocked_controls('HOLD')

    def test_inspection_blocks_every_human_semantic_route_atomically_after_restart(self):
        self.assert_blocked_controls('INSPECTION')

    def test_review_communication_permission_does_not_authorize_semantic_changes(self):
        self.assert_blocked_controls('HOLD', communication='REVIEW_PERMITTED')

    def test_review_and_renewed_participation_allow_paused_human_correction(self):
        hold = self.stop('HOLD')
        command = self.commands()[0]
        self.h.confirm(self.h.run_control('PAUSE', 'Remain paused during review').confirmation)
        self.resolve_hold(hold)
        self.reopen()
        result = self.command(command)
        self.assertEqual(result['state_id'], self.k.memory.head)
        self.assertEqual('PAUSED', self.k.run()[1].status)
        self.assertEqual('RESOLVED', self.store.control(self.run, hold)[1].status)
        self.k.memory.verify()

    def test_inspection_clearance_allows_paused_restoration(self):
        key = self.stop('INSPECTION')
        command = self.commands()[1]
        self.h.confirm(self.h.run_control('PAUSE', 'Remain paused during inspection').confirmation)
        self.command({'kind': 'INSPECT_PARTICIPATION', 'role': 'OPERATOR', 'request_id': key,
            'assessment': 'Inspected synthetic malformed output', 'decision': 'CLEAR_INSPECTION', 'evidence_event_ids': []})
        self.reopen()
        result = self.command(command)
        self.assertEqual(result['state_id'], self.k.memory.head)
        self.assertEqual('PAUSED', self.k.run()[1].status)
        self.k.memory.verify()

    def test_nonsemantic_recovery_access_reduction_and_containment_remain_available(self):
        hold = self.stop('HOLD')
        before = self.k.memory.head
        self.assertEqual(self.run, self.h.inspect()['run_id'])
        self.command({'kind': 'REVOKE_GRANT', 'grant_id': self.grant_id, 'reason': 'Restrict access'})
        self.command({'kind': 'RESOLVE_EPISODE', 'episode_id': self.episode_id, 'disposition': 'SKIPPED',
            'reason': 'No semantic changes while held', 'proposal': None, 'intervention_id': None})
        self.h.emergency_stop(reason='Synthetic material threat', terminate=True,
            alternatives=['Keep task stopped'], unresolved_consequences=['Review required'])
        self.assertEqual(before, self.k.memory.head)
        self.assertEqual('HELD', self.store.control(self.run, hold)[1].status)
        self.assertEqual('TERMINATED', self.k.run()[1].status)
