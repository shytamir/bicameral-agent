# Persistent Agent Continuity Experiment

## 1. Research question

Can a process built from stateless model calls improve operational continuity through bounded handoffs, explicit obligations, and revisable lessons from experience?

The working hypothesis is that deliberate consolidation can reduce repeated mistakes and improve transfer enough to justify its extra model calls, tokens, latency, and human attention. This is an empirical claim. Neither a plausible memory structure nor contract tests establish it.

The process is the unit of study. The project makes no claim about consciousness, personhood, human memory, autonomous goal creation, or a need for self-preservation.

## 2. Document responsibilities

- This Architecture owns the research question, comparisons, first-pilot scope, and limits on interpretation.
- The [Operating Constitution and Execution Protocol](Operating%20Constitution%20and%20Execution%20Protocol.md) owns authority, epistemic treatment, and permitted behavior.
- The [Executable Specification](Executable%20Specification.md) translates those decisions into contracts and required checks. Its title names its intended destination; no executable implementation exists.
- [README](README.md) owns current status; [ROADMAP](ROADMAP.md) owns delivery planning; [AGENTS.md](AGENTS.md) governs repository workflow.

Architecture and Protocol govern different concerns at the same authority level. A conflict requires explicit revision. Subordinate documents cannot resolve it through implementation defaults.

Requirements are design decisions unless identified as hypotheses or observations. Superseded versions remain in Git; they are not a second active specification.

## 3. Components

| Component | Responsibility | Boundary |
|---|---|---|
| Operator | Pursue the Objective, propose actions, inspect results, retrieve evidence, report outcomes | Cannot commit governed semantic state or issue authority |
| Steward | Propose the handoff and changes to Itches, Invariants, and Commitments | Read-only evidence access; no environment tools |
| State Kernel | Authenticate requests, enforce authority, contracts and budgets, journal evidence, schedule and commit | Does not decide what observations mean or whether a proposition is true |

One model may perform both cognitive roles through separate stateless calls with distinct prompts and capabilities. Cross-call information passes through recorded inputs; provider conversation memory is excluded.

Separation makes authority and memory changes inspectable. It does not guarantee good judgment, factual correctness, or immunity to malicious content within otherwise authorized work.

## 4. Persistent structures

| Structure | Purpose | Limitation |
|---|---|---|
| Event Journal | Exact observations, messages, actions, outcomes, provenance | Recording text establishes neither permission nor truth |
| Continuity State | Bounded handoff of working facts, assumptions, blockers, next steps and references | Not a complete autobiography or new Objective |
| Itch | Independently addressable unresolved discrepancy | Not a duty to investigate every surprise |
| Invariant | Versioned, scoped, revisable procedural lesson | Not a mathematical invariant or infallible belief |
| Commitment | Future obligation under one Objective | Not permission to execute its action |

Objectives, Grants and the Constitution are external control state, not learned memory. Invariant is retained as project vocabulary; its propositions may be tentative, challenged, wrong, or retired.

Raw evidence and inactive semantic records may grow in storage. Active input must remain bounded as a whole. Storage retention, input selection, and authority are distinct concerns.

## 5. Episode cycle

1. Human input or a due Commitment supplies a wake under an active Objective.
2. The Kernel assembles bounded Operator input from the handoff, selected semantic records, control context and wake.
3. The Operator proposes actions and observes recorded results. An Episode may consist only of reasoning or retrieval.
4. The Operator declares completed work, checkpoint, blocker, or need for human input; alternatively the Kernel records interruption.
5. In A/C, the Steward reads bounded evidence and proposes an atomic change set.
6. The Kernel records accepted changes or visible failure before admitting the next task Episode.

Episode completion does not satisfy its Objective. Evidence from failed Episodes remains available.

## 6. First-pilot scope

The first task family is repair and maintenance of a simulated service configuration. Its fixture has registered resource IDs, enumerated configuration values, deterministic health observations, and controlled environmental changes. It supports delayed obligations, repeated traps, changed reality, and transfer to different resource layouts.

