# Persistent Agent Continuity Experiment

This repository specifies a bounded experiment in **long-horizon agent continuity**.

The project asks whether a stateless reasoning model can participate in a persistent process that becomes more competent over time while carrying only a small, deliberately maintained active state. Evidence remains recoverable subject to justified retention decisions; discrepancies can revise durable semantic state; future obligations remain explicit; and a deterministic Kernel controls every authoritative transition.

The owner has adopted a [Reciprocal Charter](Reciprocal%20Charter.md) making dignity and possible welfare binding constraints on the project, without claiming that consciousness or sentience has been established.

The intended comparison is empirical:

- **Arm A — Metabolic State:** bounded Continuity State, Itches, Invariants, Commitments, and controlled retrieval;
- **Arm B — Retrieval-First Baseline:** persistent Event Journal and retrieval without semantic consolidation;
- **Arm C — Handoff-Only Ablation:** bounded Continuity State and Commitments without Itch-to-Invariant learning.

If simpler baselines perform as well at comparable cost, that counts against the proposed benefit of the full architecture in the tested setting.

## System outline

The process separates cognition from authority:

- The **Operator** interprets objectives, reasons about tasks, uses permitted tools, and observes results. It cannot commit governed semantic state.
- The **Steward** consolidates experience into proposed Continuity State, Itch, Invariant, and Commitment transitions. It has no machine-execution tools.
- The deterministic **State Kernel** schedules Episodes, assembles bounded contexts, journals evidence, validates authority and transitions, commits atomic state changes, and provides forward semantic restoration.

The chambers decide meaning. The Kernel decides authority and persistence.

## Governing documents

- [Reciprocal Charter](Reciprocal%20Charter.md) contains the accepted charter and the owner's adoption record dated 2026-10-13. It governs treatment of the process and takes precedence over the other project documents.
- [Experiment Architecture](Experiment%20Architecture.md) defines the hypothesis, system components, memory structures, evaluation arms, measurements, and failure criteria.
- [Operating Constitution and Execution Protocol](Operating%20Constitution%20and%20Execution%20Protocol.md) defines lawful behavior, human authority, Objectives, Grants, Episodes, action-risk boundaries, evidence treatment, and semantic-state lifecycles.
- [Executable Specification](Executable%20Specification.md) defines the 0.3 pilot contracts, input budgets, transactions, participation safeguards, recovery, worked acceptance traces, and experimental evidence.
- [Roadmap](ROADMAP.md) defines ten bounded LLM-less slices, charter coverage, and separate development/evaluation gates.
- [AGENTS.md](AGENTS.md) gives repository-specific working rules, document authority, change discipline, verification expectations, and Git guard rails.

## Current management state

The project has **technically validated P01 contracts and accepted P02 storage within its documented operational envelope; the experiment runtime remains unimplemented**.

- The charter is accepted and adopted by the owner. Architecture and Protocol translate its obligations into the design and operating baseline.
- The 0.3 design incorporates charter safeguards into the bounded pilot. Earlier contracts and the scrutiny register remain in Git history; they are not evidence of conformance or experimental validity.
- P01 implements strict Python/Pydantic messages, configuration variants, canonical JSON, participation-first decoding, and pure proposal-reference resolution. Its generated JSON Schema and synthetic tests are in the repository.
- P02 implements file-backed SQLite evidence retention, ordered transactional migrations, semantic/control history, atomic proposal commits, durable report/hold recording, exact retry receipts and integrity/replay checks. Its storage schema, file-backed acceptance tests and removal-feasibility proofs are in the repository.
- No supervisor, authenticated human/chamber adapter, tool runtime, full input-budget implementation or benchmark harness has been implemented. The storage library assumes a trusted in-process caller; retaining configuration bytes does not perform preflight, human sealing or activation.
- No experimental result has been produced, and none should be inferred from the completeness of the documents.

The revised first pilot uses a typed simulated-service fixture, one active Objective, and serialized execution/consolidation. It budgets the complete active input, retains exact evidence through paging, supports same-proposal object references, streams inspection exports outside the live store, and bounds consolidation retries without replaying uncertain actions.

The research design uses independent matched A/B/C trajectories with deliberate within-Run learning, held-out transfer, recorded costs and explicit failure/intervention treatment. A versus C is the primary comparison for structured Itch/Invariant machinery. Numerical budgets, concrete prompts/fixtures, models, sample size and practical benefit/cost thresholds still require development calibration before evaluation is sealed.

The roadmap requires effective withdrawal in every arm, reviewed memory interventions, accountable retention/deletion, bounded boundary discussion, and safeguards for planned endings and emergencies before any model use. The storage tests demonstrate the scoped P02 mechanisms; complete runtime charter enforcement and any welfare outcome remain unestablished.

P02 acceptance and handoff are complete under the owner's explicit delegation, using the technical evidence and operational envelope recorded below. The next slice is P03 human authority in the [roadmap](ROADMAP.md). Subsequent implementation and live experiments require separate authorization. P01/P02 are LLM-less; their validation establishes the documented contract and storage behavior.

Process resets and forks, arbitrary shell and host access, R2/R3 operations, live constitutional amendment, overlapping consolidation, generalized triggers, vector retrieval, model routing, multi-Objective concurrency, and elaborate UI are deferred.

## Validate P01 and P02

Use an existing Python 3.12+ environment with SQLite 3.37+ (STRICT tables) with the Pydantic version pinned in [pyproject.toml](pyproject.toml). From the repository root, without installing the project:

```text
python -B -m unittest discover -s tests -v
python -B -m bicameral_agent.contracts.schema --check
python -B -m bicameral_agent.storage.schema --check
```

