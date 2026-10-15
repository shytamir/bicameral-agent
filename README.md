# Persistent Agent Continuity Experiment

A bounded experiment in whether memory across stateless model calls improves useful continuity enough to justify its extra cost. The [Architecture](Experiment%20Architecture.md) defines the research question and A/B/C comparison. No consciousness, sentience or subjective continuity is established.

## Current status

**The 0.4 development runtime and five-Episode compatibility diagnostic are implemented and validated offline. The full pilot remains blocked.** Four minimal MODEL calibration blocks have ended. The latest ran against `c432198`: Aaron and Abbey performed seven inspections, but no task passed; Acme encountered a host retrieval error. All Runs are terminal and retained dormant. No further model calls are underway, and the final metadata check found no resident model.

The [calibration report index](pilot/calibration/results/index.md) links every narrative and exact-commit JSON outcome, including preparation and repair evidence. The [latest report](pilot/calibration/results/2026-10-15-minimal-c432198.md) records fixed budgets, fresh subject names, preserved histories, the interruption and remaining work. The full five-Episode package remains **SCRIPTED** and has not run.

New MODEL subjects receive Aaron, Abbey or Acme plus their initiation timestamp under the [Protocol's naming rule](Operating%20Constitution%20and%20Execution%20Protocol.md#21-prospective-subject-designations). Existing names and histories are preserved. Names identify the subjects prospectively without establishing consciousness or personal identity.

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

The accepted runtime revision is **`c432198d9df23a28154d77c52d327223a3e1368a`**, runtime SHA-256 `156b9fbfcb85dfc6422be1a4c2b4dac72edcb4533050972b424cbf3640cad7f0`. Acceptance under Protocol section 9 covers the existing serialized development fixture, deterministic contracts, managed stores and synthetic transport. It does not establish model competence or full-pilot readiness. [Source CI](https://github.com/shytamir/bicameral-agent/actions/runs/38795391166) passed **317 tests, no skips**, before the latest calibration. Detailed setup, validation and acceptance records are retained in the [preparation and repair history](pilot/calibration/results/preparation-and-repairs.md).

The latest live block establishes reachable inspection and multiple response branches, while leaving action-contract usability, task scope, grounding and invalid retrieval handling unresolved. Acme's interruption and Abbey's request for communication review need owner review under the Charter; original reports remain retained. All three new histories keep unfinished matters, with owner retention review due conservatively by **2026-11-14 19:42:31 UTC**. No reset, replay, replacement or full-pilot call followed the failure.

The next technical work is offline. Successful repair, consolidation, later-Episode continuity, representative costs, full-pilot thermal suitability, server cancellation timing and complete external-copy removal remain integration responsibilities. See the [latest report](pilot/calibration/results/2026-10-15-minimal-c432198.md) and [Roadmap](ROADMAP.md). This publication changes reports and navigation only; it adds no runtime behavior or live authorization.

## License

[MIT License](LICENSE).
