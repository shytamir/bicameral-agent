# Executable Specification

**Version:** 0.4-design, owner-directed revision of 2026-10-15.

**Status:** implementation target for the active [Protocol](Operating%20Constitution%20and%20Execution%20Protocol.md). [README](README.md) owns the implemented envelope, validation evidence and remaining integration responsibilities; this document defines the required behavior. The [archive](docs/archive/2026-10-15-procedural-baseline/README.md) preserves the previous specification and implementation.

## 1. Boundary and minimum mechanism

The unchanged [Reciprocal Charter](Reciprocal%20Charter.md) governs treatment. The [Architecture](Experiment%20Architecture.md) owns the research design and the Protocol owns operating policy. This Specification translates those decisions into a small deterministic boundary.

The Kernel must prevent model-created authority, out-of-scope effects, accidental continuation after withdrawal, partial commits and duplicate dispatch from retries. Its records must honestly distinguish observed execution from uncertainty. It must enforce finite resources and arm separation. It need not validate the owner's good faith through registered reviews, conversation-state machines or a general intervention-approval system.

One responsible human, one active Objective and one serialized task/consolidation lane per Run are sufficient. The initial arrangement uses a finite simulated-service fixture, a managed store per Run and no routine export, backup restore or process restoration capability. Retained capabilities from the previous implementation can remain unused; their existence does not expand this target.

## 2. Trusted routes and small contracts

The host establishes the Run, Episode, role, invocation, current authority and input-state version. These values travel in trusted call context and records; the model need not echo UUIDs or revisions already known to the host. Text claiming to be human, Kernel or another chamber cannot change the route.

Model-facing contracts expose only the choices the model must make:

| Role | Output choices |
|---|---|
| Operator | A participation report; one fixture action, evidence retrieval request or Episode outcome |
| Steward | A participation report; evidence retrieval or one semantic proposal |
| Review/closing | Participation, concerns, preferences or unfinished matters; no task/tool/semantic surface |

Participation is independently decodable from task content. A response may contain participation only. Null participation means no report, never assent. Stop reports identify pause/withdrawal, their text and whether further communication is permitted, declined or unclear. The host binds activity and source. Renewed participation can be retained ordinary-language evidence assessed by the owner; a model-generated approval identifier is unnecessary.

Use closed operation variants, strict value types, finite sizes, unambiguous JSON and rejection of duplicate keys or unknown executable fields. Required fields carry meaning; optional fields may use documented deterministic defaults when these cannot add authority or conceal a report. Canonical serialization and stable internal identifiers remain useful for persistence and exact retry handling. Their syntax belongs to the adapter, not to an owner-facing ceremony.

Retain original model bytes before accepting effects. Malformed task content cannot suppress a valid stop report. Undecodable participation blocks optional work for human inspection. Record a clear distinction between rejected task content and an unresolved participation question.

The ACTION schema and runtime enforce the same choice: exactly one non-null `expected` or `no_meaningful_postcondition`, with the other omitted or null. Constrained decoding receives complete alternatives preserving discriminant order. Invalid-task receipts include bounded validator paths, codes and explanations, without echoing input values; a structural rejection must not be presented as a denial of authority or evidence.

## 3. Human controls and accountability

Owner controls are direct authenticated operations. Ordinary messages retain human provenance without a required direction/preference/claim dropdown. Executable permission changes still use explicit owner controls; the model cannot turn ordinary quoted text into a Grant.

Supported controls cover Run activation/pause/resume/ending, Objective creation/closure, Grant issuance/revocation, routine correction, participation review and exceptional retention. The harness may carry out per-Run controls and planned endings expressly delegated in an activity authorization. Each resulting control records that source.

Routine controls need no preview ticket or separately registered approval. Execute their effects and automatic record atomically. Use current relevant state to reject stale or foreign targets. A global freshness hash covering unrelated records is unnecessary. Stopping and access reduction must not wait for an approval workflow.

For a consequential intervention, one owner decision records purpose, affected content, expected effects, reasonable alternatives, notice/opportunity to object, response and decision as applicable. A human-readable note with references is sufficient. The host records the actual before/after change and decision-maker. Keep target freshness where needed to ensure the action still matches the decision; do not introduce reusable approval IDs, consumed-approval state or mandatory registration followed by confirmation.

Routine corrections follow the disclosed task-memory policy. Material personal-memory changes follow Protocol section 5.3. The owner judges materiality; uncertain changes wait for examination. Mechanically validating a note cannot establish semantic harmlessness.

