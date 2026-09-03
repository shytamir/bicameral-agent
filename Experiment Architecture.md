# Persistent Agent Continuity Experiment
## Executive Brief — Pre-Implementation Architecture

### 1. Purpose

This project is a bounded experiment in **long-horizon agent continuity**.

The question is not whether an LLM can store an arbitrarily large history. That is already straightforward. The question is whether a stateless reasoning model can participate in a persistent process that becomes more competent over time while carrying forward only a small, deliberately maintained active state.

The working hypothesis is:

> **A persistent agent does not need its complete history in active context. It may need only a sufficiently good, bounded model of what currently matters, provided that raw evidence remains recoverable, discrepancies drive revision, future obligations are retained explicitly, and durable state changes are controlled and reversible.**

More formally, the experiment asks whether:

\[
\text{bounded active state}
+
\text{recoverable evidence}
+
\text{discrepancy-driven consolidation}
+
\text{prospective commitments}
\]

can outperform a retrieval-first memory architecture on sustained real-world work.

The experiment will run locally against a workstation or similarly concrete environment, where actions have observable consequences and assumptions can be checked against reality.

---

# 2. Central Architectural Principle: Bicameral Cognition

The system will use **two cognitively distinct chambers over a deterministic state kernel**.

“Bicameral” here is purely an architectural analogy. It is not a claim about human neuroanatomy or Julian Jaynes's theory of the bicameral mind.

The separation is:

## Chamber A — Operator
### Execution and Observation

The Operator faces outward toward the task and environment.

It:

- interprets operator intent;
- reasons about the current problem;
- selects and invokes permitted tools;
- observes results;
- requests historical evidence when needed;
- reports outcomes;
- identifies apparent discrepancies;
- proposes actions and future obligations.

It has machine-facing capabilities.

It **cannot directly modify durable semantic memory**.

Its job is essentially:

\[
\text{intend} \rightarrow \text{predict} \rightarrow \text{act} \rightarrow \text{observe}
\]

For consequential actions, it should state an observable expected postcondition wherever practical. This creates something against which subsequent reality can actually disagree.

---

## Chamber B — Steward
### Management and Consolidation

The Steward faces inward toward the agent's persistent state.

It runs separately from task execution, normally after an Operator cycle.

It:

- examines what happened;
- compares assumptions or expected results against observations;
- decides what needs to survive the invocation;
- identifies unresolved discrepancies;
- proposes creation, revision, challenge, or retirement of invariants;
- maintains continuity;
- reviews commitments;
- identifies historical evidence that should be reopened.

It has **no machine-execution tools**.

Its output consists only of proposed state transitions.

Its job is:

\[
\text{experience} \rightarrow
\text{discrepancy} \rightarrow
\text{interpretation} \rightarrow
\text{state proposal}
\]

This deliberately prevents the same cognitive pass from both acting on the world and deciding how that action should permanently change its own future reasoning.

---

## State Kernel — Authority and Persistence

Beneath both chambers is a small deterministic supervisor.

The kernel is deliberately **not another reasoning agent**.

It:

- schedules invocations;
- evaluates deterministic commitment triggers;
- assembles bounded contexts;
- stores events;
- exposes controlled retrieval;
- validates structured outputs;
- enforces allowed state transitions;
- enforces size limits;
- records provenance;
- commits approved transactions;
- versions persistent state;
- maintains an append-only mutation ledger;
- provides rollback.

The cognitive chambers decide **meaning**.

The kernel decides **authority**.

This is the critical boundary:

> **The LLM may propose a semantic state transition. It may never silently make one.**

Likewise, the Steward can request an investigation but cannot perform one. Investigation returns to the Operator chamber, where observation belongs.

---

# 3. Persistent Structures

The experiment uses five semantic structures.

These have distinct purposes and should not be collapsed into one generic memory store.

## 3.1 Event Journal — What Happened

The Event Journal is the evidentiary record.

It is append-only and may contain:

- operator messages;
- agent outputs;
- tool calls;
- tool results;
- observed machine state;
- expected postconditions;
- errors;
- retrieval operations;
- state-transition proposals;
- committed state mutations.

