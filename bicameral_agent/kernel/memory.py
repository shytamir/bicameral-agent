"""Shared semantic transactions for human, Steward and deterministic triggers.

The integrated ledger uses P02's append-only payload/record transactions and P01
resolution/P02 lifecycle validation. The earlier P02 storage-probe ledger is not
an alternate exposed runtime route.
"""
from ..contracts.base import canonical_bytes, parse
from ..contracts.resolution import ResolutionContext, resolve_proposal
from ..contracts.semantics import ContinuityState, StateProposal
from ..storage.contracts import StoredObject
from ..storage.semantics import stage
from ..storage.store import identifier, Store
from .models import SemanticCommit, MemoryHead


class Memory:
    def __init__(self, kernel):
        self.k = kernel

    @property
    def head(self):
        value = self.k.records.get('MEMORY_HEAD', self.k.run_id)
        return value['state_id'] if value else None

    def objects(self):
        return {key: parse(StoredObject, canonical_bytes(value)) for key, value in self.k.records.latest('OBJECT')}

    def continuity(self):
        value = self.k.records.get('MEMORY_HEAD', self.k.run_id)
        return None if value is None else parse(ContinuityState, canonical_bytes(value['continuity']))

    def _resolve(self, proposal, objects, parent, objective, tick, allocator, prior):
        events = self.k.store.events(self.k.run_id)
        context = parse(ResolutionContext, canonical_bytes({
            'run_id': self.k.run_id, 'objective_id': objective, 'parent_state_id': parent, 'arm': self.k.config.arm,
            'objects': [{key: obj.model_dump(mode='json')[key] for key in
                        ('object_id', 'run_id', 'object_type', 'objective_id', 'revision', 'family_id', 'commitment_links')}
                        for obj in objects.values()],
            'events': [{'event_id': e['id'], 'run_id': self.k.run_id, 'chamber_visible': e['visibility'] == 'CHAMBER'} for e in events]}))
        resolution = resolve_proposal(proposal, context, allocator)
        referenced = Store._event_ids(resolution.proposal.model_dump(mode='json'))
        for event in events:
            if event['id'] in referenced:
                self.k.store.read_payload(self.k.run_id, event['payload_id'])
        final, changes = stage(resolution, objects, run_id=self.k.run_id, task_tick=tick,
                               event_sources={e['id']: e['source'] for e in events}, prior_evidence=prior)
        return resolution, final, changes

    def prior(self):
        result = {}
        for _, _, ledger in self.k.records.history('SEMANTIC_COMMIT'):
            for mutation, changes in zip(ledger['resolved']['mutations'], ledger['changes']):
                for change in changes:
                    result.setdefault(change['after']['object_id'], set()).update(Store._event_ids(mutation))
        return result

    def apply(self, proposal, *, source, authority_event_id, episode_id=None):
        if not self.k.store._db.in_transaction:
            raise ValueError('semantic acceptance requires a transaction')
        proposal = parse(StateProposal, canonical_bytes(proposal))
        if len(canonical_bytes(proposal)) > self.k.config.budgets.proposal_bytes:
            raise ValueError('proposal byte limit')
        run = self.k.run()[1]
        objects = self.objects()
        resolution, final, changes = self._resolve(proposal, objects, self.head, run.objective_id,
                                                   run.task_tick, identifier, self.prior())
        bundle = canonical_bytes({'continuity': resolution.proposal.continuity.model_dump(mode='json'),
                                  'selected_objects': [final[r.object_id].model_dump(mode='json')
                                                       for r in resolution.proposal.continuity.selected_objects],
                                  'inapplicable_count': 0, 'change_cursor': None})
        if len(bundle) > self.k.config.budgets.active_semantic_tokens:
            raise ValueError('scripted byte-token semantic budget')
        state_id = identifier()
        ledger = {'state_id': state_id, 'parent': self.head, 'source': source, 'authority_event_id': authority_event_id,
                  'episode_id': episode_id, 'objective_id': run.objective_id, 'task_tick': run.task_tick,
                  'run_revision': self.k.run()[0],
                  'objective_revision': self.k.store.control(self.k.run_id, run.objective_id)[0] if run.objective_id else None,
                  'episode_revision': self.k.store.control(self.k.run_id, episode_id)[0] if episode_id else None,
                  'original': proposal.model_dump(mode='json'), 'resolved': resolution.proposal.model_dump(mode='json'),
                  'bindings': [b.model_dump(mode='json') for b in resolution.bindings],
                  'changes': [[{'before': before.model_dump(mode='json') if before else None,
                               'after': after.model_dump(mode='json')} for before, after in group] for group in changes]}
        self.k.records.put('SEMANTIC_COMMIT', state_id, parse(SemanticCommit, canonical_bytes(ledger)), expected=0)
        for group in changes:
            for before, after in group:
                self.k.records.put('OBJECT', after.object_id, after, expected=before.revision if before else 0)
        self.k.records.put('MEMORY_HEAD', self.k.run_id,
                           MemoryHead(state_id=state_id, continuity=resolution.proposal.continuity),
                           expected=self.k.records.revision('MEMORY_HEAD', self.k.run_id))
        return {'state_id': state_id, 'bindings': ledger['bindings']}

    def verify(self):
        objects, parent, prior, continuity, history = {}, None, {}, None, []
        for key, revision, ledger in self.k.records.history('SEMANTIC_COMMIT'):
            ledger = parse(SemanticCommit, canonical_bytes(ledger)).model_dump(mode='json')
            if revision != 1 or ledger['state_id'] != key or ledger['parent'] != parent:
                raise ValueError('semantic ledger chain mismatch')
            event = self.k.store._db.execute('SELECT role,source,payload_id FROM events WHERE run_id=? AND id=?',
                                            (self.k.run_id, ledger['authority_event_id'])).fetchone()
            allowed = {'HUMAN': {('HUMAN', 'O-D')}, 'KERNEL': {('KERNEL', 'K')}, 'STEWARD': {('STEWARD', 'A')}}
            if event is None or tuple(event)[:2] not in allowed.get(ledger['source'], set()):
                raise ValueError('semantic transaction lacks its recorded authority')
            self.k.store.read_payload(self.k.run_id, event['payload_id'])
            run = self.k.store._control_at(self.k.run_id, self.k.run_id, ledger['run_revision'])
            if (run.status not in ({'ACTIVE', 'PAUSED'} if ledger['source'] == 'HUMAN' else {'ACTIVE'}) or
                    run.objective_id != ledger['objective_id'] or run.task_tick != ledger['task_tick']):
                raise ValueError('invalid retained semantic control basis')
            if ledger['objective_id']:
                objective = self.k.store._control_at(self.k.run_id, ledger['objective_id'], ledger['objective_revision'])
                if objective.status != 'ACTIVE':
                    raise ValueError('semantic acceptance used terminal Objective')
            if ledger['source'] == 'STEWARD':
                episode = self.k.store._control_at(self.k.run_id, ledger['episode_id'], ledger['episode_revision'])
                if episode.phase != 'CONSOLIDATING' or episode.objective_id != run.objective_id:
                    raise ValueError('Steward acceptance used ineligible Episode')
            ids = iter(b['object_id'] for b in ledger['bindings'])
            resolution, final, changes = self._resolve(parse(StateProposal, canonical_bytes(ledger['original'])),
                objects, parent, ledger['objective_id'], ledger['task_tick'], lambda: next(ids), prior)
            expected = [[{'before': b.model_dump(mode='json') if b else None, 'after': a.model_dump(mode='json')}
                         for b, a in group] for group in changes]
            if (resolution.proposal.model_dump(mode='json') != ledger['resolved'] or expected != ledger['changes']
                    or [b.model_dump(mode='json') for b in resolution.bindings] != ledger['bindings']):
                raise ValueError('semantic replay differs from retained proposal')
            for mutation, group in zip(ledger['resolved']['mutations'], changes):
                for _, after in group:
                    prior.setdefault(after.object_id, set()).update(Store._event_ids(mutation))
                    history.append((after.object_id, after.revision, after.model_dump(mode='json')))
            objects, parent, continuity = final, key, resolution.proposal.continuity
        if objects != self.objects() or parent != self.head or continuity != self.continuity():
            raise ValueError('semantic projection mismatch')
        if history != self.k.records.history('OBJECT'):
            raise ValueError('semantic object history differs from ledger')
        return objects