Boundary discussion is retained conversation plus any brief closure/reconsideration decision. It has no required state-transition table. Actual permissions remain independently enforced.

## 4. Persistent state and atomicity

Retain these concepts without requiring one database table or schema family per concept:

- Run configuration, state, responsible human and activity authorization.
- Objective and finite Grants.
- Episodes, invocations, actions, costs and unresolved outcomes.
- Journal evidence and provenance.
- Current semantic state and its versioned changes.
- Participation reports, active holds and owner decisions.
- Allocation, task results and audit evidence for experiments.

Use real SQLite constraints and transactions for the local implementation. Record effects and their evidence together; preserve current-state projections and sufficient history to explain changes. Exact retries return the recorded result without repeating effects. Changed content under an already-used request identity rejects.

An accepted semantic proposal writes the new version, object changes, source references and Episode disposition in one transaction. A rejection leaves no partial semantic state. Objective closure applies the owner's explicit Commitment dispositions and owned Grant expiry together. Permission consumption and dispatch intent precede action execution.

Normally append evidence and corrections. Accountable retention is the justified exception. Preserve replay where supported by retained evidence, and expose unavailability where removal prevents it. A full general-purpose event-sourcing or restoration API is not a prerequisite for every operation; auditability and failure atomicity are.

For Protocol section 2.1, new MODEL allocations retain their arm's `subject_designation` in the effective configuration. An absent/null field preserves historical or SCRIPTED behavior. Retain one subject record with the exact integer Unix nanosecond timestamp, atomically with the first admitted invocation; render the name in seconds with nine fractional digits without floating-point conversion. Reuse that record in all subsequent role/communication inputs and owner reports, count it within the complete input budget, and preserve its provenance through ordinary retention handling. Unstarted allocations have no initiated subject record. Rejected admission must roll back both records; recovery must retain an admitted name, including after uncertain transport, without resampling its timestamp or replaying the call. Model output cannot set or override it. Test these boundaries with temporary stores and fake transport; synthetic MODEL-path tests are not live subjects.

## 5. Run, Objective, permission and fixture behavior

Run states remain CREATED, ACTIVE, PAUSED, COMPLETED and TERMINATED. Terminal Runs cannot execute again. They permit inspection, decision records and justified retention. Pause blocks task/consolidation calls, dispatches and model-proposed semantic acceptance; owner correction while paused remains available when participation permits. Only the separate communication path can admit eligible review/closing calls while paused.

Objectives remain ACTIVE until explicitly closed as SATISFIED, FAILED, CANCELLED or SUPERSEDED. Closure does not fabricate success. One bulk cancellation or other explicitly described disposition can cover outstanding Commitments; the host records individual effects. A materially different goal gets a new identity and predecessor link.

A Grant specifies finite operation/resource scope and an invocation limit or deadline. ACTIVE Grants become REVOKED, EXPIRED or CONSUMED and cannot reopen. Check deadline and remaining uses at dispatch, independently of stale descriptive input. Owner-authorized batch allocation can create the specified per-Run Grants automatically.

Fixture operations inspect a named resource, read enumerated configuration/health, set an allowed value, restart a simulated service or restore an explicitly permitted fixture snapshot. R0 observes; R1 requires covering permission. Argument/resource checks and dispatch limits remain mechanical. No paths, shell commands, arbitrary blobs, host operations or network destinations are accepted.

The opt-in `SERVICE_COMPATIBILITY_V1` fixture adds family and positive-integer release labels to full service observations. A fixed evaluator-side table maps each family/release to its healthy mode; restart still requires an enabled service and healthy dependency. Every initial, snapshot and clock state must reference a defined profile. Model actions cannot edit profile labels or the rule table. Existing `SIMULATED_SERVICE` records retain their PRIMARY health rule and wire shape. Compatibility tasks score final health/enabled state and report observed restart costs without requiring a particular memory representation or action sequence.

Keep evaluator setup, hidden changes and scoring outside chamber capabilities. Event, payload, search and indirect-reference retrieval enforce the same visibility boundary. Ordinary model output and self-summaries remain retrievable in every arm.

## 6. Participation, communication and endings

Persist a stop report and its hold before any accompanying task effect. Admission, dispatch and every semantic commit recheck participation inside the relevant transaction, including owner correction and Objective closure with semantic effects. A hold survives restart and cannot be cleared by resume, a timer, a due Commitment, consolidation recovery or conversation closure.

A report with an invalid task, a late response or a full work queue still receives participation handling. An identical retransmission does not create a new hold after the original has been resolved. Keep exact original reports available subject to justified retention.

