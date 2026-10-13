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

## 7. Bounded input and explicit memory channels

### 7.1 Budget contract

Configuration supplies positive limits for total input, reserved output, active semantic tokens, wake/input bytes, exchange tokens, retrieved page bytes/tokens, proposal bytes, model calls per Episode/consolidation, cumulative input/output tokens, elapsed work, queued wakes, and active Grants. The counters and limit units are named in configuration; none is chosen from apparent importance. No numeric value is prescribed before calibration with the chosen backend and fixture.

The active semantic count covers Continuity State text, reference overhead, and the complete rendered bodies of selected Itches, Invariants, and Commitments. A referenced body cannot be carried outside that count. B has no semantic bundle. Every arm has the same total Operator input ceiling, output reservation, action/call limits, and retrieval surface; A/C consolidation cost is additional and recorded.

Count the final serialized request with the pinned tokenizer and framing rule. Record the exact request bytes, local accounted count, and provider-reported usage separately; they must not be falsely presented as the same measurement. A backend without a validated framing bound is ineligible. Section counts are diagnostic; admission uses the full request count plus reserved output. Equality fits; exceeding any applicable limit prevents dispatch.

Preflight proves that the fixed Constitution, prompt, tools, maximum admitted control header, minimal wake, budget metadata and a minimal empty semantic bundle fit with room for a configured evidence page and proposal output. Control input is bounded too: the fixture registry is finite, at most one Objective is active, active Grant count is capped, and human input is stored as a bounded opening excerpt plus an exact pageable payload. Reject an over-limit new control record or queue insertion visibly; do not silently evict an obligation or permission.

### 7.2 Active selection and views

Continuity State contains typed epistemic items with Event references, task focus/next steps, and explicit selected object-version references. A proposal validates its fully rendered post-transaction bundle. Selecting the same object twice is invalid. Creation and selection in the same proposal use section 8's reference contract.

At Episode opening, use the latest committed selection and exact handoff. Render only same-Run, current, lifecycle-applicable selected objects for the bound Objective or a Run-global Invariant family. A mechanically inapplicable reference is omitted from the input view with a bounded change notice and cursor to exact change Events; the persisted handoff is not rewritten. If a selected current projection would exceed the budget, open no task call and enter bounded consolidation recovery. Do not silently drop an otherwise applicable object to fit.

All other objects are inactive for input purposes, not deleted or expired. Object-index retrieval returns deterministic bounded pages and supports explicit ID/type/lifecycle filters. The Kernel does not pick objects by semantic similarity. A due Commitment produces one bounded wake identifying that obligation; its body is a separately budgeted page if necessary. Stored Commitments are polled regardless of active selection.

No context contains an unbounded list of pending Episodes, all Invariants, all Commitments, or all Grants. Aggregate counts and stable index cursors describe larger collections. Grant records are descriptive views only; action authorization always reads current control state.

### 7.3 Episode evidence and retrieval

The Operator receives a fixed opening package plus bounded current-Episode exchange. Before a further result would require an oversized next request, preserve the result and end execution with a context interruption; do not generate a semantic outcome. The next phase can read the exact evidence through pages.

The Steward's base input contains Objective/control context, a bounded current semantic view, the execution-ending record, and an Episode evidence index: cutoff, event count, first/last sequence, counts by event type, and manifest hash/cursor. This index is mechanical metadata, not a semantic summary. The complete ordered manifest and payloads are immutable and pageable; they need not fit together in one call.

Within a consolidation attempt, the Steward can explicitly release previously loaded evidence pages from its working input and request others. Journal the page-selection changes and every exact model input. The fixed base and budget counters remain. Selected pages and the bounded exchange must fit before dispatch; there is no automatic relevance-based eviction. Reading many pages still consumes the attempt's cumulative token, call, and elapsed limits.

When the normal semantic base cannot fit, a recovery base contains only its identity/hash, bounded control/wake metadata, failure code, and cursors for prior semantic state and Episode evidence. It never automatically includes the oversized content. This gives consolidation an input-size-independent route to propose a smaller selection. Human pause, inspection, correction and termination remain available without any model.

Retrieval operations are exact Event/record lookup, sequence range, lexical Journal search, filtered semantic-object index, manifest page, and payload page. An accepted request fixes the visibility scope and cutoff before its own request Event. Sequence/index order uses sequence then ID; lexical results use pinned lexical rank then sequence/ID. Cursors bind query, cutoff and visibility scope. Exact replay returns original bytes; a changed request under the same idempotency key rejects. No raw SQL is exposed.

Every page carries source classes, IDs/hashes, returned size, truncation, and next cursor or an explicit end marker. Binary payloads are paged as exact bytes; reconstruct before decoding split Unicode. Page bytes, serialized token cost, and cumulative budgets are checked. Empty results and missing/stale/foreign references have explicit outcomes.

### 7.4 Channel and visibility checks

Only the memory channels declared in Architecture section 6 exist. Fixture setters accept enumerated values for registered IDs, not free-text notes, paths, code, or arbitrary blobs. Human labels and fixture metadata cannot be modified through agent operations. Ordinary Operator/Steward outputs remain journal evidence; their wording is not semantically censored to enforce an ablation.

Agent-visible and evaluator-only evidence use distinct access scopes. Event, search, object, manifest and payload lookup each enforce that scope; possessing a payload hash or referencing it indirectly never grants access. Audit labels and scoring evidence remain unavailable to chambers throughout the Run, including later repetitions. They remain available to authorized human evaluation/inspection.

### 7.5 Required traces

- Grow inactive Invariants beyond any single input: opening size remains bounded; each inactive record is still reachable by pages.
- Trigger an unselected Commitment: enqueue its wake exactly once without injecting every other obligation into context.
- Fill the current exchange: retain the last result, interrupt, and construct a fitting recovery/consolidation base without semantic trimming.
- Read a manifest larger than the model context through multiple selected pages; retain exact per-call inputs and never claim unread pages were inspected.
- Attempt a notes field, arbitrary file write, or evaluator lookup through search and then by payload ID: reject each channel, including indirect access.
- Store/retrieve an ordinary self-summary in B: permit it and charge its output and retrieval cost.

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

Readiness is documentary only. Proposal identity, inspection, recovery and methodology remain explicit checkpoints. Bounded-input and visibility traces must become executable tests in their implementation slice; prose does not establish conformance.