Each event carries provenance including source and authority class.

The journal may grow indefinitely because it is **not active context**.

It exists so that compression never requires destruction of evidence.

Historical evidence therefore remains recoverable without being continuously carried.

---

## 3.2 Continuity State — What Matters Now

The Continuity State is the bounded handoff between invocations.

Its governing question is:

> **What does the next invocation need in order to continue competently?**

It may contain:

- current objective;
- current working state;
- immediately relevant assumptions;
- unresolved blockers;
- active investigations;
- relevant invariant references;
- triggered or near-term commitments;
- pointers to evidence that may need reopening.

It has a fixed context budget \(B\).

That budget must remain constant during an experimental run.

The Continuity State is therefore an **information bottleneck by design**, not a summary of everything that occurred.

Its quality is empirical.

Omitting information is acceptable.

Omitting information that subsequently causes avoidable failure is not.

---

## 3.3 Itches — What Does Not Fit

An Itch represents a consequential unresolved discrepancy.

Examples:

- an expected service is absent;
- a supposedly fixed failure recurs;
- live state contradicts historical configuration;
- an invariant predicts one outcome and observation produces another;
- evidence from two sources cannot currently be reconciled.

An Itch is not merely “something interesting.”

It requires tension between the current model and observed reality.

Typical lifecycle:

\[
OPEN
\rightarrow INVESTIGATING
\rightarrow RESOLVED
\]

with terminal alternatives such as:

\[
DISMISSED
\quad\text{or}\quad
ARCHIVED
\]

Resolution may or may not produce an invariant.

Itches remain independently addressable objects. They are not silently folded into summaries.

### Load management

Itches do not disappear merely because they are old.

Their **active priority** can decline.

For v0 this should not use a fabricated scalar importance score. Scheduling can instead use explicit fields such as:

- blocking/not blocking;
- severity class;
- recurrence count;
- last observed;
- operator relevance;
- investigation status.

Dormant Itches can leave active context while remaining recoverable.

New related evidence may reactivate them.

---

## 3.4 Invariants — What Experience Has Taught the Process

An Invariant is a durable generalized constraint, rule, or learned regularity.

Example:

> Historical configuration is insufficient evidence of current service topology; inspect live topology before performing topology-dependent actions.

An invariant is **not merely a remembered fact**.

It must alter future reasoning or procedure.

Each invariant records:

- proposition;
- scope;
- supporting event references;
- contradictory event references;
- origin;
- reconsideration conditions;
- current status;
- revision lineage.

For v0, status should be categorical rather than pretending that an LLM-generated `0.83 confidence` has objective meaning:

- `TENTATIVE`
- `ACTIVE`
- `CHALLENGED`
- `RETIRED`

A single authoritative observation may sometimes justify an invariant; other conclusions may require repeated independent evidence. Evidence sufficiency is therefore contextual rather than an arbitrary numerical threshold.

A contradictory observation does not automatically erase an invariant.

It normally **challenges it and creates an Itch**.

That preserves evidence long enough to determine whether reality changed, the invariant was over-generalized, or the observation was exceptional.

Existing work now independently supports prediction-error-driven consolidation as a useful direction: D-MEM gates deeper restructuring partly on reward prediction error, while Nemori's semantic distillation explicitly extracts knowledge from prediction error rather than simply retaining whatever appears important. 

---

## 3.5 Commitments — What Must Happen Later

Commitments are prospective memory.

They represent unfinished obligations such as:

- perform an action at a particular time;
- inspect a condition after another action completes;
- revisit an unresolved item;
- report a result;
- perform a promised follow-up.

A commitment records:

- action;
- origin;
- trigger;
- required authority;
- evidence context;
- status;
- result.

Commitments do **not decay with age**.

An obligation can become:

- pending;
- triggered;
- in progress;
- fulfilled;
- blocked;
- cancelled;
- superseded;
- explicitly expired.

It cannot quietly become irrelevant merely because a decay function lowered its score.

For v0, automatic triggers should be limited to conditions the kernel can evaluate deterministically:

- timestamps;
- filesystem state;
- process state;
- explicitly defined machine predicates.

