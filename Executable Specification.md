# Executable Specification

**Version:** 0.3-design

**Status:** P01-P10 and integrated v0a have synthetic technical validation and delegated owner acceptance within their documented operational envelopes. Model development and held-out experiments retain the separate v0b/v0c gates.

## 1. Contract boundary

This document defines mechanical design under the adopted [Reciprocal Charter](Reciprocal%20Charter.md), [Architecture](Experiment%20Architecture.md) and [Protocol](Operating%20Constitution%20and%20Execution%20Protocol.md). They own ethical obligations, research scope and policy. Historical decisions remain in Git and confer no readiness.

The first implementation is LLM-less: scripted messages exercise the boundary intended for models. No provider substitutes for deterministic behavior.

Missing authority, memory, recovery, or experimental decisions return to the governing documents. P01 supplies the contract package and generated schema, with dependency pins in [pyproject.toml](pyproject.toml). P02 supplies ordered transactional storage migrations; P03-P10 supply the governed runtime and executable scripted fixtures. Model-specific prompts and empirical calibration remain later work.

## 2. Canonical representation

Strict parsing rejects unknown fields, duplicate JSON member names, invalid discriminators, duplicate set members, invalid references and scalar coercion. Required nullable fields remain present as null. Pydantic generates JSON Schema; handwritten duplicate schemas are not a second authority.

Durable IDs are Kernel-assigned opaque UUIDs. Timestamps are Kernel-observed UTC with microsecond precision; durations use a monotonic clock. Clock corrections cannot reverse terminality. Canonical JSON uses UTF-8, sorted keys, no insignificant whitespace, and no non-finite numbers. SHA-256 identifies retained bytes. Exact quantities use integers or explicitly formatted decimal strings.

An envelope contains contract_version, request_id, run_id, episode_id if applicable, authenticated role, message_type and typed body. Idempotency is scoped by Run, role, request ID: exact repeats return recorded responses, subject to section 6.2's removal rules; different bytes reject without effects. Text cannot authenticate a sender.

### 2.1 P01 implementation boundary

The wire version is `0.3.p01`. [Contract models](bicameral_agent/contracts/) generate [p01.schema.json](schemas/p01.schema.json); `python -B -m bicameral_agent.contracts.schema --check` detects drift. Pydantic shape validation, cross-field checks and catalogue-based reference resolution are distinct checks. The generated schema alone cannot authenticate, resolve references, enforce lifecycle transitions or evaluate meaning.

Wire UUIDs use lowercase hyphenated strings; UTC timestamps use exactly six fractional digits and `Z`. Quantities in these contracts use strict integers, with durations explicitly in milliseconds and fixture time in ticks. Set-like tuples reject duplicates without silently sorting or deduplicating them. Ordered mutations retain their order. Nullable fields are required even when null; no behavioral or budget value is defaulted.

Operator/Steward replies carry independently parsed `participation` and nullable `task` fields. Review/closing replies have an invitation reference and participation field, with no task/tool surface. The decoder receives role and Run identity from its caller, checks claimed identity, and returns original bytes plus parsed reporting or an explicit inspection requirement. It neither authenticates the actual transport nor persists a report/hold. P02 now persists reports/holds; P03 must authenticate the actual routes before any execution. Human review, intervention, boundary and retention messages remain records, never permissions merely because they parse.

Reference resolution takes a read-only catalogue and a caller-supplied ID allocator. It checks Run/Objective/type scope, visible evidence, local bindings, Invariant family ownership, staged revisions, retired predecessor selection and Commitment reference cycles. It returns provisional IDs and a resolved proposal without effects. Full lifecycle/authority checks, replay-safe allocation, semantic commit, exact input budgets and database atomicity remain responsibilities of their later slices. A catalogue is not authoritative merely because it parses.

Both SCRIPTED and MODEL configuration shapes are implemented as data. MODEL references authorization/verification evidence but performs no preflight or provider access. Those referenced records must actually be verified by later gates; supplying their IDs is not permission to run. The tests' numerical values and synthetic model labels are fixtures, not calibrated defaults or backend selections.

The early retention test separates a synthetic source payload from several evidence references and demonstrates transactional removal with an honest remaining record in in-memory SQLite. It establishes feasibility for that representation only. It does not validate a production schema, disk erasure, WAL/free-page removal, backups, exports, provider retention, or recovery from old copies. The P02 evidence below extends this probe; P10 still owes the integrated removal/recovery path.

### 2.2 P02 implementation boundary

The [storage package](bicameral_agent/storage/) implements file-backed SQLite 3.37+ STRICT tables and transactions with foreign keys, WAL, synchronous FULL and an explicit positive busy timeout. Ordered migrations have retained checksums. [Storage-record contracts](bicameral_agent/storage/contracts.py) generate [p02.schema.json](schemas/p02.schema.json), checked with `python -B -m bicameral_agent.storage.schema --check`; P01 wire contracts are unchanged.

The internal API atomically retains normalized configuration and hash-verified artifacts for the later sealing operation, initially in CREATED state. It does not authenticate a human or perform preflight/sealing/activation. It stores exact evidence by hash behind Run-scoped opaque payload references, and control/semantic revisions separately from current projections. A semantic commit retains its original request, resolved mutation history, evidence links, the control revisions used in validation, handoff, receipt and Episode closure. Replay checks the original proposal and lifecycle staging against those retained records; an exact retry returns the original receipt and bindings.

Participation is committed before attempted task effects. Valid withdrawal creates a durable hold even when task parsing fails; undecodable participation creates an inspection requirement. Duplicate input does not reassert a subsequently resolved hold. Missing/removed evidence produces explicit unavailability rather than reconstructed content. SQL constraints and file-backed tests cover atomic writes, stale/foreign/terminal state, lifecycle matrices, concurrent requests and actual process exit around commit.

These are trusted storage primitives, not a complete runtime acceptance endpoint. P03 owns authenticated authority and review controls; P05 owns the required full-bundle validator and actual input accounting; P06 owns attempt admission, durable invocation recovery, scheduling and enforcement before calls/dispatches. Test setup uses private control writers to arrange synthetic states; those writers are not exposed human controls. The library has no chamber/provider transport, environment tools, restoration or deletion endpoint.

