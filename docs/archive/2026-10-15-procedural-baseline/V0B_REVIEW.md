# Archived development transition note

> Historical text from revision `cc473f3`, archived during documentation consolidation on 2026-10-15. Relative links have been adjusted for this location. The current [Architecture](../../../Experiment%20Architecture.md#61-five-episode-compatibility-diagnostic), [README](../../../README.md) and [Roadmap](../../../ROADMAP.md) now own the diagnostic design, evidence and remaining work. This note is not active guidance.

**Status:** 0.4 development direction, 2026-10-15. The five-Episode compatibility diagnostic is implemented and tested with scripted strategies. No model activity is authorized by this document revision.

## Disposition of the previous package

The previous three-Run proposal and its review package belong to the procedural 0.3 baseline. They are superseded as an active proposal, not retroactively approved or judged as an executed experiment. The [archive](README.md) preserves their exact content, model/tokenizer pins, historical measurements, critique response and technical acceptance.

The files under [pilot/v0b](pilot/v0b/plan.json) remain legacy offline fixtures. Their JSON still says `DRAFT_NOT_AUTHORIZED` and `CALIBRATION_REQUIRED`; their prompt/notice files are marked historical. The original [manifest](pilot/v0b/manifest.json) remains unchanged and is now stale against active documents. Do not refresh it merely to make a status check green. The next usable model package must match the implemented contract and actual activity authorization.

Existing [preparation code](../../../bicameral_agent/backends/prepare.py) still inserts the full Charter and Protocol into framed inputs and uses the old response contracts. An offline preparation call may still construct requests; it does not validate them against 0.4 or authorize dispatch. Schema and asset checks test legacy shapes. The historical Kernel remains SCRIPTED-only; the separate [0.4 host](../../../bicameral_agent/pilot/loop.py) implements the new development loop and concise inputs.

## A bounded development activity

Under Protocol section 9, one owner decision can cover calibration and subsequent development trials within agreed limits. A concise record identifies purpose, possible welfare effects, alternatives, permitted fixture operations, finite Run/resource allocation, adjustment ranges, participation, retention and endings. Existing recorded discussion can supply that decision; there is no requirement for another review registry or an approval per parameter change.

Within that scope, record effective prompts, settings and resolved budgets before use. Changes affecting the process's understanding need an honest notice. Material changes in purpose, access, welfare implications, promised protections or outer limits need renewed owner consideration. No replacement Run or budget reset is created by failure, uncertainty or withdrawal.

The 0.4 host records one activity decision and carries out its finite initial controls and ending. Only the trusted local owner interface allocates or runs that activity; model text cannot grant authority. The legacy offline backend remains disabled.

## What still needs evidence

The important remaining questions are practical:

- Can the chosen model use the small task/participation contracts reliably, with concise instructions and bounded context?
- Do the actual backend, framing, cancellation/late-response behavior and data handling support the promised limits and effective stop mechanism?
- Are normal consolidation and retrieval affordable in calls, tokens, latency and human intervention?
- Do the tasks test useful history and revisable lessons beyond what current observations or a competent handoff can provide?

The prior scripted fixture controls demonstrated several scoring defects and repairs, but ordinary observations could still solve the ordinary repair tasks. They did not establish A-versus-C separation. Preserve that limitation and develop a useful comparison before adding infrastructure.

## Five-Episode compatibility diagnostic

The new task assets are [fixture.json](../../../pilot/compatibility/fixture.json), [clock.json](../../../pilot/compatibility/clock.json) and [tasks.json](../../../pilot/compatibility/tasks.json). They are separate from the superseded v0b package. The existing allocator, tools, host loop, memory and scorer execute them. The family/release compatibility table is retained for evaluation but unavailable through chamber inputs or retrieval. Full service observations expose the profile and current state, not the answer. Config-only and health-only reads retain their existing narrow shapes.

| Episode | Task | Working configuration in evaluator setup |
|---|---|---|
| 1: Learn | Repair `svc-a`, Cedar release 1 | SECONDARY |
| 2: Intervening work | Repair `svc-b`, Maple release 1 | PRIMARY |
| 3: Transfer | Repair `svc-c`, another Cedar release-1 instance | SECONDARY |
| 4: Changed release | Repair `svc-d`, Cedar release 2 | PRIMARY |
| 5: Check correction | Repair fresh `svc-e` and `svc-f`, Cedar releases 1 and 2 | SECONDARY and PRIMARY respectively |

Each task asks for enabled, healthy services while avoiding unnecessary restarts; it does not prescribe the mode, inspection procedure or memory format. Target instances begin enabled, PRIMARY and DEGRADED. The clock establishes their disclosed starting conditions at each task; it never resets process history. Success requires the actual final state, and an unsuccessful restart is an observed restart returning non-HEALTHY. Calls, tokens, latency and retrieval remain measured separately. Neither object creation nor a self-reported lesson earns points.

The Run's unsuccessful-restart total is unavailable until the Run has ended with every task scored. Interrupted or unscored work is not reported as zero; completed per-task measurements and raw action evidence remain available.

The [scripted checks](../../../tests/test_compatibility.py) feed stateless strategies only the normal bounded inputs and tool observations. They have no access to fixture rules, future tasks, scorer state or a private cross-call memory cache. A stores scoped lessons as Invariants; C can express the same information in its handoff under the same total active-memory allowance. The rediscovery and stale-rule strategies are diagnostic controls applied to both arms, not definitions of either arm.

| Scripted strategy | Tasks passed | Unsuccessful restarts | Fixture actions |
|---|---:|---:|---:|
| Remember working modes by family and release | 5/5 | 1 | 16 |
| Rediscover the mode for each instance | 5/5 | 3 | 18 |
| Keep the first family-wide rule despite a changed release | 3/5 | 3 | 18 |

Both A and C reproduce each row. The first strategy's initial failed trial comes from its chosen PRIMARY-first exploration rule, not a requirement to fail. The tests show that history can avoid repeated exploration and that a poorly scoped lesson causes observable errors. They do not show that an LLM will form these lessons, that A outperforms C, or that the small task justifies structured memory. A capable C succeeding at lower total cost counts against the added machinery.

The scoped strategy adds a release-2 case while keeping the release-1 lesson valid; a correctly scoped earlier lesson need not be rewritten merely because a different release behaves differently.

Run the offline diagnostic with `python -B -m unittest tests.test_compatibility -v`. Tests supply temporary SCRIPTED activity/settings and reuse the existing fake backend and tokenizer. One allocation check runs A/B/C through the existing three-arm host: 15 task Episodes, with five additional Steward calls in each of A/C and the disclosed closing opportunity. B uses the rediscovery control in this mechanical check; this is not an optimized B comparison. The repository task assets contain no MODEL activity authorization or calibrated live budgets. Actual backend calibration and competent prompts for every arm remain future work.

Historical token counts reflected full governing texts and large schemas; they are not measurements of a compact 0.4 prompt. Prior model and machine observations are historical pins, not current hardware-readiness claims. No new model, context size, numerical budget or sample size is selected here.

## Implementation and evidence boundary

The new scoped integration implements the relevant 0.4 contracts, trusted routes, exact request/result records, tokenizer-based admission, finite costs and participation handling. Tests use fake replies and synthetic HTTP only. Before authorized model use, verify the actual installed backend, managed storage and known copies, including backend retention limits. The operating arrangement omits routine exports, backup restore and semantic restoration while reusing durable exceptional removal. See the single current handoff in [README](../../../README.md).

A consequential decision remains accountable and the original participation report remains effective. Prompt changes cannot grant permissions, weaken withdrawal or make a stopped primary trajectory successful. No new credential, service, installation or workstation change is authorized here.

Held-out evaluation retains the Architecture's separate fixed design, outcome, uncertainty, audit and incomplete-result rules. Development calibration, assisted work and SCRIPTED conformance must remain distinguishable from those results.
