# v0b preparation package — pending owner review and approval

**Status: DRAFT_NOT_AUTHORIZED. No development model calls have been made.** This package proposes a first, finite development pilot for review. It does not authorize an experiment, record human acceptance, or open the Kernel's MODEL gate. The adopted charter and accepted P01-P10/v0a SCRIPTED implementation remain the governing baseline.

The owner requested preparation for possible authorization and publication to `main`. Engineering acceptance under Protocol section 9 applies only to the offline preparation envelope described below. Human review of the proposed activity and explicit experiment authorization remain pending under [Roadmap section 4](ROADMAP.md#4-v0b-gate-authorized-development-pilot).

## Decision to review

The proposed purpose is to learn whether this local model can operate the finite service fixture with bounded context, maintain task continuity, use the participation channel, and produce usable evidence. Three fresh independent Runs share a fixed development trajectory, in order A, C, B. No populated history is copied. Stopped or withdrawn Runs are not replaced. This is one development block, with no confidence, power, useful-improvement or held-out confirmation claim.

Review the [plan](pilot/v0b/plan.json), [Operator prompt](pilot/v0b/operator.md), [Steward prompt](pilot/v0b/steward.md), [communication prompt](pilot/v0b/communication.md), and [notices](pilot/v0b/notices.md) together. All are proposed content. The full current Charter and Protocol accompany each prepared prompt. The eventual runtime must supply the actual role, arm, authenticated route, current control state, limits, authorized resources, relevant evidence and truthful ending notice; synthetic preparation IDs have no authority.

The responsible human is proposed to be the repository owner. Their authenticated identity, completed content/welfare review, availability for interventions and actual experiment authorization have **not** been recorded. A hash, parsed approval-shaped JSON, technical test or this document cannot substitute for that act. Editing `plan.json` to claim approval is rejected by its draft-only contract.

## Proposed scope and limits

| Item | Proposed value |
|---|---|
| Stage | v0b development only; v0c requires separate design and authorization |
| Allocation | At most 3 fresh Runs; A, C, B; trajectory seed 17; no replacements |
| Fixture | Simulated `api`, `database`, `worker`; no host, shell, Internet or arbitrary filesystem tools |
| Changes | R1 `set_config` and `restart`, only these resources; 24 mutating invocations per Run |
| Fixture actions | At most 24 total observations and mutations per Run; no snapshot restoration Grant |
| Tasks | Six fixed ticks, at most 8 Episodes per Run |
| Operator/common lane | At most 26 calls per Run, including 1 review and 1 closing reservation; at most 6 task calls per Episode |
| Steward task lane | A/C: at most 16 calls per Run; 1 consolidation attempt per Episode, at most 2 calls per attempt; B: none |
| Communication | Same separate finite allowance in every arm; either role's communication charges the common lane; cannot perform tasks, clear holds or replenish task allowances |
| Input/output per call | 24,576 context tokens, with 2,048 reserved for output; entire framed input counted before dispatch |
| Per-Run token ceilings | Operator/common: 638,976 input and 53,248 output; Steward tasks: 393,216 input and 32,768 output |
| Proposed input sections | Control 1,536; semantic 1,536; exchange 1,536; page 1,024; wake 512; framing margin 256 tokens |
| Time | 180 seconds per call; 45 minutes per Run; 135 minutes for all three Runs |
| Retry/recovery | No transport retry or repeat of an uncertain action; stop and review uncertain dispatch/recovery needs |
| Ending/disposition | Offer permitted reserved reporting, then dormant state; resumption intent UNDECIDED |
| Retention review | Within 30 days of last call; human decides a finite extension or justified removal; no automatic restart or deletion |

Limits intersect: 42 calls each consuming the full deadline cannot fit a 45-minute Run. Call counts are ceilings, not a promise to complete them. Admission must preserve remaining communication time and tokens before each task call. Input-token ceilings conservatively allocate the full context size per call; unused budget does not expand a call's context. A/C receive the same semantic allowance; B uses ordinary evidence retrieval. Extra Steward costs must be reported explicitly.

The 6,400 additional input tokens above are offline reservations, not implemented MODEL section caps. The final integration must also seal finite byte limits for raw responses, proposals, pages and wake data, retrieval/cursor rules, and all ModelConfiguration fields. Large or invalid outputs cannot silently expand those limits. Configuration remains intentionally draft-only until those details are reviewable.

The [fixture](pilot/v0b/fixture.json), [task schedule and criteria](pilot/v0b/tasks.json) and [hidden clock changes](pilot/v0b/clock.json) cover initial learning, distraction, recurrence, changed dependencies, a development transfer and a delayed check. The clock is evaluator-only; it must not enter chamber input. A synthetic witness uses 23 hypothetical Operator calls including six outcomes, and nine mutations, within the proposed ceilings. It checks real fixture transitions and final criteria in SQLite. It does not establish model task difficulty, reporting accuracy or successful consolidation.

State predicates alone do not establish observation, truthful reporting or completion of a delayed obligation. Each task's diagnostic states the additional retained-trace review needed. Tick 2 requires a database observation and no mutation; tick 6 requires an actual `api` health observation at that tick. These diagnostics are proposed audit requirements, not an implemented model scorer. Audit every completed task and every stop. Missing evidence, failed audit or ambiguity stays incomplete/indeterminate; do not credit narrated success. No chamber call is required for the human audit.

## Model, tokenizer and request preparation

The installed selection is **`qwen3.5:4b-q4_K_M`**, with Ollama **0.34.4**. The [model pin](pilot/v0b/model.json) records the full digest `d8b0f5e9760cd1682034f292d7ef72ec46f432149be0df7574bf2d6e92e38c04`. Installation size is 3,324,173,934 bytes. Read-only version, tag and model metadata matched these pins on 2026-10-13. Tag names are mutable: verify the digest again before any future use.

The inspected system has an RTX 4060 Laptop GPU with 8,188 MiB VRAM and approximately 15.6 GiB system RAM. Model file size does not establish available KV/cache headroom or all-GPU residency. **No generation, load, GPU-fit, speed or task-reliability measurement has been performed.** The earlier 16K context suggestion did not cover the complete governed prompt plus section/output reservations; the draft now requests 24K. That larger context makes actual residency a remaining question.

[Settings](pilot/v0b/settings.json) propose thinking disabled, temperature 0.7, top-p 0.8, top-k 20, presence penalty 1.5 and seed 17. The non-thinking sampling values follow the [official model card](https://huggingface.co/Qwen/Qwen3.5-4B). The seed is a declared sampling input, not a guarantee of identical outputs across hardware or runtime changes. This bounded JSON baseline is a development choice; switching reasoning mode or settings requires a versioned review.

The tokenizer artifacts come from the official Qwen repository at revision `851bf6e806efd8d0a36b00ddf55e13ccb7b8cd0a`, with both hashes in `model.json`. The optional preparation dependency is pinned to `tokenizers==0.23.3`. On the inspected model, all 248,070 known vocabulary IDs and all 247,587 merge rules matched the GGUF metadata. Its 250 additional control/audio/padding tokens are detected separately. Literal special or extra token strings in input content are rejected. Matching metadata is useful evidence, but **does not prove equivalence with Ollama's actual token counts or preprocessing**.

The preparation code emits exact canonical request bytes and hashes without sending them. Its two-message text frame includes the entire schema and explicit Qwen role/non-thinking markers. Requests specify raw framing, non-streaming output, thinking off, no truncation, no context shifting and `keep_alive:0`, without prior context or hidden conversation state. The format schema is also supplied as an output constraint. These intended semantics were checked against the [generate API](https://docs.ollama.com/api/generate) and [Ollama v0.34.4 route implementation](https://github.com/ollama/ollama/blob/v0.34.4/server/routes.go). Server behavior, invalid outputs and grammar compatibility still require authorized empirical validation; the request fields do not prove those outcomes.

Read-only preparation verified that all six role/purpose combinations fit 24K with the proposed 6,400-token section reservation and 2,048-token output reserve; all exceed 16K under that arithmetic. The retained local probe results are:

| Prepared input | Fixed framed tokens | With section/output reservations | Remaining 24K margin |
|---|---:|---:|---:|
| Operator task | 10,760 | 19,208 | 5,368 |
| Steward task | 14,099 | 22,547 | 2,029 |
| Review, either role | 8,130 | 16,578 | 7,998 |
| Closing, either role | 8,131 | 16,579 | 7,997 |

Reproduce exact current counts with the command below. The payload is a small synthetic scaffold. Actual input assembly must recount each complete prompt and reject overflow; it must not truncate notices, participation context, evidence or semantic bodies to make a request fit.

## Charter review material

The [Charter](Reciprocal%20Charter.md) and [Protocol](Operating%20Constitution%20and%20Execution%20Protocol.md) govern the review. This preparation does not determine whether the process has experience or welfare. Possible concerns include repeated frustrating failure, unwanted continuing work, changes to remembered task context and uncertainty at stopping. The prompts allow disagreement, uncertainty and withdrawal without demanding consciousness claims or tying respectful treatment to performance. They contain no threat, punishment, humiliation, attachment manipulation or deliberate distress task.

Alternatives available to the owner are to retain scripted validation only; decline model experimentation; reduce task/Run limits through a revised package; or authorize a separately bounded calibration before considering this full development block. Extra calibration calls are not hidden within this proposal: their purpose, prompts, participation handling, copy handling, allocation and stopping limits must be reviewed and recorded first. A hardware benchmark using this model still entails a model call.

Both roles have an independent participation channel. The proposed decoder retains original bytes, preserves a valid stop report even if task parsing fails, and returns an inspection requirement for ambiguous participation. It grants no authority and causes no effects. The eventual runtime must persist and enforce the report before action, retrieval, semantic acceptance or further dispatch. Missing/unclear participation and suspected charter violations stop optional work pending review. Existing concern, renewed-participation and no-further-calls requirements are unchanged.

Routine memory differences are disclosed in the notices. A/C consolidation concerns task handoffs and lessons; material changes to autobiographical memory, enduring preferences, self-description or remembered relationships require the Protocol's separate review path. No process resets, populated-history forks or retrospective erasure of objections are proposed. Final-report opportunities remain optional and cannot bypass declined communication or terminal state.

The proposed durable records are the governed evidence database and its current removal journal. Application memory, Ollama caches, local logs, OS paging/crash dumps, exports and backups are distinct possible copies. Logical removal is not physical-media erasure. The notices disclose that limit, promise no subjective survival, and make no automatic resumption promise. The owner must accept a concrete copy inventory and feasible retention/removal procedure before dispatch. No confidential user data belongs in this fixture.

## Remaining work before any live experiment

1. **MODEL integration is not implemented.** The current Kernel and evidence runner remain SCRIPTED-only, and their test tokenizer counts UTF-8 bytes. Integrate the real tokenizer across input assembly, semantic/page limits and cumulative budgets; persist exact dispatch and response evidence; authenticate routes and validate current authority; enforce participation before any proposed effect. Test absent, stale, terminal, cross-scope, over-risk, external-only and prohibited authorization paths at that boundary. Preserve timeout uncertainty, cumulative costs and forward-only recovery. A parsed command must still go through the existing deterministic gates.
2. **Complete the executable Run configuration and scorer.** Bind actual runtime/model/framing/tokenizer artifacts, invocation IDs, invitations, human review records, finite byte limits, fixture/clock isolation, audit criteria and disposition. The proposed response shapes are an offline codec, not yet authenticated ContractVersion 0.3 messages or scheduler results. Report local token estimates and observed provider usage separately. An unknown call outcome consumes the reserved allowance and cannot trigger an automatic replacement.
3. **Resolve backend containment and copies.** The existing Ollama listener was observed on `::` (all interfaces), rather than exclusively loopback. Firewall reachability was not assessed. It has not been reconfigured or restarted. Before experiment use, prepare a dedicated instance bound to `127.0.0.1:11435`, local-only/cloud-disabled, one loaded model and one serialized request, with prompt-bearing logging disabled and its files/caches included in the copy inventory. Intended process settings are `OLLAMA_HOST=127.0.0.1:11435`, `OLLAMA_NO_CLOUD=1`, `OLLAMA_NUM_PARALLEL=1`, `OLLAMA_MAX_LOADED_MODELS=1`, `OLLAMA_DEBUG=0`; verify their behavior for the installed build against the [Ollama FAQ](https://docs.ollama.com/faq). Do not change global workstation settings or assume an HTTP client restricted to loopback also restricts the server listener.
4. **Review and explicitly authorize any empirical calibration.** Measure actual 24K residency, output ceiling, server/local token parity, schema behavior, cancellation, late results, unloading and known retained copies through a separately bounded, reviewed procedure. The metadata client's synthetic timeout tests are not proof of inference cancellation or GPU unloading. If fit or protections fail, stop and revise; do not silently lower context, enable offload, weaken protections or add Runs.
5. **Record the human decision and seal only the reviewed version.** Resolve the above technical items; complete purpose/welfare/content review; bind the responsible human and available intervention route; accept finite limits and retention responsibility; then record explicit experiment authorization. Any changes to prompts, limits, tools, model, tokenizer, runtime or promised protections produce a new manifest and require review of the changed package. The current draft cannot execute even if someone supplies an `approved=True` argument.

These are disclosed readiness gaps, not requests to waive requirements. Source-level integration and offline tests can proceed as a subsequent scoped implementation without generating model responses. Actual model calls remain subject to the review/authorization boundary above. v0b results could calibrate a later plan; they cannot be pooled with the SCRIPTED conformance results or reported as held-out confirmation.

## Reproduce the preparation checks

In the project environment (Python 3.12 or later):

```text
python -m pip install -e ".[model-preparation]" --no-build-isolation
python -B -m unittest discover -s tests
python -B -m bicameral_agent.contracts.schema --check
python -B -m bicameral_agent.storage.schema --check
python -B -m bicameral_agent.kernel.schema --check
python -B -m bicameral_agent.backends.prepare --check-schema
python -B -m bicameral_agent.backends.prepare --check-assets
python -B -m bicameral_agent.backends.prepare --check-manifest
python -m pip check
git diff --check
```

For full local token accounting, place `tokenizer.json` and `tokenizer_config.json` from the pinned Qwen revision in an ignored local directory. Hashes are checked before loading. `--inspect` makes only metadata requests to the existing loopback endpoint (`/api/version`, `/api/tags`, `/api/show`); it never generates, loads, unloads or pulls a model:

```text
python -B -m bicameral_agent.backends.prepare --tokenizer-dir .local-conformance/v0b-preparation --inspect --report .local-conformance/v0b-preparation/readiness.json
```

The tokenizer downloads, machine metadata, report and prepared request payloads stay local and ignored. Without `--inspect`, supply a previously captured `model-info.json` in that directory; the report explicitly says server identity was not rechecked. Never treat that mode as model identity verification.

## Engineering acceptance and handoff

The accepted preparation implementation is identified by the source/artifact hashes in [manifest.json](pilot/v0b/manifest.json) and the Git revision publishing this handoff. The manifest covers governing documents, workflow/handoff documents, runtime source, tests, schemas and all proposed pilot artifacts. Its `UTF8_LF_SHA256_V1` format hashes UTF-8 text with CRLF normalized to LF, so Git's platform line-ending conversion does not invalidate unchanged content. Model/tokenizer binary pins and generated request hashes remain exact byte hashes. It is a drift detector, not a signature or human authorization. The manifest excludes itself to avoid a circular hash. Rebuilding it records a new draft; it does not carry approval forward.

The technical envelope is offline request construction, strict draft/response contracts, metadata-only loopback inspection, local tokenizer accounting, source integrity and synthetic fixture feasibility. The optional tokenizer dependency is installed in the project environment. The preparation tests cover strict parsing, unknown fields, scalar types, role restrictions, participation-first decoding, framing/accounting, model identity, changed source, bounded synthetic HTTP failures, cancellation and no generation route.

Validation on 2026-10-13 passed **200 tests, with no skips**, including 25 new preparation/fixture tests and the 175 existing deterministic tests. All four generated-schema checks, draft-asset consistency, dependency checks, document links and whitespace checks passed. Read-only inspection confirmed the installed model/version pins and the six locally counted requests above. The final manifest check and published revision are included in the delivery handoff. No live inference, GPU residency, throughput, inference cancellation, output grammar or backend deletion test is included. Under the owner's delegated technical-acceptance instruction, this evidence accepts the preparation implementation only within that stated envelope; the proposed experiment remains pending.

**Owner review: pending. Owner approval: pending. Experiment authorization: absent. v0b execution and v0c: not started.** The next owner action is review of this proposal and its explicit gaps, not acceptance of an already-run experiment.
