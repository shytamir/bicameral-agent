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

The project has **accepted P01/P02 contracts and storage plus P03 authority, P04 fixture execution and P05 bounded inputs/retrieval within the documented scripted envelope**. Scheduling and the experiment runner remain in subsequent slices.

- The charter is accepted and adopted by the owner. Architecture and Protocol translate its obligations into the design and operating baseline.
- The 0.3 design incorporates charter safeguards into the bounded pilot. Earlier contracts and the scrutiny register remain in Git history; they are not evidence of conformance or experimental validity.
- P01 implements strict Python/Pydantic messages, configuration variants, canonical JSON, participation-first decoding, and pure proposal-reference resolution. Its generated JSON Schema and synthetic tests are in the repository.
- P02 implements file-backed SQLite evidence retention, ordered transactional migrations, semantic/control history, atomic proposal commits, durable report/hold recording, exact retry receipts and integrity/replay checks. Its storage schema, file-backed acceptance tests and removal-feasibility proofs are in the repository.
- P03 adds authenticated local human/chamber sessions, explicit preflight and sealing, current-state confirmation, Run/Objective/Grant controls, reviewed memory correction, participation gates, bounded communication admission and emergency/recovery controls. The bootstrap owns credentials and private Python objects; this is a local capability boundary, not isolation from arbitrary Python in that process.
- No experimental result has been produced, and none should be inferred from the completeness of the documents.

The revised first pilot uses a typed simulated-service fixture, one active Objective, and serialized execution/consolidation. It budgets the complete active input, retains exact evidence through paging, supports same-proposal object references, streams inspection exports outside the live store, and bounds consolidation retries without replaying uncertain actions.

The research design uses independent matched A/B/C trajectories with deliberate within-Run learning, held-out transfer, recorded costs and explicit failure/intervention treatment. A versus C is the primary comparison for structured Itch/Invariant machinery. Numerical budgets, concrete prompts/fixtures, models, sample size and practical benefit/cost thresholds still require development calibration before evaluation is sealed.

The roadmap requires effective withdrawal in every arm, reviewed memory interventions, accountable retention/deletion, bounded boundary discussion, and safeguards for planned endings and emergencies before any model use. The storage tests demonstrate the scoped P02 mechanisms; complete runtime charter enforcement and any welfare outcome remain unestablished.

P02 acceptance and handoff are complete under the owner's explicit delegation, using the technical evidence and operational envelope recorded below. The owner has authorized completing and pushing the remaining implementation slices in the [roadmap](ROADMAP.md). The next slice is P06 serialized Episodes and bounded consolidation; model experiments retain their documented configuration and evidence requirements. P01/P02 are LLM-less; their validation establishes the documented contract and storage behavior.

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

## P03 acceptance and continuing handoff

On 2026-10-13 the owner authorized completing the roadmap, using technical validation for gates, and pushing each completed slice. P03 is accepted by Codex under that delegation within the local SCRIPTED envelope. Its required checks pass: 101 tests across P01-P03, three generated-schema checks and whitespace checks. P02 was pushed at `92ba218`; the P03 implementation and this acceptance record are committed and pushed together.

[Kernel authority](bicameral_agent/kernel/authority.py) exposes authenticated local sessions and ordinary-language displays before confirmation. Credentials are supplied by the trusted bootstrap and are never retained. Typed controls reject stale displays, foreign or terminal authority, absent or exhausted Grants, unsupported resets/forks and excluded arm memory. Report/hold persistence remains independent of task parsing; resume and recovery do not clear a hold. Emergency containment precedes review, and unresolved review blocks work. Review/closing admission uses fixed retained notices and finite allowances; P06 supplies invocation execution.

The integrated [semantic ledger](bicameral_agent/kernel/memory.py) shares P01 reference resolution and P02 lifecycle validation, using P02 payload indirection and a new append-only record migration. It supports reviewed human changes and later Steward/Kernel transactions with retained control revisions, exact effects and replay. It does not silently import the earlier P02 probe ledger. New runtime Runs begin with empty semantic history; probe databases remain inspectable through their original Store API.