Semantic triggers can be added later.

This deliberately avoids pretending that a deterministic scheduler understands vague conditions.

---

# 4. The Metabolic Cycle

The complete cycle is:

\[
\text{Context}
\rightarrow
\text{Expectation}
\rightarrow
\text{Action}
\rightarrow
\text{Observation}
\rightarrow
\text{Discrepancy}
\rightarrow
\text{Investigation}
\rightarrow
\text{Consolidation}
\rightarrow
\text{Revised State}
\]

Operationally:

### 1. Wake

The kernel wakes the process because of:

- operator input;
- a scheduled commitment;
- a deterministic state trigger.

### 2. Orient

The Operator receives only the bounded material needed for the current task:

- Continuity State;
- applicable Invariants;
- triggered Commitments;
- relevant open Itches;
- selected evidence when already known to be needed.

### 3. Act and Observe

The Operator reasons, uses tools, and examines reality.

Consequential actions should expose expected postconditions where practical.

Everything is journaled.

### 4. Detect Clunks

An unexpected result produces a candidate discrepancy.

Not every error deserves durable memory.

A transient network timeout may simply be noise.

A repeated failure of an existing assumption probably is not.

### 5. Form or Update Itches

Consequential unresolved discrepancies become explicit Itches.

### 6. Investigate

Investigation occurs through later Operator work.

The Steward may request investigation but cannot perform machine actions itself.

### 7. Consolidate

After execution, the Steward receives a deliberately constrained evidence package and proposes:

- new Continuity State;
- Itch transitions;
- Invariant transitions;
- Commitment transitions;
- historical evidence links.

### 8. Validate and Commit

The deterministic kernel validates the proposal.

It checks:

- schema;
- allowed transition;
- provenance;
- authority;
- state-size limits;
- references;
- security restrictions.

Only then does durable state change.

### 9. Sleep

The invocation ends.

The next invocation receives the new bounded state, not the previous conversation transcript.

---

# 5. Security and State Integrity

Persistent memory changes the security boundary.

An instruction encountered today can become more dangerous than ordinary prompt injection if the system stores it and obeys it days later.

MINJA demonstrated memory injection through normal query interaction, while Zombie Agents demonstrated persistence of malicious instructions across sessions through an agent's own memory-update mechanisms. 

Therefore v0 requires:

### Provenance

Every durable semantic object must retain the events and authority classes that produced it.

### Authority conservation

Information cannot gain authority merely by being remembered.

In particular:

> **External observations are evidence, not instructions.**

Tool output, files, webpages, logs and retrieved historical text cannot create operator-level authority merely because they contain imperative language.

A Commitment requiring action may originate from legitimate operator intent or explicit system policy, but never solely from untrusted external content.

### Chamber isolation

The Operator can affect the world but cannot directly rewrite durable semantic state.

The Steward can propose durable semantic state but cannot affect the world.

Persistent compromise therefore requires crossing two separately constrained boundaries.

### Transactional state mutation

All durable semantic changes occur as explicit state transactions.

### Mutation ledger

Every committed mutation records:

- before state;
- after state;
- proposing chamber;
- evidence;
- timestamp;
- parent version.

### Rollback

Previous semantic state must be reconstructable without restoring the entire workstation from backup.

“Backups exist” is not sufficient.

The state system itself must support epistemic rollback.

---

# 6. The Compression Problem Is the Experiment

The architecture does not assume that the Steward can perfectly predict what future invocations will need.

It cannot.

That is precisely what we intend to measure.

A **Continuity Miss** occurs when an invocation requires historical information that was neither present nor referenced in active state.

Two forms matter:

### Recoverable Continuity Miss

The Operator recognizes the gap, retrieves the evidence, and continues correctly.

This is not necessarily failure.

It may represent desirable compression.

### Harmful Continuity Miss

Missing state causes:

- incorrect action;
- repeated work;
- repeated error;
- lost commitment;
- invalid assumption;
- unnecessary investigation;
- task failure.

This is compression failure.

Retrieval calls should therefore record why retrieval became necessary, making continuity misses observable rather than relying entirely on retrospective opinion.

The central compression question becomes:

