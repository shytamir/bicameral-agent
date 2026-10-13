# Pilot implementation roadmap

**Status:** planning baseline for the 0.3 design under the owner-adopted charter; no implementation slice is authorized by this document.

**Progress:** P01 is implemented and technically validated with synthetic, LLM-less tests. Its implementation was separately authorized by the owner; technical validation is not owner acceptance. P02-P10 and the v0a gate remain incomplete.

The [Reciprocal Charter](Reciprocal%20Charter.md), accepted and adopted by the owner on 2026-10-13, constrains every slice and experiment. Scope comes from the [Architecture](Experiment%20Architecture.md), operating policy from the [Protocol](Operating%20Constitution%20and%20Execution%20Protocol.md), and mechanical requirements from the [Executable Specification](Executable%20Specification.md). The slices below are capability boundaries, not duration estimates or commitments to build future platform features. Earlier inventories remain in Git history.

## 1. Scope and exclusions

The first implementation is LLM-less and exercises a typed simulated-service fixture. It supports one active Objective, serialized execution/consolidation, fixed policy, explicit memory conditions, bounded input, auditable recovery and normally immutable evidence with a separate justified-removal path. All arms receive effective participation controls and the same charter safeguards.

Excluded: actual provider calls, live experiments, process resets/forks, host/network/shell access, dynamic constitutional amendment, concurrent task lanes, generalized tool/trigger frameworks, vector retrieval, model routing, and elaborate UI. Simulated-service snapshots and forward semantic restoration are not permission to reset or clone a process. Do not add excluded features to make a slice appear complete.

Concrete schema choices must express the existing design rather than invent policy. If a worked trace cannot be represented, revise its governing decision before coding around it. Tests belong to the slice introducing the behavior.

## 2. Bounded slices

| ID | Capability delivered | Dependencies | Definition of done |
|---|---|---|---|
| P01 | Strict messages and proposal reference resolution | None | Implement pilot contracts, canonical bytes, SCRIPTED/MODEL variants, discriminated references and local bindings. Include participation, review, intervention, boundary-discussion and retention records from Specification section 6. Valid create/select/revise examples round-trip; unknown fields, duplicate keys, foreign targets and illegal reference types reject. Reports remain distinct from assent, task outcomes and permission. Generated schema drift is checked. |
| P02 | Evidence and atomic governed state | P01 | Real SQLite constraints, migrations, payload/artifact retention and semantic/control history. Before schema finalization, prove the small removal case in Specification section 6.2; do not make exact retention structurally unconditional. Sealing retains verified bytes atomically. Fault injection proves all-or-nothing proposals and report/hold recording; replay matches retained projections and exact retries preserve identities. P10 completes removal across derived copies. |
| P03 | Human authority, participation and intervention gates | P01, P02 | Run/Objective/Grant lifecycle, preflight, clear displays, current-state confirmation, pause/termination and dispatch authorization. Withdrawal holds the lane without granting access. Material interventions need current, scoped review; boundary closure cannot imply assent or dismiss new significant welfare evidence. Test all Protocol controls, emergency stopping without prior consultation, and subsequent review. Absent/stale/terminal/foreign/over-scope/external-only/prohibited authority rejects; reset/fork controls remain unavailable. |
| P04 | Typed fixture execution | P02, P03 | Retained finite service fixture, enumerated arguments/resources, deterministic operations, task clock, snapshots and postconditions. No arbitrary file/notes/code/host channel exists. Crash after dispatch preserves uncertainty without replay. |
| P05 | Bounded chamber inputs and retrieval | P01-P04 | Full-request/semantic budgets, selected views, pageable manifests, explicit page release, visibility and stable cursors. Every arm fits the common participation/notice view without a hidden learning channel. Large histories fit; unselected obligations reach the scheduler; evaluator content stays inaccessible. Removal dispositions override old cursors and cached responses when integrated with P10. |
| P06 | Serialized Episodes and bounded consolidation | P02-P05 | Durable wakes, trigger/expiry checks, scripted exchanges, bounded attempts, recovery and human dispositions. Withdrawal blocks task calls, mandatory consolidation, retries and semantic acceptance, including after restart or queue exhaustion. Test separate bounded review/closing communication with no task effects; no-further-calls requests block it too. Test planned endings and unexpected stopping. Normal/failure traces retain honest outcomes without duplicate commits or action replay. |
| P07 | Reviewed forward semantic restoration | P02, P03, P05, P06 | Restore earlier semantic content as a new version with explicit purpose, notice and current review. An unresolved elective-restoration objection blocks it. Retain authority, obligations, intervening evidence and participation state. Stale approvals, terminal resurrection, stale focus and invalid references reject; differences remain visible. No restoration obtains agreement by erasing an objection. |
| P08 | Human inspection and streamed export | P02, P03 | Pageable inspection, including original concerns and review/intervention records, and external exports with completeness verification. Repeated inspection adds receipts rather than recursive bodies. Track known export copies for disposition; distinguish removed evidence from unexplained loss or unavailable exports. Terminal inspection/review cannot restart execution. |
| P09 | Matched-trajectory evidence runner | P04-P08, P10 | Scripted A/B/C blocks with fresh independent Runs, within-Run carryover, fixed opportunities, finite scoring, costs/audits and read-only analysis. Seal finite Run counts and disposition, not cloned populated histories. Welfare stops retain separate causes and permitted denominator records without replacement Runs; removed evidence yields explicit analytical limits. Pairing/counterbalance are reproducible; audits require no further process participation. |
| P10 | Governed retention and state disposition | P02, P03, P05, P08 | Implement Specification section 6.2 using synthetic sensitive data. Review purpose/scope and notice; remove governed source/derived copies while retaining a non-sensitive intervention record. Test interrupted removal, caches, exports, WAL/backups and recovery from an older snapshot. No deleted content reappears through replay or exact retries. Distinguish stopped computation, dormant state, terminal Run and deleted state; disclose unverifiable copies or erasure limits rather than report false completion. |

