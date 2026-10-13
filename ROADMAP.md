# Pilot implementation roadmap

**Status:** planning baseline for the 0.2 design; no implementation slice is authorized by this document.

This replaces the former 18-epic inventory, preserved in Git history. Scope comes from the [Architecture](Experiment%20Architecture.md), policy from the [Protocol](Operating%20Constitution%20and%20Execution%20Protocol.md), and mechanical requirements from the [Executable Specification](Executable%20Specification.md). The slices below are capability boundaries, not duration estimates or commitments to build future platform features.

## 1. Scope and exclusions

The first implementation is LLM-less and exercises a typed simulated-service fixture. It supports one active Objective, serialized execution/consolidation, fixed policy, explicit memory conditions, bounded input, auditable recovery and immutable evidence.

Excluded: actual provider calls, live experiments, host/network/shell access, dynamic constitutional amendment, concurrent task lanes, generalized tool/trigger frameworks, vector retrieval, model routing, and elaborate UI. Do not add them to make a slice appear complete.

Concrete schema choices must express the existing design rather than invent policy. If a worked trace cannot be represented, revise its governing decision before coding around it. Tests belong to the slice introducing the behavior.

## 2. Bounded slices

| ID | Capability delivered | Dependencies | Definition of done |
|---|---|---|---|
| P01 | Strict messages and proposal reference resolution | None | Implement the pilot message/configuration contracts, canonical bytes, SCRIPTED/MODEL variants, discriminated references and local binding resolution. Valid create-and-select/revise-and-select examples round-trip; unknown fields, duplicate keys, foreign targets and illegal reference types reject. Generated schema drift is checked. |
| P02 | Append-only evidence and atomic governed state | P01 | Real SQLite constraints, versioned migrations, immutable payload/artifact retention and semantic/control mutation history. Configuration sealing retains verified artifact bytes atomically. A scripted multi-object proposal commits wholly or not at all under fault injection; replay matches projections; exact retries preserve identities. |
| P03 | Human authority and control gates | P01, P02 | Run/Objective/Grant lifecycle, preflight/activation guards, ordinary-language displays, current-state confirmation, pause/termination and dispatch authorization. Absent, stale, terminal, foreign, over-scope, external-only and prohibited action paths reject without effects. |
| P04 | Typed fixture execution | P02, P03 | Retained finite service fixture, enumerated arguments/resources, deterministic operations, task clock, snapshots and postconditions. No arbitrary file/notes/code/host channel exists. Crash after dispatch preserves uncertainty without replay. |
| P05 | Bounded chamber inputs and retrieval | P01-P04 | Full-request and semantic budgets, selected views, pageable manifests/records, explicit evidence-page release, visibility and stable cursors. Large histories fit through bounded views; an unselected obligation still reaches the scheduler; evaluator content stays inaccessible. |
| P06 | Serialized Episodes and bounded consolidation | P02-P05 | Durable wakes, trigger/expiry checks, scripted chamber exchanges, attempt accounting, recovery inputs and human dispositions. Normal, rejected, timed-out and crash-interrupted traces terminate honestly; no duplicate semantic commit or action replay occurs. |
| P07 | Forward semantic restoration | P02, P03, P05, P06 | Restore earlier semantic content as a new version while retaining current authority, obligations and evidence. Illegal terminal resurrection, stale focus and invalid references reject; rejected differences are visible. |
| P08 | Human inspection and streamed export | P02, P03 | Consistent pageable inspection and external exports with completeness/hash verification. Repeated inspection adds receipts rather than recursively stored export bodies; unavailable external artifacts are distinguished from missing source evidence. |
| P09 | Matched-trajectory evidence runner | P04-P08 | Scripted A/B/C blocks with independent Runs, within-Run carryover, fixed virtual-clock opportunities, finite scoring, cost/audit records and a read-only analysis artifact. Failed/unattempted tasks remain in denominators; pairing and counterbalance are reproducible. |

Each slice needs a scoped implementation request and reviewable acceptance evidence. P01 should begin with the specification's concrete successful reference examples, not an attempt to generate a universal schema framework.

## 3. v0a gate: deterministic conformance

All selected slices work together using scripted Operator/Steward fixtures and an explicitly labelled test configuration. Required evidence includes:

- a complete task-to-consolidation trace plus a delayed unselected Commitment;
- same-proposal create/reference and Invariant revision;
- a large manifest/semantic archive handled within input budgets;
- rejection atomicity, crash/timeout accounting and bounded recovery;
- inspection twice, forward restoration, and denial of evaluator/memory escape channels;
- several matched scripted blocks with incomplete outcomes, correct pairing and finite criteria.

Run these against real SQLite rather than a mocked store. Report which cases ran, failures, unsupported behavior, and residual limitations. Scripted conformance is not experimental evidence and must never be pooled with model Runs.

## 4. v0b gate: authorized development pilot

Only after deterministic conformance and explicit model-experiment authorization:

- select and verify the backend, model, tokenizer and stateless transport;
- implement concrete role prompts and development trajectories;
- calibrate all input/output/page/control limits, deadlines and bounded retry allowance;
- give each arm a recorded comparable opportunity to develop its retrieval/prompt strategy;
- measure fixture difficulty, task-criterion quality, costs and variance;
- choose the independent block count with precision justification, positive useful-improvement threshold, cost ceiling and positive audit sample rates.

Development data may change the design through versioned revisions. It cannot be reported as held-out confirmation.

## 5. v0c gate: separately authorized held-out comparison

Before dispatch, seal the entire study plan and artifacts specified by Architecture section 8 and Specification section 11. Verify fresh independent Runs, withheld evaluation seeds/layouts, the expanded counterbalanced schedule, analysis implementation, budgets, intervention policy and finite scoring. Unknown or omitted values fail this gate.

Preserve every allocated trajectory. Complete required audits and publish the primary paired outcomes, costs, failure causes and limitations, including a negative or indeterminate result. A positive fixture result justifies considering broader work; it does not authorize workstation access.

## 6. Present boundary

Design revision is complete as a documentary starting point. No schema package, database runtime, fixture adapter, chamber integration, tests or experimental results have been implemented. The next actionable work is a separately authorized P01 slice.