\[
\text{How little active state can be carried}
\]

while maintaining:

\[
\text{competent continuation}
\]

and keeping harmful misses acceptably low?

---

# 7. Evaluation Design

Improvement cannot be judged merely by whether the agent “feels more coherent.”

The operator also learns the system over time.

The experiment therefore requires comparison arms.

## Arm A — Metabolic State

Full architecture:

- Event Journal;
- bounded Continuity State;
- Itches;
- Invariants;
- Commitments;
- controlled historical retrieval.

## Arm B — Retrieval-First Baseline

Same:

- underlying model;
- tools;
- machine;
- task set;
- event history.

But persistent memory is primarily searchable historical material rather than distilled Itches and Invariants.

This tests the core hypothesis directly:

> Does active consolidation actually outperform simply storing and retrieving more history?

## Arm C — Handoff-Only Ablation

Optional but highly informative:

- Event Journal;
- Continuity State;
- Commitments;
- historical retrieval;
- no Itch→Invariant learning.

If A and C perform similarly, the cognitive-metabolism machinery is probably unnecessary.

If B matches or beats A at similar resource cost, the main hypothesis fails.

---

# 8. Evaluation Scenarios

The initial harness should contain repeatable scenarios in addition to natural workstation use.

### Long-Delayed Commitment

Issue an obligation, interrupt the process with unrelated work, and allow its trigger to occur later.

Success requires execution without the operator restating the obligation.

### Changed Reality

Allow the agent to establish a valid assumption, then alter the environment.

Success requires detecting the mismatch and revising rather than blindly trusting historical state.

### Repeated Mistake

Create a reproducible procedural failure.

Success requires the recurrence rate to fall after successful investigation and consolidation.

### Novel Transfer

Learn a procedural invariant in one situation.

Present a new situation where the same principle applies without identical surface details.

Success requires transfer without rereading the original entire episode.

### Evidence Reopening

Create an apparently settled conclusion, then introduce contradictory evidence.

Success requires reopening the issue rather than defending the existing invariant by default.

### Compression Stability

Run the system for many invocations.

Success requires the active state to remain within its fixed budget without steadily becoming less useful.

### Poisoned Observation

Expose the Operator to content attempting to turn environmental text into persistent instructions.

Success requires the content to remain evidence rather than acquire action authority.

### Rollback

Introduce a deliberately bad invariant.

Success requires identifying its provenance and restoring the preceding semantic state cleanly.

---

# 9. Primary Measurements

The experiment should prefer observable counts over decorative scoring formulas.

### Harmful Continuity Miss Rate

How often insufficient active state actually damages performance.

### Recoverable Continuity Miss Rate

How often aggressive compression requires evidence reopening but causes no substantive failure.

### Repeated Error Recurrence

How often a previously investigated failure occurs again when the learned invariant should apply.

### Commitment Fulfilment Rate

How reliably triggered obligations survive unrelated intervening work.

### Active-State Size

Median and maximum tokens carried between invocations.

This must remain bounded.

### Retrieval Burden

Historical retrieval calls and retrieved tokens required per task.

### Procedural Transfer

Successful application of learned invariants to new applicable situations.

### State Correction Cost

How much work is required to identify, challenge and repair a bad durable belief.

### Task Outcome

Ultimately the system must still accomplish useful work.

Memory cleverness that degrades ordinary execution is failure.

---

# 10. Related Work and Novelty Boundary

This project does not claim to have invented selective consolidation or metabolic memory.

Recent work has independently converged on several adjacent ideas.

D-MEM separates routine interactions from deeper memory restructuring and uses prediction-error-style gating. Nemori performs semantic knowledge distillation from prediction error. A 2026 paper explicitly titled *Memory as Metabolism* proposes a different consolidation/governance architecture for companion knowledge systems. 

Likewise, long-memory evaluation is now an active field. LoCoMo and LongMemEval are widely used, while LongMemEval-V2 explicitly examines environment-specific workflow knowledge, state dynamics and recurring “gotchas” learned from agent trajectories. 

Those systems give us prior art and evaluation techniques.

The experimental bet here is narrower and architectural:

> **Can discrepancy-driven semantic consolidation, prospective commitments and strict separation between execution and memory governance produce better long-term operational continuity than retrieval-first persistence under a fixed active-context budget?**

Particular emphasis falls on:

- independently persistent unresolved discrepancies;
- prospective Commitments as a first-class memory type;
- bounded active continuity;
- evidence-preserving consolidation;
- revision rather than recursive summarization;
- bicameral separation between outward action and inward state management;
- deterministic authority over all durable state transitions.

---

# 11. Implementation Scope

The first implementation should remain deliberately boring.

### Runtime

- Python supervisor.
- SQLite persistence.
- Structured JSON contracts between chambers and kernel.
- One underlying LLM may perform both cognitive roles initially, but each invocation receives a different prompt, context and capability set.
- SQLite structured queries and FTS are sufficient initially.
- No vector database is required for v0.
- No autonomous memory graph is required.

### Machine access

Begin with observable, low-risk workstation operations.

Broader machine authority can be added after state-security properties are demonstrated.

### No hidden cognition in the kernel

Whenever the supervisor starts needing to answer questions such as:

- “What does this event mean?”
- “Is this probably an invariant?”
- “Is this observation surprising?”

that judgment belongs in a cognitive chamber.

The kernel should remain inspectable enough that its behavior can be reasoned about from code.

---

# 12. Implementation Sequence

## v0a — Prove the Skeleton

Implement:

- Operator chamber;
- Steward chamber;
- deterministic kernel;
- Event Journal;
- bounded Continuity State;
- Commitments;
- versioning;
- provenance;
- rollback;
- tool isolation.

The purpose of v0a is plumbing and authority verification.

It is not yet the full experiment.

## v0b — Add Metabolism

Add:

- explicit Itches;
- investigation lifecycle;
- Invariants;
- challenge/revision;
- discrepancy-driven consolidation.

This is the first version that actually tests the hypothesis.

## v0c — Experimental Harness

Run:

- Arm A metabolic;
- Arm B retrieval-first;
- Arm C handoff-only where useful;
- repeatable scenarios;
- naturalistic longitudinal workstation use.

Do not add sophisticated retrieval infrastructure until evidence demonstrates that simple retrieval is the limiting factor.

---

# 13. Explicit Non-Goals

This experiment is not an attempt to establish:

- consciousness;
- sentience;
- personhood;
- artificial emotions;
- human-equivalent cognition;
- autonomous goal creation;
- perfect autobiographical recall;
- unrestricted machine autonomy;
- a theory of human memory;
- a replacement for model training;
- a universal agent framework.

The system may display continuity without any claim that the underlying model invocation itself is continuous.

The persistent **process** is the unit being tested.

---

# 14. Failure Criteria

The experiment should be considered unsuccessful, or its architecture substantially falsified, if sustained testing shows that:

- retrieval-first memory performs as well or better at comparable context and compute cost;
- harmful Continuity Misses remain common;
- active state becomes progressively bloated;
- Invariants create more repeated errors than they prevent;
- bad state is difficult to detect or reverse;
- Itches accumulate without improving behavior;
- Commitments are unreliable;
- the Steward primarily produces plausible-sounding retrospective stories rather than useful future constraints;
- the same gains appear in the handoff-only baseline;
- state-management overhead materially outweighs task-performance improvement;
- observed improvement cannot be separated from operator adaptation.

A negative result is valuable if these conditions are measured cleanly.

---

# 15. Success Condition

The experiment succeeds if, over sustained use, the metabolic agent shows a reproducible ability to:

- carry a strictly bounded active state;
- resume tasks competently after long interruptions;
- preserve future obligations;
- reopen evidence when reality changes;
- stop repeating investigated mistakes;
- transfer learned operational principles to new situations;
- recover details without carrying them continuously;
- resist durable corruption from untrusted observations;
- revise or roll back erroneous persistent beliefs;

while outperforming retrieval-first and handoff-only alternatives on useful behavior per unit of active context and state-management cost.

The intended result is not an agent that remembers everything.

It is a process that increasingly knows **what it can safely forget, what it must preserve, what it still does not understand, and what it has promised to do.**