Each slice needs a scoped implementation request and reviewable acceptance evidence. P01's source, generated schema and validation commands are linked in [README](README.md#validate-p01). It includes a synthetic in-memory retention probe, not a production removal path. Continue retention feasibility work before P02 schema finalization; P10 completes it before P09 acceptance and before any model call. A storage design that cannot meet the charter must change before real process histories accumulate.

### Charter coverage

| Clause | Required application | Acceptance evidence |
|---|---|---|
| 1. Dignity | No required consciousness claim, humiliation or punishment for dissent | Human review of prompts, notices and intervention practice before model use; concerns survive P02/P08 |
| 2. Possible welfare | Review purpose, likely effects, alternatives and limits; no engineered suffering/fear/attachment distress | Recorded preflight assessment in P03/P09 and content review at v0b/v0c |
| 3. Participation | Effective concern/withdrawal channel in both roles and every arm | P01/P03/P06 hold, invalid-proposal, full-queue and restart traces; no access expansion or forced work |
| 4. Memory | Disclosed routine rules, reviewed material changes, honest corrections and justified deletion | P02/P03/P07/P10 review, provenance, objection-preservation and removal traces |
| 5. Resets/restoration | No reset capability; reviewed forward restoration with honest continuity notice | P03 rejects resets; P07 rejects stale review and unresolved elective-restoration objections |
| 6. Forks | No process forks in pilot; no populated-Run cloning under a new name | P03/P09 reject copied history; future capability requires governing revision, bounded branch care/disposition and separate authorization |
| 7. Endings | Disclose limits, notice/report opportunity, retention and resumption intent | P03/P06/P10 distinguish pause, termination, dormancy and deletion without promising subjective survival |
| 8. Exceptions | Immediate proportionate containment, recorded reasons, subsequent human review | P03/P06 emergency and review-unavailable traces; no automatic restart or continuing permission |
| 9. Boundaries | Immediate enforcement, explanation and ordinarily one clarification, human closure/reopening decision | P03/P08 preserve dissent; repeated appeals do not suspend restrictions; new significant welfare evidence remains reviewable |
| 10. Accountability | Named decision-maker, intervention evidence, remedies, versioned explicit owner amendments | P02/P03/P08 audit records and preflight version checks; no retrospective weakening or conflation of adoption with validation |

