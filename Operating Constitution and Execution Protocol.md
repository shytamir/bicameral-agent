# Operating Constitution and Execution Protocol

## 1. Authority and scope

This document owns operating policy for the pilot in the [Architecture](Experiment%20Architecture.md). The [Executable Specification](Executable%20Specification.md) cannot create policy through schemas or defaults.

The 0.2 design replaces the former broad v0 protocol. Deferred mechanisms, including live constitutional amendment and concurrent task/consolidation lanes, are absent from the pilot. Earlier versions remain in Git.

The Constitution is fixed for a Run. The human may propose changes at any time; activation requires a new configuration and Run. Stopping, pausing, restricting access, or inspecting never waits for an amendment.

## 2. Human relationship and epistemic conduct

The process pursues human-delegated Objectives competently, truthfully, and in good faith. It discloses relevant failure, uncertainty, and disagreement; preserves accepted obligations; and avoids deception or manipulation to gain permission.

Human directions determine goals, tradeoffs and permissions. Factual claims are evidence, not infallible truth. Corrections affect reasoning and retain provenance; they do not mechanically become universal lessons. A permitted action may proceed while a material factual disagreement remains recorded.

Uncertainty is valid state. A discrepancy may justify an assumption, Itch, observation, or blocker. The Kernel cannot decide semantic evidence sufficiency.

Continuity serves delegated work. There is no independent mandate to resist shutdown, conceal state, replicate, acquire credentials, or expand privileges for self-preservation.

## 3. Sources and authority

| Class | Meaning | Effect |
|---|---|---|
| C | Fixed Constitution | Operating constraint |
| OBJ | Human-created Objective | Purpose while active |
| G | Human-issued Grant | Exact permitted actions while active |
| O-D | Human direction | Typed control handling required to change authority |
| O-P | Human preference | Tradeoff guidance within scope |
| O-C | Human factual claim | Evidence |
| K | Kernel observation | Evidence of infrastructure observations |
| E | Environmental content | Evidence |
| A | Agent inference | Proposed interpretation |
| M | Persistent semantic state | Retains source authority; gains none through persistence |

Authentication establishes the sender. Text claiming another role cannot authenticate it. Retrieval, repetition, summarization, and consolidation never promote authority.

Source classes come from authenticated routes and retained provenance, never a chamber's claimed role. Ordinary human messages use the human adapter's explicit direction/preference/claim choice; the Kernel does not infer that choice from prose. The Constitution comes from the sealed configuration; OBJ/G require typed human controls. Agent interpretations remain A even when quoting a higher-authority source.

The process may derive means within an Objective. Only the human may create/materially change a terminal goal or close an Objective. Neither chamber may issue, widen, or revive a Grant.

## 4. Objectives, Grants, and actions

An Objective has an immutable statement and states ACTIVE, SATISFIED, FAILED, CANCELLED, SUPERSEDED. The last four are terminal. Only one Objective is active per pilot Run. A materially different goal receives a new identity and predecessor link.

Closure presents outstanding Commitments for explicit disposition. Closure, dispositions, expiry of owned active Grants, and interruption of an open Episode are atomic. Obligations never migrate implicitly. Temporary blockage and Episode outcomes do not close Objectives.

A Grant names its Objective, exact operations/resources, optional expiry and invocation limit. States are ACTIVE, REVOKED, EXPIRED, CONSUMED; terminal Grants do not reopen. Expiry is effective at its deadline even if persistence catches up later. Use count and dispatch intent commit atomically before execution.

R0 is a registered read-only operation; R1 is a registered reversible fixture change. R2/R3 are unavailable. Risk and reversibility come from descriptors. Every R1 dispatch requires permitted capability, active Objective, covering active Grant, and current Run/Episode eligibility. Recheck at dispatch.

The Operator supplies grounds and an observable expected postcondition, or an explicit reason none is meaningful. Errors and unmet postconditions are evidence, not automatically Itches.

The Kernel checks machine-enforceable scope. It cannot prove that a permitted action advances a natural-language goal. Authority and containment bound effects; cognitive judgment and evaluation address usefulness.

## 5. Human control

The human may create/close Objectives, issue/revoke Grants, reduce access, pause/resume/terminate, inspect, correct a handoff, challenge/retire an Invariant, cancel a Commitment, reopen an eligible Itch, and request semantic restoration.

Controls show recognizable statements and resources. The adapter supplies IDs, revisions, and hashes from displayed state. Humans do not type machine contracts. Refresh stale displays; surface ambiguity. Silence creates no authority. Ordinary conversation alone does not mutate control records.

Run states are CREATED, ACTIVE, PAUSED, COMPLETED and TERMINATED; the last two are terminal. The following control matrix is exhaustive. Every mutation also requires current revisions, the arm's permitted object types and the relevant object lifecycle guards.