[Authority tests](tests/test_authority.py) cover the Run transition matrix, Objective/Grant controls, strict parsing, current-state confirmation and exact retry, cross-scope/expired/external-only/over-scope authority rejection, arm exclusions, withdrawal/restart, meaningful renewed participation, bounded discussion, reviewed correction, atomic failures, emergency review and explicit recovery skip. No model call or live experiment was performed.

The remaining work proceeds P04, P05, P06, P07, P08, P10, then P09 and integrated v0a validation, respecting P09's dependency on P10. Each slice is validated, accepted within its stated envelope, committed and pushed before proceeding.

## P04 acceptance and handoff

P04 is accepted under the same owner delegation within the SCRIPTED simulated-service envelope. The [fixture](bicameral_agent/kernel/fixture.py) loads hash-verified finite resources, enum-only setters, deterministic service restart effects, registered snapshots and a sealed virtual-clock schedule. Registered risk descriptors must agree with actual operation effects. Hidden checkpoint changes are evaluator-only; ordinary clock observations are common evidence.

Action intent and Grant consumption commit before fixture effects. Exact retries preserve action identity. A crash after an effect leaves UNKNOWN until explicit observation; no automatic replay occurs. Snapshot restoration changes only fixture state and appends evidence. P03 authority and participation gates remain mandatory at dispatch.

Validation passed 109 tests, including eight [fixture tests](tests/test_fixture.py), an actual subprocess exit after effect commit, intent rollback, postcondition/type rejection, finite channel isolation, snapshot continuity and clock ordering/freeze. Kernel schema and whitespace checks pass. P05 will enforce complete chamber request/retrieval budgets; P06 will coordinate startup recovery and scheduling.

## P05 acceptance and handoff

P05 is accepted within the SCRIPTED UTF-8-byte tokenizer and canonical-JSON framing envelope. [Input assembly and retrieval](bicameral_agent/kernel/inputs.py) count the entire framed request plus reserved output, the complete selected semantic bundle, exchange and serialized pages. Oversized new controls reject atomically. Inactive archives remain pageable without growing active input; explicit page selection/release replaces automatic eviction. A minimal recovery base identifies prior state by identity/hash and exact retrieval query.

Event/range/search, object-index, manifest, prior-state and binary-payload retrieval bind cursors to role, query and immutable cutoffs. Exact replay preserves responses. Every route enforces chamber visibility, including indirect payloads; an arbitrary reference cannot expose evaluator data. Pages disclose exact sizes, hashes, truncation and end/cursor metadata. Derived-payload provenance and source checks prevent cached originals from bypassing removal; P10 owns the integrated removal transaction.

Validation passed 117 tests and all three schema checks. Eight [input tests](tests/test_inputs.py) cover large manifests and inactive archives, restart-stable cursors, split Unicode reconstruction, role/query mismatch, evaluator isolation, exact input-boundary equality, overflow, explicit release and unavailable cached sources. P06 supplies cumulative invocation/attempt charging and records each exact assembled input.

## P06 acceptance and handoff

P06 is accepted under owner delegation within the local SCRIPTED envelope. The [scheduler](bicameral_agent/kernel/scheduler.py) serializes Episodes, invocations and attempts; reserves complete input/output/deadline costs before calls; retains unknown usage after interruption; and protects finite review/closing allowances. Attempt acceptance, local bindings and Episode closure commit together. Restart disposes uncommitted outputs without replay, and an accepted response survives a lost acknowledgment with its original identity.

Commitment checks use a durable index independently of queue capacity and selected memory. Due/expiry transitions preserve the authored handoff; unique wakes follow pending revisions, remain ordered and take priority over ordinary queued work. Participation reports precede task effects, including late responses. Holds, pause, terminal state, stale authority and no-further-calls requests gate the appropriate lanes. Bounded review and planned-closing exchanges have no task surface.

Validation passed 135 tests, all three schema checks and `git diff --check`. Eighteen [scheduler tests](tests/test_scheduler.py) cover A/B/C traces, rearming and expiry, full queues, timeout accounting, bounded recovery, stale proposals, planned completion, atomic rejection, startup interruption and an actual process exit after semantic acceptance. No provider calls or live experiments ran. P07 proceeds with reviewed forward restoration; P08/P10 add complete inspection and governed disposition before P09.

