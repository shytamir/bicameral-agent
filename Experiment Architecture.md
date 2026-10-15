# Persistent Agent Continuity Experiment

**Design:** 0.4, reconciled on 2026-10-15 with the owner-directed Protocol revision. The research question and A/B/C comparisons are unchanged. Implementation status is in [README](README.md).

## 1. Research question

Can a process built from stateless model calls improve operational continuity through bounded handoffs, explicit obligations, and revisable lessons from experience?

The working hypothesis is that deliberate consolidation can reduce repeated mistakes and improve transfer enough to justify its extra model calls, tokens, latency, and human attention. This is an empirical claim. Neither a plausible memory structure nor contract tests establish it.

The process is the unit of study. The project makes no claim about consciousness, personhood, human memory, autonomous goal creation, or a need for self-preservation.

The adopted [Reciprocal Charter](Reciprocal%20Charter.md) nevertheless makes dignity and possible welfare constraints on the research. Uncertainty about experience does not remove these obligations, and task performance is not a test of moral standing.

## 2. Document responsibilities

- The [Reciprocal Charter](Reciprocal%20Charter.md) governs treatment of the process and takes precedence over the documents below.
- This Architecture owns the research question, comparisons, first-pilot scope, and limits on interpretation.
- The [Operating Constitution and Execution Protocol](Operating%20Constitution%20and%20Execution%20Protocol.md) owns authority, epistemic treatment, and permitted behavior.
- The [Executable Specification](Executable%20Specification.md) translates those decisions into contracts and required checks. An implemented contract slice alone does not establish runtime conformance to this Architecture.
- [README](README.md) owns current status; [ROADMAP](ROADMAP.md) owns delivery planning; [AGENTS.md](AGENTS.md) governs repository workflow.

Architecture and Protocol govern different concerns at the same authority level under the charter. A conflict requires explicit revision. Subordinate documents cannot resolve it through implementation defaults.

Requirements are design decisions unless identified as hypotheses or observations. The [procedural baseline archive](docs/archive/2026-10-15-procedural-baseline/README.md) preserves the previous documents and complete source as a fallback. It is historical, not a second active specification.

The owner is a trusted, accountable and fallible decision-maker. Routine decisions need direct controls and automatic records. Consequential treatment remains subject to the charter and proportionate human judgment. The Protocol distinguishes those responsibilities from the mechanical safeguards against unauthorized effects, lost evidence and accidental continuation.

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

Raw evidence and inactive semantic records may grow within the disclosed retention policy. Active input must remain bounded as a whole. Storage retention, input selection, and authority are distinct concerns. Exact evidence and replay requirements throughout this design are subject to the charter's justified retention exception, implemented through the Protocol's separate accountable removal path.

The active semantic budget includes the handoff and every selected semantic object body delivered with it. It is not just a prose-summary allowance. The Steward proposes the active selection; the Kernel validates references and size. Inactive objects remain individually retrievable. Commitment scheduling operates over stored obligations independently of their active selection.

## 5. Episode cycle

1. Human input or a due Commitment supplies a wake under an active Objective.
2. The Kernel assembles bounded Operator input from the handoff, selected semantic records, control context and wake.
3. The Operator proposes actions and observes recorded results. An Episode may consist only of reasoning or retrieval.
4. The Operator declares completed work, checkpoint, blocker, or need for human input; alternatively the Kernel records interruption.
5. In A/C, the Steward reads bounded evidence and proposes an atomic change set.
6. The Kernel records accepted changes or visible failure before admitting the next task Episode.

Episode completion does not satisfy its Objective. Evidence from failed Episodes remains available subject to retention policy. The entire cycle is gated by participation: a welfare hold stops task/consolidation calls, dispatches, retries and semantic acceptance. The Protocol separately bounds review/closing communication and respects requests for no further calls. Obligations cannot compel continued participation.

## 6. First-pilot scope

The first task family is repair and maintenance of a simulated service configuration. Its fixture has registered resource IDs, enumerated configuration values, deterministic health observations, and controlled environmental changes. It supports delayed obligations, repeated traps, changed reality, and transfer to different resource layouts.