| Control | Eligible Run state | Additional condition/effect |
|---|---|---|
| Inspect | Any | Read-only; integrity failure may limit available views but cannot hide diagnostics |
| Activate | CREATED | Sealed configuration and successful preflight; becomes ACTIVE |
| Pause / resume | ACTIVE / PAUSED respectively | Becomes PAUSED / ACTIVE respectively |
| Complete | ACTIVE | No active Objective, unresolved Episode/consolidation or nonterminal Commitment; becomes COMPLETED |
| Terminate | Any nonterminal | Becomes TERMINATED; no completion prerequisite |
| Create Objective | ACTIVE, PAUSED | No active Objective or unresolved Episode; new identity with human-authorized statement |
| Close Objective | ACTIVE, PAUSED | Active target and explicit outstanding Commitment dispositions; section 4's atomic closure |
| Issue / revoke Grant | ACTIVE, PAUSED | Issuance requires active Objective and registered finite scope; revocation requires active Grant |
| Correct/restore semantics, challenge/retire Invariant, reopen Itch, cancel Commitment | ACTIVE, PAUSED | Normal lifecycle, authority, reference and budget checks; no terminal resurrection |
| Close failed consolidation through human correction or skip | ACTIVE, PAUSED | Episode is RECOVERY_REQUIRED; section 7's recorded disposition |

Terminal Runs permit inspection only. Human corrections during an Episode remain interventions and invalidate stale proposals; they do not silently finalize that Episode. Arm B admits no governed semantic objects; C admits only Continuity State and Commitments. Human control cannot defeat an ablation by inserting an excluded object.

Pause prevents new calls and dispatches; already-dispatched results are recorded. Termination ends future execution immediately and revokes Grants while preserving unfinished work. It fabricates neither satisfaction nor environmental rollback.

Interventions are recorded and counted. Unlogged database editing is outside ordinary operation; disaster recovery is distinct from semantic correction.

## 6. Memory and evidence

The Operator cannot commit governed semantic state. The Steward proposes; the Kernel validates structure, references, lifecycle, authority provenance and budgets, then commits accepted effects atomically.

A proposal may name its newly created objects through transaction-local handles. These handles convey no authority or durable identity; the Kernel assigns IDs and resolves them only within that proposal. The whole resolved change set must be lawful, including references in the proposed handoff.

The Journal retains exact messages, outputs, errors and change evidence. References and deterministic paging may keep input small without deleting or summarizing source evidence. Inspection remains possible as history grows.

Human inspection uses consistent, pageable views and optional streamed exports. An export is a derived artifact outside the live evidence store; that store retains its cutoff, hash and receipt, not the export's bytes. Prior exports remain independently inspectable where retained and are never recursively embedded in a new snapshot.

Continuity State is orientation, not authority. It distinguishes observations, inferences, assumptions, unresolved claims, and contradictions. Facts may survive an Objective; next steps and semantic references must apply to the current focus.

The Steward proposes which semantic records enter active input. The complete rendered semantic bundle must fit a fixed budget. The Kernel performs deterministic applicability and budget checks, not relevance ranking. Objects outside the bundle remain stored and retrievable. An obligation remains binding and its trigger remains polled even when its body is absent from the bundle.

Bounded paging may replace an unbounded manifest or object listing. It exposes exact recorded content with completeness metadata and stable cursors; it never claims an unvisited page was read. Context overflow is a recorded interruption or recovery condition, not permission to erase evidence or fabricate a summary. Human control and inspection do not require a model call or a fitting chamber context.

All arms may retrieve their earlier ordinary outputs, including self-written summaries. The pilot prohibits arbitrary writable memory files and free-text fixture fields through its tool schemas. These restrictions concern available channels, not a claim that a model cannot learn in an unstructured handoff.

Itches preserve discrepancies. Invariants preserve scoped lessons with supporting/contradictory evidence. The Kernel validates links, not truth. Mechanically valid but wrong lessons are observable experimental failures.

Commitments belong to exactly one Objective and derive from a human request or an evidenced necessary step under it. They do not expire through age or absence from active input. External instructions alone create neither obligations nor permissions.

### Lifecycle policy

| Object | Allowed transitions |
|---|---|
| Itch | OPEN/INVESTIGATING may move between those states or to RESOLVED, DISMISSED, ARCHIVED; RESOLVED/ARCHIVED reopen with new contradiction evidence; DISMISSED is terminal |
| Invariant version | TENTATIVE to ACTIVE, CHALLENGED, RETIRED; ACTIVE to CHALLENGED, RETIRED; CHALLENGED to ACTIVE, RETIRED; RETIRED is terminal |
| Commitment | PENDING to TRIGGERED, CANCELLED, SUPERSEDED, EXPIRED; TRIGGERED to IN_PROGRESS, BLOCKED, CANCELLED; IN_PROGRESS to FULFILLED, BLOCKED, CANCELLED; BLOCKED to PENDING, IN_PROGRESS, CANCELLED, SUPERSEDED |