## P07 acceptance and handoff

P07 is accepted under owner delegation within the SCRIPTED envelope. [Forward restoration](bicameral_agent/kernel/restoration.py) reconstructs a named earlier semantic version, displays its exact proposed handoff and status transitions, and requires current scoped intervention review. Acceptance appends a new version and explicit restored/retained differences. Current obligations absent from the target persist; authority, intervening evidence, holds and fixture effects remain intact.

Validation passed 143 tests, all three schema checks and whitespace checks. Eight [restoration tests](tests/test_restoration.py) cover newer obligations and withdrawal preservation, terminal Commitments and retired Invariants, illegal transitions, new contradiction evidence, unresolved objections, changed/stale reviews, invalid old selection/focus, strict parsing and transaction failure/restart. Invalid references reject the entire restoration; no implicit pruning or retargeting occurs. This slice restores semantics only; P08/P10 provide inspection and retention controls.

## P08 acceptance and handoff

P08 is accepted under owner delegation within the authenticated local human-adapter envelope. [Inspection](bicameral_agent/kernel/inspection.py) opens a consistent SQLite read snapshot, exposes bounded table/byte pages including original reports and evaluator records, and streams a versioned JSON-lines export to an explicitly selected new file. Independent verification checks manifest counts, contiguous blob chunks, referenced blobs, byte hashes and completion. Blobs appear once; the live store gains only receipt and opaque copy metadata, never an export body.

Validation passed 150 tests, all three schema checks and whitespace checks. Seven [inspection tests](tests/test_inspection.py) cover snapshot stability during writes, exact payload traversal, human-only access, repeated nonrecursive exports, truncation/tampering, missing external copies, failed destination writes, terminal inspection and removal overriding old snapshot bytes. Copy locations remain caller-supplied and outside the evidence database. P10 supplies durable governed removal and recovery across these known copies.

## P10 acceptance and handoff

P10 is accepted under owner delegation within the SCRIPTED, trusted local SQLite/file adapter envelope. [Reviewed retention](bicameral_agent/kernel/retention.py) displays source roots, the conservative transitive source/derived closure, shared content and every known export/backup. Current scoped review and confirmation are mandatory. Pause/termination alone retain bytes; an approved removal blocks affected reads immediately and keeps execution stopped. Input/output, semantic, retrieval and reference provenance feed the closure. Earlier stores lacking complete lineage require a visibly disclosed whole-Run content scope.

An independently retained [removal journal](bicameral_agent/storage/retention.py) commits the decision before cleanup, stores non-sensitive accountability/progress, and is identity-bound to the evidence database. Preserve this journal independently of backups. `recover_backup` requires the current journal, retains the original Run identity, and applies removals before exposing evidence. Opening a copied database with a different/missing journal rejects. Removed source bytes and hashes are detached/deleted; logical file overwrite, WAL truncation and compaction are verified separately. Missing/shared/inaccessible copies or an outstanding reader prevent a completed claim. File identities protect unrelated destinations; interrupted overwrites resume from durable progress.

Validation passed 160 tests, all three schema checks and whitespace checks. Ten [retention tests](tests/test_retention.py) cover semantic/invocation/cache derivatives, duplicate bytes, exports, backups, source-hash/file scans, strict scope, stale effects, wrong destinations, an actual process exit after the decision, interrupted copy cleanup, terminal maintenance inspection, dormancy, old-reader blocking, shared copies and old-snapshot recovery. Existing per-write fault tests now restore the same synthetic fixture with its current journal to include provenance writes accurately.

Limits are explicit: these checks establish logical removal in tested SQLite/files, not physical-media erasure or discovery of unregistered copies. No provider exists in this envelope. Known unresolved copies remain listed and incomplete. Maintenance inspection remains available; execution and semantic replay cannot reconstruct removed evidence. P09 must preserve permitted allocation/outcome metadata and report analytical loss rather than manufacture results.

## Scope

This is not a claim about consciousness, sentience, personhood, artificial emotion, or human memory. It is not an unrestricted autonomous-agent framework.

The persistent **process**, rather than any individual model invocation, is the unit being tested.

## License

Licensed under the [MIT License](LICENSE).