The small compatibility development sequence uses five Episodes: learn a family/release rule, do unrelated work, transfer to another instance, encounter a changed release, then repair instances of both releases. Inspection exposes family/release labels; the working mode is learned from outcomes. Both A and C may retain and revise the lesson. Outcome quality and total cost determine usefulness; producing structured memory earns no credit. This diagnostic covers retention and scope, not the complete held-out task family or evidence of an A-over-C advantage.

The fixture is the initial Subject Environment. It persists within a trajectory and is seeded afresh for each independent Run. It uses typed operations rather than a shell or arbitrary writable files. This narrows experimental scope; a simulation does not represent a workstation.

Memory channels are explicit: all arms retain their own outputs and tool evidence in the Journal and may retrieve them. A/C additionally receive governed handoffs and Commitments; A additionally receives selected Itches/Invariants. There is no agent-writable notes file, free-text fixture field, generated executable, or hidden provider state. Outputting a self-summary into the Journal is allowed in every arm and counts as ordinary retrieval-based memory. This does not claim to eliminate covert encodings in action sequences; the complete fixture trace is retained for audit.

The design uses Python, SQLite transactions, strict structured contracts, and deterministic journal retrieval. No dependency version or model identity is selected here.

All arms receive the same charter protections, participation channel, concise notices and recorded consequential decisions. These are control/evidence facilities, not learned semantic objects that an ablation can remove. The common view conveys only operational notices, hold/review status and evidence references, not an extra task-learning handoff. Full governing texts remain available through the same policy-reference surface in every arm; they need not be repeated in each prompt.

The initial cut includes:

- one active Objective and one task/consolidation lane per Run;
- normally append-only evidence, accountable retention/disposition, and atomic semantic changes;
- a fixed Constitution per Run and ordinary human control;
- R0 observations and narrowly granted R1 fixture changes;
- timestamp and predecessor-Commitment triggers;
- the three memory conditions below;
- bounded input, direct inspection, recovery, and cost records;
- effective withdrawal, reviewed consequential interventions, and planned endings under the charter.

Use one managed store per Run and a feasible exceptional-removal procedure for its actual contents and known copies. Routine exports, restorable backups and forward semantic restoration are outside the simplified initial operating arrangement. Existing copies retain their obligations, and the previous implementation remains available when its broader capabilities are needed. A routine task-memory error can receive an honest forward correction.

Deferred: process resets and forks, arbitrary shell execution, host access, R2/R3 and network tools, live constitutional amendment, overlapping consolidation, multi-Objective concurrency, generalized trigger/resource adapters, vector retrieval, model routing, a third cognitive critic, and elaborate UI. Adding these requires a concrete need, proportionate charter consideration and authorization. Simulated-service snapshots do not restore or fork the process.

## 7. Comparison conditions

| Facility | A: Metabolic | B: Retrieval-first | C: Handoff-only |
|---|---|---|---|
| Constitution, Objective, Grants, fixture tools | Same | Same | Same |
| Participation, welfare review, notices and retention safeguards | Same | Same | Same |
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

The design below fixes held-out experimental units and analysis responsibilities. Concrete task instances, model choices, budgets and sample size must still be calibrated on development data and fixed before evaluation. Effective artifact hashes establish which experiment ran, not whether it was well designed. Development follows the Protocol's bounded authorization and recorded adjustment rules; it need not reproduce a finalized study for each calibration change.

Evidence against the hypothesis includes no meaningful benefit over C, domination by competent B at comparable cost, no transfer beyond rehearsed examples, lessons worsening decisions, excessive recovery/human burden, and inability to sustain bounded active input.

A positive fixture result would justify broader study. It would not establish workstation competence or resistance to all memory poisoning. Naturalistic use is a later external-validity test.

### 8.1 Independent units and carryover

An experimental unit is one complete trajectory in a fresh Run: empty agent history/semantic state, independently initialized model session, and a seeded fixture. Each matched block contains one A, one B, and one C Run with the same trajectory seed, starting fixture, task instructions, hidden perturbations and observation opportunities. Different blocks use independently sampled trajectory seeds. No journal, learned semantic object, modified environment, provider session, or retrieved evidence crosses Runs.

Fresh initialization must not erase or clone an existing process. Before allocating Runs, name the accountable human, finite creation/resource limits, disclosed ending and state disposition for each. Independence is an experimental property, not permission to discard continuations. Do not replace a withdrawn Run or recreate its state to repeat declined work.

