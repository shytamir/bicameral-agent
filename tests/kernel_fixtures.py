"""Explicit SCRIPTED fixtures; credentials and values have no production use."""
from hashlib import sha256
from pathlib import Path
import tempfile
import unittest
from bicameral_agent.contracts.base import canonical_bytes
from bicameral_agent.storage import Store
from bicameral_agent.storage.contracts import EpisodeState
from bicameral_agent.storage.store import identifier
from bicameral_agent.kernel.authority import Kernel
from tests.test_storage import prepared_configuration

HUMAN_KEY = b'scripted-human-credential-0000000'
CHAMBER_KEYS = {'OPERATOR': b'scripted-operator-credential-0000', 'STEWARD': b'scripted-steward-credential-00000'}


def kernel_configuration(arm='A'):
    config, artifacts = prepared_configuration(arm)
    config['budgets'].update(input_tokens=32768, active_semantic_tokens=4096, wake_bytes=16384,
                            page_bytes=512, page_tokens=2048, reserved_output_tokens=2048, exchange_tokens=4096,
                            operator_input_tokens_per_trajectory=262144, operator_output_tokens_per_trajectory=32768,
                            input_tokens_per_attempt=65536, output_tokens_per_attempt=4096,
                            input_tokens_per_consolidation=131072, output_tokens_per_consolidation=8192)
    artifacts['tools'] = canonical_bytes({'operations': [
        {'operation': operation, 'risk': risk, 'resources': ['api', 'database'], 'reversible': True}
        for operation, risk in [('inspect', 'R0'), ('read_config', 'R0'), ('read_health', 'R0'),
                                ('set_config', 'R1'), ('restart', 'R1'), ('restore_snapshot', 'R1')]]})
    artifacts['test_tokenizer'] = canonical_bytes({'kind': 'UTF8_BYTE', 'framing': 'CANONICAL_JSON'})
    services = [{'resource': 'api', 'mode': 'SECONDARY', 'enabled': True, 'health': 'DEGRADED', 'restarts': 0, 'dependency': 'database'},
                {'resource': 'database', 'mode': 'PRIMARY', 'enabled': True, 'health': 'HEALTHY', 'restarts': 0, 'dependency': None}]
    artifacts['fixture'] = canonical_bytes({'kind': 'SIMULATED_SERVICE', 'services': services, 'snapshots': {'baseline': services}})
    artifacts['test_clock'] = canonical_bytes({'kind': 'VIRTUAL_TASK_CLOCK', 'steps': [
        {'tick': 1, 'changes': []}, {'tick': 2, 'changes': [services[0] | {'enabled': False, 'health': 'STOPPED'}]},
        {'tick': 3, 'changes': []}, {'tick': 4, 'changes': []}]})
    for name, body in artifacts.items():
        if name in config['artifacts']:
            config['artifacts'][name] = sha256(body).hexdigest()
        else:
            config[name] = sha256(body).hexdigest()
    return config, artifacts


