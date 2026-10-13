# Executable Specification

**Version:** 0.2-design

**Status:** implementation design under revision; no code or runtime conformance exists.

## 1. Contract boundary

This document defines mechanical design under the [Architecture](Experiment%20Architecture.md) and [Protocol](Operating%20Constitution%20and%20Execution%20Protocol.md), which own research scope and policy. It replaces 0.1 and its scrutiny register; historical decisions remain in Git and confer no readiness.

The first implementation is LLM-less: scripted messages exercise the boundary intended for models. No provider substitutes for deterministic behavior.

Missing authority, memory, recovery, or experimental decisions return to the governing documents. Schema files, migrations, dependency versions, prompts and fixtures do not yet exist.

## 2. Canonical representation

Strict parsing rejects unknown fields, invalid discriminators, duplicate set members, invalid references and scalar coercion. Required nullable fields remain present as null. Pydantic generates JSON Schema; handwritten duplicate schemas are not a second authority.

Durable IDs are Kernel-assigned opaque UUIDs. Timestamps are Kernel-observed UTC with microsecond precision; durations use a monotonic clock. Clock corrections cannot reverse terminality. Canonical JSON uses UTF-8, sorted keys, no insignificant whitespace, and no non-finite numbers. SHA-256 identifies retained bytes. Exact quantities use integers or explicitly formatted decimal strings.

An envelope contains contract_version, request_id, run_id, episode_id if applicable, authenticated role, message_type and typed body. Idempotency is scoped by Run, role, request ID: exact repeats return recorded responses; different bytes reject without effects. Text cannot authenticate a sender.

## 3. State and ownership

| Record | Required content and owner |
|---|---|
| Run Configuration | Configuration and retained artifact hashes; human seals after preflight |
| Run | Configuration, arm, seed, fixed Constitution, lifecycle, clocks; human-directed Kernel control |
| Objective | Immutable statement, authority Event, lifecycle, lineage; human control |
| Grant | Objective, operations/resources, expiry/limit, use count, lifecycle; human issuance/revocation, Kernel consumption/expiry |
| Episode | Objective, wake, opening state/cutoff, execution end, consolidation disposition |
| Event | Same-Run sequence, actor, source classes, time, exact payload and object references; append-only |
| Semantic revision | Object identity/type, parent/revision, content, lifecycle, evidence; accepted proposal |
| Mutation | Transaction, before/after content and hashes, proposer/authority, supporting Events; append-only |
| Action | Immutable request, decision, dispatch intent, terminal result |
| Invocation | Exact input/output, role, status, tokens, measured duration or explicit unavailable measurement |

Itches carry Objective, discrepancy, lifecycle, evidence. Invariant families carry Objective or Run-global ownership; versions carry immutable proposition/scope, predecessor, lifecycle, evidence. Commitments carry Objective, immutable action/trigger/expiry, authority origin, lifecycle and result. Continuity State carries focus, typed epistemic items, next steps, selected object/Event references.

References are typed and Run-scoped. Evidence crosses Episodes but never Runs implicitly. Semantic proposals cannot represent control mutations. The Protocol owns legal lifecycle edges; transition tests cover its complete matrices.

## 4. Persistence and atomic boundaries

Use SQLite with foreign keys, WAL, synchronous FULL, and configured busy timeout. Migrations are ordered, transactional and versioned. Integrity failure blocks execution while remaining visible to inspection/recovery tools.

Events, payloads, mutations, evaluation results and audits are append-only. Projections change only with the transaction recording their transition. Immutable payloads are stored once by hash; references confer no authority.

Semantic commit validates current parent/revisions and the complete proposed projection, then atomically writes revisions, evidence links, mutations, handoff and Episode closure. Rejection retains proposal/errors separately; none of its mutations survive.

Objective closure atomically applies Commitment dispositions, Grant expiry and interruption. Consumption and dispatch intent commit before adapter execution. Crash between intent and result yields UNKNOWN; recovery observes the fixture and never assumes an action should be replayed.