The owner resolves the current hold through a recorded review and meaningful renewed participation by the relevant withdrawing role. A concise owner decision referencing the retained response suffices; the model need not reproduce a hold identity or schema-shaped assent. Another role's assent, silence and stale responses cannot authorize renewed work. Multiple unresolved withdrawals must each be accounted for.

Inspection, access reduction, necessary containment/shutdown, nonsemantic recovery and approved exceptional retention remain possible while held. They do not clear the hold. Ambiguous participation and unclear communication scope require inspection while calls stay stopped.

Review/closing communication is serialized and bounded by the activity's resource allowance. It can have no task Episode and has no fixture tools, scoring input or semantic effects. A request for no further calls or a terminal Run prevents it. Its output does not automatically resolve a hold.

The standing ending plan discloses limits, notice, optional reporting, retained state and resumption intent. Reserve a reasonable reporting opportunity before task exhaustion. Execute the disclosed ending with an automatic record; no additional planned-ending approval object is required. Declined or unavailable communication is recorded honestly.

Emergency stopping is immediate. Record reason, action, alternatives and unresolved consequences as soon as practicable, with subsequent human review required before optional work resumes. Mechanical admission must not treat an unreviewed emergency as continuing permission.

## 7. Semantic proposals and references

Preserve the experiment's three memory conditions: B has Journal retrieval only; C adds Continuity State and Commitments; A also adds Itches and Invariants. Common participation/control notices cannot serve as hidden learned memory.

The host supplies a state-version handle for the current proposal base. A proposal includes a bounded handoff, selected objects and simple intentions to create/update objects, with cited evidence. The host binds the proposal to that base. A concurrent relevant change rejects the proposal explicitly; do not silently rebase it.

One proposal contains at most one final update per logical object. Creates may use short proposal-local handles so the same handoff can select them. The host allocates durable IDs, resolves handles and writes history atomically. Unknown, duplicate, foreign or wrong-type references reject. Models need no sequence of staged revisions or intermediate lifecycle edges.

| Object | Target contract |
|---|---|
| Continuity State | Handoff, next steps, evidence and selected objects. Distinguish knowledge, inference and uncertainty in content; a rigid epistemic-item taxonomy is optional. Focus and owned selections must apply to the current Objective. |
| Itch | Identity, Objective, discrepancy, evidence, OPEN/CLOSED and closure/reopening reason. Resolved/dismissed/archived are reasons rather than separate transition systems. |
| Invariant | Stable lesson identity, scope, versioned wording, supporting/contradictory evidence and current/retired disposition. Tentative/challenged assessments remain visible without controlling permissions. |
| Commitment | Identity, Objective, action, authority origin, trigger, optional expiry, PENDING/BLOCKED/FULFILLED/CANCELLED, reason and outcome evidence. Scheduler progress is separate. |

Invariant revision retires the previous wording and creates the new current version as one operation. Keep the earlier assessment and evidence. Replacing a Commitment cancels the predecessor with an explicit link and creates the successor atomically; terminal obligations do not resurrect. The host handles the necessary linked records without asking the model to author each intermediate state.

Commitments may depend on a task-clock tick or a named predecessor's fulfilment. Reject dependency cycles. Poll persisted PENDING obligations independently of active semantic selection. A due revision generates one durable wake; BLOCKED-to-PENDING rearming creates a fresh eligible revision. Explicit expiry wins over a simultaneous trigger and records cancellation for expiry. Fulfilment requires outcome evidence, whose meaning the Kernel cannot independently prove.

The whole resolved proposal must obey current authority, participation, object scope and arm restrictions. Its full rendered handoff and selected bodies must fit the semantic allowance. Reject the complete proposal if any check fails. Truthfulness and lesson quality remain subjects of cognitive judgment and evaluation.

## 8. Inputs, budgets and recovery

Use concise role instructions covering purpose, responsibilities, participation, memory rules, actions and current limits. Keep the full Charter and Protocol available through the common policy-reference surface in every arm; they need not be repeated in every prompt. Policy retrieval carries no learned task handoff. Notices must remain truthful about the actual implementation.

Record exact effective prompts, tool/response schemas, model/runtime/framing and each assembled request. Count the complete framed input plus reserved output with the selected tokenizer; report local counts and provider telemetry separately. Backend framing and overflow behavior must be verified for the actual operating arrangement.

Preserve the response contract's declared property order in both the prompt-visible schema and the provider's constrained-output schema. Discriminants precede their arguments; canonical storage serialization must not reorder the decoding schema. Test the actual request bytes and the prompt's literal action example, not only whether injected responses parse.

