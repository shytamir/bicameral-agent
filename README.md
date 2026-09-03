# Persistent Agent Continuity Experiment

This repository specifies a bounded experiment in **long-horizon agent continuity**.

The project asks whether a stateless reasoning model can participate in a persistent process that becomes more competent over time while carrying only a small, deliberately maintained active state. Raw evidence remains recoverable; discrepancies can revise durable semantic state; future obligations remain explicit; and a deterministic Kernel controls every authoritative transition.

The intended comparison is empirical:

- **Arm A — Metabolic State:** bounded Continuity State, Itches, Invariants, Commitments, and controlled retrieval;
- **Arm B — Retrieval-First Baseline:** persistent Event Journal and retrieval without semantic consolidation;
- **Arm C — Handoff-Only Ablation:** bounded Continuity State and Commitments without Itch-to-Invariant learning.

If the simpler baselines perform as well as the full architecture at comparable cost, the central hypothesis fails.

## System outline

The process separates cognition from authority:

- The **Operator** interprets objectives, reasons about tasks, uses permitted tools, and observes results. It cannot directly rewrite durable semantic state.
- The **Steward** consolidates experience into proposed Continuity State, Itch, Invariant, and Commitment transitions. It has no machine-execution tools.
- The deterministic **State Kernel** schedules Episodes, assembles bounded contexts, journals evidence, validates authority and transitions, commits atomic state changes, and provides auditable rollback.

The chambers decide meaning. The Kernel decides authority and persistence.

## Governing documents

- [Experiment Architecture](Experiment%20Architecture.md) defines the hypothesis, system components, memory structures, evaluation arms, measurements, and failure criteria.
- [Operating Constitution and Execution Protocol](Operating%20Constitution%20and%20Execution%20Protocol.md) defines lawful behavior, human authority, Objectives, Grants, Episodes, action-risk boundaries, evidence treatment, and semantic-state lifecycles.
- [AGENTS.md](AGENTS.md) gives repository-specific working rules, document authority, change discipline, verification expectations, and Git guard rails.

An **Executable Specification** is the next translation layer: canonical schemas, machine contracts, deterministic invariants and tests, transaction semantics, and sealed run configuration.

## Current management state

The project is **pre-implementation and under specification scrutiny**.

- The Architecture and Operating Constitution and Execution Protocol are the current committed design and governance baseline.
- A first Executable Specification draft has been authored locally and is being reviewed. It is not yet accepted or part of the committed project state.
- No supervisor, persistence layer, chamber adapter, tool runtime, or benchmark harness has been implemented.
- No experimental result has been produced, and none should be inferred from the completeness of the documents.

The next substantive boundary is acceptance of an executable specification coherent enough to become tests and deterministic Kernel code. The initial implementation should prove schemas, authority checks, lifecycle transitions, append-only evidence, atomic Episode consolidation, and rollback constraints before connecting an LLM.

Deferred features—including vector retrieval, model routing, semantic Commitment triggers, multi-Objective concurrency, R3 operations, and elaborate UI—should be added only when the experiment demonstrates a need.

## Scope

This is not a claim about consciousness, sentience, personhood, artificial emotion, or human memory. It is not an unrestricted autonomous-agent framework.

The persistent **process**, rather than any individual model invocation, is the unit being tested.

## License

Licensed under the [MIT License](LICENSE).
