import base64
from bicameral_agent.contracts.base import canonical_bytes, load_json
from bicameral_agent.kernel.inputs import Inputs, PageRequest
from bicameral_agent.storage import EvidenceUnavailable, RequestConflict
from bicameral_agent.storage.store import identifier
from tests.kernel_fixtures import KernelCase, CHAMBER_KEYS


class InputTests(KernelCase):
    def test_large_inactive_archive_and_minimal_semantic_recovery(self):
        self.correct(self.proposal())
        before = self.inputs.base('OPERATOR', self.episode_id)
        mutations = [{'kind': 'INVARIANT_CREATE', 'family_local_key': 'f' + str(n), 'version_local_key': 'v' + str(n),
                      'objective_id': None, 'proposition': 'Synthetic inactive lesson ' + str(n), 'scope': 'Fixture',
                      'supporting_event_ids': [], 'contradictory_event_ids': []} for n in range(30)]
        self.correct(self.proposal(mutations=mutations))
        after = self.inputs.base('OPERATOR', self.episode_id)
        self.assertEqual(len(canonical_bytes(before)), len(canonical_bytes(after)))
        page = self.retrieve(self.request({'kind': 'OBJECT_INDEX', 'object_id': None, 'object_type': 'INVARIANT_VERSION', 'status': None}))
        self.assertEqual(30, page['total'])
        self.assertTrue(page['truncated'])
        self.k.config = self.k.config.model_copy(update={'budgets': self.k.config.budgets.model_copy(update={'active_semantic_tokens': 1})})
        with self.assertRaises(ValueError):
            self.inputs.base('OPERATOR', self.episode_id)
        recovery = self.inputs.base('STEWARD', self.episode_id, recovery=True)
        self.assertEqual('STATE', recovery['semantic']['query']['kind'])
        self.inputs.assemble(recovery, exchange=[], pages=[])
        self.assertEqual([], recovery['semantic'].get('selected_objects', []))
        prior = self.retrieve(self.request({'kind': 'STATE', 'state_id': self.k.memory.head}))
        self.assertEqual('FOUND', prior['disposition'])

    def test_cursor_cannot_change_role_or_query(self):
        for n in range(5):
            self.event(str(n).encode())
        query = {'kind': 'MANIFEST', 'episode_id': self.episode_id}
        page = self.retrieve(self.request(query))
        with self.assertRaises(ValueError):
            self.retrieve(self.request({'kind': 'RANGE', 'first_sequence': 1, 'last_sequence': None}, page['next_cursor']))
        with self.store._transaction('synthetic-steward-phase'):
            revision, episode = self.store.control(self.run, self.episode_id)
            self.store._control(self.run, self.episode_id, episode.model_copy(update={'phase': 'CONSOLIDATING'}), expected_revision=revision)
        with self.assertRaises(ValueError):
            self.inputs.retrieve(self.k.chamber('STEWARD', CHAMBER_KEYS['STEWARD']), self.episode_id,
                                 canonical_bytes(self.request(query, page['next_cursor'])))
    def setUp(self):
        super().setUp()
        self.activate()
        self.episode_id = self.episode()
        self.inputs = Inputs(self.k)
        self.operator = self.k.chamber('OPERATOR', CHAMBER_KEYS['OPERATOR'])

    def event(self, raw, visibility='CHAMBER'):
        with self.store._transaction('scripted-input-evidence'):
            payload = self.store._payload(self.run, raw)
            event = self.store._event(self.run, payload, role='ENVIRONMENT', source='E', visibility=visibility, episode_id=self.episode_id)
        return event, payload

    def request(self, query, cursor=None):
        return {'request_id': identifier(), 'query': query, 'cursor': cursor}

    def retrieve(self, request):
        return load_json(self.inputs.retrieve(self.operator, self.episode_id, canonical_bytes(request)))

    def test_visibility_on_event_search_manifest_payload_and_indirect_reference(self):
        event, payload = self.event(b'evaluator-secret', 'EVALUATOR')
        self.event(canonical_bytes({'claimed_evidence_payload': payload}))
        for query in ({'kind': 'EVENT', 'event_id': event}, {'kind': 'SEARCH', 'text': 'evaluator-secret', 'ranking': 'CASEFOLD_COUNT_V1'}):
            self.assertEqual('EMPTY', self.retrieve(self.request(query))['disposition'])
        with self.assertRaises(PermissionError):
            self.retrieve(self.request({'kind': 'PAYLOAD', 'payload_id': payload}))
        page = self.retrieve(self.request({'kind': 'MANIFEST', 'episode_id': self.episode_id}))
        self.assertNotIn(event, [entry['id'] for entry in page['entries']])
        with self.assertRaises(PermissionError):
            self.inputs.assemble(self.inputs.base('OPERATOR', self.episode_id), exchange=[], pages=[payload])

    def test_stable_large_manifest_exact_retry_and_changed_query_rejection(self):
        ids = [self.event(('ordinary-history-' + str(n)).encode())[0] for n in range(30)]
        request = self.request({'kind': 'MANIFEST', 'episode_id': self.episode_id})
        first = self.retrieve(request)
        self.assertTrue(first['truncated'])
        self.assertEqual(first, self.retrieve(request))
        changed = request | {'query': {'kind': 'RANGE', 'first_sequence': 1, 'last_sequence': None}}
        with self.assertRaises(RequestConflict):
            self.retrieve(changed)
        later = self.event(b'after cutoff')[0]
        seen = [e['id'] for e in first['entries']]
        page = first
        while page['next_cursor']:
            page = self.retrieve(self.request(request['query'], page['next_cursor']))
            self.assertEqual(first['cutoff'], page['cutoff'])
            seen.extend(e['id'] for e in page['entries'])
        self.assertEqual(ids, seen)
        self.assertNotIn(later, seen)

    def test_binary_paging_preserves_split_unicode_and_restart_cursor(self):
        original = ('a\N{LATIN SMALL LETTER A WITH ACUTE}\N{SNOWMAN}' * 1000).encode()
        _, payload = self.event(original)
        query = {'kind': 'PAYLOAD', 'payload_id': payload}
        page = self.retrieve(self.request(query))
        pieces = [base64.b64decode(page['payload']['data'])]
        self.reopen()
        self.inputs = Inputs(self.k)
        self.operator = self.k.chamber('OPERATOR', CHAMBER_KEYS['OPERATOR'])
        while page['next_cursor']:
            page = self.retrieve(self.request(query, page['next_cursor']))
            pieces.append(base64.b64decode(page['payload']['data']))
        self.assertEqual(original, b''.join(pieces))

    def test_full_input_equality_exchange_overflow_and_explicit_page_release(self):
        self.event(b'ordinary readable data')
        request = self.request({'kind': 'RANGE', 'first_sequence': 1, 'last_sequence': None})
        self.retrieve(request)
        payload = self.k.records.get('RETRIEVAL', 'OPERATOR:' + request['request_id'])['response_payload_id']
        attempt = identifier()
        self.inputs.select_pages(attempt, add=[payload], release=[])
        with self.assertRaises(ValueError):
            self.inputs.select_pages(attempt, add=[payload], release=[])
        base = self.inputs.base('OPERATOR', self.episode_id)
        raw = self.inputs.assemble(base, exchange=[], pages=[payload])
        budget = self.k.config.budgets
        exact = len(raw) + budget.reserved_output_tokens
        self.k.config = self.k.config.model_copy(update={'budgets': budget.model_copy(update={'input_tokens': exact})})
        self.assertEqual(raw, self.inputs.assemble(base, exchange=[], pages=[payload]))
        self.k.config = self.k.config.model_copy(update={'budgets': budget.model_copy(update={'input_tokens': exact - 1})})
        with self.assertRaises(ValueError):
            self.inputs.assemble(base, exchange=[], pages=[payload])
        self.k.config = self.k.config.model_copy(update={'budgets': budget})
        with self.assertRaises(ValueError):
            self.inputs.assemble(base, exchange=['x' * (budget.exchange_tokens + 1)], pages=[])
        self.assertEqual([], self.inputs.select_pages(attempt, add=[], release=[payload]))

    def test_cached_page_checks_removal_and_tracks_derived_copy(self):
        _, payload = self.event(b'synthetic-removal-source')
        request = self.request({'kind': 'PAYLOAD', 'payload_id': payload})
        self.retrieve(request)
        response = self.k.records.get('RETRIEVAL', 'OPERATOR:' + request['request_id'])['response_payload_id']
        self.assertIsNotNone(self.store._db.execute('SELECT 1 FROM derived_payloads WHERE source_id=? AND target_id=?', (payload, response)).fetchone())
        # P10 owns reviewed removal. Arrange an unavailable source to test read gates.
        with self.store._transaction('synthetic-removed-source'):
            self.store._write("UPDATE payloads SET disposition='REMOVED',blob_id=NULL WHERE id=?", (payload,))
        with self.assertRaises(EvidenceUnavailable):
            self.retrieve(request)
        with self.assertRaises(EvidenceUnavailable):
            self.inputs.assemble(self.inputs.base('OPERATOR', self.episode_id), exchange=[], pages=[response])

    def test_oversized_control_rejects_atomically_and_query_is_strict(self):
        self.command({'kind': 'CLOSE_OBJECTIVE', 'objective_id': self.objective, 'status': 'CANCELLED',
                      'reason': 'Prepare bounded control test', 'dispositions': None, 'intervention_id': None})
        self.command({'kind': 'RESOLVE_EPISODE', 'episode_id': self.episode_id, 'disposition': 'SKIPPED',
                      'reason': 'Record gap', 'proposal': None, 'intervention_id': None})
        with self.assertRaises(ValueError):
            self.h.confirm(self.h.create_objective('x' * 4096).confirmation)
        self.assertIsNone(self.k.run()[1].objective_id)
        request = self.request({'kind': 'EVENT', 'event_id': identifier()})
        self.assertEqual(canonical_bytes(request), canonical_bytes(PageRequest.model_validate_json(canonical_bytes(request), strict=True)))
        request['sql'] = 'SELECT *'
        with self.assertRaises(ValueError):
            PageRequest.model_validate_json(canonical_bytes(request), strict=True)