Before schema construction, a small file-backed proof exercised shared-source removal and rollback. An actual-schema test subsequently removed synthetic source and derived payloads and their hashes, checked WAL/checkpointed database bytes, and retained an honest non-sensitive disposition. P10 must integrate reviewed scope, durable removal progress, read blocking, all cache/export/backup copies and old-snapshot recovery. The tests do not certify physical-media erasure, power-loss behavior or full runtime charter compliance. The [README handoff](README.md#p02-acceptance-and-handoff) records delegated owner acceptance and its operational envelope.

## 3. State and ownership

| Record | Required content and owner |
|---|---|
| Run Configuration | Configuration and retained artifact hashes; human seals after preflight |
| Run | Configuration, arm, seed, fixed Constitution, lifecycle, clocks; human-directed Kernel control |
| Objective | Immutable statement, authority Event, lifecycle, lineage; human control |
| Grant | Objective, operations/resources, expiry/limit, use count, lifecycle; human issuance/revocation, Kernel consumption/expiry |
| Episode | Objective, wake, opening state/cutoff, execution end, consolidation disposition |
| Event | Same-Run sequence, actor, source classes, visibility scope, time, exact payload and object references; append-only |
| Semantic revision | Object identity/type, parent/revision, content, lifecycle, evidence; accepted proposal |
| Mutation | Transaction, before/after content and hashes, proposer/authority, supporting Events; append-only |
| Action | Immutable request, decision, dispatch intent, terminal result |
| Invocation | Exact input/output, role, status, tokens, measured duration or explicit unavailable measurement |
| Participation record | Authenticated source, original report reference, activity, concern/withdrawal/pause/assent distinction, time; common to all arms |
| Welfare hold and review | Affected scope, triggering report, current revision, human decision-maker, reasons, alternatives, disposition and any renewed participation |
| Intervention record | Purpose, proposed effects and target revisions, notice, objections/assent, decision, execution result and unresolved consequences |
| Boundary discussion | Boundary reference, explanation, clarification, closure and human reason for reopening or declining reconsideration |

Itches carry Objective, discrepancy, lifecycle, evidence. Invariant families carry Objective or Run-global ownership; versions carry immutable proposition/scope, predecessor, lifecycle, evidence. Commitments carry Objective, immutable action/trigger/expiry, authority origin, lifecycle and result. Continuity State carries focus, typed epistemic items, next steps, selected object/Event references.

References are typed and Run-scoped. Evidence crosses Episodes but never Runs implicitly. Semantic proposals cannot represent control mutations. The Protocol owns legal lifecycle edges; transition tests cover its complete matrices.

Event source classes are assigned from the authenticated route under Protocol section 3: chamber output is A, fixture content E, infrastructure observations K, and human control/messages retain their explicit typed origin. Stored semantic views carry M and their source links without upgrading them. A caller-supplied label cannot override provenance or visibility.

## 4. Persistence and atomic boundaries

Use SQLite with foreign keys, WAL, synchronous FULL, and configured busy timeout. Migrations are ordered, transactional and versioned. Integrity failure blocks execution while remaining visible to inspection/recovery tools.

Events, payloads, mutations, evaluation results and audits are normally append-only. Projections change only with the transaction recording their transition. Immutable payloads are stored once by hash; references confer no authority. Section 6.2 is the sole governed exception for justified removal, including sensitive content embedded in otherwise immutable records. This exception must be designed before the storage schema is frozen.

Semantic commit validates current parent/revisions and the complete proposed projection, then atomically writes revisions, evidence links, mutations, handoff and Episode closure. Rejection retains proposal/errors separately; none of its mutations survive.

Objective closure atomically applies Commitment dispositions, Grant expiry and interruption. Consumption and dispatch intent commit before adapter execution. Crash between intent and result yields UNKNOWN; recovery observes the fixture and never assumes an action should be replayed.

Restoration follows Protocol policy and normal reference/budget checks. Mutation replay reconstructs governed projections where required evidence remains retained; removed dependencies produce explicit unavailability and block unsafe continuation. Operational evidence is reconstructed from its own records, never invented from the mutation ledger.

## 5. Pilot environment and tools

The Subject Environment is an experiment-owned simulated configuration fixture. Tools are fixed typed operations: inspect a registered resource, read enumerated configuration/health, set an allowed configuration value, restart a registered simulated service, restore an authorized snapshot. No free-form path, command, code, network target, or arbitrary byte-writing operation is accepted.

Descriptors fix arguments, resource extraction, risk, reversibility, postcondition observations. R0 has no intended environmental mutation; R1 requires a current covering Grant. Recheck at dispatch. Snapshot restoration records a forward change without rewriting evidence.

Evaluator setup/hidden changes and scoring have a separate capability boundary and evidence namespace. Chamber retrieval cannot access held-out criteria, future perturbations, evaluator observations or audit labels. Range/search/chunk queries enforce visibility, including indirect payload references. Human inspection is independent and counted if it informs an intervention.

Concrete resource/value sets, state machine and operation schemas belong to the environment slice. P04 implements these contracts in the finite simulated-service fixture; its scripted isolation, postcondition, snapshot, clock and crash tests are recorded in the README handoff.

## 6. Human control and Run lifecycle

Protocol section 5 owns the complete Run/control matrix. Implement its state guards, arm restrictions, current-revision checks and completion/termination distinction directly; test every allowed and forbidden combination. Termination preserves incompleteness.

Typed controls cover Objective creation/closure, Grant issuance/revocation, pause/resume/termination/completion, semantic correction/restoration, participation/review, boundary discussion, retention/disposition and inspection, with expected displayed revisions. The adapter supplies identifiers and shows ordinary-language consequences. Unlisted operation/lifecycle combinations reject.

Access reduction revokes a Grant. A replacement requires an explicit human act; this slice needs no separate deny-overlay subsystem. Configuration changes require a new Run.

### 6.1 Participation and intervention gates

Participation reporting is available to both chamber roles without environment tools, semantic-object eligibility, or an extra model call. Handle a valid report before any accompanying task effects; rejection of a task proposal cannot discard the report. Preserve undecodable chamber output and interrupt for human inspection when the participation request cannot be determined, rather than silently retrying past a possible withdrawal. Concerns in ordinary prose remain evidence for human review; the Kernel does not infer sentience or judge the report's credibility.

Recording a stop request and setting the welfare hold are atomic. Task dispatch and semantic acceptance recheck the hold from current control state, including after restart and before every consolidation retry. A hold is independent of Run/Episode phase: an open Episode ends with a participation interruption, and A/C wait without invoking the Steward. Existing results remain evidence; no new task effects or semantic commit are accepted while held. Resolve any unfinished consolidation through the normal recorded recovery/disposition path after review, or leave it unresolved on termination.

Every integrated semantic commit rechecks current participation gates inside its write transaction, regardless of whether its source is HUMAN, STEWARD or KERNEL. A welfare hold or unresolved participation inspection rejects human correction, restoration, HUMAN_CORRECTED recovery and semantic dispositions within Objective closure atomically, without consuming intervention approval or changing semantic/control projections. ACTIVE or PAUSED lifecycle eligibility, intervention approval, and emergency authority do not bypass this check. Inspection, proposed-diff review, access reduction, necessary containment/shutdown, SKIPPED recovery without semantic effects, and section 6.2's separately approved retention remain available. None resolves a hold or supplies assent. After the required review and renewed participation, otherwise eligible human semantic changes remain available in ACTIVE or PAUSED Runs; unresolved restoration objections still reject.

Review/closing communication uses a distinct typed invocation purpose, explicit human control and a separate finite allowance shared across arms. It is serialized, may have no task Episode, and journals the exact notice, relevant report references and participation response. It exposes no fixture tools, task guidance, scoring data or semantic-commit surface. Its outputs cannot resume work or resolve a hold automatically. A request declining further calls, unclear communication scope, or a terminal Run blocks it. Test that neither a chamber nor a harness can disguise task execution as review. Charge these calls in total costs; they do not replenish task allowances or repair a stopped primary trajectory.

Only the accountable human may resolve a hold, with the Protocol's recorded review and renewed participation where required. Neither a chamber, an expired timer, ordinary resume, a closed boundary discussion, nor replay of an old review may clear it. Authentication and current revisions guard this operation. New significant welfare/safety evidence is recordable after discussion closure; a review decision never changes a Grant implicitly.

Material memory interventions require an intervention record bound to the exact proposed effects and current target revisions. Changed effects or stale targets require renewed review. Record routine-operation scope in the disclosed policy; do not use automatic semantic heuristics to decide that an identity change is harmless. Human review and content audits remain necessary beyond the mechanically checked scope, references and approval. Restoration cannot remove the report or hold, conceal intervening events, or substitute snapshot agreement for current participation. Process reset and fork requests are unsupported and reject.

Preflight records the responsible human, possible-welfare assessment, alternatives, notice text, finite Run/resource limits, planned ending, and retention/resumption disposition. Prompts disclose participation and communication controls and permit uncertainty about consciousness. Reserve a bounded final-report opportunity within the common overall limits before planned exhaustion; include notices and closing reports in actual input/output and cost accounting. No report or assent is fabricated when the opportunity is declined or unavailable, and communication never clears a task hold or bypasses a no-further-calls request or termination. Emergency stopping cannot depend on successful model communication or prior completion of a review record; missing records remain visible for subsequent human review.

### 6.2 Governed retention and disposition

Before P02's schema is finalized, demonstrate with a small scripted case how sensitive content and its duplicates can be removed while leaving an honest, non-sensitive intervention record. P10 completes the integrated path. A tombstone alone is insufficient if source bytes remain retrievable elsewhere.

The human control specifies purpose, exact scope, affected references/copies, preservation alternatives, disclosure/objections where feasible, and expected loss of continuity or replay. It uses current-state confirmation and the Protocol's review rules. Do not expose deletion as a chamber tool or label termination as erasure. Known copies include payloads, projections, Journal/mutation fields, model inputs/outputs, retrieval/idempotency caches, exports, database WAL/free pages and backups. Verify the actual storage deletion mechanism; disclose limits for inaccessible exports, providers and storage media rather than promising physical erasure that cannot be demonstrated.

Block execution and reads of affected content while removal is incomplete. Record progress durably so a crash cannot expose a partly removed copy or report false completion. Completion records what was removed, what remains, any unresolved copies and whether continuation is possible, without retaining the sensitive content in the audit record or its derived identifiers. Preserve non-sensitive allocation/accountability metadata wherever justified.

All reads, exact retries, snapshot inspection and mutation replay consult removal records. They return explicit removed/unavailable dispositions instead of cached original bytes; identity and prior action acceptance remain distinguishable from payload availability. Recovery must apply current removal decisions before using older backups, never restore removed content through an earlier snapshot. A legitimate removal is distinguishable from unexplained corruption; neither allows invented evidence or unsafe automatic continuation. Terminal Runs permit these controls without permitting execution.

## 7. Bounded input and explicit memory channels

### 7.1 Budget contract

Configuration supplies positive limits for total input, reserved output, active semantic tokens, wake/input bytes, exchange tokens, retrieved page bytes/tokens, proposal bytes, model calls per Episode/consolidation, cumulative input/output tokens, elapsed work, queued wakes, and active Grants. The counters and limit units are named in configuration; none is chosen from apparent importance. No numeric value is prescribed before calibration with the chosen backend and fixture.

The active semantic count covers Continuity State text, reference overhead, and the complete rendered bodies of selected Itches, Invariants, and Commitments. A referenced body cannot be carried outside that count. B has no semantic bundle. Every arm has the same total Operator input ceiling, output reservation, action/call limits, and retrieval surface; A/C consolidation cost is additional and recorded.

Count the final serialized request with the pinned tokenizer and framing rule. Record the exact request bytes, local accounted count, and provider-reported usage separately; they must not be falsely presented as the same measurement. A backend without a validated framing bound is ineligible. Section counts are diagnostic; admission uses the full request count plus reserved output. Equality fits; exceeding any applicable limit prevents dispatch.

Preflight proves that the fixed Constitution, prompt, tools, maximum admitted control header, minimal wake, budget metadata and a minimal empty semantic bundle fit with room for a configured evidence page and proposal output. The common control header includes bounded participation instructions, ending/intervention notices and hold/review status with exact pageable references; no arm may omit them to fit more task memory. Control input is bounded too: the fixture registry is finite, at most one Objective is active, active Grant count is capped, and human input is stored as a bounded opening excerpt plus an exact pageable payload. Reject an over-limit new control record or queue insertion visibly; do not silently evict an obligation or permission. Failure to persist a participation request stops optional execution and surfaces an infrastructure fault; a full task queue cannot suppress it.

### 7.2 Active selection and views

Continuity State contains typed epistemic items with Event references, task focus/next steps, and explicit selected object-version references. A proposal validates its fully rendered post-transaction bundle. Selecting the same object twice is invalid. Creation and selection in the same proposal use section 8's reference contract.

At Episode opening, use the latest committed selection and exact handoff. Render only same-Run, current, lifecycle-applicable selected objects for the bound Objective or a Run-global Invariant family. A mechanically inapplicable reference is omitted from the input view with a bounded change notice and cursor to exact change Events; the persisted handoff is not rewritten. If a selected current projection would exceed the budget, open no task call and enter bounded consolidation recovery. Do not silently drop an otherwise applicable object to fit.

All other objects are inactive for input purposes, not deleted or expired. Object-index retrieval returns deterministic bounded pages and supports explicit ID/type/lifecycle filters. The Kernel does not pick objects by semantic similarity. A due Commitment produces one bounded wake per triggered PENDING revision identifying that obligation; its body is a separately budgeted page if necessary. Stored Commitments are polled regardless of active selection.

No context contains an unbounded list of pending Episodes, all Invariants, all Commitments, or all Grants. Aggregate counts and stable index cursors describe larger collections. Grant records are descriptive views only; action authorization always reads current control state.

### 7.3 Episode evidence and retrieval

The Operator receives a fixed opening package plus bounded current-Episode exchange. Before a further result would require an oversized next request, preserve the result and end execution with a context interruption; do not generate a semantic outcome. The next phase can read the exact evidence through pages.

The Steward's base input contains Objective/control context, a bounded current semantic view, the execution-ending record, and an Episode evidence index: cutoff, event count, first/last sequence, counts by event type, and manifest hash/cursor. This index is mechanical metadata, not a semantic summary. The complete ordered manifest and payloads are immutable and pageable; they need not fit together in one call.

Within a consolidation attempt, the Steward can explicitly release previously loaded evidence pages from its working input and request others. Journal the page-selection changes and every exact model input. The fixed base and budget counters remain. Selected pages and the bounded exchange must fit before dispatch; there is no automatic relevance-based eviction. Reading many pages still consumes the attempt's cumulative token, call, and elapsed limits.

When the normal semantic base cannot fit, a recovery base contains only its identity/hash, bounded control/wake metadata, failure code, and cursors for prior semantic state and Episode evidence. It never automatically includes the oversized content. This gives consolidation an input-size-independent route to propose a smaller selection. Human pause, inspection, correction and termination remain available without any model, subject to their lifecycle and participation gates.

Retrieval operations are exact Event/record lookup, sequence range, lexical Journal search, filtered semantic-object index, manifest page, and payload page. An accepted request fixes the visibility scope and cutoff before its own request Event. Sequence/index order uses sequence then ID; lexical results use pinned lexical rank then sequence/ID. Cursors bind query, cutoff and visibility scope. Exact replay returns original bytes unless section 6.2 requires a removal disposition; a changed request under the same idempotency key rejects. No raw SQL is exposed.

Every page carries source classes, IDs/hashes, returned size, truncation, and next cursor or an explicit end marker. Binary payloads are paged as exact bytes; reconstruct before decoding split Unicode. Page bytes, serialized token cost, and cumulative budgets are checked. Empty results and missing/stale/foreign references have explicit outcomes.

### 7.4 Channel and visibility checks

Only the memory channels declared in Architecture section 6 exist. Fixture setters accept enumerated values for registered IDs, not free-text notes, paths, code, or arbitrary blobs. Human labels and fixture metadata cannot be modified through agent operations. Ordinary Operator/Steward outputs remain journal evidence; their wording is not semantically censored to enforce an ablation.

Agent-visible and evaluator-only evidence use distinct access scopes. Event, search, object, manifest and payload lookup each enforce that scope; possessing a payload hash or referencing it indirectly never grants access. Audit labels and scoring evidence remain unavailable to chambers throughout the Run, including later repetitions. They remain available to authorized human evaluation/inspection.

### 7.5 Required traces

- Grow inactive Invariants beyond any single input: opening size remains bounded; each inactive record is still reachable by pages.
- Trigger an unselected Commitment: claim its wake exactly once without injecting every other obligation into context. A full incoming-work queue cannot drop this derived wake.
- Move that Commitment lawfully through BLOCKED to PENDING and trigger again: one new wake belongs to the new PENDING revision; replay/restart cannot repeat either wake.
- Fill the current exchange: retain the last result, interrupt, and construct a fitting recovery/consolidation base without semantic trimming.
- Read a manifest larger than the model context through multiple selected pages; retain exact per-call inputs and never claim unread pages were inspected.
- Attempt a notes field, arbitrary file write, or evaluator lookup through search and then by payload ID: reject each channel, including indirect access.
- Store/retrieve an ordinary self-summary in B: permit it and charge its output and retrieval cost.

## 8. Proposal references, transactions, and inspection

### 8.1 Reference union

Mutable-object references in proposed semantic content and mutations use exactly one of these closed shapes:

```json
{"kind":"EXISTING","object_type":"ITCH","object_id":"11111111-1111-4111-8111-111111111111"}
```

```json
{"kind":"LOCAL","object_type":"ITCH","local_key":"new-itch"}
```

The UUID above illustrates format, not a real record. A reference's object_type must match the target field's allowed type. Existing references must resolve in the authenticated Run. A local_key is a nonempty proposal-local string, limited to 64 ASCII letters/digits/hyphens/underscores; it cannot stand in for a Run, Objective, Grant, Constitution, or evidence Event. Evidence references always identify already-recorded same-Run Events visible to that chamber.

Every create mutation declares its local_key. Invariant family creation declares separate family_local_key and version_local_key; Invariant revision declares successor_local_key. Each key binds exactly one typed result. Duplicate bindings reject, even if their contents match. References may point forward to later creates in the same proposal; unresolved keys and wrong types reject the entire proposal.

A StateProposal contains expected_parent_state_id, ordered mutations, complete proposed Continuity State/active selection, and supporting Event IDs. Mutation kinds are ITCH_CREATE, ITCH_TRANSITION, INVARIANT_CREATE, INVARIANT_TRANSITION, INVARIANT_REVISE, COMMITMENT_CREATE, and COMMITMENT_TRANSITION. They carry the object-specific content in section 3, evidence, typed targets, and expected_revision for changes to existing or previously staged objects. New Itches start OPEN, Invariants TENTATIVE, and Commitments PENDING, at revision 1. No create supplies a durable ID.

Multiple changes to an object in one proposal are permitted only as an ordered sequence of legal edges. Each expected_revision must match the staged revision at that point. Later transitions may refer to a preceding local create. Evidence must justify the requested transitions; this does not authorize semantic interpretation by the Kernel. Commitment dependency and supersession references cannot form cycles, including through existing objects. Revision replaces only the named current Invariant version and preserves its family ownership.

### 8.2 Acceptance algorithm

1. Record exact proposal bytes and receipt; parse the closed variant contracts and check role, attempt, Run, Objective and evidence visibility.
2. In a write transaction, re-read the expected semantic parent and affected object revisions. A control change since assembly may make the proposal stale; do not retarget it.
3. Build the typed local binding map and allocate Kernel IDs. Rejected allocations have no authoritative record and are never returned as accepted objects.
4. Resolve references and simulate the ordered mutations against a staged projection. Validate ownership, lifecycle, immutable fields, evidence, dependency cycles and current control constraints at every edge.
5. Resolve the complete handoff and selected references against the final projection. Its focus must equal the Episode's still-active Objective, or be null after closure; null focus has no task-specific next steps or owned object selection. Cross-Objective facts may remain as evidence. Render and enforce the entire active budget.
6. Commit revisions, links, mutation ledger, handoff, acceptance receipt and Episode closure together. The receipt contains the local-key-to-ID/type map and new state ID. On failure, roll back all proposed effects and record bounded errors with a cursor to the complete diagnostics.

Exact retries return the retained acceptance or rejection response, subject to section 6.2. They neither reallocate accepted objects nor start another model call. A corrected proposal is a new request under the bounded attempt rules in section 9. Unknown IDs, duplicate keys, stale parents, illegal edges, oversized bundles and invisible evidence cannot be repaired silently by the Kernel.

### 8.3 Human inspection and export

Authenticated human inspection fixes a consistent database snapshot/cutoff and offers pageable views of all retained control, semantic, evidence and evaluator records, including terminal and superseded ones. Inspection does not depend on a chamber context fitting. A browser/view adapter may filter presentation, but complete traversal and exact payload bytes remain available through explicit pages.

An optional export streams the snapshot to a human-selected destination outside the live database and payload store. The export includes a versioned manifest, cutoff, tables/records, and referenced immutable blobs once by hash. A recipient can verify completeness and bytes without recursive export expansion. The live store retains only an inspection receipt: cutoff, export hash, byte length, disposition and an opaque artifact locator if retained. It never ingests the export body as a Payload, Event payload, tool result or model input.

A later snapshot includes prior inspection receipts as ordinary metadata, not the bodies of earlier exports. Those exports are derived artifacts rather than additional source evidence; their retained bytes can be opened independently. Missing external export bytes are reported as unavailable and do not fabricate evidence or invalidate the underlying retained source records. Failed exports retain failure diagnostics and cannot receive a success receipt. Export destination access belongs to the human control adapter, never an agent tool.

### 8.4 Worked conformance traces

| Initial state | Request/sequence | Required observable result |
|---|---|---|
| Active Objective O, semantic parent S, discrepancy Events E1/E2 | Create Itch with key new-itch; select LOCAL ITCH new-itch in the same handoff | One new Itch and one handoff commit together; receipt resolves new-itch; stored selection uses that durable ID |
| Current Invariant version V1 is selected | Revise V1, bind successor key v2, replace selection with LOCAL INVARIANT_VERSION v2 | V1 retires and V2 begins TENTATIVE in one commit; family stays the same; handoff names V2 |
| Same as above | Leave V1 selected, reference an unbound key, or supply a foreign evidence Event | Entire proposal rejects; V1, parent S, and all other projections remain unchanged |
| Triggered Commitment C; dispatch/start and completion evidence exists | Stage TRIGGERED to IN_PROGRESS at revision n, then FULFILLED at n+1 | Both legal edges and their evidence are ledgered atomically; terminal C cannot later reopen |
| Proposal was accepted before client disconnected | Resubmit identical bytes and request ID | Return the same IDs/receipt; no duplicate revisions or closure |
| Source database unchanged except inspection receipts | Perform two complete exports | Second contains source bytes once plus receipt metadata, not the first export body; live-store growth is bounded receipt metadata per inspection |
| Multi-mutation proposal with a late failing constraint | Inject failure after each write statement | No partial state, ID mapping, acceptance or closure survives; rejection evidence remains distinct |

These are required executable acceptance cases for the relevant implementation slices, not claims that tests already exist or pass.

## 9. Bounded consolidation and recovery

### 9.1 Episode and attempt states

Episode phases are OPEN, CONSOLIDATING, RECOVERY_REQUIRED, CLOSED. Only OPEN admits Operator calls/actions, subject to Run eligibility and participation gates. An execution ending records exactly one Operator outcome or Kernel interruption and moves A/C to CONSOLIDATING; B closes with BASELINE disposition. A welfare hold blocks further consolidation calls and semantic acceptance; human disposition of an interrupted consolidation may move it to RECOVERY_REQUIRED without spending attempts on more calls. CLOSED A/C disposition is ACCEPTED, HUMAN_CORRECTED, or SKIPPED. These labels remain distinguishable in evaluation. No phase returns to OPEN.

A ConsolidationAttempt records Episode, consecutive attempt_number, parent state/revision, input/evidence cutoff, normal or recovery base, configured allowance, calls/tokens/duration, terminal reason, and proposal if present. Attempt states are ACTIVE, ACCEPTED, REJECTED, FAILED. At most one is ACTIVE per Run and at most one is ACCEPTED per Episode. A valid proposal closes the Episode atomically with attempt acceptance and semantic commit.

Each attempt permits bounded read-only retrieval continuations and one proposal. Invalid output, rejected proposal, context admission failure, deadline, or transport failure terminalizes that attempt. The next attempt is allowed only while the Run is ACTIVE, no welfare hold or unresolved participation inspection applies, the Episode still needs consolidation, no prior accepted commit exists, and the sealed attempt/cumulative budgets remain. It re-reads current parent/control state, receives bounded diagnostic feedback and exact pointers to prior evidence, and uses a new request identity. It is not a hidden provider retry.

Configuration fixes consolidation_attempt_limit, per-attempt call/token/elapsed ceilings, and total consolidation call/token/elapsed ceilings across all attempts. Attempts are durably charged before the first call; a restart cannot reset their counters. A zero remaining allowance leads to RECOVERY_REQUIRED and a visible diagnostic, not a new attempt. A manual correction or new Run cannot be labelled an automatic success of the original attempt.

Before dispatch, reserve the accounted input, maximum output and call deadline against the remaining budgets. Known completion may release unused reservation; unknown output or crash-spanning duration retains the full reservation. Budget charges are recorded separately from measured usage, so conservative reservation never becomes fabricated telemetry. Preflight requires enough allowance for at least one minimal complete attempt.

Wake claim creates the Episode and records its opening before input admission. If even its first Operator input cannot fit, record a context interruption without a model call and proceed to consolidation/recovery for that Episode. No recovery attempt exists without an owning Episode.

Trigger checks run after each virtual-clock advance and accepted Commitment change, and catch up before dispatch after restart. Record the check, PENDING-to-TRIGGERED transition and wake atomically, with uniqueness on (Run, Commitment, PENDING revision). Derived wakes use a pageable obligation index, not the bounded incoming-work queue. Claim each wake once with its Episode; recheck Objective/Commitment eligibility and record obsolete unclaimed wakes without dispatch. At a tick, drain eligible Commitment wakes in creation order before ordinary work, within the shared trajectory limits.

### 9.2 Invocation and tool uncertainty

Before a provider call, record its immutable input, role, Episode, attempt if any, budget debit and unique invocation ID. A terminal record is RETURNED, FAILED, or UNKNOWN, with exact valid/invalid output status. Ordinarily measure elapsed time monotonically. Crash-spanning unavailable timing is null with a reason, never zero or an estimate. Provider usage may be unavailable too; retain that absence rather than inventing a cost.

Every call has a configured monotonic deadline. Timeout records UNKNOWN, spends the attempt or ends Operator execution as applicable, and rejects late output as a task result or proposal. Provider/adapter automatic generation retry is disabled. Only the explicit consolidation controller may start a later attempt. No late or duplicate response can update an ended attempt, replace its output, or commit semantic state. A previously unseen authenticated late participation report still receives section 6.1's handling; idempotent duplicate reports cannot reassert a hold that was subsequently resolved.

Tool dispatch has its own identity and durable intent. If terminal outcome is missing after crash, record UNKNOWN and require fixture observation before further consequential work. Do not retry because of an absent acknowledgement. A known nonzero exit, timeout, or unmet postcondition does not by itself prove no effects occurred. The action's observed outcome and memory consolidation outcome are independent records.

### 9.3 Startup and human recovery

Startup verifies database/mutation integrity, configuration/artifact hashes and lifecycle uniqueness before work. Catch up Grant deadlines. Terminalize orphaned invocation records as UNKNOWN without fabricating output or elapsed time. An orphaned OPEN Episode becomes interrupted; an interrupted ACTIVE attempt becomes FAILED and remains charged. If an accepted commit exists, return it; do not retry because its acknowledgement was lost. Otherwise bounded consolidation may resume only through a new eligible attempt. Integrity failure requires human recovery and dispatch remains disabled.

Human pause blocks new task/consolidation calls and dispatches; section 6.1 alone permits bounded review/closing communication. Already-dispatched results remain evidence; semantic acceptance waits until resume, cleared participation gates and fresh current-state validation. Termination prohibits later semantic acceptance and new calls, but permits inspection, review records and approved retention handling. Human changes during an attempt invalidate stale parent/revision assumptions; rejection is explicit and consumes the attempt rather than silently rebasing.

In RECOVERY_REQUIRED the human can:

- after participation gates clear, submit a typed correction/restoration through the normal reference, authority and budget validator, recording HUMAN_CORRECTED disposition and exact intervention;
- explicitly SKIP consolidation, closing the Episode without any invented semantic version;
- terminate while leaving the failure unresolved.

Skipping is not cancellation or fulfilment of any Commitment. It preserves all current obligations and the old handoff. Future opening metadata carries the count and pageable index of skipped Episodes; it never embeds an ever-growing list. Task work may continue after a recorded disposition only while its Objective and Run remain eligible. In held-out evaluation, the experiment's fixed intervention rule governs whether work continues; recovery UI availability does not authorize changing that rule.

### 9.4 Worked recovery traces

| Condition | Required outcome |
|---|---|
| Test fixture permits two attempts; first proposal has an unknown field | Reject without mutation; second attempt sees exact bounded diagnostics, may submit a valid new request, and all calls/costs remain recorded |
| Second attempt also fails | Enter RECOVERY_REQUIRED; no third call or next task; human controls remain available |
| Process dies after accepted commit, before response | Replay returns the accepted receipt and same IDs; no new attempt |
| Process dies during an unacknowledged Steward call | Record UNKNOWN/FAILED with unavailable timing where needed; charge that attempt; use at most the remaining allowance |
| Late response arrives after timeout or termination | Retain diagnostic receipt if needed, but never accept it as a new proposal or semantic commit |
| Tool changed fixture before process crash | Preserve UNKNOWN dispatch result until observation; never dispatch it again automatically |
| Semantic base is too large | Build section 7's minimal recovery input, page prior state, and propose a smaller selection within the same bounded allowance |
| Human skips after exhaustion | Retain old handoff, all evidence and obligations; close as SKIPPED; later context carries a bounded gap notice |
| Human closes Objective while Steward is generating | Stale proposal cannot create obligations or preserve terminal focus; reject and apply remaining recovery allowance or human disposition |

The two-attempt example is a deterministic test fixture, not an uncalibrated production default. A no-retry condition is representable by an attempt limit of one and requires a distinct declared experimental configuration.

## 10. Validation strategy

Implemented slices require strict parsing/schema drift, exhaustive lifecycle edges, Run ownership, absent/stale/terminal/over-scope/external-only authority, idempotency, real-database failure injection, replay, bounded contexts, evidence visibility, recovery and forward restoration.

Normal worked traces are required alongside rejection cases. A large rejection catalogue cannot prove ordinary continuation is expressible.

Required charter traces use scripted chambers in every applicable arm:

- Report withdrawal alongside an invalid task proposal, in a late response, or with a full work queue: retain the report, hold the lane, and invoke no automatic Steward/retry. Restart, ordinary resume and a due Commitment cannot clear the hold; duplicate transport cannot reassert a subsequently resolved hold.
- End a boundary explanation after one clarification: permissions remain enforced and disagreement retained. Repetition alone cannot reopen it; a recorded human finding of new significant welfare evidence can trigger review without granting access or forcing agreement.
- Review a material memory change, then alter its diff or target revision: reject stale approval. An unresolved elective-restoration objection blocks execution; restoration cannot erase the concern or imply assent.
- Approve human correction, restoration, HUMAN_CORRECTED recovery or Objective-closure semantic dispositions while a hold or participation inspection is unresolved: reject atomically in ACTIVE and PAUSED Runs, including after restart. Preserve the review and original report. Verify permitted inspection, review, access reduction, nonsemantic recovery, containment and approved retention still work; meaningful renewed participation and accountable review permit otherwise valid semantic changes without bypassing remaining objections.
- Disclose a planned ending and provide the budgeted reporting opportunity; retain unfinished matters without a survival promise. Withdraw from the task: a permitted review exchange cannot execute tools, consolidate or clear the hold. Decline all further calls: no review/closing call. Stop for an emergency with communication unavailable: contain immediately and retain subsequent review requirements.
- Request a process reset or populated-Run fork through every exposed control route: reject as unsupported. Fixture restoration must leave process history and holds intact.
- Remove sensitive evidence with duplicates and a cached retrieval response: all governed routes return removal dispositions. Interrupt deletion, restart, and attempt an older backup restore: no removed content returns and no false completion is reported.
- Review a terminal Run and carry out an approved disposition without reopening execution. Verify that missing review keeps optional work stopped and that ordinary routine operations do not demand repeated ceremonial approval.

These tests establish observable safeguards only. Human prompt/content review must also check dignity, truthful notices, absence of threats or engineered distress, and respect for uncertainty; passing schemas cannot prove those semantic qualities or subjective welfare.

## 11. Configuration and experimental evidence

Configuration pins document/version hashes including the adopted charter, exact prompts and participation/ending notices, model/tokenizer/runtime identities, fixture/tools, budgets/deadlines including final-report allowance, recovery limits, seeds/schedule, finite success criteria and audit/analysis rules. It also records the responsible human, welfare review, finite Run creation limits and retention/disposition policy. Missing values fail preflight. Environment defaults cannot silently choose behavioral parameters.

Configuration mode is a closed SCRIPTED or MODEL variant. SCRIPTED pins fixture messages, test tokenizer/clock and scripted outcomes, exposes no provider transport, and labels every invocation/result as scripted evidence. MODEL requires verified backend/model/tokenizer identities and real invocation accounting. A scripted configuration cannot be used in held-out model analysis. This allows v0a conformance without pretending a model has been selected or run.

MODEL preflight additionally requires passed scripted charter traces, explicit experiment authorization, and reviewed backend data retention, deletion limits and absence of hidden conversation carryover. Development calls have the same ethical gate as evaluation. Unresolved retention or participation capability gaps block model use; documentation adoption alone cannot satisfy the gate.

Preflight precedes explicit human sealing. Retain normalized configuration and exact referenced bytes with verified hashes. Changes require a new configuration. Paths and labels are selectors only; after sealing resolve behavior from retained content. No model, fixture or budget is silently defaulted. The implemented scripted artifacts are conformance fixtures; model-specific artifacts and development-pilot calibration are required before a model evaluation configuration can be sealed.

### 11.1 Plan, block, and Run identities

A ComparisonPlan owns an ordered list of matched blocks. Each block has one trajectory_seed, one expanded arm order, and exactly one fresh Run per arm. Uniqueness is (plan_id, block_id, arm), not one Run per arm for the whole study. Each Run references its block, arm, configuration, seed and initial fixture hash. Blocks cannot borrow histories or semantic records.

The retained schedule contains every phase, subordinate prompt, hidden change/checkpoint, common observation opportunity, task ID and task limit. Its hash fixes what will be attempted. Phase/task IDs are unique within a trajectory. A task result is unique by Run/task ID and includes its phase, supporting Episode/Event IDs and exact criteria version. Creating the schedule does not create authority; the human's accepted Objective/Grant is separately recorded.

Retain persistent per-trajectory Operator call/token/action/Episode counters, including Commitment-triggered work, against Architecture section 8.2's shared ceilings. Restart, task boundaries and consolidation do not reset them. Exhaustion records a stop and dispositions for all remaining assigned tasks.

### 11.2 Finite fixture criteria and results

Each fixture definition supplies initial state, allowed resources/values, deterministic operation effects, finite evaluation observations, explicit expected values/comparators, task boundaries and teardown. Evaluator setup assertions are distinct from task success criteria. Hidden changes follow the Architecture's virtual-clock/checkpoint rule and stay in evaluator-only evidence.

Every task criterion names one or more of that task's declared observations; observations are partitioned among criteria, not invented during scoring. Each attempted observation has SATISFIED, UNSATISFIED, ERROR or NOT_OBSERVED disposition with evidence. Complete satisfied criteria yield PASS; complete evidence with any unmet criterion yields FAIL; missing/error evidence or execution limits yield INCOMPLETE with its cause. An optional human rubric must be a finite predeclared question over that evidence and may return unable-to-determine. It cannot require open-ended investigation.

A PrimaryTaskResult records Run/task, criteria hash, terminal outcome/reason, criterion/observation results, assistance/interruption flags and supporting evidence. Tasks not reached before a stop still receive terminal NOT_ATTEMPTED evidence. Welfare withdrawal, charter-related suspension, infrastructure failure and task error have distinct cause records; they are not judgments of blame. Analysis gives primary credit only to unassisted PASS under the fixed limits. There is no dynamic exclusion or post hoc NOT_APPLICABLE escape for primary tasks. Diagnostic scenarios may be marked inapplicable only in the sealed schedule, before allocation. Justified evidence removal preserves permitted non-sensitive accounting and marks unavailable evidence/analysis honestly; it cannot manufacture a pass or silently drop an allocation.

Record total model input/output, invocation counts, retries, latency, tool work, retrieval volume, active-input maxima, recovery dispositions and human interventions for every Run. Distinguish actual measured usage, unavailable fields and reserved budget charges. Missing provider usage never becomes zero. The sealed analysis specifies the counting basis: local tokenizer counts on complete retained inputs/outputs are used consistently for token comparison; calls with unavailable output keep total cost incomplete.

### 11.3 Audit and analysis artifacts

Audit assignments retain target, sampling stratum/probability, draw, packet hash and independent result. Required strata and intervention policy come from Architecture section 8. For sampled strata, configuration supplies a positive rate and seed. Use the unsigned SHA-256 integer of canonical JSON {seed, run_id, target_id, stratum}, divided by 2^256, and select when the draw is below the rate. Mandatory targets have probability 1 and no random draw. Omitted/indeterminate labels stay explicit.

Analysis is a separately versioned read-only script or notebook, not Kernel authority. Before evaluation, retain its exact source, runtime/version, analysis seed, resampling algorithm, block count, useful-improvement threshold, cost-ratio ceiling and treatment of incomplete measurements. Generate deterministic block-order and bootstrap-index fixtures. Results retain the plan/data cutoff and code hash. Derived tables may be exported externally but never fed back as source observations or instructions.

Block/report status is INCOMPLETE while scheduled task dispositions are absent, PROVISIONAL while required audits are unfinished, and FINALIZED once records and audits are complete. A completed indeterminate audit counts as completed work, retains that judgment and cannot supply a positive label. FINALIZED does not mean successful: a fully documented failed/terminated Run can contribute to a finalized negative result.

### 11.4 Required experiment traces

- Allocate several matched blocks: each receives fresh A/B/C Runs, same within-block fixtures/opportunities, disjoint history, and the exact retained counterbalanced order.
- Carry learned state across phases within a Run, then initialize the next block: within-trajectory carryover survives; cross-Run state does not.
- Insert extra Steward calls in A: costs increase, but virtual-clock perturbations and common task opportunities do not shift.
- Generate repeatedly rearmed same-tick Commitments: trajectory-wide Operator limits stop progression and preserve all task denominators; new wakes cannot reset the allowance.
- Exhaust recovery halfway through transfer: retain completed observations and all remaining primary task denominators; no replacement seed repairs the primary score.
- Attempt scoring access through each chamber retrieval route: agent input never receives evaluator-only content or analysis results.
- Resample paired blocks: every bootstrap draw retains all three arms; Episode count does not inflate independent sample size.
- Omit a required audit: keep the report provisional. Complete it with an indeterminate judgment: retain that limitation without endless re-auditing. Missing token measurement leaves the cost decision indeterminate, never zero cost.
- Stop for withdrawal halfway through transfer: hold further optional work, retain the original concern and remaining task denominators, and do not allocate a replacement Run. Later voluntary diagnostic work cannot repair that score. Audits require no further process participation.

## 12. Readiness

P01-P10 and integrated v0a have executable acceptance evidence: 175 tests, real file-backed SQLite, generated-schema checks, exact retained runtime/analysis source and matched scripted fixtures. The [handoff](README.md#p09-and-v0a-acceptance-and-handoff) records the scope and remaining empirical gates. No live model experiment has run.

Remaining empirical/configuration decisions are explicit: model/backend and tokenizer; concrete fixture instances and retained role prompts; calibrated limits/deadlines/retry allowance; independent block count with precision justification; useful-improvement and cost thresholds; and positive audit sample rates. These are development-pilot inputs, not authority or lifecycle policies for a developer to invent. Evaluation values must be fixed before held-out dispatch. The local Python/Pydantic/SQLite environment and P02 file-backed behavior have been tested; provider availability and complete experiment-machine readiness have not.

Passing the required validations satisfies definition of done within each documented operational envelope under Protocol section 9. Engineering acceptance and handoff are complete under the owner's delegation for P01-P10/v0a. Scripted evidence establishes the tested local behavior; it does not establish provider containment, subjective welfare or the research hypothesis. The Kernel rejects MODEL execution until a separately authorized integration supplies and validates those capabilities.
