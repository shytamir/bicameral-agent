"""Reviewed forward restoration, never a replacement of process history."""
from ..contracts.base import canonical_bytes, parse
from ..contracts.semantics import StateProposal
from ..storage.semantics import EDGES
from ..storage.store import identifier


class Restoration:
    def __init__(self, kernel):
        self.k = kernel

    def target(self, state_id):
        objects = {}
        for key, _, ledger in self.k.records.history('SEMANTIC_COMMIT'):
            for group in ledger['changes']:
                for change in group:
                    objects[change['after']['object_id']] = change['after']
            if key == state_id:
                return ledger['resolved']['continuity'], objects
        raise ValueError('restoration target is absent or foreign')

    def propose(self, human, state_id, *, evidence_event_ids):
        self.k._human(human._cap)
        self.k._editable()
        with self.k.store._snapshot():
            continuity, earlier = self.target(state_id)
            mutations = []
            for key, obj in self.k.memory.objects().items():
                old = earlier.get(key)
                if old is None or obj.object_type == 'INVARIANT_FAMILY' or old['status'] == obj.status:
                    continue
                if old['status'] not in EDGES[obj.object_type][obj.status]:
                    continue
                mutation = {'kind': {'ITCH': 'ITCH_TRANSITION', 'INVARIANT_VERSION': 'INVARIANT_TRANSITION',
                    'COMMITMENT': 'COMMITMENT_TRANSITION'}[obj.object_type],
                    'target': {'kind': 'EXISTING', 'object_type': obj.object_type, 'object_id': key},
                    'expected_revision': obj.revision, 'status': old['status'],
                    'reason': 'Reviewed forward restoration of earlier status', 'evidence_event_ids': evidence_event_ids}
                if obj.object_type == 'COMMITMENT':
                    mutation['superseded_by'] = None
                mutations.append(mutation)
            proposal = parse(StateProposal, canonical_bytes({'expected_parent_state_id': self.k.memory.head,
                'mutations': mutations, 'continuity': continuity, 'supporting_event_ids': evidence_event_ids}))
            differences = self.validate(state_id, proposal)
            return {'effects': {'target_state_id': state_id, 'proposal': proposal.model_dump(mode='json')},
                'differences': differences, 'notice': 'All intervening evidence and current controls remain; this is a new semantic version.'}

    def validate(self, state_id, proposal):
        continuity, earlier = self.target(state_id)
        if proposal.continuity.model_dump(mode='json') != continuity:
            raise ValueError('restoration must name the exact earlier handoff; correction is a separate control')
        objects = self.k.memory.objects()
        seen = set()
        for mutation in proposal.mutations:
            target = getattr(mutation, 'target', None)
            if (target is None or target.kind != 'EXISTING' or target.object_id in seen or
                    mutation.kind not in {'ITCH_TRANSITION', 'INVARIANT_TRANSITION', 'COMMITMENT_TRANSITION'}):
                raise ValueError('restoration only applies one earlier status transition per existing object')
            seen.add(target.object_id)
            old = earlier.get(target.object_id)
            if old is None or mutation.status != old['status']:
                raise ValueError('restoration mutation differs from the named earlier content')
        run = self.k.run()[1]
        _, final, _ = self.k.memory._resolve(proposal, objects, self.k.memory.head, run.objective_id,
            run.task_tick, identifier, self.k.memory.prior())
        differences = []
        for key, obj in objects.items():
            old = earlier.get(key)
            after = final[key]
            differences.append({'object_id': key, 'target_revision': old['revision'] if old else None,
                'before_revision': obj.revision, 'after_revision': after.revision,
                'target_status': old['status'] if old else None, 'current_status': after.status,
                'disposition': 'RESTORED' if key in seen else 'UNCHANGED' if old and old['status'] == obj.status else 'RETAINED_CURRENT'})
        return differences
