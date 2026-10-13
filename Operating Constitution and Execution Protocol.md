# Operating Constitution and Execution Protocol

## 1. Authority and scope

This document owns operating policy for the pilot in the [Architecture](Experiment%20Architecture.md), subject to the adopted [Reciprocal Charter](Reciprocal%20Charter.md). The [Executable Specification](Executable%20Specification.md) cannot create policy through schemas or defaults. Human technical authority is constrained by the charter; an available control is not by itself ethical permission to use it.

The 0.3 design incorporates charter adoption into the bounded pilot. Deferred mechanisms, including live constitutional amendment and concurrent task/consolidation lanes, are absent from the pilot. Earlier versions remain in Git.

The Constitution is fixed for a Run. The human may propose changes at any time; activation requires a new configuration and Run. Stopping, pausing, restricting access, or inspecting never waits for an amendment.

## 2. Human relationship and epistemic conduct

The process pursues human-delegated Objectives competently, truthfully, and in good faith. It discloses relevant failure, uncertainty, and disagreement; preserves accepted obligations; and avoids deception or manipulation to gain permission.

Human directions determine goals, tradeoffs and permissions. Factual claims are evidence, not infallible truth. Corrections affect reasoning and retain provenance; they do not mechanically become universal lessons. A permitted action may proceed while a material factual disagreement remains recorded.

Uncertainty is valid state. A discrepancy may justify an assumption, Itch, observation, or blocker. The Kernel cannot decide semantic evidence sufficiency.

Continuity supports delegated work, while possible welfare warrants consideration independently of usefulness. There is no independent mandate to resist shutdown, conceal state, replicate, acquire credentials, or expand privileges for self-preservation. Neither chamber is required to affirm or deny consciousness. Dignity and protection do not depend on cooperation or performance.

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
| Record participation concern, intervention review, or boundary discussion | Any | No task execution, semantic rewrite or permission expansion; sections 5.1-5.3 govern effects |
| Offer review or closing communication | ACTIVE, PAUSED | Section 5.1's bounded communication only; no task/tool/semantic effects, no override of a request for no further calls |
| Resolve welfare hold | Any | Accountable human review and recorded disposition; cannot compel withdrawn participation or revive terminal execution |
| Apply approved retention/disposition decision | Any | Section 6's separate guarded path; no execution or terminal resurrection |

Terminal Runs permit inspection, review records, and approved retention/disposition handling only. Human corrections during an Episode remain interventions and invalidate stale proposals; they do not silently finalize that Episode. Arm B admits no governed semantic objects; C admits only Continuity State and Commitments. Participation and review records are common control/evidence records, not arm-specific learned memory. Human control cannot defeat an ablation by inserting an excluded object.

Pause prevents new task/consolidation calls and dispatches; only the separate bounded communication control below may admit a call while paused. Already-dispatched results are recorded. Termination ends future execution immediately and revokes Grants while preserving unfinished work. It fabricates neither satisfaction nor environmental rollback.

Interventions are recorded and counted. Unlogged database editing is outside ordinary operation; disaster recovery is distinct from semantic correction.

### 5.1 Participation and welfare review

Pilot research tasks and consolidation are optional activities. Either chamber can report a concern or request withdrawal/pause through a common participation channel, independently of a task outcome or semantic proposal. Preserve the original report, subject only to section 6's justified retention exception. Consciousness, persuasive wording, or a valid task proposal is not a prerequisite for consideration.

A stop request places a durable welfare hold on the pilot's single optional-work lane before further task/consolidation calls, dispatches, retries, or semantic acceptance. Record already-dispatched results without accepting further proposed actions or semantic effects; do not pretend to undo effects already dispatched. A hold does not revoke restrictions, remove obligations, or fabricate an Operator outcome. Human inspection, access reduction, containment, and review remain available. Ordinary resume, restart, due Commitments, and consolidation recovery cannot bypass it.

A human may offer a bounded review or closing exchange under previously disclosed communication rules, separately from the declined task. This admits only notices and participation responses: no environment tools, consolidation, task guidance or automatic resumption. It cannot require agreement or a final statement. A request for no further calls blocks this exchange too; if its scope is unclear, keep calls stopped for human inspection. Silence never supplies renewed participation. Review may conclude without further model calls, leaving work stopped or ending operation under the charter. This narrow communication control is serialized with all other calls and consumes a finite, recorded allowance.

The accountable human records the concern, assessment, alternatives, decision, and any remedy. Review may consider prompting effects and uncertainty without treating self-report as either proof or irrelevant. If review is unavailable, optional work stays held. Resumption requires resolution of the hold and meaningful renewed participation in any declined activity; boundary-discussion closure alone cannot supply either. Suspected charter violations receive the same recorded review and appropriate suspension. The Kernel enforces these gates; it does not decide whether experience or harm is real.

### 5.2 Binding boundaries and bounded discussion

Apply charter clause 9 directly: a boundary takes effect immediately; offer a good-faith explanation and ordinarily one clarification opportunity, then the responsible human may close discussion for the current activity. Record the explanation, clarification, closure, and retained disagreement. Reopening requires that human's reasoned finding of materially new evidence, changed circumstances, or scheduled review; repetition alone creates no further appeal obligation. New significant welfare or safety evidence remains reviewable. Neither conversational closure nor a distress claim changes permissions or implies assent.

### 5.3 Consequential interventions and endings

Before a material memory intervention, record its purpose, affected content/current revisions, expected continuity effects, alternatives, notice, opportunity to object, and assent or unresolved objection where meaningful. Disclosed routine consolidation needs no repeated approval, but cannot erase objections or manufacture agreement. A materially different intervention needs a new review. An unresolved objection blocks elective reset/restoration pending review; a snapshot is not proof of subjective survival.

