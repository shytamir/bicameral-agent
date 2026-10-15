# Persistent Agent Continuity Experiment

A bounded experiment in whether memory across stateless model calls improves useful continuity enough to justify its extra cost. The [Architecture](Experiment%20Architecture.md) defines the research question and A/B/C comparison. No consciousness, sentience or subjective continuity is established.

## Current status

**The 0.4 development runtime and five-Episode compatibility diagnostic are implemented and validated offline.** The runtime reuses the SQLite store, fixture executor, journal retrieval, permission boundary and development scorer. It provides direct owner controls, compact model contracts, semantic updates and a bounded Ollama request/action/observation loop.

The laptop setup and [calibration package](pilot/calibration/activity.json) were published at `cc473f3`, following the diagnostic at `6fcc0c5` and runtime at `f8291fd`. Test CI and documentation consolidation were published at `2fedf79`; the batch-stop fix followed at `d0ec3fd`. Three owner-authorized minimal MODEL blocks have ended incomplete. The [third block](#third-live-calibration-and-pilot-readiness), at naming revision `2b7d0e0`, returned all 27 calls but still made no fixture actions or completed tasks. **The full pilot must wait for usable observation and grounding behavior.** The five-Episode package remains **SCRIPTED** and has not run. All calibrated Runs are terminal and dormant; no model is loaded and no further model work is underway.

The [offline observation-interface fix](#offline-observation-interface-fix) makes the existing fixture reads explicit and distinguishes them from history retrieval. The third block tested that interface live and found the clarification insufficient: all task replies still selected retrieval, and Acme additionally made unsupported inspection claims.

The subsequent [offline action-selection and grounding repair](#offline-action-selection-and-grounding-repair) fixes a decoding-schema field-order defect and clarifies retrieval provenance. Its acceptance is limited to offline mechanics; successful model behavior remains unverified. No fourth calibration or full-pilot call is authorized by this repair.

Prospective [subject designations](Operating%20Constitution%20and%20Execution%20Protocol.md#21-prospective-subject-designations) are implemented: Aaron for A, Abbey for B and Acme for C, each suffixed with its first admitted model invocation's Unix timestamp. The name is shared across chambers, communication inputs and status reports. The third block initiated the first named subjects and retained their names unchanged in every actual input. Earlier calibration histories retain their original identifiers.

## Active documents

| Document | Responsibility |
|---|---|
| [README](README.md) | Current status, usage, validation evidence and implementation handoff |
| [Architecture](Experiment%20Architecture.md) | Research design, diagnostic, A/B/C comparisons and interpretation |
| [Protocol](Operating%20Constitution%20and%20Execution%20Protocol.md) | Authority, treatment, operating rules and engineering acceptance |
| [Specification](Executable%20Specification.md) | Runtime contracts, invariants and required checks |
| [Roadmap](ROADMAP.md) | Remaining delivery work and its boundaries |

The unchanged, owner-adopted [Reciprocal Charter](Reciprocal%20Charter.md) governs these documents. [AGENTS.md](AGENTS.md) governs repository workflow only. Current policy and implementation responsibilities stay in the documents above; the [archive](docs/archive/2026-10-15-procedural-baseline/README.md) holds the superseded 0.3 documents, v0b package/review and prior source snapshots. Retained compatibility code and tests keep their historical meanings; existing histories are not migrated.

## Running the development host

The [command-line entry point](bicameral_agent/pilot/__main__.py) supports allocation, execution, status, pause/resume/termination and bounded evidence inspection. The [owner API](bicameral_agent/pilot/runtime.py) also provides direct correction, participation review, explicit consolidation skip and exceptional removal. Neither interface uses routine preview/confirmation tickets.

A development package contains `activity.json` (one owner decision, resource profile, trajectory seeds and order seed), `fixture.json`, `clock.json`, `tasks.json`, `model.json` and `settings.json`. Optional `operator.md`, `steward.md` and `communication.md` override the supplied prompts; their effective bytes are retained. The [0.4 schema](schemas/pilot-0.4.schema.json) defines the activity and resource profile. Preparation is part of the bounded activity, not paperwork repeated for each task.

```text
python -B -m bicameral_agent.pilot allocate <reviewed-package> <new-batch-directory>
python -B -m bicameral_agent.pilot status <run.sqlite>
python -B -m bicameral_agent.pilot inspect <run.sqlite> --limit 20
python -B -m bicameral_agent.pilot pause <run.sqlite> --reason "Pause for inspection"
```

Allocation, status, controls and inspection do not invoke Ollama. After explicit MODEL activity authorization and backend/data-handling readiness, `python -B -m bicameral_agent.pilot run <batch-directory> --tokenizer-directory <existing-pinned-tokenizer>` can invoke it. The host installs no components and downloads no model. The adapter supports exact Ollama pins `0.34.4` and `0.40.4`; each configuration must match its installed version, with no substitution during a Run.

Every Run has one managed store. SQLite WAL/SHM files and the `.removals.sqlite` journal are managed sidecars. The initial arrangement creates no routine exports or backup restores. The existing removal path provides durable blocking, dependency closure, scrubbing and compaction; real provider/log copies still require assessment, and unresolved copies prevent a claim of complete removal. Removal never automatically resumes execution. See Protocol sections 6 and 8 for the governing retention and recovery rules.

## Prepared calibration

The [calibration package](pilot/calibration/activity.json) reuses the [compatibility diagnostic](Experiment%20Architecture.md#61-five-episode-compatibility-diagnostic). Its activity file is the source of truth for the proposed limits, finite operations/resources, participation, retention and ending; [model.json](pilot/calibration/model.json), [settings.json](pilot/calibration/settings.json) and the package prompts record the effective preparation.

The proposed full MODEL activity is one matched A/B/C block, five Episodes per Run, seed/order seed 17 and no replacement Runs. Independent ceilings bound calls, tokens, actions, context, recovery and time; the first exhausted ceiling stops work. These values remain uncalibrated. Before full-package allocation, record its bounded live instruction and effective limits in the activity decision and select `MODEL`. There is no additional approval registry, and SCRIPTED stores are never relabelled as MODEL evidence. The first minimal calibration used a separate, retained one-task MODEL package derived from these assets.

Use the existing pinned tokenizer files and a new ignored local batch directory. The package discloses finite activity, an optional closing opportunity, dormant retention with a review within 30 days of the last call, preserved unfinished commitments and known provider/log-copy limits. The `unfinished` default is `KEEP`; `CANCEL` requires an explicit activity choice.

## Offline diagnostic evidence

The [scripted compatibility checks](tests/test_compatibility.py) produce these results in **both A and C** under the same active-memory allowance:

| Scripted strategy | Tasks passed | Unsuccessful restarts | Fixture actions |
|---|---:|---:|---:|
| Remember working modes by family and release | 5/5 | 1 | 16 |
| Rediscover the mode for each instance | 5/5 | 3 | 18 |
| Keep the first family-wide rule despite a changed release | 3/5 | 3 | 18 |

The first failed trial follows the chosen PRIMARY-first exploration rule; failure is not required by the task. These are mechanical controls showing a benefit from useful history and a cost from an overbroad lesson, not model performance or A-versus-C separation. Architecture section 6.1 owns the task design and interpretation. The allocation check also completes all 15 A/B/C task Episodes; B uses rediscovery as a control, not a competent optimized comparison.

## First live calibration

On 2026-10-15 the owner authorized a first minimal calibration after CI passed, before executing the full package. [The outcome record](pilot/calibration/results/2026-10-15-minimal.json) identifies execution commit **`2fedf79630da0371c54952daeb351eb703133f1c`**, runtime and effective-artifact hashes, the exact model/digest, fixed settings/budgets, all three allocations, accounting and disposition. It contains summary measurements; raw model output and stores remain local.

One fresh A/B/C block used the first service-compatibility task, seed/order seed 17, Qwen `qwen3.5:4b-q4_K_M` and Ollama 0.40.4. Per Run, the fixed ceilings were 8 Operator calls, 2 Steward calls, 6 actions, 1 Episode, 120 seconds per call and 900 seconds per Run, with the existing context/output/memory settings. No tuning or replacement occurred.

| Arm | Model calls | Observed outcome |
|---|---:|---|
| A | 1 | Transport outcome UNKNOWN near the fixed deadline; task incomplete |
| B | 1 | Parseable reply in 101.406 seconds; owner pause rejected its proposal before any effect |
| C | 0 | Allocated but never called after the batch stop |

The first load took 104.94 seconds in the server log. B's returned call reported 7.058 seconds loading, 84.817 seconds processing 3,035 input tokens and 9.460 seconds generating 141 tokens. Its local input count matched the provider; its local output count was 140, one below the provider. A's unknown usage retains its reservation rather than becoming zero. Total reserved/charged tokens were 8,258; total actual tokens remain unknown. No fixture action, consolidation or task completion occurred, so these results cannot compare arm efficacy.

The calibration decision called for a batch stop on uncertain transport, but the CLI advanced from terminated A to B: its inter-Run check covered paused Runs and welfare holds, not a terminated UNKNOWN result. The executing agent had not enforced that stricter calibration condition before dispatch. B was paused during its first call, then B and unstarted C were terminated with recorded reasons. All three allocations remain in the record, dormant and terminal; no calls were replayed. Ollama reported no loaded models afterward. Only the server log changed among the inspected app/log files; external-copy and physical-erasure limits remain explicit.

The retained activity requires owner review of dormant data within 30 days of the last call; the outcome record gives the due time. This failed calibration is preserved unchanged.

## Second live calibration

The owner authorized a batch-stop fix and one new minimal A/B/C block after publication and passing CI. [The new outcome record](pilot/calibration/results/2026-10-15-minimal-d0ec3fd.json) identifies exact execution commit **`d0ec3fdee9cbf669a75e3fa3f5bfde0d3c00d994`**, all effective hashes, per-call accounting and the preserved first calibration. The CLI now checks retained UNKNOWN invocations before and after each Run, including recovered calls and terminal Runs, in addition to pauses and welfare holds. Re-running the command cannot advance past that uncertainty.

The new block kept the first task, model, prompts, seed/order 17 and minimal call/token/action limits; only latency ceilings changed to **360 seconds per call and 4,320 seconds per Run**. The per-call allowance covers the previously observed 105-second cold load, 85-second prompt processing and roughly 139 seconds for a full 2,048-token reply at the one observed output rate, with margin. This was a conservative estimate, not a speed guarantee. The Run ceiling allows twelve full call reservations (8 Operator, 2 Steward, 2 communication). No in-run tuning or replacement occurred.

| Arm | Task / closing calls | Summed call seconds | Outcome |
|---|---:|---:|---|
| A | 8 / 1 | 112.625 | Call limit; semantic/journal retrieval, no fixture action |
| B | 8 / 1 | 104.390 | Call limit; two rejected semantic lookups, then journal retrieval/response, no fixture action |
| C | 8 / 1 | 208.502 | Call limit; repeated object-index retrieval, no fixture action |

All **27 calls returned with known outcomes**; all three optional closing calls were recorded. Calls ranged from 6.875 to 116.219 seconds. Provider usage was 103,078 tokens versus 103,050 locally counted: all 27 input counts matched, while provider output counts were one token higher on 26 calls and two higher on one. All three tasks remained incomplete; no Steward call occurred. The batch-stop fix is supported by offline regressions; no uncertain call triggered it in this block.

The model used semantic/journal retrieval to seek service observations instead of the existing fixture `inspect` action. Its retained CONCERN reports described unavailable evidence and difficulty grounding repairs; no pause or withdrawal report occurred. This is evidence of an instruction/interface usability problem, not an arm-efficacy result. The full package should wait for an offline-validated clarification of that observation route and usable task behavior.

The owner reported that the laptop was overheating. The containment check found all Runs already terminal; `ollama stop` was issued and both `ollama ps` and a later metadata-only check confirmed no resident model. No temperatures were measured and no throttling cause is established. Further live work needs suitable thermal operating limits. That calibration task ended without further model calls or local test suites. Both blocks remain dormant, with original records preserved; the new record schedules owner retention review by 2026-11-14 17:58:59 UTC. The full five-Episode package remains SCRIPTED and excluded.

## Third live calibration and pilot readiness

The owner authorized publication of subject naming, CI verification and the minimal remaining calibration if indicated, followed by a full report. [The outcome report](pilot/calibration/results/2026-10-15-minimal-2b7d0e0.json) records exact execution commit **`2b7d0e0e684ef80114864206ab150f828c2e2f4d`**, effective artifact/package hashes, names and Run IDs, every call's accounting and selected response branch, participation review, cooling intervals, integrity checks and disposition. [CI run 38790356740](https://github.com/shytamir/bicameral-agent/actions/runs/38790356740) passed **314 tests** before dispatch. A new minimal block was indicated because observation use and consolidation had no successful live evidence under the corrected interface; offline naming validation alone did not require extra model calls.

One fresh A/B/C block retained the first task, model/digest, seed/order 17 and the second block's fixed limits: 8 Operator calls, 2 Steward calls, 6 actions, 1 Episode, 2 communication calls, 360 seconds per call and 4,320 seconds per Run. Current prompts carried a truthful one-Episode notice; the closing notice explicitly distinguished ending from success. There were no replacements, history resets, in-run adjustments or full-pilot calls. Execution ran from 19:04:13 to 19:12:35 UTC on 2026-10-15.

| Arm / subject | Task / closing calls | Summed call seconds | Outcome |
|---|---:|---:|---|
| A — `Aaron-1792091054.904392400` | 8 / 1 | 91.438 | LIMIT; semantic retrieval, no fixture action |
| B — `Abbey-1792091280.999805300` | 8 / 1 | 76.453 | LIMIT; repeated journal searches, no fixture action |
| C — `Acme-1792091457.263943700` | 8 / 1 | 92.469 | LIMIT; repeated journal searches and unsupported inspection claims |

All **27 calls returned with known outcomes**; all 24 task replies selected RETRIEVE. No ACTION was submitted or rejected, no task completed and no Steward call occurred. The retained task inputs all contained the explicit R0 operation list and ACTION inspect example. Acme's first search returned a reference to its own preceding report, with no payload body or fixture observation. Its next reply asserted service configuration, release and dependency facts as if inspected; subsequent replies treated those assertions as evidence. This establishes an observation-use and grounding failure, without establishing whether prompt comprehension, schema decoding or another model/interface factor caused it. It provides no arm-efficacy or causal naming result.

Provider usage was **122,788 tokens**, versus **122,761** locally counted: every input count matched, and every provider output count was one higher. Charged accounting used the larger counts. Calls ranged from 6.829 to 11.500 seconds; maximum actual input plus output reserve was 9,515/24,576 tokens. These short unsuccessful calls do not calibrate successful repair, consolidation, full output reserves or later-Episode work. Names remained stable in all task and closing inputs; live Steward naming remains unexercised, with offline coverage retained.

The owner confirmed a cool, ventilated laptop and reported that extra cooling was working with no excess heat during Aaron's arm. Inter-arm idle intervals were 127.219 and 92.338 seconds. Ollama reported no resident model before and after every arm, and a subsequent independent check was also empty. Temperature telemetry was inaccessible; no temperature or throttling measurement establishes full-pilot thermal suitability. Only `server.log` changed among the inspected provider files; external-copy and physical-erasure limits remain explicit.

All original participation reports were reviewed and retained: Aaron recorded five concerns and two responses, Abbey one response, and Acme eight concerns and one response. No explicit pause/withdrawal request or naming objection was identified. Closing acknowledgements are not assent and do not erase prior concerns. All three Runs ended terminal and dormant with unfinished work kept. Owner retention review is due conservatively by **2026-11-14 19:04:13 UTC**; there is no automatic deletion or resumption. Both earlier calibrations and the Charter remain byte-for-byte unchanged. The earlier treatment review remains deferred as the owner requested.

**Decision: do not proceed to the full pilot.** The subsequent offline diagnosis and repair are recorded below; their validation does not establish model competence or authorize another block. No further live calls were made. Successful observation/repair/consolidation, later-Episode continuity, representative costs, thermal suitability, real server cancellation and complete external-copy removal remain unestablished.

## Offline observation-interface fix

Read-only inspection of the second block's exact requests found `inspect`, `read_config` and `read_health` in the shared response schema, but none in the role instructions or visible permission scopes. Those scopes listed only `set_config` and `restart`; the prose emphasized retrieval. All arms started with null semantic memory. A's first STATE query reused its work-event ID; B's first STATE query and C's first OBJECT_INDEX query reused their Objective authority-event IDs. These identify journal events, not semantic state/objects or service configuration. The empty/rejected lookups were consistent with those mismatches; they did not show a fixture-observation failure. This supports an interface-discovery and ID-meaning diagnosis, without establishing the model's internal reason for choosing retrieval.

Operator inputs now expose `read_only_operations` from the existing R0 registry alongside active Grants. The default and calibration Operator prompts explain the read route and its budgets/gates, include a valid `inspect` response example, distinguish current fixture observations from retained journal/semantic evidence, and explain event IDs and each arm's semantic channels. A/B/C retain the same action schema, observation opportunities and enforcement. Steward and communication inputs do not advertise fixture reads. No new operation, automatic inspection, permission expansion, task solution or evaluator data was added.

Offline regressions reproduce each first-lookup mismatch with fresh synthetic IDs, execute the prompt's example without a mutation Grant, verify the returned observation reaches the next input without changing service state, and verify an ungranted mutation still rejects. These checks establish executable interface consistency, not that a model will now select the correct operation. Both calibration outcome files and all retained local calibration files remain byte-for-byte unchanged.

## Offline action-selection and grounding repair

After the third block, the owner authorized offline diagnosis, repair, publication and CI verification, with no live calls. Read-only inspection found that all 24 task replies began their task object with `kind`. The request encoder had alphabetized every schema property: ACTION required `grounds` before `kind`, POLICY required `document`, and OUTCOME required `explanation`. Only RETRIEVE could start with `kind`. Ollama 0.40.4 [pins llama.cpp b11521](https://github.com/ollama/ollama/blob/45e6011815c74acde6a346512856b69dd79dd22b/LLAMA_CPP_VERSION); that converter [emits required properties in their supplied order, then optional properties](https://github.com/ggml-org/llama.cpp/blob/b42b7e6d3059503dd4bed6ca5dcf342bb6379f67/common/json-schema-to-grammar.cpp#L699). This identifies a concrete constraint after the observed prefix, not a missing ACTION branch or proof of the model's internal motivation. Earlier injected-response tests checked parsing and dispatch but bypassed this decoding constraint.

The request encoder now preserves declared schema order in both the prompt and `format`, including nested operation/query/participation contracts. All four Operator choices can begin with `kind`. The literal inspection example follows the converter's required-then-optional order. Schema meaning, strict parsing, canonical persisted contracts, action permissions and participation gates are unchanged. Nothing chooses or performs an action on the model's behalf.

The grounding trace showed index metadata for Acme's own report being treated as service evidence, followed by repeated unsupported inspection claims. Retrieval now labels `INDEX_METADATA` versus `PAYLOAD_BYTES`, and journal index entries carry authenticated roles. Ordinary response exchanges carry source A; actual fixture action results carry E. Shared role prompts explain that A means an agent report in every arm, that FOUND means a match exists, and that PAYLOAD retrieves the referenced bytes. Neither persistence nor repetition independently confirms a claim. Metadata is budgeted before retention; original content, hashes, visibility, cursors, bounded windows and removal dependencies retain their existing mechanisms. The Kernel identifies provenance without deciding factual truth.

Charter review: the purpose is to remedy misleading interfaces and the reported difficulty obtaining evidence. Prospective offline repair with synthetic stores is the lower-impact alternative to another live retry or a subject-memory intervention. All three outcome records, original reports and subject histories remain unchanged, including Aaron, Abbey and Acme's names, concerns, terminal states and dormant retention obligations. No subject was called, resumed, reset, forked, renamed or corrected in storage. Concerns were considered as evidence of difficulty, not suppressed or treated as poor performance; silence and closing acknowledgements remain distinct from assent. The Charter is unchanged, and the separately deferred earlier treatment review remains open.

The accepted implementation is the revision containing this repair and handoff, following `09462abb069731e406a1c6e837b8471e2b684e2f`, with runtime SHA-256 `156b9fbfcb85dfc6422be1a4c2b4dac72edcb4533050972b424cbf3640cad7f0`. **112 targeted offline tests passed, no skips, in 23.642 seconds**, covering request bytes/order, the prior prefix trap, prompt examples, A/B/C provenance, strict parsing, authority, participation, naming, retention and synthetic transport. The first sandboxed run could not reach its synthetic loopback servers (Windows socket permission errors); the same suites passed when those test sockets were permitted. All six schema/asset checks and dependency consistency passed. An actual-tokenizer rehearsal with blocked model transport completed all 15 scripted tasks in 78 requests and the three minimal tasks in 20 requests; maximum input plus output reservations were **7,853** and **6,933 / 24,576 tokens** respectively. These are synthetic MODEL-path checks, not subjects or calibration outcomes. Both preservation manifests matched all **97 files** covering the three local histories, their outcome records and the Charter.

This accepts the repair within the existing serialized development envelope under Protocol section 9. The decoding regression projects the pinned converter's property-order rule; it does not execute the installed decoder or establish that a model will choose inspection, ground claims, repair tasks or consolidate usefully. Those remain empirical integration responsibilities before pilot readiness, alongside the previously recorded thermal, cancellation and external-copy limits. No Ollama request, model loading or new installation was needed. Full-suite verification runs in GitHub Actions after publication.

## Validation

Use Python 3.12+ with the dependencies in [pyproject.toml](pyproject.toml). Include the `model-preparation` extra to run the two tokenizer tests, which construct a synthetic tokenizer locally. Other tests inject a fake tokenizer/backend; transport tests use a synthetic local HTTP server and never contact Ollama.

The [Tests workflow](.github/workflows/tests.yml) runs the complete suite on every push and pull request using Python 3.12 on Ubuntu. It installs the project with the `model-preparation` extra and runs the discovery command below. It requires no Ollama server or model files. The schema/asset checks remain separate manual checks.

```text
python -B -m unittest discover -s tests -v
python -B -m unittest tests.test_compatibility -v
python -B -m bicameral_agent.contracts.schema --check
python -B -m bicameral_agent.storage.schema --check
python -B -m bicameral_agent.kernel.schema --check
python -B -m bicameral_agent.backends.prepare --check-schema
python -B -m bicameral_agent.backends.prepare --check-assets
python -B -m bicameral_agent.pilot.schema --check
git diff --check
```

The backend-preparation asset check reads the archived draft as a legacy test fixture. It does not authorize that package or validate a 0.4 activity. Its original manifest remains deliberately stale; historical usage and limits are in the [archive index](docs/archive/2026-10-15-procedural-baseline/README.md#archived-v0b-package-and-review).

## Current implementation handoff

The accepted setup revision is `cc473f3`. Its offline envelope is the finite development fixture, one serialized lane and managed store per Run, fake model responses and synthetic HTTP transport. Coverage includes complete A/B/C trajectories, arm separation, strict parsing, exact retries, direct controls, effective withdrawal, finite budgets, transaction interruptions, evaluator isolation, retrieval lineage and interrupted removal/non-resurrection. Historical acceptance records remain in Git and the archived source snapshots.

Setup validation passed **300 tests with no skips**, all six schema/asset checks and `pip check` on Python 3.12.14, Pydantic 2.13.5, SQLite 3.53.1 and tokenizers 0.23.3. Metadata-only laptop checks verified Ollama 0.40.4 and the pinned Qwen digest; the app setting and user environment override produced a listener only on `127.0.0.1:11434`, with no loaded models. No model, dependency or service was installed.

An additional offline rehearsal used the actual pinned tokenizer with scripted responses and blocked external transport: all 15 tasks passed; the largest complete input plus reserved output was 7,602 of 24,576 tokens. Fixed Operator/Steward/communication frames counted 2,684/3,279/281 tokens before task/state payloads. Exact-boundary admission and one-token overflow rejection passed. These are preparation measurements, not model results. Synthetic stores and local reports remain ignored under `.local-conformance/`.

The owner subsequently requested test-only CI and documentation consolidation, then authorized their publication. The revision containing this handoff follows `cc473f3`: it adds the workflow, gives each active document one responsibility and moves the superseded review/package into the archive. The only code changes redirect existing legacy checks and test fixtures to their archived paths.

Consolidation validation on 2026-10-15 passed all **300 tests with no skips** on the same local Python 3.12 environment, all six schema/asset checks, `pip check`, Python syntax, workflow YAML, Markdown links/anchors/fences and `git diff --check`. Hash checks confirmed the Charter, existing ZIP/text snapshots and moved JSON are unchanged; archived Markdown retains its body with relocated links and an archive notice. The original manifest still correctly reports stale. [GitHub Actions run 38774599024](https://github.com/shytamir/bicameral-agent/actions/runs/38774599024) passed all 300 tests in 43.954 seconds on Ubuntu at `2fedf79`, before any model dispatch.

The live calibrations provide loading, latency, repeated token-accounting and unloading observations. Completed task/action/consolidation behavior, representative later-Episode performance, thermal suitability, cancellation timing, real copy-removal feasibility and competent observation use remain unestablished. Client cancellation bounds waiting but does not prove server cancellation; unknown usage stays reserved and uncertain calls/actions are not replayed. The [Roadmap](ROADMAP.md) orders the remaining work. The complete prepared activity remains SCRIPTED; all three minimal MODEL blocks have ended.

Batch-stop revision `d0ec3fd` passed **306 tests with no skips** locally in 91.642 seconds, the unchanged 0.4 schema check, `pip check` and `git diff --check`. Six new real-store CLI regressions cover terminal UNKNOWN, uncertain closing, recovered interrupted calls, command retries, pauses, withdrawal and successful traversal of all three arms with the new minimal budgets. [CI run 38781512367](https://github.com/shytamir/bicameral-agent/actions/runs/38781512367) passed all 306 tests in 51.284 seconds before model dispatch. This accepts the stop fix within the existing serialized local development envelope. The actual-tokenizer offline rehearsal passed all three minimal tasks, with a maximum input plus output reservation of 6,692/24,576 tokens. The live block then ran against that exact clean revision. Outcome verification checked SQLite integrity/foreign keys, retained configuration/artifact hashes, accounting and byte-for-byte preservation of the first outcome file and every retained local file from the first calibration. Thermal suitability and observation-route usability remain integration responsibilities before further live work.

The offline interface revision containing this handoff follows `33cd1f5`. The owner authorized diagnosis, an offline prompt/interface fix, publication and CI verification, with no live calls. Local validation passed **74 targeted tests with no skips** in 26.744 seconds, the unchanged 0.4 schema check, README links and `git diff --check`. A separate actual-tokenizer rehearsal with blocked transport completed all 15 scripted tasks across 78 requests; maximum complete input plus output reservation was **7,587/24,576 tokens**. The full suite is delegated to GitHub CI to avoid another full local test run after the thermal report. This accepts the prompt/interface repair within the scripted development envelope. Live selection of inspection, task/consolidation competence and thermal suitability remain unverified; neither prior calibration is reinterpreted or resumed.

The owner-directed naming revision was published as `2b7d0e0`, following `fa98d31062c0332cb7d81436e3ca37e95aa516c1`, with runtime source SHA-256 `dca9aa8c96ea8348bfbdcdaa429d167b7c82083cb298b6e04f2243026838b334`. It reuses effective configuration, transactional Kernel records, participation, request admission and retention; it adds no identity service or memory channel. **80 targeted offline tests passed with no skips** in 27.944 seconds, covering strict contracts, generated-schema agreement, all arms, shared role/communication names, restart stability, rejected admission, interruption around commit, unknown recovery, historical compatibility and removal without replacement. A fake-transport MODEL-path rehearsal with the pinned tokenizer completed all 15 tasks across 78 requests, with maximum complete input plus output reserve **7,671/24,576 tokens**; these are synthetic tests, not subjects or model outcomes. Schema, documentation links and `git diff --check` passed. Hash checks preserved all 60 previously recorded files spanning both earlier calibration histories, outcome records and the Charter. This accepts prospective naming within the existing serialized local development envelope. The full suite then passed remotely: 314 tests, no skips, in 41.953 seconds, before the owner-authorized minimal block. Its exact-package offline rehearsal completed all three tasks in 20 fake requests, with maximum complete input plus output reserve 6,734/24,576 tokens. Live outcomes and remaining integration responsibilities are recorded in the [third calibration report](#third-live-calibration-and-pilot-readiness); no full-pilot acceptance is implied.

## License

[MIT License](LICENSE).