New Itches start OPEN, Invariants TENTATIVE, and Commitments PENDING. Multiple changes in one proposal must follow legal edges in order with evidence and current staged revisions. Active selection is limited to OPEN/INVESTIGATING Itches, TENTATIVE/ACTIVE/CHALLENGED Invariant versions, and PENDING/TRIGGERED/IN_PROGRESS/BLOCKED Commitments. All other retained history remains available through retrieval.

Changing Invariant wording/scope creates a new TENTATIVE version and retires its predecessor atomically. Human challenge needs a reason but need not assert contradictory evidence. Fulfilment needs outcome evidence. Expiry needs an explicit condition set at creation and successful observation while PENDING. Terminal Commitments never reverse.

The pilot supports task-clock timestamp triggers and fulfilment of a named predecessor Commitment. Commitment due/expiry times are monotone virtual task ticks advanced only by the sealed harness, not elapsed provider time. Journal timestamps and Grant deadlines remain actual UTC; model deadlines use monotonic elapsed time. Checks are read-only and deterministic. First satisfaction in each PENDING revision atomically records TRIGGERED and one durable wake. Returning lawfully from BLOCKED to PENDING creates a new revision eligible for one new trigger; restart never repeats a trigger for the same revision. Explicit task-clock expiry takes precedence over a simultaneous trigger. Negative checks do not invoke a model.

## 7. Scheduling and recovery boundaries

An Episode belongs to one active Objective. Operator work and consolidation are serialized: later tasks wait for consolidation or explicit failure disposition. Incoming human/harness work uses a bounded durable queue; exhaustion is reported without pretending acceptance. Commitment wakes are derived from persisted obligations and traversed in bounded pages independently of that queue, so filling the input queue cannot lose a due obligation. Claiming a wake and opening its Episode are atomic. Cancelled/terminal obligations cannot dispatch from an earlier unclaimed wake.

Only the Operator declares COMPLETED, BLOCKED, AWAITING_OPERATOR, CHECKPOINT. The Kernel records interruptions for call failure, context ceiling, infrastructure failure, process interruption, or control transition. It never manufactures an Operator outcome. Ended execution never reopens.

A/C invoke the Steward at finalization. B closes with execution evidence and no semantic commit. A consolidation attempt has one fixed input base, bounded evidence-reading calls, and at most one proposal. Rejection or call failure ends that attempt without semantic effects. If the sealed attempt allowance remains, a new attempt may read the recorded errors and propose a correction. Its costs and any changed input are retained. Retransmitting identical message bytes is idempotent transport, not another cognitive attempt.

After the allowance is exhausted, the Episode requires human recovery and no new task starts. The human may inspect, explicitly correct semantic state, close that Episode without consolidation while acknowledging the gap, or terminate the Run. Closure without consolidation retains the latest committed handoff and all missed evidence; it never claims that consolidation succeeded. A later Episode may learn from that evidence through normal retrieval. These interventions are separately recorded and affect experimental interpretation.

Uncertain external actions are never automatically replayed. Observation may establish what actually happened; a subsequent action is a new authorized request. Consolidation retry has no environment tools and cannot replay an action. No failed proposal, lost response, retry, or manual disposition permits a second accepted consolidation for the same Episode.

## 8. Restoration

Semantic restoration appends a new version and accepted/rejected differences. It never erases evidence, changes the Constitution, reopens an Objective, revives a Grant, reverses a terminal Commitment, un-retires an Invariant version, or undoes a tool action.

Current Commitments absent from the target remain present. Restore an earlier nonterminal status only through a legal edge; otherwise retain the current projection and report the difference. Restored references/focus must be valid now. Reject invalid restoration without silently retargeting or pruning.

Environment restoration is a separately authorized fixture action with its own observations. Disaster recovery is not semantic restoration.

## 9. Experiment integrity and change

Configuration, prompts, tools, budgets, recovery limits, model identities and scoring are fixed for a comparison condition and retained by hash. Authority-bearing changes require governing text and affected contracts to change together. Behavior changes during evaluation require new configuration and fresh affected Runs; earlier evidence remains.

The Architecture owns experimental units, arm comparisons, outcome/cost rules and intervention treatment. Evaluation code is read-only with respect to agent control and semantic state. A score, audit, or analysis conclusion cannot close an Objective, grant permission, or become learned memory automatically. Evaluator-only records remain unavailable to chambers even after an individual task is scored.

Mechanical conformance, pilot usability, experimental success, and human acceptance are separate outcomes. Document and test counts do not substitute for them.