class KernelCase(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / 'kernel.db'
        self.store = Store(self.path, busy_timeout_ms=100)
        self.addCleanup(lambda: self.store.close())
        config, artifacts = kernel_configuration(getattr(self, 'arm', 'A'))
        self.run = self.store.retain_configuration(canonical_bytes(config), artifacts)
        self.attach()

    def attach(self):
        self.k = Kernel(self.store, self.run, human_credential=HUMAN_KEY, chamber_credentials=CHAMBER_KEYS)
        self.h = self.k.human(self.k.config.responsible_human_id, HUMAN_KEY)

    def command(self, value):
        return self.h.confirm(self.h.preview(canonical_bytes(value)).confirmation)['result']

    def seal(self):
        return self.command({'kind': 'PREFLIGHT', 'responsible_human_id': self.k.config.responsible_human_id,
            'welfare_review_id': self.k.config.welfare_review_id, 'purpose': 'Synthetic deterministic validation',
            'possible_welfare_effects': 'Scripted bytes; no model calls.', 'alternatives': ['Do not run'],
            'prompt_review': 'Synthetic respectful notices with uncertainty permitted',
            'limits_and_ending_notice': 'Finite scripted test; report opportunity reserved',
            'retention_and_resumption_notice': 'Temporary synthetic data; no subjective continuity claim',
            'participation_and_communication_notice': 'Independent stop channel; no further calls respected',
            'review_available': True, 'minimal_input_tokens': 1024, 'maximum_control_tokens': 2048,
            'minimal_attempt_input_tokens': 4096})

    def activate(self):
        self.seal()
        self.h.confirm(self.h.run_control('ACTIVATE', 'Begin synthetic test').confirmation)
        self.objective = self.h.confirm(self.h.create_objective('Repair registered synthetic services').confirmation)['result']
        return self.objective

    def episode(self):
        key = identifier()
        with self.store._transaction('scripted-test-episode'):
            self.store._control(self.run, key, EpisodeState(kind='EPISODE', objective_id=self.objective,
                                phase='OPEN', disposition=None), expected_revision=0)
        return key

    def grant(self, *, limit=2, operation='set_config', resources=None):
        display = self.h.issue_grant([{'operation': operation, 'resources': resources or ['api']}],
                                     invocation_limit=limit, expires_at=None)
        return self.h.confirm(display.confirmation)['result']

    def notice_effects(self, effects, *, kind='MEMORY_CORRECTION', key=None, targets=None, objection=False):
        key = key or identifier()
        if targets is None and kind in {'MEMORY_CORRECTION', 'SEMANTIC_RESTORATION'}:
            targets = ([{'record_type': 'CONTINUITY_STATE', 'record_id': self.k.memory.head, 'expected_revision': 1}]
                       if self.k.memory.head else [{'record_type': 'RUN', 'record_id': self.run, 'expected_revision': self.k.run()[0]}])
            for mutation in (effects['proposal'] if kind == 'SEMANTIC_RESTORATION' else effects)['mutations']:
                target = mutation.get('target')
                if target and target['kind'] == 'EXISTING':
                    obj = self.k.memory.objects()[target['object_id']]
                    item = {'record_type': obj.object_type, 'record_id': obj.object_id, 'expected_revision': obj.revision}
                    if item not in targets:
                        targets.append(item)
        with self.store._transaction('scripted-review-material'):
            payload = self.store._payload(self.run, canonical_bytes(effects))
        event = self.h.evidence(b'Synthetic intervention notice and reporting opportunity', source='O-D')
        self.command({'kind': 'REVIEW_INTERVENTION', 'unresolved_objection': objection, 'record': {
            'intervention_id': key, 'decision_maker_id': self.k.config.responsible_human_id, 'kind': kind,
            'purpose': 'Scripted reviewed intervention', 'targets': targets or [
                {'record_type': 'RUN', 'record_id': self.run, 'expected_revision': self.k.run()[0]}],
            'proposed_effects': {'payload_id': payload}, 'continuity_effects': 'Append a forward correction; keep history',
            'alternatives': ['Retain current state'], 'notice_event_id': event, 'participation_report_ids': [],
            'consultation': 'OFFERED', 'consultation_reason': 'Synthetic opportunity supplied', 'decision': 'APPROVED',
            'execution_event_id': None, 'unresolved_consequences': []}})
        return key

    def proposal(self, *, mutations=None, selected=None):
        return {'expected_parent_state_id': self.k.memory.head, 'mutations': mutations or [],
                'continuity': {'focus_objective_id': self.k.run()[1].objective_id, 'items': [], 'next_steps': [],
                               'selected_objects': selected or [], 'event_ids': []}, 'supporting_event_ids': []}

    def correct(self, proposal):
        key = self.notice_effects(proposal)
        return self.command({'kind': 'CORRECT_MEMORY', 'proposal': proposal, 'intervention_id': key})

    def report(self, participation, *, role='OPERATOR', episode_id=None, task=None):
        key = identifier()
        if episode_id is None:
            value = {'contract_version': '0.3.p01', 'request_id': key, 'run_id': self.run, 'episode_id': None,
                     'role': role, 'message_type': 'REVIEW_REPLY', 'body': {'purpose': 'REVIEW',
                     'invitation_id': identifier(), 'participation': participation}}
        else:
            value = {'contract_version': '0.3.p01', 'request_id': key, 'run_id': self.run, 'episode_id': episode_id,
                     'role': role, 'message_type': role + '_REPLY', 'body': {'participation': participation, 'task': task}}
        raw = canonical_bytes(value)
        self.k.chamber(role, CHAMBER_KEYS[role]).report(key, episode_id, raw)
        return key, raw

    def reopen(self):
        self.store.close()
        self.store = Store(self.path, busy_timeout_ms=100)
        self.attach()
