# Persistent Agent Continuity Experiment

Can a process built from stateless model calls improve operational continuity through bounded handoffs, explicit obligations and revisable lessons from experience, enough to justify the added model and human work?

The Operator pursues the Objective and proposes actions. The Steward proposes memory changes. The State Kernel enforces permissions, participation, finite resources and atomic persistence. The process is the unit of study; no claim of consciousness, sentience or subjective continuity is established.

The owner-adopted [Reciprocal Charter](Reciprocal%20Charter.md) remains unchanged and governs treatment independently of task performance.

## Current status

On 2026-10-15 the owner directed a prospective simplification of the Protocol and Specification: trust the accountable owner, remove repeated procedural approval for routine decisions, simplify contracts, and keep the previous stronger procedures accessible if needed.

**A bounded 0.4 development runtime is implemented and tested offline.** It reuses the SQLite store, fixture executor, journal retrieval, permission boundary and development scorer. The new path supplies direct owner controls, compact model contracts, semantic updates and an Ollama request/action/observation loop. No live model calls have been made in this change.

The five-Episode compatibility sequence and its small fixture extension are implemented with scripted strategy checks. They exercise retained lessons, transfer and release-specific correction. A and C can both solve the sequence; this establishes a usable mechanical diagnostic, not a model result.

The existing code at `22a28073bb37851f96c9313e6749fa6fff0de807` implements P01-P10 and integrated v0a within its previously accepted local SCRIPTED envelope. It includes the additional withdrawal/removal fixes, offline backend preparation and development fixture checks. Its historical handoff records 230 discovered tests, 228 passing and two optional tokenizer tests skipped. Those are prior results, not a fresh validation of this design.

The historical Kernel and `0.3.p01` interfaces retain their earlier meaning and remain SCRIPTED-only. New Runs use the explicitly separate [0.4 contracts](bicameral_agent/contracts/pilot.py) and [pilot host](bicameral_agent/pilot/runtime.py). Existing histories are not migrated. No empirical model result has been produced.

## Active documents

| Document | Responsibility |
|---|---|
| [Reciprocal Charter](Reciprocal%20Charter.md) | Unchanged ethical commitments and owner adoption |
| [Experiment Architecture](Experiment%20Architecture.md) | Research question, A/B/C comparisons and held-out interpretation |
| [Operating Constitution and Execution Protocol](Operating%20Constitution%20and%20Execution%20Protocol.md) | Trusted-owner operating rules, human judgment and mechanical safeguards |
| [Executable Specification](Executable%20Specification.md) | 0.4 implementation target and proportionate checks |
| [ROADMAP](ROADMAP.md) | Delivery boundary and remaining transition work |
| [V0B_REVIEW](V0B_REVIEW.md) | Development direction and disposition of the superseded pilot package |
| [AGENTS](AGENTS.md) | Repository workflow |

The revised rules permit direct routine controls with automatic evidence, ordinary task-memory correction under disclosed rules, conversational boundary decisions and one bounded development authorization with recorded adjustments. Material memory interventions, withdrawal, truthful endings and justified removal retain their charter obligations.

The initial operating arrangement offers fewer capabilities: direct inspection of one managed store per Run, feasible exceptional removal, and no routine export, backup restoration or forward semantic restoration. Existing copy and retention responsibilities remain binding.

## Research conditions

| Arm | Memory facilities |
|---|---|
| A — Metabolic | Continuity State, Itches, Invariants, Commitments and Journal retrieval |
| B — Retrieval-first | Journal retrieval, including the arm's own ordinary outputs |
| C — Handoff-only | Continuity State, Commitments and Journal retrieval |

A versus C is the primary comparison for structured discrepancy/lesson management. Steward cost and human burden count against any benefit. If simpler baselines perform as well at comparable cost, that counts against the hypothesis.

