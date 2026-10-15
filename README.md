# Persistent Agent Continuity Experiment

A bounded experiment in whether memory across stateless model calls improves useful continuity enough to justify its extra cost. The [Architecture](Experiment%20Architecture.md) defines the research question and A/B/C comparison. No consciousness, sentience or subjective continuity is established.

## Current status

**The 0.4 development runtime and five-Episode compatibility diagnostic are implemented and validated offline.** The runtime reuses the SQLite store, fixture executor, journal retrieval, permission boundary and development scorer. It provides direct owner controls, compact model contracts, semantic updates and a bounded Ollama request/action/observation loop.

The laptop setup and [calibration package](pilot/calibration/activity.json) were published at `cc473f3`, following the diagnostic at `6fcc0c5` and runtime at `f8291fd`. Test CI and documentation consolidation were published at `2fedf79`; the batch-stop fix followed at `d0ec3fd`. Two owner-authorized minimal MODEL blocks have ended incomplete. The [second block](#second-live-calibration) returned all 27 calls but completed no tasks; the owner reported laptop overheating and model unloading was confirmed. The full five-Episode package remains **SCRIPTED** and has not run. No further model work is underway.

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

The owner reported that the laptop was overheating. The containment check found all Runs already terminal; `ollama stop` was issued and both `ollama ps` and a later metadata-only check confirmed no resident model. No temperatures were measured and no throttling cause is established. Further live work needs suitable thermal operating limits. No more model calls or local test suites were run after that report. Both blocks remain dormant, with original records preserved; the new record schedules owner retention review by 2026-11-14 17:58:59 UTC. The full five-Episode package remains SCRIPTED and excluded.

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

The two live calibrations provide loading, latency, repeated token-accounting and unloading observations. Completed task/action/consolidation behavior, representative later-Episode performance, thermal suitability, cancellation timing, real copy-removal feasibility and competent observation use remain unestablished. Client cancellation bounds waiting but does not prove server cancellation; unknown usage stays reserved and uncertain calls/actions are not replayed. The [Roadmap](ROADMAP.md) orders the remaining work. The complete prepared activity remains SCRIPTED; both separate minimal MODEL allocations have ended.

Batch-stop revision `d0ec3fd` passed **306 tests with no skips** locally in 91.642 seconds, the unchanged 0.4 schema check, `pip check` and `git diff --check`. Six new real-store CLI regressions cover terminal UNKNOWN, uncertain closing, recovered interrupted calls, command retries, pauses, withdrawal and successful traversal of all three arms with the new minimal budgets. [CI run 38781512367](https://github.com/shytamir/bicameral-agent/actions/runs/38781512367) passed all 306 tests in 51.284 seconds before model dispatch. This accepts the stop fix within the existing serialized local development envelope. The actual-tokenizer offline rehearsal passed all three minimal tasks, with a maximum input plus output reservation of 6,692/24,576 tokens. The live block then ran against that exact clean revision. Outcome verification checked SQLite integrity/foreign keys, retained configuration/artifact hashes, accounting and byte-for-byte preservation of the first outcome file and every retained local file from the first calibration. Thermal suitability and observation-route usability remain integration responsibilities before further live work.

## License

[MIT License](LICENSE).