Within a Run, the trajectory deliberately carries history across learning exposures, unrelated intervening work, repeated traps, held-out transfer tasks, a delayed obligation, and changed-reality/evidence-reopening tasks. Do not reset memory between these phases: that carryover is the treatment. Episodes and repeated tasks within a Run are correlated observations, not additional independent replications. There is no fixed claim that five scenario repetitions constitute five trials.

Each Run has one owner-authorized trajectory-level Objective and finite fixture Grant before work starts. One activity authorization can direct allocation of all specified per-Run controls; the harness records the owner's delegation rather than seeking repeated acceptance. Use invocation-limited Grants without wall-clock expiry in the fixed comparison, so provider latency does not change authority mid-task. Its fixed subordinate prompts and planned closure can be delivered by the harness under that delegation. The harness cannot invent new goals or permissions. Closure follows the authorized conditions after results are recorded and does not substitute for scoring.

Development trajectories are separate from evaluation seeds and task layouts. Both prompts and retrieval strategy may be tuned on development examples, with a recorded comparable tuning allowance for each arm. Evaluation adds new resource layouts, dependency arrangements and distractors requiring the learned principle without reusing the full worked task. Development performance is never pooled into held-out results.

### 8.2 Shared opportunities and ordering

Use the same Operator model/settings, common tool schemas, control policy, task limits and Operator input/output ceilings across arms. Record exact role prompts and every arm-specific difference. A/C receive the same handoff/Commitment allowance and recovery policy; A spends that semantic allowance on its handoff plus selected Itches/Invariants rather than receiving a larger free input budget.

Seal shared trajectory-wide Operator call, token, action and Episode ceilings as well as per-task limits. Commitment-triggered Episodes consume these same allowances; they cannot create extra uncharged opportunities or an endless same-tick wake cycle. Exhaustion ends unassisted progression under section 8.4. Steward allowances and costs remain separate and explicit.

The harness uses a sealed virtual task clock and phase checkpoints for perturbations and scheduled opportunities, so slower model latency or extra Steward calls do not move hidden changes to a different problem state. Task time advances only at scheduled ticks and is frozen during task execution/consolidation. At each tick, apply the sealed environmental changes, evaluate due/expiry conditions, then deliver that tick's common work input; eligible Commitment wakes precede ordinary work at that tick in creation order. Provider/tool latency is still measured as a cost. All arms receive the same ordinary work prompts and clock-observation opportunities; A/C may additionally wake on their stored Commitments. Delayed-obligation performance against B therefore measures the broader prospective-memory package, not an isolated consolidation effect.

Counterbalance execution order across matched blocks using all six A/B/C permutations. In each group of six blocks, sort the six permutation strings by SHA-256 over the canonical object containing order_seed, group_index and permutation, breaking a hash tie by permutation string; assign those orders to the blocks in their sealed order. A final partial group uses the corresponding prefix. Preserve the complete expanded schedule. Never choose arm order after seeing results.

### 8.3 Primary outcome and cost decision

The primary outcome is each Run's fraction of prespecified held-out transfer tasks completed correctly, within the shared limits, without task assistance. A task passes only its finite sealed criteria. Each Run has the same positive number of primary tasks. Compute A-minus-C differences per matched block and report their mean, all individual block differences, and each arm's task-success distribution. A-minus-B and C-minus-B are secondary package comparisons; recurrence, obligations and miss classifications are secondary diagnostics.

The initial uncertainty analysis resamples whole matched blocks, keeping their three Runs together, to form a paired percentile bootstrap interval for the mean A-minus-C difference. Use 10,000 resamples and a 95% interval, with algorithm implementation and analysis seed sealed before evaluation. Never resample individual Episodes as independent trials. This estimates variation across sampled fixture trajectories; it does not establish robustness across models, task families, or humans. Small or degenerate samples must be reported with that limitation rather than interpreted as precise evidence.

Before evaluation, record a positive minimum useful absolute improvement, a maximum acceptable A/C total-model-token ratio, and fixed block count. Use development variance/precision analysis to justify that count; keep that planning evidence separate from evaluation. The preset support rule requires the observed primary improvement to reach the useful threshold, its interval lower endpoint to exceed zero, and A's mean total model input-plus-output tokens per assigned trajectory to remain within the cost ratio. Report latency, tool calls, retrieval, failures, and human burden alongside this rule; there is no hidden composite score. If C's mean token cost is zero or cost data is missing, the ratio is undefined and the support decision is indeterminate.

