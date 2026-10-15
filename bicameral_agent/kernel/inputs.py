"""Exact bounded views and visibility-bound retrieval for scripted byte tokens."""
import base64
from hashlib import sha256
from typing import Annotated, Literal
from pydantic import Field
from ..contracts.base import Contract, Identifier, Text, Nonnegative, Positive, canonical_bytes, load_json, parse
from ..storage import EvidenceUnavailable, RequestConflict
from ..storage.contracts import StoredObject
from ..storage.semantics import SELECTABLE
from ..storage.store import identifier


class EventQuery(Contract):
    kind: Literal['EVENT']
    event_id: Identifier


class RangeQuery(Contract):
    kind: Literal['RANGE']
    first_sequence: Positive
    last_sequence: Positive | None


class SearchQuery(Contract):
    kind: Literal['SEARCH']
    text: Text
    ranking: Literal['CASEFOLD_COUNT_V1']


class ObjectQuery(Contract):
    kind: Literal['OBJECT_INDEX']
    object_id: Identifier | None
    object_type: Literal['ITCH', 'INVARIANT_FAMILY', 'INVARIANT_VERSION', 'COMMITMENT'] | None
    status: Text | None


class ManifestQuery(Contract):
    kind: Literal['MANIFEST']
    episode_id: Identifier


class PayloadQuery(Contract):
    kind: Literal['PAYLOAD']
    payload_id: Identifier


class StateQuery(Contract):
    kind: Literal['STATE']
    state_id: Identifier


Query = Annotated[EventQuery | RangeQuery | SearchQuery | ObjectQuery | ManifestQuery | PayloadQuery | StateQuery, Field(discriminator='kind')]


class PageRequest(Contract):
    request_id: Identifier
    query: Query
    cursor: Identifier | None


class InputContracts(Contract):
    page_request: PageRequest