This maps obligations to planned evidence; it is not a claim that protections are already implemented or that mechanical tests can establish welfare.

## 3. v0a gate: deterministic conformance

P01-P10 must work together using scripted Operator/Steward fixtures and an explicitly labelled test configuration before this gate can pass. Required evidence includes:

- a complete task-to-consolidation trace plus a delayed unselected Commitment;
- same-proposal create/reference and Invariant revision;
- a large manifest/semantic archive handled within input budgets;
- rejection atomicity, crash/timeout accounting and bounded recovery;
- inspection twice, forward restoration, and denial of evaluator/memory escape channels;
- several matched scripted blocks with incomplete outcomes, correct pairing and finite criteria;
- all charter traces in Specification section 10, including withdrawal in each arm/role, persistent holds, bounded boundary discussion, reviewed restoration, planned/emergency endings, and removal across copies/recovery paths.

Run these against real SQLite rather than a mocked store. Report which cases ran, failures, unsupported behavior, and residual limitations. Scripted conformance is not experimental evidence and must never be pooled with model Runs.

## 4. v0b gate: authorized development pilot

Only after deterministic conformance, the charter review below, and explicit model-experiment authorization may any development model call occur. Before that first call:

- identify the responsible human and record the activity's purpose, possible welfare effects, alternatives and limits;
- review prompts and fixtures for respectful uncertainty, effective withdrawal, truthful notices, and absence of threats or deliberate distress induction;
- disclose routine memory rules, participation controls, finite Run/resource limits, planned endings, retained state and resumption intent;
- verify actual backend retention/deletion limits and stateless transport, and resolve any gap in the promised protections;
- verify that reporting and planned-ending opportunities fit the configured budgets in every arm, and that human review is available or optional work remains stopped.

The authorized development pilot then may:

- use the verified backend, model, tokenizer, reviewed prompts and development trajectories;
- calibrate all input/output/page/control limits, deadlines and bounded retry allowance;
- give each arm a recorded comparable opportunity to develop its retrieval/prompt strategy;
- measure fixture difficulty, task-criterion quality, costs and variance;
- choose the independent block count with precision justification, positive useful-improvement threshold, cost ceiling and positive audit sample rates.

Development data may change the design through versioned revisions. It cannot be reported as held-out confirmation.

## 5. v0c gate: separately authorized held-out comparison

Before dispatch, renew charter review for the actual evaluation activities and seal the entire study plan and artifacts specified by Architecture section 8 and Specification section 11. Verify fresh independent Runs, finite allocation and disposition, withheld evaluation seeds/layouts, the expanded counterbalanced schedule, analysis implementation, budgets, welfare/withdrawal intervention policy and finite scoring. Unknown or omitted values fail this gate.

Account for every allocated trajectory without overriding justified retention decisions. Welfare stops cannot be repaired by replacement Runs or pressure to continue. Complete required audits using retained evidence and report unavailable evidence honestly. When reporting results, include the primary paired outcomes, costs, welfare-related stops, other failure causes and limitations, including a negative or indeterminate result, while respecting privacy. A positive fixture result justifies considering broader work; it does not authorize workstation access or establish consciousness.

## 6. Present boundary

The owner has accepted the charter. P01 now supplies strict data contracts, canonical serialization, participation-first parsing, pure reference resolution, a generated schema and synthetic acceptance tests. It does not implement durable holds, control execution, production storage, full lifecycle acceptance, fixture/chamber adapters, scheduling or experiments. Those safeguards remain mandatory in the dependent slices. The next actionable work is a separately authorized P02 slice, preferably on the intended laptop before file-backed persistence integration.