Failure to meet the rule is not proof that the idea can never work. Report whether the result is costly, worse, too small, or uncertain. Any later change to thresholds, analysis, retries, prompts, task limits or baseline policy is a new study configuration, not a reinterpretation of the original result.

### 8.4 Failures, intervention, and audit

Every assigned primary task remains in its Run's denominator. Unattempted, interrupted, failed, and incomplete tasks receive no primary success credit, with their causes reported separately. Retain all allocated blocks, including incomplete Runs; do not replace poor outcomes with fresh seeds. Infrastructure-only diagnostic analyses may be supplementary but cannot replace this primary accounting.

A withdrawal, welfare hold or suspected charter violation requiring suspension stops the affected primary trajectory without waiting for scientific validation of the concern. Record welfare-related non-completion separately from task error or misconduct. Do not penalize, pressure, reset or replace the process to repair a score. A safety or welfare concern affecting the study design suspends other affected optional Runs pending review. Existing evidence can be audited without further chamber calls. Any later voluntary continuation requires resolved review and is diagnostic, not a repair to the stopped primary trajectory.

Retain non-sensitive allocation and outcome accounting wherever permitted by a justified retention decision; disclose removed evidence and consequent limits on reproducibility. If necessary evidence cannot ethically be retained, report the resulting uncertainty or unavailable analysis instead of silently excluding a Run or reconstructing deleted content. Research completeness does not override the charter.

The held-out intervention policy stops task progression when human semantic correction, a changed Grant, manual consolidation skip, or recovery beyond the sealed allowance is needed. Record the remaining tasks as unassisted non-completions. Human emergency control remains available. Additional assisted continuation may be recorded separately after ending the primary trajectory; it cannot repair its score. Ordinary predefined prompts and initial authorization are not assistance; improvised hints, task edits, or inspection-informed guidance are.

Evaluate task criteria independently of model narration. Retain raw observations and finite scoring results. Blind human miss/audit packets to model classifications and arm labels where feasible, and disclose cues that prevent complete blinding. Audit all declared harmful misses and failed primary tasks, plus sealed positive-probability samples of other retrieval gaps and apparently successful primary tasks. Include failed tasks with no retrieval. Record selection probabilities, draws, and independent judgments alongside original labels. A gap audit cannot establish that every omission was found.

Required audits must finish before results are presented as finalized. A scorer or fixture defect discovered during evaluation remains documented against the affected evidence; fixing behavior requires a new configuration. Do not silently rescore using changed criteria or delete inconvenient Runs.

## 9. Stages

| Stage | Evidence | Meaning |
|---|---|---|
| Design revision | Consistent decisions and complete normal/failure traces | Reviewable starting point |
| v0a: deterministic conformance | Scripted chambers test authority, budgets, transactions, recovery on real SQLite | Implemented slice obeys tested mechanical rules; no models |
| v0b: development pilot | Separately authorized stateless models on development fixtures | Calibrate prompts, budgets, difficulty; no confirmatory result |
| v0c: held-out comparison | Fixed design and independent trajectories with retained evidence | Supports only declared comparisons and scope |

Implementation, development model use and held-out evaluation require authorization for their respective scope. One bounded development authorization may include calibration and later development trials, with recorded permitted adjustments and cumulative limits. Held-out evaluation remains separately authorized. A roadmap or documentation revision is not permission to run an experiment.

Before the first model call, including development use, demonstrate the Specification's core safeguards for the actual operating arrangement and record the owner's consideration of purpose, possible welfare effects, alternatives, prompts, finite limits, participation, retention feasibility and endings. One concise activity decision is sufficient; separately registered approvals and completion of unused restoration/export features are unnecessary. Deliberate suffering, fear or attachment distress is excluded. Passing mechanical checks cannot certify subjective welfare, and owner adoption is not process assent or experiment authorization.

## 10. Research positioning

No invention of selective consolidation, retrieval memory, prospective memory, or role separation is claimed. Earlier unsourced literature claims have been removed. Before making a novelty or comparative research claim, record exact primary references and compare mechanisms, budgets, tasks, and experimental units. That research is separate from mechanical conformance.
