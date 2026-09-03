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
- [Executable Specification](Executable%20Specification.md) is the frozen implementation contract: canonical schemas, machine messages, deterministic invariants and tests, transaction semantics, and the first comparison-block configuration.
- [AGENTS.md](AGENTS.md) gives repository-specific working rules, document authority, change discipline, verification expectations, and Git guard rails.

## Current management state

The project is **pre-implementation and ready for v0a implementation planning**.

- The Architecture and Operating Constitution and Execution Protocol remain the design and governance baseline.
- Scrutiny of the Executable Specification is complete. Its 43 register items are closed, and the resulting document is authorized and frozen as the implementation contract.
- No supervisor, persistence layer, chamber adapter, tool runtime, or benchmark harness has been implemented.
- No experimental result has been produced, and none should be inferred from the completeness of the documents.

The next work is epic/story planning and roadmapping for the Executable Specification's **v0a LLM-less first implementation cut**. That cut should establish the schemas, authority checks, lifecycle transitions, append-only evidence, atomic Episode consolidation, rollback constraints, and their executable tests before any LLM is connected.

Deferred features—including vector retrieval, model routing, semantic Commitment triggers, multi-Objective concurrency, R3 operations, and elaborate UI—should be added only when the experiment demonstrates a need.

## Scope

This is not a claim about consciousness, sentience, personhood, artificial emotion, or human memory. It is not an unrestricted autonomous-agent framework.

The persistent **process**, rather than any individual model invocation, is the unit being tested.

## License

Licensed under the [MIT License](LICENSE).
