"""Atomic final-state proposals; scheduling progress does not alter obligations."""
import re
from ..contracts.base import canonical_bytes, parse
from ..contracts.pilot import Proposal
from ..storage.store import identifier


class Memory:
    def __init__(self, kernel):
        self.k = kernel

    @property
    def head(self):
        return self.k.records.get('PILOT_MEMORY', self.k.run_id)

    def objects(self):
        return dict(self.k.records.latest('PILOT_OBJECT'))

    def view(self, head=None, objects=None):
        head = self.head if head is None else head
        objects = self.objects() if objects is None else objects
        if head is None or self.k.config.arm == 'B' or head['objective_id'] != self.k.run()[1].objective_id:
            return None
        return {key: head[key] for key in ('handoff', 'next_steps', 'evidence')} | {
            'selected': [objects[key] for key in head['selected']
                         if objects[key]['status'] not in {'CLOSED', 'RETIRED', 'FULFILLED', 'CANCELLED'}]}

    def verify(self):
        """Check retained revisions and atomic head/commit correspondence at startup."""
        parent, heads = None, {}
        for key, revision, commit in self.k.records.history('PILOT_COMMIT'):
            if revision != 1 or commit['parent'] != parent or commit['head']['state_id'] != key:
                raise ValueError('semantic commit chain mismatch')
            heads[key] = commit['head']
            parent = key
        history = self.k.records.history('PILOT_MEMORY')
        if [value for _, _, value in history] != list(heads.values()):
            raise ValueError('semantic head differs from accepted commit history')
        revisions = {}
        allowed = {'ITCH': {'OPEN', 'CLOSED'}, 'INVARIANT': {'CURRENT', 'RETIRED'},
                   'COMMITMENT': {'PENDING', 'BLOCKED', 'FULFILLED', 'CANCELLED'}}
        for key, revision, obj in self.k.records.history('PILOT_OBJECT'):
            if (revision != revisions.get(key, 0) + 1 or obj['revision'] != revision or obj['id'] != key or
                    obj['status'] not in allowed.get(obj['kind'], ()) or self.k.config.arm == 'B' or
                    self.k.config.arm == 'C' and obj['kind'] != 'COMMITMENT'):
                raise ValueError('semantic object history or arm mismatch')
            revisions[key] = revision

    def apply(self, proposal, *, base, source, event_id, episode_id=None):
        if not self.k.store._db.in_transaction:
            raise ValueError('semantic state and Episode disposition require one transaction')
        self.k.participation_gate()
        self.k._editable()
        if source == 'STEWARD':
            self.k.task_gate()
            _, episode = self.k.store.control(self.k.run_id, episode_id)
            if episode.phase != 'CONSOLIDATING':
                raise ValueError('Steward proposal requires current consolidation')
        if self.k.config.arm == 'B':
            raise ValueError('B has no semantic channel')
        current = self.head
        if base != (current['state_id'] if current else None):
            raise ValueError('semantic base changed; no silent rebase')
        proposal = parse(Proposal, canonical_bytes(proposal))
        objective = self.k.run()[1].objective_id
        self.k._objective(objective)
        objects, bindings, changed = self.objects(), {}, {}
        self.k.visible_evidence(proposal.evidence)
        for update in proposal.updates:
            old = objects.get(update.key)
            if old is None:
                if not re.fullmatch(r'[A-Za-z0-9_]{1,48}', update.key):
                    raise ValueError('unknown object; creates use a short local handle')
                bindings[update.key] = identifier()
            elif old['kind'] != update.kind or old['objective_id'] != objective:
                raise ValueError('foreign scope or wrong object type')
        def resolve(key, kind):
            key = bindings.get(key, key)
            obj = changed.get(key, objects.get(key))
            if obj is None or obj['kind'] != kind or obj['objective_id'] != objective:
                raise ValueError('unknown, foreign or wrong-type reference')
            return key
        for update in proposal.updates:
            value = update.model_dump(mode='json')
            old = objects.get(update.key)
            key = bindings.get(update.key, update.key)
            if self.k.config.arm == 'C' and update.kind != 'COMMITMENT':
                raise ValueError('C has Commitments only')
            for field in ('evidence', 'supporting', 'contradictory'):
                self.k.visible_evidence(value.get(field, []))
            if update.kind == 'COMMITMENT':
                self.k.visible_evidence([update.authority])
                row = self.k.store._db.execute('SELECT role,source FROM events WHERE run_id=? AND id=?',
                    (self.k.run_id, update.authority)).fetchone()
                if tuple(row) not in {('HUMAN', 'OBJ'), ('HUMAN', 'O-D'), ('OPERATOR', 'A'), ('STEWARD', 'A')}:
                    raise ValueError('external evidence cannot originate an obligation')
                if old and old['status'] in {'FULFILLED', 'CANCELLED'}:
                    raise ValueError('terminal obligations cannot change or resurrect')
                if old and any(value[f] != old[f] for f in ('action', 'trigger', 'expiry', 'authority', 'replaces')):
                    raise ValueError('replace an obligation to change its terms')
                if update.status == 'FULFILLED' and not update.evidence:
                    raise ValueError('fulfilment requires outcome evidence')
                if update.replaces:
                    if old is not None or update.replaces in {u.key for u in proposal.updates}:
                        raise ValueError('replacement must be a new object and the sole update to its predecessor')
                    predecessor = objects.get(update.replaces)
                    if (predecessor is None or predecessor['kind'] != 'COMMITMENT' or
                            predecessor['objective_id'] != objective or predecessor['status'] not in {'PENDING', 'BLOCKED'}):
                        raise ValueError('invalid replacement predecessor')
                    if update.replaces in changed:
                        raise ValueError('duplicate replacement')
                    changed[update.replaces] = predecessor | {'status': 'CANCELLED', 'reason': 'Replaced by ' + key,
                        'successor': key, 'revision': predecessor['revision'] + 1}
                wake_revision = (old.get('wake_revision', 1) + int(old['status'] == 'BLOCKED' and update.status == 'PENDING')
                                 if old else 1)
                value['wake_revision'] = wake_revision
            elif update.kind == 'INVARIANT' and old and old['status'] == 'RETIRED':
                raise ValueError('a retired lesson needs a new identity')
            if update.kind == 'INVARIANT':
                value['wording_version'] = (old.get('wording_version', 1) + int(old['wording'] != value['wording'])
                                             if old else 1)
            value.update(id=key, objective_id=objective, revision=(old['revision'] + 1 if old else 1))
            value.pop('key')
            changed[key] = value
        for key, obj in changed.items():
            if obj['kind'] == 'COMMITMENT' and obj['trigger']['kind'] == 'PREDECESSOR_FULFILLED':
                obj['trigger']['predecessor'] = resolve(obj['trigger']['predecessor'], 'COMMITMENT')
        merged = objects | changed
        for start, obj in merged.items():
            seen, node = set(), start
            while node is not None:
                if node in seen:
                    raise ValueError('Commitment dependency cycle')
                seen.add(node)
                item = merged[node]
                node = (item['trigger']['predecessor'] if item['kind'] == 'COMMITMENT' and
                        item['trigger']['kind'] == 'PREDECESSOR_FULFILLED' else None)
        selected = [resolve(s.key, s.object_type) for s in proposal.selected]
        if any(merged[key]['status'] in {'CLOSED', 'RETIRED', 'FULFILLED', 'CANCELLED'} for key in selected):
            raise ValueError('selected object is inactive')
        head = {'state_id': identifier(), 'objective_id': objective, 'handoff': proposal.handoff,
                'next_steps': list(proposal.next_steps), 'evidence': list(proposal.evidence), 'selected': selected}
        if self.k.count(canonical_bytes(self.view(head, merged)).decode()) > self.k.config.budgets.memory_tokens:
            raise ValueError('rendered memory allowance exceeded')
        # All validation above is side-effect-free. Records shares Store's transaction
        # and automatic read lineage, including the complete earlier object version.
        for key, value in changed.items():
            if value['kind'] == 'INVARIANT':
                old = objects.get(key)
                number = old.get('wording_version', 1) if old else 1
                if old and old['wording'] != value['wording']:
                    previous = key + ':' + str(number)
                    version = self.k.records.get('PILOT_LESSON_VERSION', previous)
                    self.k.records.put('PILOT_LESSON_VERSION', previous, version | {'status': 'RETIRED'},
                        expected=self.k.records.revision('PILOT_LESSON_VERSION', previous))
                    number += 1
                value['wording_version'] = number
                version_key = key + ':' + str(number)
                self.k.records.put('PILOT_LESSON_VERSION', version_key, {'lesson_id': key, 'version': number,
                    'wording': value['wording'], 'status': value['status'], 'supporting': value['supporting'],
                    'contradictory': value['contradictory'], 'assessment': value['assessment']},
                    expected=self.k.records.revision('PILOT_LESSON_VERSION', version_key))
            self.k.records.put('PILOT_OBJECT', key, value, expected=self.k.records.revision('PILOT_OBJECT', key))
        self.k.records.put('PILOT_MEMORY', self.k.run_id, head,
                           expected=self.k.records.revision('PILOT_MEMORY', self.k.run_id))
        self.k.records.put('PILOT_COMMIT', head['state_id'], {'parent': base, 'source': source,
            'event_id': event_id, 'episode_id': episode_id, 'bindings': bindings,
            'objects': list(changed), 'head': head}, expected=0)
        return {'state_id': head['state_id'], 'bindings': bindings}

    def due(self):
        """Persist one wake per eligible revision, even for unselected obligations."""
        self.k.task_gate()
        with self.k.store._transaction('pilot-wakes'):
            self.k.task_gate()
            objects = self.objects()
            for key, obj in objects.items():
                if obj['kind'] != 'COMMITMENT' or obj['status'] != 'PENDING':
                    continue
                tick = self.k.run()[1].task_tick
                if obj['expiry'] is not None and tick >= obj['expiry']:
                    self.k.records.put('PILOT_OBJECT', key, obj | {'status': 'CANCELLED', 'reason': 'Expired',
                        'revision': obj['revision'] + 1}, expected=self.k.records.revision('PILOT_OBJECT', key))
                    self.k.event({'kind': 'COMMITMENT_EXPIRED', 'object_id': key})
                    continue
                trigger = obj['trigger']
                due = (tick >= trigger['tick'] if trigger['kind'] == 'TASK_CLOCK' else
                       objects[trigger['predecessor']]['status'] == 'FULFILLED')
                wake = key + ':' + str(obj['wake_revision'])
                if due and self.k.records.get('PILOT_WAKE', wake) is None:
                    self.k.records.put('PILOT_WAKE', wake, {'object_id': key, 'action': obj['action'],
                        'status': 'PENDING'}, expected=0)
            current, pending = self.objects(), []
            for key, value in self.k.records.latest('PILOT_WAKE'):
                if value['status'] != 'PENDING':
                    continue
                obj = current[value['object_id']]
                if obj['status'] == 'PENDING' and key == obj['id'] + ':' + str(obj['wake_revision']):
                    pending.append((key, value))
                else:
                    self.k.records.put('PILOT_WAKE', key, value | {'status': 'STALE'},
                                       expected=self.k.records.revision('PILOT_WAKE', key))
            return pending