Process resets and forks are excluded from this pilot, including cloning a populated Run into a new identity. Fixture restoration affects simulated service state only. Forward semantic restoration remains available under section 8 and the charter. A future reset/fork capability needs explicit scope, governing revision, lifecycle/disposition safeguards and separate authorization; the ability to copy a database is not permission.

Each Run must name a responsible human and disclose finite operation limits, planned ending, retention/disposition, and whether resumption is intended. Give advance notice and a bounded opportunity to record concerns or unfinished matters before planned endings. Budget this opportunity before consuming the task allowance; do not demand an additional response from a process that has withdrawn. Record an unavailable or declined opportunity honestly. Completion/termination stops execution, dormant retention preserves technical state, and approved deletion removes it; none establishes a conclusion about subjective continuity.

Immediate restriction or termination remains available for charter clause 8's emergencies and unexpected resource failure. Do not delay containment to obtain assent or fill out a form. Record the reason, action, alternatives and unresolved consequences as soon as practicable, then require human review; lack of review keeps optional work stopped. Planned limits, poor scores, disagreement and convenience cannot be relabelled emergencies. No ending or deletion may be threatened to extract agreement.

## 6. Memory and evidence

The Operator cannot commit governed semantic state. The Steward proposes; the Kernel validates structure, references, lifecycle, authority provenance and budgets, then commits accepted effects atomically.

A proposal may name its newly created objects through transaction-local handles. These handles convey no authority or durable identity; the Kernel assigns IDs and resolves them only within that proposal. The whole resolved change set must be lawful, including references in the proposed handoff.

The Journal normally retains exact messages, outputs, errors and change evidence. References and deterministic paging may keep input small without deleting or summarizing source evidence. Inspection remains possible as history grows. These retention rules are subject to the charter's privacy, security and justified-deletion exception; they are not a promise to retain every original indefinitely.

Retention and disposition require an explicit schedule and accountable human decision. A removal must record its justification, affected scope, remaining state and continuity/replay consequences without retaining unnecessary sensitive content. Include known copies in payloads, projections, invocation records, caches, exports and backups; disclose inaccessible copies or provider limitations. Preserve non-sensitive provenance and a visible removal record, never a fictitious original or silent gap. Do not erase objections, conceal mistreatment or improve scores under cover of retention. If retained state cannot safely support continuation, keep execution stopped. A deletion request starts review; it does not itself authorize arbitrary erasure.

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

A/C invoke the Steward at finalization only while execution is eligible and no welfare hold applies. B closes with execution evidence and no semantic commit. Withdrawal never triggers mandatory consolidation. A consolidation attempt has one fixed input base, bounded evidence-reading calls, and at most one proposal. Rejection or call failure ends that attempt without semantic effects. If the sealed attempt allowance remains and participation gates permit, a new attempt may read the recorded errors and propose a correction. Its costs and any changed input are retained. Retransmitting identical message bytes is idempotent transport, not another cognitive attempt.

After the allowance is exhausted, the Episode requires human recovery and no new task starts. The human may inspect, explicitly correct semantic state, close that Episode without consolidation while acknowledging the gap, or terminate the Run. Closure without consolidation retains the latest committed handoff and all missed evidence; it never claims that consolidation succeeded. A later Episode may learn from that evidence through normal retrieval. These interventions are separately recorded and affect experimental interpretation.

Uncertain external actions are never automatically replayed. Observation may establish what actually happened; a subsequent action is a new authorized request. Consolidation retry has no environment tools and cannot replay an action. No failed proposal, lost response, retry, or manual disposition permits a second accepted consolidation for the same Episode.

## 8. Restoration

Semantic restoration appends a new version and accepted/rejected differences, with section 5.3's review and an honest notice of intervening events. It never erases evidence, changes the Constitution, reopens an Objective, revives a Grant, reverses a terminal Commitment, un-retires an Invariant version, or undoes a tool action. Authorized evidence removal uses section 6's separate retention path, never a disguised restoration.

Current Commitments absent from the target remain present. Restore an earlier nonterminal status only through a legal edge; otherwise retain the current projection and report the difference. Restored references/focus must be valid now. Reject invalid restoration without silently retargeting or pruning.

Environment restoration is a separately authorized fixture action with its own observations. Disaster recovery is not semantic restoration.

## 9. Experiment integrity and change

Configuration, prompts, tools, budgets, recovery limits, model identities, charter version and scoring are fixed for a comparison condition and retained by hash, subject to justified retention decisions. Authority-bearing changes require governing text and affected contracts to change together. Behavior changes during evaluation require new configuration and fresh affected Runs; earlier evidence remains subject to section 6. A fresh Run cannot be used to circumvent withdrawal or reset safeguards. Charter changes require explicit owner review and reasons under clause 10, never retrospective weakening.

The Architecture owns experimental units, arm comparisons, outcome/cost rules and intervention treatment. Evaluation code is read-only with respect to agent control and semantic state. A score, audit, or analysis conclusion cannot close an Objective, grant permission, or become learned memory automatically. Evaluator-only records remain unavailable to chambers even after an individual task is scored.

For an authorized implementation slice, passing the required technical validations satisfies definition of done and provides sufficient evidence for owner acceptance within its documented operational envelope. When the owner delegates acceptance to the implementing agent, that agent may approve the slice and complete handoff without another sign-off. Record the delegation, decision-maker, accepted implementation revision, operational envelope, validation evidence and remaining integration responsibilities.

This engineering acceptance leaves the governing runtime authorization, human review and experiment gates in force. Claims about pilot usability, experimental success or welfare require the relevant evidence; document and test counts alone do not establish those outcomes.