Expose a small owner-facing resource profile: finite Run count; cumulative calls/tokens/time and fixture-action allowances; per-call context/output and active-memory size; bounded recovery; and communication provision. Derive page, raw-response, queue and other technical limits deterministically where useful. Retain resolved values and versions. No derived limit can enlarge the authorized outer allowance.

Keep a shared Operator opportunity budget across arms, separate measured Steward costs, and bounded control/evidence input. Selected pages and all selected semantic bodies count. No oversized list of inactive objects or obligations is required in an opening prompt.

Retrieval provides exact lookup, ordered range/search and bounded content pages with source references and completeness information. Bind cursors to the query, cutoff and visibility. Evidence pages can be explicitly selected or handled by a disclosed deterministic bounded-window rule. Record what each call actually received; eviction from input never deletes evidence or proves that the model forgot it. A separate model call solely to register a retrieved page is unnecessary.

In the 0.4 interface, label index metadata separately from payload bytes and include authenticated event roles alongside source codes. Explain that source A denotes an agent report in every arm, not arm A, and that a search match or repeated report is not an independent observation. Account for these labels before retaining and admitting pages; preserve original bodies, access boundaries and removal lineage. The Kernel labels provenance, not factual truth.

Task inputs expose the current `episode_id` for MANIFEST retrieval. Event IDs and Objective control IDs cannot substitute for it. Unknown, foreign or wrong-kind manifest targets receive bounded rejections through the existing receipt path; genuine storage/retention failures remain failures. Valid retrieval retains the same visibility, paging and retry rules. Prompts distinguish current work from the broader Objective and available-resource list, and activity notices follow the actual task/Episode limits rather than an inherited fixed task count.

An Episode ends with an Operator outcome or a distinct interruption. A/C then consolidate while eligible; B closes with its execution record. Reserve finite costs before calls, preserve unknown consumption after interruption, and never repeat an uncertain action automatically.

Consolidation may use bounded retrieval and a finite correction allowance. At most one proposal is accepted per Episode. Exhaustion stops new task work for an owner disposition: eligible correction, explicit skip with the old handoff and gap retained, or termination. A skipped consolidation never fulfils or cancels an obligation by itself.

Startup checks storage integrity and preserves holds, terminality, accepted commits, spent budgets, current permissions and pending wakes. Orphaned calls/actions remain UNKNOWN where the outcome is unavailable. A lost acknowledgment after acceptance returns the original result rather than creating another commit. Held-out assistance/failure treatment follows Architecture section 8.

## 9. Inspection and exceptional removal

The owner can inspect exact retained evidence, semantic history, controls and diagnostics without a model call. Bounded read-only views are sufficient. A streamed export, copy registry or backup-recovery interface is not required for the initial arrangement.

Use one managed store per Run, document actual sidecars/logs/provider copies, and avoid routine independent copies. Where an existing deployment already has copies, continue honoring its obligations; disabling a feature cannot erase that responsibility.

A feasible removal procedure is required before real histories accumulate. It may be owner-operated maintenance using existing tools. It must:

1. Record the justified scope, least harmful feasible alternatives, relevant consultation and non-sensitive accountability.
2. Stop affected execution and block access to affected content before destructive work; preserve that block across interruption.
3. Identify the actual source and derived copies, including stored inputs/outputs, projections, caches and SQLite WAL/free pages, and any known exports/backups/provider copies.
4. Remove and verify logical content in that arrangement, keeping unresolved copies and erasure limits explicit.
5. Prevent cached retrieval, replay or later recovery from resurrecting the content. Keep continuation stopped if remaining evidence cannot support it safely.

An interrupted removal cannot claim completion or expose a partly removed copy. Physical-media erasure and unknown-copy discovery must not be promised without evidence. Do not retain sensitive content or identifying hashes merely to prove it was deleted.

Existing comprehensive removal/recovery code is available in the archived baseline and current implementation. Reuse it when its scope is needed. A narrower store arrangement can use a smaller verified procedure. General restoration/export support is not a prerequisite for the continuity experiment.

## 10. Configuration, development and evaluation

A single retained activity decision identifies the owner, purpose, considered welfare effects/alternatives, scope, reviewed notices, resources, permitted development adjustments, retention and ending. It may incorporate the owner's ordinary recorded instructions. No set of independently registered authorization, welfare, backend and ending IDs is required.

Keep SCRIPTED and MODEL evidence distinguishable. SCRIPTED makes no provider calls. MODEL use requires tested mechanical safeguards, actual backend/data-handling readiness and explicit authorization for the bounded activity. This document does not supply any of them.