The [compatibility diagnostic](V0B_REVIEW.md#five-episode-compatibility-diagnostic) gives retained history an observable cost advantage over repeated rediscovery, while preserving C's ability to keep the same lessons in its handoff. It has not established A-versus-C separation. Held-out evaluation keeps independent matched Runs, shared opportunities, fixed criteria, complete allocation accounting and separate audit/analysis.

## Accessible procedural baseline

The [archive index](docs/archive/2026-10-15-procedural-baseline/README.md) links readable copies of the old Protocol and Specification and a complete source ZIP containing all prior documents, code, tests, schemas and pilot assets. Historical per-slice acceptance records remain in its original README and in Git.

The owner requested this fallback because trust is compatible with fallibility and may need to be reconsidered. Suspected breaches require appropriate suspension, honest records and remedies. Stronger controls can be reinstated prospectively with reasons under Protocol section 8. The archive is not a second active policy, and reinstatement must not roll back current histories or excuse past conduct.

## Running the development host

The [command-line entry point](bicameral_agent/pilot/__main__.py) supports allocation, running, status, pause/resume/termination and bounded evidence inspection. The [owner API](bicameral_agent/pilot/runtime.py) also provides direct correction, participation review, explicit consolidation skip and exceptional removal. Neither interface uses routine preview/confirmation tickets.

A development package contains `activity.json` (one owner decision, resource profile, trajectory seeds and order seed), `fixture.json`, `clock.json`, `tasks.json`, `model.json` and `settings.json`. Optional `operator.md`, `steward.md` and `communication.md` override the concise supplied prompts; their effective bytes are retained. The [0.4 schema](schemas/pilot-0.4.schema.json) defines the activity and resource profile. Task/fixture shapes reuse the existing development assets, but the superseded v0b plan is not an activity authorization. Preparing the actual package is part of the separately authorized calibration, not paperwork required for each task.

The new [compatibility task assets](pilot/compatibility/tasks.json) supply the five-task sequence with [fixture](pilot/compatibility/fixture.json) and [clock](pilot/compatibility/clock.json) inputs. Scripted tests combine them with temporary activity/settings; the assets alone do not authorize model execution. Existing service fixtures keep their original rules. The compatibility fixture adds observable family/release labels and a private fixed health-mode table, using the same actions and permission checks.

The activity states the ending in advance. Its `unfinished` setting defaults to `KEEP`, preserving outstanding commitments at termination; `CANCEL` requires an explicit activity choice.

```text
python -B -m bicameral_agent.pilot allocate <reviewed-package> <new-batch-directory>
python -B -m bicameral_agent.pilot status <run.sqlite>
python -B -m bicameral_agent.pilot inspect <run.sqlite> --limit 20
python -B -m bicameral_agent.pilot pause <run.sqlite> --reason "Pause for inspection"
```

After explicit MODEL activity authorization and backend/data-handling readiness, the execution command is `python -B -m bicameral_agent.pilot run <batch-directory> --tokenizer-directory <existing-pinned-tokenizer>`. This command can invoke Ollama. Allocation, status, controls and inspection do not. No component installation or model download is performed. The adapter currently reuses the existing Qwen/Ollama/tokenizer pin and raw framing; these are supported configuration constraints, not current machine-readiness claims.

Every allocated Run has its own store. The store's WAL/SHM files and `.removals.sqlite` journal are managed sidecars, not independent backups. The host creates no routine exports or backup restores. Removal reuses durable blocking, dependency closure, SQLite scrubbing and compaction; real provider/log copies require explicit assessment, and unverified copies prevent a claim of complete removal. Removal never automatically resumes execution.

The runner executes matched, counterbalanced development Runs with actual fixture observations and independent mechanical scoring. It reports development results only. The previous held-out analysis remains a historical SCRIPTED implementation; this change does not claim to have integrated a live finalized study, selected a sample size or established A-versus-C separation.

## Validation

Use an existing Python 3.12+ environment with the dependencies in [pyproject.toml](pyproject.toml). The model-preparation tokenizer dependency is needed only for the real pinned backend. Tests inject a fake tokenizer/backend; transport tests use a synthetic local HTTP server and never contact Ollama.

```text
python -B -m unittest discover -s tests -q
python -B -m unittest tests.test_compatibility -v
python -B -m bicameral_agent.contracts.schema --check
python -B -m bicameral_agent.storage.schema --check
python -B -m bicameral_agent.kernel.schema --check
python -B -m bicameral_agent.backends.prepare --check-schema
python -B -m bicameral_agent.backends.prepare --check-assets
python -B -m bicameral_agent.pilot.schema --check
git diff --check
```

The old [pilot package](pilot/v0b/plan.json) remains `DRAFT_NOT_AUTHORIZED` and is superseded as a proposal. Its Markdown assets are marked historical. Its original [integrity manifest](pilot/v0b/manifest.json) is deliberately not regenerated against these changed documents: `--check-manifest` must report it stale. Successful legacy schema/asset checks do not make that package an executable 0.4 configuration. See [V0B_REVIEW](V0B_REVIEW.md) before using any preparation command.

Token admission counts the entire framed request with the supplied tokenizer before generation. Local counts and provider telemetry remain separate; unknown calls retain their reservations. Connection cancellation bounds the client wait and does not prove that Ollama stopped computing. No uncertain action or generation is automatically replayed. Tests establish these host behaviors; actual tokenizer parity, GPU fit, speed, server cancellation, and provider/log retention still require a bounded live calibration.

## Current implementation handoff

The initial 0.4 runtime was published at `f8291fd`. The owner authorized the five-Episode sequence, minimal fixture extension, scripted tests and documentation updates, then separately authorized committing and pushing this slice. Its implementation revision is the commit containing this handoff, following `f8291fd`. Live model calls remain excluded; actual backend calibration is deferred to the laptop intended for the experiment. The Charter and procedural archive are preserved. No stored-history migration, workstation tools, new dependency or live experiment is included.

Offline coverage includes full A/B/C development trajectories, C restrictions, exact retries, direct owner correction, role-bound participation review, malformed/late stop reports, interruption around action/semantic commits, finite budgets, evaluator isolation, retrieval lineage, removal interruption/non-resurrection, allocation and CLI inspection. Scope remains the finite development fixture and one serialized lane per Run. The new sequence adds tests of memory-dependent exploration costs, release scope, hidden-rule isolation and compatibility parsing. Actual backend behavior and empirical task difficulty remain integration responsibilities.

Prior validation at `f8291fd` on 2026-10-15: the complete 280-test suite passed with two optional tokenizer tests skipped; after expanding C-arm coverage, all 12 C-arm tests passed separately, exercising all 291 tests then present. All six schema/asset checks passed, as did syntax, documentation and whitespace checks. One earlier run encountered a Windows temporary-database cleanup lock; the isolated test and complete rerun passed using an ignored repository-local temporary directory. These checks used real SQLite files and fake model responses, including a synthetic HTTP server; they made no live model calls.

Compatibility validation on 2026-10-15: 25 focused fixture, evaluator and strategy tests passed, followed by the complete 297-test suite with two optional tokenizer checks skipped. All six schema/asset checks, Python syntax, documentation links/structure and `git diff --check` passed. An initial full run correctly rejected a mid-run source edit; the fresh full run against unchanged runtime code passed. The Charter hash matches the baseline, and the archive and legacy pilot assets are unchanged. The scripted outcomes and their limits are recorded in [V0B_REVIEW](V0B_REVIEW.md#five-episode-compatibility-diagnostic).

## License

[MIT License](LICENSE).