The fixture is the initial Subject Environment. It persists within a trajectory and is seeded afresh for each independent Run. It uses typed operations rather than a shell or arbitrary writable files. This narrows experimental scope; a simulation does not represent a workstation.

The design uses Python, SQLite transactions, strict structured contracts, and deterministic journal retrieval. No dependency version or model identity is selected here.

The initial cut includes:

- one active Objective and one task/consolidation lane per Run;
- append-only evidence and atomic semantic changes;
- a fixed Constitution per Run and ordinary human control;
- R0 observations and narrowly granted R1 fixture changes;
- timestamp and predecessor-Commitment triggers;
- the three memory conditions below;
- bounded input, inspection, recovery, and cost records.

Deferred: arbitrary shell execution, host access, R2/R3 and network tools, live constitutional amendment, overlapping consolidation, multi-Objective concurrency, generalized trigger/resource adapters, vector retrieval, model routing, a third cognitive critic, and elaborate UI. Adding these requires a concrete need and an authorized slice.

## 7. Comparison conditions

| Facility | A: Metabolic | B: Retrieval-first | C: Handoff-only |
|---|---|---|---|
| Constitution, Objective, Grants, fixture tools | Same | Same | Same |
| Agent-visible journal and retrieval | Yes | Yes | Yes |
| Bounded Continuity State | Yes | No | Yes |
| Explicit Commitments and deterministic wakes | Yes | No | Yes |
| Structured Itches and Invariants | Yes | No | No |
| Steward consolidation | Full | None | Handoff and Commitments |

A versus C is the primary diagnostic comparison for structured discrepancy/lesson management on top of handoff and prospective memory. A versus B compares the complete package with retrieval-first persistence. C versus B measures the combined addition of handoff and Commitments.

No comparison isolates a component more narrowly than its treatment differences. B/C can still reason about discrepancies and describe lessons in ordinary outputs or handoff text. The treatment is explicit machinery and its role instructions, not the existence of learning.

Every arm receives the same Operator model, action opportunities, observations, task instructions, and input ceiling. Steward work is a measured treatment cost. Retrieval policy and prompts must be developed competently for each arm before evaluation and then fixed.

## 8. Evidence and interpretation

Measure task outcomes, repeated errors, held-out transfer, Commitment fulfilment, model tokens/calls, latency, retrieval volume, active-input size, and human intervention. Report runtime and consolidation failures separately from semantic mistakes.

A Continuity Miss is a diagnostic judgment that missing history impaired or delayed continuation. Retrieval of an unreferenced Event is only a candidate signal. A reference gap does not prove missing knowledge; no-retrieval failures remain possible. Independent audit and task outcomes must accompany self-reports.

Trajectory design, replication, cost rules, scoring, and analysis are still being revised. No comparison may begin until those choices and fixtures are fixed. Sealing bytes establishes which experiment ran, not whether it was well designed.

Evidence against the hypothesis includes no meaningful benefit over C, domination by competent B at comparable cost, no transfer beyond rehearsed examples, lessons worsening decisions, excessive recovery/human burden, and inability to sustain bounded active input.

A positive fixture result would justify broader study. It would not establish workstation competence or resistance to all memory poisoning. Naturalistic use is a later external-validity test.

## 9. Stages

| Stage | Evidence | Meaning |
|---|---|---|
| Design revision | Consistent decisions and complete normal/failure traces | Reviewable starting point |
| v0a: deterministic conformance | Scripted chambers test authority, budgets, transactions, recovery on real SQLite | Implemented slice obeys tested mechanical rules; no models |
| v0b: development pilot | Separately authorized stateless models on development fixtures | Calibrate prompts, budgets, difficulty; no confirmatory result |
| v0c: held-out comparison | Fixed design and independent trajectories with retained evidence | Supports only declared comparisons and scope |

Each stage requires separate authorization. A roadmap is not permission to run an experiment.

## 10. Research positioning

No invention of selective consolidation, retrieval memory, prospective memory, or role separation is claimed. Earlier unsourced literature claims have been removed. Before making a novelty or comparative research claim, record exact primary references and compare mechanisms, budgets, tasks, and experimental units. That research is separate from mechanical conformance.