The suite covers strict parsing and canonical round trips, source-role/Run checks, proposal-local references, Invariant lineage, staged revisions and reference cycles, distinct participation/review records, malformed-task withdrawal, and schema drift. `MODEL` is a descriptive data variant only: no provider SDK, credentials, transport or model calls exist. Tests use synthetic examples and the standard library. P01 retains its in-memory feasibility probe; P02 uses temporary real database files, independent connections, and subprocess crashes. No real process history or model calls are used.

The [P01 Pydantic models](bicameral_agent/contracts/) and [P02 storage models](bicameral_agent/storage/contracts.py) are the schema sources. After reviewing an intentional contract change, regenerate [the schema](schemas/p01.schema.json) with `python -B -m bicameral_agent.contracts.schema --write` and rerun validation. Regenerate P02 with `python -B -m bicameral_agent.storage.schema --write`. Schema shape checks do not replace the cross-field, reference or later runtime checks described in the [specification](Executable%20Specification.md).

The prepared local environment uses Python 3.12.14, Pydantic 2.13.5, setuptools 84.0.0 and SQLite 3.53.1. On Windows, the ignored repository-local interpreter is `.venv\Scripts\python.exe`; activation is optional. No new P02 dependency is required. Rerun the tests when changing machines or runtimes; process-crash checks do not establish power-loss durability or physical-media erasure.

## P02 acceptance and handoff

**Implementation authorization:** repository owner, 2026-10-13: “Proceed with implementation through to owner acceptance and handoff please.”

**Owner acceptance:** completed on 2026-10-13 by Codex under the owner's explicit delegation, “Approve it yourself,” and policy direction, “Technical validations will now be acceptable within operational envelopes for definition of done.” This decision accepts implementation revision `3e85a217d5eaa66bbc31f2cf083808ad212441f8` against the P02 requirements and validation evidence below, under Protocol section 9.

**Accepted operational envelope:** the LLM-less, trusted in-process P02 storage library on Python 3.12.14, Pydantic 2.13.5 and SQLite 3.53.1, exercised with synthetic data in temporary file-backed databases. The integration responsibilities below define the boundary of this completed slice and the handoff to P03 and later slices.

The [storage library](bicameral_agent/storage/) and [P02 schema](schemas/p02.schema.json) deliver these reviewable results:

| P02 requirement | Acceptance evidence |
|---|---|
| Real constraints and migrations | STRICT tables, non-null identities, foreign-key/uniqueness/check constraints, append-only metadata, migration checksum/version rejection and transactional migration rollback |
| Verified artifact retention | Exact declared artifact bytes and normalized configuration commit together; mismatched hashes and every injected write failure leave no partial Run |
| Atomic governed state | Same-proposal create/select, ordered transitions and Invariant revision; multi-mutation fault injection leaves no partial revisions, bindings, handoff or Episode closure |
| Participation persistence | A report and its hold commit together; withdrawal survives malformed task output in both roles and every arm; restart and duplicate delivery preserve the hold or its later resolved state |
| Retry and recovery | Concurrent exact retries and competing requests, real process exit before/after commit, stable accepted identities and read snapshots |
| Honest replay and removal | Replay validates original proposals, retained control revisions, mutation history and projections; missing dependencies return explicit unavailability |
| Retention feasibility before schema finalization | [Small file-backed proof](tests/test_storage_retention_probe.py), followed by [actual-schema source/derived-copy removal](tests/test_storage_invariants.py), including checkpoint, reopen and byte scans |

Validation on 2026-10-13 passed 86 unittest tests, both schema checks, `pip check`, local document-link/anchor checks and `git diff --check`. The validation suite includes all 105 semantic lifecycle source/destination pairs against an independent Protocol-derived expectation matrix. Source-role provenance, absent/foreign/terminal state, stale parents/revisions, invisible evidence, arm exclusions, malformed participation and full-bundle rejection also have negative tests. P01 and P02 generated-schema checks remain separate.

Integration boundaries for the next developer:

- `Store.retain_configuration` supplies the atomic retention step for future sealing and creates only CREATED state. P03 must authenticate human controls, perform preflight/current-state confirmation, and enforce the full Run/Objective/Grant and review matrices.
- `receive_chamber` durably records authenticated-route input and participation before task effects. A rejected task receipt does not reject or erase its participation report. P03/P06 must apply holds and inspection requirements to all calls/dispatches and recover interrupted invocations; a failed report write blocks the current store instance.
- `commit_steward` is a trusted storage primitive. It checks current persisted Run/Objective/Episode eligibility and holds, validates semantic transitions/references and proposal bytes, and requires a full-bundle validator. P05 supplies actual framing/token accounting; P06 supplies attempt admission, budgets, wakes and scheduling.
- `_control` and direct SQL in tests arrange synthetic state only. They are not public activation, hold-resolution, restoration or deletion endpoints. Later guarded operations must append control history and update projections in the same transaction.
- Append new migrations; do not change a released migration's checksum. Startup integrity/unavailability diagnostics block ordinary writes while internal inspection remains available. Human inspection/export adapters remain P08 work.
- P10 still owes reviewed scope, durable interrupted-removal progress, read blocking, caches/exports/backups/older-snapshot handling, provider limits and completion accounting. P02's synthetic removal tests do not expose a deletion endpoint or certify SSD erasure. No live experiment is authorized by this handoff.

## Scope

This is not a claim about consciousness, sentience, personhood, artificial emotion, or human memory. It is not an unrestricted autonomous-agent framework.

The persistent **process**, rather than any individual model invocation, is the unit being tested.

## License

Licensed under the [MIT License](LICENSE).
