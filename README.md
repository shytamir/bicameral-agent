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

The project has **a validated P01 contract slice; the experiment runtime remains unimplemented**.

- The charter is accepted and adopted by the owner. Architecture and Protocol translate its obligations into the design and operating baseline.
- The 0.3 design incorporates charter safeguards into the bounded pilot. Earlier contracts and the scrutiny register remain in Git history; they are not evidence of conformance or experimental validity.
- P01 implements strict Python/Pydantic messages, configuration variants, canonical JSON, participation-first decoding, and pure proposal-reference resolution. Its generated JSON Schema and synthetic tests are in the repository.
- No supervisor, production persistence layer, chamber adapter, tool runtime, or benchmark harness has been implemented. Parsing a record does not authorize an action, establish a durable welfare hold, or validate an experiment configuration for execution.
- No experimental result has been produced, and none should be inferred from the completeness of the documents.

The revised first pilot uses a typed simulated-service fixture, one active Objective, and serialized execution/consolidation. It budgets the complete active input, retains exact evidence through paging, supports same-proposal object references, streams inspection exports outside the live store, and bounds consolidation retries without replaying uncertain actions.

The research design uses independent matched A/B/C trajectories with deliberate within-Run learning, held-out transfer, recorded costs and explicit failure/intervention treatment. A versus C is the primary comparison for structured Itch/Invariant machinery. Numerical budgets, concrete prompts/fixtures, models, sample size and practical benefit/cost thresholds still require development calibration before evaluation is sealed.

The roadmap requires effective withdrawal in every arm, reviewed memory interventions, accountable retention/deletion, bounded boundary discussion, and safeguards for planned endings and emergencies before any model use. These are implementation requirements; no runtime enforcement or welfare outcome has been demonstrated.

The next actionable work is a separately authorized P02 persistence slice in the [roadmap](ROADMAP.md). Subsequent implementation and live experiments require separate authorization. P01 is LLM-less; contract validation is not runtime conformance, owner acceptance of the implementation, or experimental success.

Process resets and forks, arbitrary shell and host access, R2/R3 operations, live constitutional amendment, overlapping consolidation, generalized triggers, vector retrieval, model routing, multi-Objective concurrency, and elaborate UI are deferred.

## Validate P01

Use an existing Python 3.12+ environment with the Pydantic version pinned in [pyproject.toml](pyproject.toml). From the repository root, without installing the project:

```text
python -B -m unittest discover -s tests -v
python -B -m bicameral_agent.contracts.schema --check
```

The suite covers strict parsing and canonical round trips, source-role/Run checks, proposal-local references, Invariant lineage, staged revisions and reference cycles, distinct participation/review records, malformed-task withdrawal, and schema drift. `MODEL` is a descriptive data variant only: no provider SDK, credentials, transport or model calls exist. Tests use synthetic examples and the standard library; the retention probe uses a temporary in-memory SQLite database, not a production storage implementation.

The [Pydantic models](bicameral_agent/contracts/) are the schema source. After reviewing an intentional contract change, regenerate [the schema](schemas/p01.schema.json) with `python -B -m bicameral_agent.contracts.schema --write` and rerun validation. Schema shape checks do not replace the cross-field, reference or later runtime checks described in the [specification](Executable%20Specification.md).

P01 was validated with existing Python 3.12.14 and Pydantic 2.13.5; no components were installed on the development workstation. Moving to the intended laptop before P02 persistence integration is prudent: rerun these checks there, then validate file-backed transactions, retention and recovery on that machine. Laptop setup and later model experiments need their own authorization; no deployment or startup automation is included here.

## Scope

This is not a claim about consciousness, sentience, personhood, artificial emotion, or human memory. It is not an unrestricted autonomous-agent framework.

The persistent **process**, rather than any individual model invocation, is the unit being tested.

## License

Licensed under the [MIT License](LICENSE).