class Inputs:
    def __init__(self, kernel):
        self.k = kernel

    def _chamber(self, session):
        if session._k is not self.k or session._cap is not self.k._chamber_caps.get(session.role):
            raise PermissionError('authenticated chamber route required')

    def gate(self, session, episode_id):
        self._chamber(session)
        self.k.task_gate()
        _, episode = self.k.store.control(self.k.run_id, episode_id)
        phase = 'OPEN' if session.role == 'OPERATOR' else 'CONSOLIDATING'
        if episode.kind != 'EPISODE' or episode.phase != phase or episode.objective_id != self.k.run()[1].objective_id:
            raise ValueError('retrieval needs the current eligible Episode and role')
        if session.role == 'STEWARD' and self.k.config.arm == 'B':
            raise ValueError('arm B has no Steward task channel')

    def _cutoff(self):
        return (self.k.store._db.execute('SELECT COALESCE(MAX(sequence),0) FROM events WHERE run_id=?', (self.k.run_id,)).fetchone()[0],
                self.k.store._db.execute('SELECT COALESCE(MAX(sequence),0) FROM kernel_records WHERE run_id=?', (self.k.run_id,)).fetchone()[0])

    def _events(self, cutoff, episode_id=None):
        sql = "SELECT e.* FROM events e WHERE e.run_id=? AND e.visibility='CHAMBER' AND e.sequence<=?"
        args = [self.k.run_id, cutoff]
        if episode_id:
            sql += ' AND EXISTS(SELECT 1 FROM event_episodes x WHERE x.run_id=e.run_id AND x.event_id=e.id AND x.episode_id=?)'
            args.append(episode_id)
        return self.k.store._db.execute(sql + ' ORDER BY e.sequence,e.id', args)

    def _object_rows(self, cutoff):
        if self.k.config.arm == 'B':
            return []
        return self.k.store._db.execute('''SELECT a.* FROM kernel_records a WHERE run_id=? AND kind='OBJECT' AND sequence<=?
            AND NOT EXISTS(SELECT 1 FROM kernel_records b WHERE b.run_id=a.run_id AND b.kind=a.kind AND b.id=a.id
                AND b.sequence<=? AND b.revision>a.revision) ORDER BY a.sequence,a.id''', (self.k.run_id, cutoff, cutoff))

    def _payload_allowed(self, key, event_cutoff, record_cutoff):
        if self.k.store._db.execute("SELECT 1 FROM events WHERE run_id=? AND visibility='CHAMBER' AND sequence<=? AND payload_id=?",
                                  (self.k.run_id, event_cutoff, key)).fetchone():
            return True
        for row in self._object_rows(record_cutoff):
            if row['payload_id'] == key:
                obj = parse(StoredObject, self.k.store.read_payload(self.k.run_id, key))
                return self.k.config.arm == 'A' or obj.object_type == 'COMMITMENT'
        if self.k.config.arm != 'B' and self.k.store._db.execute(
                "SELECT 1 FROM kernel_records WHERE run_id=? AND kind='MEMORY_HEAD' AND sequence<=? AND payload_id=?",
                (self.k.run_id, record_cutoff, key)).fetchone():
            return True
        # Only fixed, Kernel-owned record types confer indirect payload access.
        for row in self.k.store._db.execute("SELECT kind,payload_id FROM kernel_records WHERE run_id=? AND sequence<=? AND kind IN ('ACTION','INVOCATION')",
                                            (self.k.run_id, record_cutoff)):
            value = load_json(self.k.store.read_payload(self.k.run_id, row['payload_id']))
            fields = ('request_payload_id',) if row['kind'] == 'ACTION' else ('input_payload_id', 'output_payload_id')
            if key in [value.get(field) for field in fields]:
                return True
        return False

    def _entries(self, query, event_cutoff, record_cutoff):
        dependencies, entries = [], []
        if isinstance(query, StateQuery):
            if self.k.config.arm == 'B':
                raise PermissionError('arm B has no semantic state channel')
            for row in self.k.store._db.execute("SELECT payload_id FROM kernel_records WHERE run_id=? AND kind='MEMORY_HEAD' AND sequence<=? ORDER BY sequence",
                                                (self.k.run_id, record_cutoff)):
                raw = self.k.store.read_payload(self.k.run_id, row['payload_id'])
                value = load_json(raw)
                if value['state_id'] == query.state_id:
                    dependencies.append(row['payload_id'])
                    entries.append({'id': query.state_id, 'payload_id': row['payload_id'], 'sources': ['M'],
                                    'sha256': sha256(raw).hexdigest(), 'bytes': len(raw)})
                    break
        elif isinstance(query, ObjectQuery):
            for row in self._object_rows(record_cutoff):
                try:
                    obj = parse(StoredObject, self.k.store.read_payload(self.k.run_id, row['payload_id']))
                except EvidenceUnavailable:
                    entries.append({'id': row['id'], 'revision': row['revision'], 'disposition': 'REMOVED', 'sources': ['M']})
                    continue
                if (self.k.config.arm == 'C' and obj.object_type != 'COMMITMENT' or
                        query.object_id is not None and obj.object_id != query.object_id or
                        query.object_type is not None and obj.object_type != query.object_type or
                        query.status is not None and obj.status != query.status):
                    continue
                dependencies.append(row['payload_id'])
                entries.append({'id': obj.object_id, 'revision': obj.revision, 'type': obj.object_type,
                                'status': obj.status, 'payload_id': row['payload_id'], 'sources': ['M'],
                                'sha256': sha256(canonical_bytes(obj)).hexdigest(), 'bytes': len(canonical_bytes(obj))})
        else:
            if isinstance(query, ManifestQuery):
                _, episode = self.k.store.control(self.k.run_id, query.episode_id)
                if episode.kind != 'EPISODE':
                    raise ValueError('manifest target is not an Episode')
            rows = self._events(event_cutoff, query.episode_id if isinstance(query, ManifestQuery) else None)
            for row in rows:
                if isinstance(query, EventQuery) and row['id'] != query.event_id:
                    continue
                if isinstance(query, RangeQuery) and (row['sequence'] < query.first_sequence or
                        query.last_sequence is not None and row['sequence'] > query.last_sequence):
                    continue
                rank = 0
                try:
                    raw = self.k.store.read_payload(self.k.run_id, row['payload_id'])
                except EvidenceUnavailable:
                    entries.append({'id': row['id'], 'sequence': row['sequence'], 'disposition': 'REMOVED', 'sources': [row['source']]})
                    continue
                if isinstance(query, SearchQuery):
                    rank = raw.decode('utf-8', errors='replace').casefold().count(query.text.casefold())
                    if rank == 0:
                        continue
                dependencies.append(row['payload_id'])
                entries.append({'id': row['id'], 'sequence': row['sequence'], 'payload_id': row['payload_id'],
                                'sha256': sha256(raw).hexdigest(), 'bytes': len(raw), 'sources': [row['source']], 'rank': rank})
            if isinstance(query, SearchQuery):
                entries.sort(key=lambda e: (-e.get('rank', 0), e['sequence'], e['id']))
        return entries, dependencies

    def _page_view(self, response):
        """Version-specific presentation, before budgeting and durable retention."""
        return response

    def retrieve(self, session, episode_id, raw):
        request = parse(PageRequest, raw)
        self.gate(session, episode_id)
        with self.k.store._transaction('retrieval'):
            self.gate(session, episode_id)
            key = session.role + ':' + request.request_id
            prior = self.k.records.get('RETRIEVAL', key)
            if prior:
                if self.k.store.read_payload(self.k.run_id, prior['request_payload_id']) != raw or prior['episode_id'] != episode_id:
                    raise RequestConflict('changed retrieval request under the same key')
                for source in prior['dependencies']:
                    self.k.store.read_payload(self.k.run_id, source)
                return self.k.store.read_payload(self.k.run_id, prior['response_payload_id'])
            if request.cursor:
                cursor = self.k.records.get('CURSOR', request.cursor)
                if cursor is None or cursor['role'] != session.role or cursor['query'] != request.query.model_dump(mode='json'):
                    raise ValueError('foreign/stale cursor scope or changed query')
                event_cutoff, record_cutoff, offset = cursor['event_cutoff'], cursor['record_cutoff'], cursor['offset']
                manifest_payload = cursor['manifest_payload_id']
            else:
                event_cutoff, record_cutoff = self._cutoff()
                offset = 0
                manifest_payload = None
            budget = self.k.config.budgets
            dependencies, entries, data = [], [], None
            if isinstance(request.query, PayloadQuery):
                payload_id = request.query.payload_id
                if not self._payload_allowed(payload_id, event_cutoff, record_cutoff):
                    raise PermissionError('unknown, foreign or invisible payload')
                body = self.k.store.read_payload(self.k.run_id, payload_id)
                dependencies = [payload_id]
                piece = body[offset:offset + budget.page_bytes]
                data = {'payload_id': payload_id, 'encoding': 'base64', 'data': base64.b64encode(piece).decode(),
                        'sha256': sha256(body).hexdigest(), 'total_bytes': len(body)}
                next_offset, total, returned_bytes = offset + len(piece), len(body), len(piece)
            else:
                if manifest_payload:
                    manifest = load_json(self.k.store.read_payload(self.k.run_id, manifest_payload))
                    all_entries, dependencies = manifest['entries'], manifest['dependencies']
                    for source in dependencies:
                        self.k.store.read_payload(self.k.run_id, source)
                else:
                    all_entries, dependencies = self._entries(request.query, event_cutoff, record_cutoff)
                    manifest_payload = self.k.store._payload(self.k.run_id,
                        canonical_bytes({'entries': all_entries, 'dependencies': dependencies}), sources=dependencies)
                total, next_offset = len(all_entries), offset
                while next_offset < total:
                    candidate = entries + [all_entries[next_offset]]
                    if len(canonical_bytes(candidate)) > budget.page_bytes:
                        break
                    entries = candidate
                    next_offset += 1
                if next_offset == offset and offset < total:
                    raise ValueError('one index entry cannot fit configured page budget')
                returned_bytes = len(canonical_bytes(entries))
            more = next_offset < total
            next_cursor = identifier() if more else None
            response = {'cutoff': event_cutoff, 'record_cutoff': record_cutoff, 'offset': offset, 'total': total,
                        'entries': entries, 'payload': data, 'returned_bytes': returned_bytes,
                        'truncated': more, 'next_cursor': next_cursor, 'end': not more,
                        'disposition': 'FOUND' if total else 'EMPTY'}
            encoded = canonical_bytes(self._page_view(response))
            if len(encoded) > budget.page_tokens:
                raise ValueError('serialized page token budget exceeded')
            tokens = self.k.count(encoded.decode()) if self.k.config.contract_version == '0.4' else len(encoded)
            if self.k.config.contract_version == '0.4' and tokens > budget.evidence_tokens:
                raise ValueError('retrieval page exceeds actual evidence token allowance')
            if more:
                self.k.records.put('CURSOR', next_cursor, {'role': session.role, 'query': request.query.model_dump(mode='json'),
                    'event_cutoff': event_cutoff, 'record_cutoff': record_cutoff, 'offset': next_offset,
                    'manifest_payload_id': manifest_payload}, expected=0)
            request_payload = self.k.store._payload(self.k.run_id, raw)
            response_payload = self.k.store._payload(self.k.run_id, encoded, sources=dependencies)
            self.k.records.put('RETRIEVAL', key, {'request_payload_id': request_payload, 'response_payload_id': response_payload,
                'dependencies': dependencies, 'episode_id': episode_id, 'bytes': returned_bytes, 'tokens': tokens}, expected=0)
            self.k.event({'kind': 'RETRIEVAL', 'request_id': request.request_id, 'response_payload_id': response_payload}, episode_id=episode_id)
            return encoded

    def semantic_view(self, objective_id):
        if self.k.config.arm == 'B':
            return None
        continuity = self.k.memory.continuity()
        if continuity is None:
            return {'continuity': None, 'selected_objects': [], 'inapplicable_count': 0, 'change_cursor': None}
        selected, omitted = [], 0
        objects = self.k.memory.objects()
        for ref in continuity.selected_objects:
            obj = objects.get(ref.object_id)
            applicable = (obj is not None and obj.status in SELECTABLE[obj.object_type] and
                          (obj.objective_id == objective_id or obj.object_type.startswith('INVARIANT') and obj.objective_id is None))
            if applicable:
                selected.append(obj.model_dump(mode='json'))
            else:
                omitted += 1
        value = {'continuity': continuity.model_dump(mode='json'), 'selected_objects': selected,
                 'inapplicable_count': omitted, 'change_cursor': self.k.memory.head if omitted else None}
        selected_ids = {obj['object_id'] for obj in selected}
        value['continuity']['selected_objects'] = [r for r in value['continuity']['selected_objects'] if r['object_id'] in selected_ids]
        if continuity.focus_objective_id != objective_id:
            value['continuity']['focus_objective_id'] = None
            value['continuity']['next_steps'] = []
            value['change_cursor'] = self.k.memory.head
        if len(canonical_bytes(value)) > self.k.config.budgets.active_semantic_tokens:
            raise ValueError('active semantic bundle exceeds budget; recovery required')
        return value

    def control_view(self):
        run = self.k.run()[1]
        objective = self.k.store.control(self.k.run_id, run.objective_id)[1] if run.objective_id else None
        grants = [value for _, value in self.k.records.latest('GRANT') if value['status'] == 'ACTIVE']
        if len(grants) > self.k.config.budgets.active_grants:
            raise ValueError('control view exceeds active Grant limit')
        control = {'run_status': run.status, 'objective': objective.model_dump(mode='json') if objective else None,
                   'grants': grants, 'hold_count': sum(h.status == 'HELD' for _, _, h in self.k.controls('WELFARE_HOLD')),
                   'task_tick': run.task_tick, 'skipped_count': sum(e.disposition == 'SKIPPED' for _, _, e in self.k.controls('EPISODE'))}
        preflight = self.k.records.get('PREFLIGHT', self.k.run_id)
        if preflight is None or len(canonical_bytes(control)) > preflight['maximum_control_tokens']:
            raise ValueError('control header cannot fit sealed maximum')
        return control

    def base(self, role, episode_id, *, recovery=False):
        if role not in {'OPERATOR', 'STEWARD'}:
            raise ValueError('unknown chamber role')
        run = self.k.run()[1]
        control = self.control_view()
        event_cutoff, record_cutoff = self._cutoff()
        rows = list(self._events(event_cutoff, episode_id))
        manifest, _ = self._entries(ManifestQuery(kind='MANIFEST', episode_id=episode_id), event_cutoff, record_cutoff)
        types = {}
        for row in rows:
            event_type = row['role'] + ':' + row['source']
            types[event_type] = types.get(event_type, 0) + 1
        index = {'cutoff': event_cutoff, 'count': len(rows), 'first': rows[0]['sequence'] if rows else None,
                 'last': rows[-1]['sequence'] if rows else None, 'sha256': sha256(canonical_bytes(manifest)).hexdigest(),
                 'counts_by_type': types, 'query': {'kind': 'MANIFEST', 'episode_id': episode_id}}
        semantic = ({'state_id': self.k.memory.head, 'failure': 'SEMANTIC_BASE_TOO_LARGE',
                     'sha256': (sha256(self.k.store.read_payload(self.k.run_id,
                         self.k.records.row('MEMORY_HEAD', self.k.run_id)['payload_id'])).hexdigest() if self.k.memory.head else None),
                     'query': ({'kind': 'STATE', 'state_id': self.k.memory.head} if self.k.memory.head else None)}
                    if recovery else self.semantic_view(run.objective_id))
        return {'mode': 'SCRIPTED', 'role': role, 'constitution': self.k.artifact('protocol').decode(),
                'charter': self.k.artifact('charter').decode(), 'memory_policy': self.k.artifact('routine_memory_policy').decode(),
                'prompt': self.k.artifact('operator_prompt' if role == 'OPERATOR' else 'steward_prompt').decode(),
                'tools': load_json(self.k.artifact('tools')) if role == 'OPERATOR' else {'retrieval_only': True},
                'participation': self.k.artifact('participation_notices').decode(), 'ending': self.k.artifact('ending_notice').decode(),
                'control': control, 'semantic': semantic, 'evidence': index, 'budgets': self.k.config.budgets.model_dump(mode='json')}

    def assemble(self, base, *, exchange, pages):
        if len(canonical_bytes(exchange)) > self.k.config.budgets.exchange_tokens:
            raise ValueError('exchange budget exceeded; retain result and interrupt')
        selected = []
        admitted = {v['response_payload_id']: v for _, v in self.k.records.latest('RETRIEVAL')}
        if len(set(pages)) != len(pages) or not set(pages) <= set(admitted):
            raise PermissionError('working pages must be unique admitted retrieval responses')
        for payload_id in pages:
            for source in admitted[payload_id]['dependencies']:
                self.k.store.read_payload(self.k.run_id, source)
            body = self.k.store.read_payload(self.k.run_id, payload_id)
            if len(body) > self.k.config.budgets.page_tokens:
                raise ValueError('loaded page exceeds token limit')
            selected.append(load_json(body))
        raw = canonical_bytes({'base': base, 'exchange': exchange, 'pages': selected})
        if len(raw) + self.k.config.budgets.reserved_output_tokens > self.k.config.budgets.input_tokens:
            raise ValueError('complete framed input plus output reservation exceeds ceiling')
        return raw

    def select_pages(self, attempt_id, *, add, release):
        if len(set(add)) != len(add) or len(set(release)) != len(release) or set(add) & set(release):
            raise ValueError('page selection lists must be disjoint sets')
        with self.k.store._transaction('page-selection'):
            previous = self.k.records.get('PAGE_SELECTION', attempt_id, {'pages': []})['pages']
            if not set(release) <= set(previous) or set(add) & set(previous):
                raise ValueError('explicit release/add must match current pages')
            allowed = {v['response_payload_id'] for _, v in self.k.records.latest('RETRIEVAL')}
            if not set(add) <= allowed:
                raise PermissionError('only admitted retrieval pages may enter working input')
            pages = [p for p in previous if p not in release] + list(add)
            for key in pages:
                self.k.store.read_payload(self.k.run_id, key)
            self.k.records.put('PAGE_SELECTION', attempt_id, {'pages': pages},
                               expected=self.k.records.revision('PAGE_SELECTION', attempt_id))
            self.k.event({'kind': 'PAGE_SELECTION', 'attempt_id': attempt_id, 'added': list(add), 'released': list(release)})
            return pages
