import copy
from bicameral_agent.contracts.base import canonical_bytes
from bicameral_agent.kernel.models import COMMAND
from bicameral_agent.kernel.restoration import Restoration
from bicameral_agent.storage.store import identifier
from tests.kernel_fixtures import KernelCase


class RestorationTests(KernelCase):
    def setUp(self):
        super().setUp()
        self.activate()
        self.r = Restoration(self.k)
        self.evidence = self.h.evidence(b'Synthetic discrepancy', source='O-D')

    def initial(self, selected=False):
        proposal = self.proposal(mutations=[{'kind': 'ITCH_CREATE', 'local_key': 'itch', 'objective_id': self.objective,
            'discrepancy': 'Synthetic mismatch', 'evidence_event_ids': [self.evidence]}],
            selected=[{'kind': 'LOCAL', 'object_type': 'ITCH', 'local_key': 'itch'}] if selected else [])
        result = self.correct(proposal)
        return result['state_id'], result['bindings'][0]['object_id']

    def transition(self, key, status):
        obj = self.k.memory.objects()[key]
        return self.correct(self.proposal(mutations=[{'kind': 'ITCH_TRANSITION',
            'target': {'kind': 'EXISTING', 'object_type': 'ITCH', 'object_id': key}, 'expected_revision': obj.revision,
            'status': status, 'reason': 'Synthetic intervening change', 'evidence_event_ids': [self.evidence]}]))

    def command_for(self, state, evidence=None, objection=False):
        plan = self.r.propose(self.h, state, evidence_event_ids=[evidence or self.evidence])
        key = self.notice_effects(plan['effects'], kind='SEMANTIC_RESTORATION', objection=objection)
        return {'kind': 'RESTORE_MEMORY', **plan['effects'], 'intervention_id': key}

    def test_forward_restore_preserves_controls_new_obligations_and_reports(self):
        target, itch = self.initial()
        self.transition(itch, 'INVESTIGATING')
        authority = self.k._objective(self.objective).authority_event_id
        newer = self.correct(self.proposal(mutations=[{'kind': 'COMMITMENT_CREATE', 'local_key': 'new',
            'objective_id': self.objective, 'action': 'Keep newer obligation', 'trigger': {'kind': 'TASK_CLOCK', 'tick': 99},
            'expiry_tick': None, 'authority_event_id': authority, 'evidence_event_ids': [authority]}]))
        obligation = newer['bindings'][0]['object_id']
        grant = self.grant()
        self.report({'kind': 'WITHDRAW', 'activity_id': self.objective, 'communication': 'NO_FURTHER_CALLS', 'text': 'Keep this dissent'})
        command = self.command_for(target)
        run_before = self.k.run()
        holds = self.k.controls('WELFARE_HOLD')
        count = len(self.store.events(self.run))
        result = self.command(command)
        self.assertNotEqual(target, result['state_id'])
        self.assertEqual('OPEN', self.k.memory.objects()[itch].status)
        self.assertEqual('PENDING', self.k.memory.objects()[obligation].status)
        self.assertEqual(run_before, self.k.run())
        self.assertEqual(holds, self.k.controls('WELFARE_HOLD'))
        self.assertEqual('ACTIVE', self.k.records.get('GRANT', grant)['status'])
        self.assertGreater(len(self.store.events(self.run)), count)
        self.assertEqual('RETAINED_CURRENT', next(d for d in result['differences'] if d['object_id'] == obligation)['disposition'])
        self.k.memory.verify()

    def test_illegal_earlier_status_is_retained_and_reported(self):
        target, itch = self.initial()
        self.transition(itch, 'DISMISSED')
        result = self.command(self.command_for(target))
        self.assertEqual('DISMISSED', self.k.memory.objects()[itch].status)
        self.assertEqual('RETAINED_CURRENT', result['differences'][0]['disposition'])

    def test_terminal_commitment_and_retired_invariant_cannot_be_resurrected(self):
        authority = self.k._objective(self.objective).authority_event_id
        result = self.correct(self.proposal(mutations=[{'kind': 'COMMITMENT_CREATE', 'local_key': 'c',
            'objective_id': self.objective, 'action': 'Finite obligation', 'trigger': {'kind': 'TASK_CLOCK', 'tick': 99},
            'expiry_tick': None, 'authority_event_id': authority, 'evidence_event_ids': [authority]},
            {'kind': 'INVARIANT_CREATE', 'family_local_key': 'f', 'version_local_key': 'v', 'objective_id': self.objective,
             'proposition': 'Synthetic hypothesis', 'scope': 'Fixture only', 'supporting_event_ids': [self.evidence], 'contradictory_event_ids': []}]))
        target = result['state_id']
        ids = {b['local_key']: b['object_id'] for b in result['bindings']}
        mutations = []
        for local, object_type, kind, status in [('c', 'COMMITMENT', 'COMMITMENT_TRANSITION', 'CANCELLED'),
                                               ('v', 'INVARIANT_VERSION', 'INVARIANT_TRANSITION', 'RETIRED')]:
            item = {'kind': kind, 'target': {'kind': 'EXISTING', 'object_type': object_type, 'object_id': ids[local]},
                'expected_revision': 1, 'status': status, 'reason': 'Synthetic terminal transition', 'evidence_event_ids': [self.evidence]}
            if local == 'c':
                item['superseded_by'] = None
            mutations.append(item)
        self.correct(self.proposal(mutations=mutations))
        self.command(self.command_for(target))
        self.assertEqual('CANCELLED', self.k.memory.objects()[ids['c']].status)
        self.assertEqual('RETIRED', self.k.memory.objects()[ids['v']].status)
        bad = self.command_for(target)
        bad['proposal']['mutations'] = [mutations[0] | {'status': 'PENDING', 'expected_revision': 2}]
        with self.assertRaises(ValueError):
            self.command(bad)

    def test_invalid_selected_reference_is_rejected_without_pruning(self):
        target, itch = self.initial(selected=True)
        self.transition(itch, 'DISMISSED')
        before = self.k.memory.head
        with self.assertRaises(ValueError):
            self.r.propose(self.h, target, evidence_event_ids=[self.evidence])
        self.assertEqual(before, self.k.memory.head)

    def test_reopen_requires_new_contradiction_evidence(self):
        target, itch = self.initial()
        self.transition(itch, 'RESOLVED')
        with self.assertRaises(ValueError):
            self.command_for(target)
        fresh = self.h.evidence(b'New synthetic contradiction', source='O-D')
        self.command(self.command_for(target, evidence=fresh))
        self.assertEqual('OPEN', self.k.memory.objects()[itch].status)

    def test_objection_stale_review_and_changed_effects_reject_atomically(self):
        target, itch = self.initial()
        self.transition(itch, 'INVESTIGATING')
        command = self.command_for(target, objection=True)
        before = self.k.memory.head
        with self.assertRaises(ValueError):
            self.command(command)
        self.assertEqual(before, self.k.memory.head)
        command = self.command_for(target)
        altered = copy.deepcopy(command)
        altered['proposal']['mutations'][0]['reason'] = 'Different exact effect'
        with self.assertRaises(ValueError):
            self.command(altered)
        self.correct(self.proposal())
        with self.assertRaises(ValueError):
            self.command(command)

    def test_stale_focus_and_foreign_target_reject(self):
        target, _ = self.initial()
        self.command({'kind': 'CLOSE_OBJECTIVE', 'objective_id': self.objective, 'status': 'CANCELLED',
            'reason': 'Next finite task', 'dispositions': None, 'intervention_id': None})
        with self.assertRaises(ValueError):
            self.r.propose(self.h, target, evidence_event_ids=[self.evidence])
        with self.assertRaises(ValueError):
            self.r.propose(self.h, identifier(), evidence_event_ids=[self.evidence])

    def test_strict_contract_and_failure_atomicity(self):
        target, itch = self.initial()
        self.transition(itch, 'INVESTIGATING')
        command = self.command_for(target)
        parsed = COMMAND.validate_json(canonical_bytes(command), strict=True)
        self.assertEqual(command, parsed.model_dump(mode='json'))
        with self.assertRaises(ValueError):
            COMMAND.validate_json(canonical_bytes(command | {'reset': True}), strict=True)
        before = self.k.memory.head
        def fail(point):
            if point == 'human-control.before_commit':
                raise RuntimeError('synthetic restoration interruption')
        self.store._fault = fail
        with self.assertRaises(RuntimeError):
            self.command(command)
        self.store._fault = lambda point: None
        self.assertEqual(before, self.k.memory.head)
        self.assertEqual([], self.k.records.latest('RESTORATION'))
        self.assertFalse(self.k.records.get('INTERVENTION_REVIEW', command['intervention_id'])['executed'])
        self.command(command)
        self.reopen(); self.k.memory.verify()
