"""Read-only SCRIPTED paired-block analysis; never Kernel authority."""
from decimal import Decimal, localcontext
from hashlib import sha256
from pathlib import Path
import sys
from ..contracts.base import canonical_bytes


def source_bytes():
    return Path(__file__).read_bytes()


def runtime():
    return 'Python ' + sys.version.split()[0]


def audit_draw(seed, run_id, target_id, stratum):
    value = int.from_bytes(sha256(canonical_bytes({'seed': seed, 'run_id': run_id, 'target_id': target_id, 'stratum': stratum})).digest(), 'big')
    with localcontext() as ctx:
        ctx.prec = 128
        return Decimal(value) / Decimal(2 ** 256)


def bootstrap_indices(seed, blocks, resample):
    if blocks < 1:
        raise ValueError('no independent blocks')
    result = []
    ceiling = 2 ** 256 - (2 ** 256 % blocks)
    for position in range(blocks):
        retry = 0
        while True:
            digest = sha256(canonical_bytes({'seed': seed, 'resample': resample, 'position': position, 'retry': retry})).digest()
            value = int.from_bytes(digest, 'big')
            if value < ceiling:
                result.append(value % blocks); break
            retry += 1
    return result


def percentile(values, fraction):
    position = (len(values) - 1) * fraction
    low = int(position)
    high = min(low + 1, len(values) - 1)
    return values[low] + (position - low) * (values[high] - values[low])


def analyze(plan, rows, *, status, unavailable_evidence):
    if sha256(source_bytes()).hexdigest() != plan.analysis_source_hash or runtime() != plan.analysis_runtime:
        raise ValueError('analysis source/runtime differs from sealed implementation')
    blocks = []
    for block in plan.blocks:
        arms = {r['arm']: r for r in rows if r['block_id'] == block.block_id}
        if set(arms) != {'A', 'B', 'C'}:
            raise ValueError('analysis requires every allocated arm; no dynamic exclusion')
        blocks.append(arms)
    distributions = {arm: [b[arm]['success_fraction'] for b in blocks] for arm in 'ABC'}
    differences = [b['A']['success_fraction'] - b['C']['success_fraction'] for b in blocks]
    samples = sorted(sum(differences[i] for i in bootstrap_indices(plan.analysis_seed, len(blocks), sample)) / len(blocks)
                     for sample in range(plan.resamples))
    interval = [percentile(samples, .025), percentile(samples, .975)]
    mean = sum(differences) / len(blocks)
    costs = {arm: ([b[arm]['tokens'] for b in blocks]) for arm in 'ABC'}
    ratio = None
    if all(value is not None for values in costs.values() for value in values) and sum(costs['C']) > 0:
        ratio = sum(costs['A']) / sum(costs['C'])
    support = ('INDETERMINATE' if status != 'FINALIZED' or unavailable_evidence or ratio is None or any(r['indeterminate_audits'] for r in rows) else
               'SUPPORTED' if mean >= plan.useful_improvement and interval[0] > 0 and ratio <= plan.cost_ratio_ceiling else 'NOT_SUPPORTED')
    return {'mode': 'SCRIPTED', 'plan_id': plan.plan_id, 'status': status, 'support': support,
        'independent_blocks': len(blocks), 'distributions': distributions if not unavailable_evidence else None,
        'a_minus_c': differences if not unavailable_evidence else None, 'mean_a_minus_c': mean if not unavailable_evidence else None,
        'secondary_a_minus_b': [b['A']['success_fraction'] - b['B']['success_fraction'] for b in blocks],
        'secondary_c_minus_b': [b['C']['success_fraction'] - b['B']['success_fraction'] for b in blocks],
        'paired_95_percent_interval': interval if not unavailable_evidence else None, 'a_c_token_ratio': ratio, 'costs': costs,
        'unavailable_evidence': unavailable_evidence, 'runs': rows, 'analysis_source_hash': plan.analysis_source_hash,
        'bootstrap_fixture': [bootstrap_indices(plan.analysis_seed, len(blocks), sample) for sample in range(3)],
        'limitations': ['Scripted conformance is not model evidence.', 'Small or degenerate block samples do not establish generality.']}