Restoration follows Protocol policy and normal reference/budget checks. Mutation replay reconstructs governed projections. Operational evidence is reconstructed from its own records, never invented from the mutation ledger.

## 5. Pilot environment and tools

The Subject Environment is an experiment-owned simulated configuration fixture. Tools are fixed typed operations: inspect a registered resource, read enumerated configuration/health, set an allowed configuration value, restart a registered simulated service, restore an authorized snapshot. No free-form path, command, code, network target, or arbitrary byte-writing operation is accepted.

Descriptors fix arguments, resource extraction, risk, reversibility, postcondition observations. R0 has no intended environmental mutation; R1 requires a current covering Grant. Recheck at dispatch. Snapshot restoration records a forward change without rewriting evidence.

Evaluator setup/hidden changes and scoring have a separate capability boundary and evidence namespace. Chamber retrieval cannot access held-out criteria, future perturbations, evaluator observations or audit labels. Range/search/chunk queries enforce visibility, including indirect payload references. Human inspection is independent and counted if it informs an intervention.

Concrete resource/value sets, state machine and operation schemas belong to the environment slice. No executable fixture contract exists until they are implemented and pass isolation tests.

## 6. Human control and Run lifecycle

Run edges: CREATED to ACTIVE, ACTIVE to PAUSED, PAUSED to ACTIVE, ACTIVE to COMPLETED, any nonterminal state to TERMINATED. Human confirmation and current-state guards apply. Completion requires no active Objective, open Episode, unresolved consolidation or nonterminal Commitment. Termination has no such precondition and preserves incompleteness.

Typed controls cover Objective creation/closure, Grant issuance/revocation, pause/resume/termination/completion, semantic correction/restoration and inspection, with expected displayed revisions. The adapter supplies identifiers and shows ordinary-language consequences. Unlisted operation/lifecycle combinations reject.

Access reduction revokes a Grant. A replacement requires an explicit human act; this slice needs no separate deny-overlay subsystem. Configuration changes require a new Run.

## 7. Context and retrieval design checkpoint

The complete active semantic input, exchange, control context and tools must fit budgets. A handoff-only ceiling is insufficient. Selection, paging, accounting and overflow contracts are being revised; implementation must not invent them.

Retrieval preserves source classes and exact content through bounded Event, range, lexical search and payload-page requests. Its scope is authenticated same-Run agent-visible evidence at a recorded cutoff. Ordering/cursors are deterministic and repeats idempotent.

## 8. Proposal identity and inspection checkpoint

Same-proposal creation/reference resolution and inspection retention are being revised. The requirement to store a complete database export inside that database is withdrawn. Inspection must provide complete reachable evidence without copying prior exports recursively.

## 9. Recovery checkpoint

The permanently spent one-session design is withdrawn. Bounded consolidation recovery, accounting, crashes and terminal failure disposition must be specified before implementation. External action uncertainty continues to prohibit automatic replay.

## 10. Validation strategy

Implemented slices require strict parsing/schema drift, exhaustive lifecycle edges, Run ownership, absent/stale/terminal/over-scope/external-only authority, idempotency, real-database failure injection, replay, bounded contexts, evidence visibility, recovery and forward restoration.

Normal worked traces are required alongside rejection cases. A large rejection catalogue cannot prove ordinary continuation is expressible.

## 11. Configuration and experiment checkpoint

Configuration pins document/version hashes, exact prompts, model/tokenizer/runtime identities, fixture/tools, budgets/deadlines, recovery limits, seeds/schedule, finite success criteria and audit/analysis rules. Missing values fail preflight. Environment defaults cannot silently choose behavioral parameters.

Preflight precedes explicit human sealing. Retain normalized configuration and exact referenced bytes with verified hashes. Changes require a new configuration. Experiment design and runnable schedules are not yet ready to seal.

## 12. Readiness

Readiness is documentary only. Context, proposal identity, inspection, recovery and methodology are explicit checkpoints. Clearing them permits slice planning; executable conformance is required before model connection under separate authorization.
