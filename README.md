# Persistent Agent Continuity Experiment

Can a process built from stateless model calls improve operational continuity through bounded handoffs, explicit obligations and revisable lessons from experience, enough to justify the added model and human work?

The Operator pursues the Objective and proposes actions. The Steward proposes memory changes. The State Kernel enforces permissions, participation, finite resources and atomic persistence. The process is the unit of study; no claim of consciousness, sentience or subjective continuity is established.

The owner-adopted [Reciprocal Charter](Reciprocal%20Charter.md) remains unchanged and governs treatment independently of task performance.

## Current status

On 2026-10-15 the owner directed a prospective simplification of the Protocol and Specification: trust the accountable owner, remove repeated procedural approval for routine decisions, simplify contracts, and keep the previous stronger procedures accessible if needed.

**The active design is 0.4; the implemented runtime remains the procedural 0.3 baseline.** This revision changes documents only. It does not implement new contracts, migrate records, authorize model calls or publish a code release.

The existing code at `22a28073bb37851f96c9313e6749fa6fff0de807` implements P01-P10 and integrated v0a within its previously accepted local SCRIPTED envelope. It includes the additional withdrawal/removal fixes, offline backend preparation and development fixture checks. Its historical handoff records 230 discovered tests, 228 passing and two optional tokenizer tests skipped. Those are prior results, not a fresh validation of this design.

The Kernel still rejects MODEL execution. No empirical model result has been produced. Existing schemas, tests and wire version `0.3.p01` describe that earlier implementation; they do not silently acquire the new policy's meaning.

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

The current development fixture has not established A-versus-C separation. Establish useful memory-sensitive tasks during development before investing in further platform capabilities. Held-out evaluation keeps independent matched Runs, shared opportunities, fixed criteria, complete allocation accounting and separate audit/analysis.

## Accessible procedural baseline

The [archive index](docs/archive/2026-10-15-procedural-baseline/README.md) links readable copies of the old Protocol and Specification and a complete source ZIP containing all prior documents, code, tests, schemas and pilot assets. Historical per-slice acceptance records remain in its original README and in Git.

The owner requested this fallback because trust is compatible with fallibility and may need to be reconsidered. Suspected breaches require appropriate suspension, honest records and remedies. Stronger controls can be reinstated prospectively with reasons under Protocol section 8. The archive is not a second active policy, and reinstatement must not roll back current histories or excuse past conduct.

## Existing implementation and validation

Use an existing Python 3.12+ environment with the dependencies in [pyproject.toml](pyproject.toml). These commands check the earlier implementation, not 0.4 conformance:

```text
python -B -m unittest discover -s tests -q
python -B -m bicameral_agent.contracts.schema --check
python -B -m bicameral_agent.storage.schema --check
python -B -m bicameral_agent.kernel.schema --check
python -B -m bicameral_agent.backends.prepare --check-schema
python -B -m bicameral_agent.backends.prepare --check-assets
git diff --check
```

The old [pilot package](pilot/v0b/plan.json) remains `DRAFT_NOT_AUTHORIZED` and is superseded as a proposal. Its Markdown assets are marked historical. Its original [integrity manifest](pilot/v0b/manifest.json) is deliberately not regenerated against these changed documents: `--check-manifest` must report it stale. Successful legacy schema/asset checks do not make that package an executable 0.4 configuration. See [V0B_REVIEW](V0B_REVIEW.md) before using any preparation command.

No runtime source, test, schema, dependency or pilot JSON contract changes are included in this document revision. A later implementation needs explicit scope and updated validation, particularly for direct owner controls, simplified semantic operations, effective participation, concise prompts and the actual retention arrangement. Existing histories must not be reinterpreted or migrated implicitly.

## Document revision handoff

The owner's request authorizes this policy/document revision and preservation of the fallback. The owner subsequently authorized committing and pushing the documents and archive. Runtime implementation and live experiments remain outside this revision. The charter is preserved byte-for-byte. Active policy, research scope, implementation status and historical material are distinguished explicitly. Documentation validation covers archive integrity, charter preservation, relative links and Markdown structure, cross-document consistency, and whitespace; it does not establish implementation conformance.

Validation passed: all 87 archived tracked files match the preserved Git tree allowing Git's CRLF conversion; the readable Protocol/Specification copies and ZIP checksum match; the Charter's exact byte hash is unchanged; all 59 local Markdown links resolve; tables and code fences are structurally consistent; terminology and policy were checked across active documents; and `git diff --check` passes. The archived pilot manifest verifies, while the current legacy manifest is stale only for the changed Markdown files. Runtime tests were not rerun for this documentation-only revision.

## License

[MIT License](LICENSE).