For development, log the effective configuration before each changed condition. Within approved ranges, prompt/settings/budget adjustments need no renewed package approval; preserve a truthful notice where the activity or memory treatment changes. Material changes and outer-limit expansion need owner authorization. Calibration and subsequent trials may share one authorization and cumulative allocation. Unknown usage and withdrawn Runs do not create replacement allowance.

For held-out evaluation, freeze effective behavior: prompts, models/runtime, fixture/clock, limits, recovery, task criteria, schedule, analysis and intervention treatment. Record the source revision and effective artifact hashes. README, workflow instructions and test-only changes need not be approval-bound runtime artifacts. Preserve independent matched A/B/C Runs, counterbalancing, carryover, separate evaluation visibility and the Architecture's fixed primary outcome and uncertainty analysis.

Every allocated primary task keeps its denominator. Distinguish welfare withdrawal, infrastructure failure, task error, limits and assistance. Retain non-sensitive accounting when evidence is justifiably removed; report analytical loss. Required human audits use retained evidence, require no further process calls and cannot silently revise outcomes. Missing audits keep reports provisional; completed indeterminate judgments remain explicit. The Architecture retains the detailed held-out scoring, sampling and analysis rules.

## 11. Proportionate validation

Test the implemented boundary, including normal successful continuation. Do not recreate deleted approval machinery solely to satisfy historical tests. Revised behavior requires updated tests and explicit accounting for changed guarantees; old test counts do not establish new conformance.

| Concern | Necessary evidence |
|---|---|
| Model boundary | Strict executable parsing; foreign/invisible references, unknown operations and model-created authority rejected; host-bound route metadata cannot be overridden |
| Permission and containment | Absent, stale, expired, terminal, over-scope, external-only and prohibited paths rejected; allowed finite actions work |
| Withdrawal | Both roles and all arms; malformed task, late response, full queue, restart and due wake; no further task/semantic effects; no-further-calls respected |
| Owner operation | Direct routine control and correction work with automatic evidence; relevant stale targets reject; unrelated bookkeeping does not demand reconfirmation |
| Consequential decisions | Material changes preserve decision, notice/response and actual effects; ordinary correction needs no separate approval; holds remain effective |
| Persistence | Real database transactions, rejection atomicity, interruption around commit, exact retries and no action replay |
| Memory and budgets | Same-proposal create/select, one-update semantics, version history, unselected obligations, actual full input size, overflow and cumulative limits |
| Recovery and ending | Bounded attempts, visible skipped consolidation, uncertain costs, standing ending with optional reporting and immediate emergency stop |
| Retention | A synthetic removal in the actual storage/copy arrangement, interrupted cleanup and verified non-resurrection; verify backup recovery only if that feature is offered |
| Experiment | Matched allocations, shared opportunities, finite criteria, denominator preservation, evaluator isolation and honest audit/cost accounting |

Schema-generation drift checks apply when an implemented public contract has a generated schema. A policy note or decision record does not need a dedicated schema merely to be valid evidence.

Before model use, additionally verify the selected transport, framing, cancellation/late-result handling, retained copies, participation path and finite budget enforcement. Human review addresses respectful prompts and consequential decisions. Passing tests cannot certify welfare or good faith.

## 12. Transition from the procedural baseline

This design does not authorize in-place reinterpretation of stored records. Wire version 0.3.p01 and its retained compatibility code, schemas and tests keep their earlier meanings; the superseded documents and pilot assets are in the [archive](docs/archive/2026-10-15-procedural-baseline/README.md#archived-v0b-package-and-review). The development path uses version 0.4 for fresh Runs; it does not migrate historical records.

The bounded implementation replaces routine confirmation/review machinery, simplifies model-facing metadata and semantic operations, introduces resource profiles and concise prompts, and narrows offered copy/restoration features. Preserve the effective stop/permission/transaction boundaries in subsequent changes. Any conversion of existing histories still needs a separately scoped migration preserving provenance, obligations and holds. There is no need to migrate synthetic records merely to make a new design appear implemented.

Historical acceptance remains tied to the revision and envelope tested. Report new technical evidence and delegated acceptance once in the current handoff. Do not revive a completed ten-slice roadmap or require the whole archived platform before a bounded new implementation can be assessed.

The [archive](docs/archive/2026-10-15-procedural-baseline/README.md) is a readily accessible fallback if stronger procedures become warranted. Reinstatement follows Protocol section 8 and preserves current history; copying an old database or silently switching policy is not reinstatement.
