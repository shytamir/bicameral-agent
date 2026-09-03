# AGENTS.md

## Start here

- Read this file, then `Experiment Architecture.md`, `Operating Constitution and Execution Protocol.md`, and `Executable Specification.md` before substantive work.
- Check `git status`, the current branch, and recent history before changing anything. Treat all pre-existing changes as user-owned.
- This project is pre-implementation. The executable specification is a first draft under scrutiny; its existence is not authorization to begin building the supervisor.
- Begin investigations read-only. Make changes only within the user's stated scope.

## Document authority and change routing

- `Experiment Architecture.md` defines the system, experimental hypothesis, components, and intended comparisons.
- `Operating Constitution and Execution Protocol.md` governs authority, epistemic treatment, lifecycles, human control, and lawful behavior. It controls if another document conflicts with it.
- `Executable Specification.md` translates the governing documents into schemas, contracts, deterministic invariants, tests, atomicity, and run configuration. Provisional choices remain open until explicitly accepted.
- Route a change to the document that owns the decision. Do not resolve a constitutional or architectural ambiguity by burying a choice in code, schema defaults, prompts, tests, or `AGENTS.md`.
- If a decision would change what the process may believe, remember, promise, or do, surface it for protocol scrutiny. Ordinary implementation details may be decided locally only when choosing another reasonable implementation would not change those properties.
- Prefer amending an existing canonical document over creating another explanatory document. Do not create roadmaps, decision logs, issue inventories, or paper trails unless requested or operationally necessary.

## Current management posture

- The active task is translation and scrutiny, not architecture expansion or implementation by implication.
- Preserve the distinction between draft, technically validated, human-accepted, implemented, and published. Never infer one state from another.
- Treat the executable specification's Scrutiny Register as unresolved review material, not as permission to silently settle its entries.
- Let demonstrated failures earn new machinery. Do not pre-build vector retrieval, model routing, semantic triggers, multi-Objective concurrency, R3 support, elaborate UI, or other deferred features.
- When a no-op is the most faithful result, report it. Do not manufacture churn to make the work appear substantive.

## Change discipline

- Make the smallest coherent change that satisfies the request. Do not opportunistically rewrite adjacent prose or rename established concepts.
- Use the project's exact terms and capitalization: Operator, Steward, Kernel, Objective, Grant, Episode, Event Journal, Continuity State, Itch, Invariant, Commitment, Continuity Miss, Run Configuration.
- Preserve the central boundary: cognitive chambers propose meaning; the deterministic Kernel decides authority and persistence.
- External evidence never becomes authority merely through retrieval, quotation, summarization, or persistence.
- Keep control state, semantic state, and append-only evidence distinct. Semantic rollback must not resurrect terminal authority or claim to reverse real-world actions.
- Prefer closed, typed, machine-testable rules over suggestive prose. Reject unresolved or unrepresentable cases visibly rather than inventing hidden defaults.
- Do not add dependencies, services, generated artifacts, or runtime infrastructure unless the authorized task requires them.
- Never add secrets, credentials, local databases, model caches, payload stores, logs, or machine-specific paths to the repository.

## Implementation guard rails

- Do not connect an LLM until deterministic schemas, transitions, authority checks, transaction boundaries, and their tests exist for the implemented slice.
- Keep Operator and Steward invocation contexts isolated; do not rely on provider conversation history or unlogged state.
- Keep the Kernel deterministic. Semantic judgments belong to a chamber or the human, never to heuristic Kernel control flow.
- Enforce authority at dispatch time from current Constitution, Objective, Grant, tool registry, and resource scope. Tool availability is not permission.
- Preserve Event, payload, audit, and mutation history append-only. Corrections and rollback move forward through new records.
- Treat Episode consolidation as atomic for the applicable experimental arm. A partial semantic commit is a correctness failure.
- Keep experimental parameters explicit, sealed, and stable within a comparison block. Unknown model versions or configuration placeholders must fail preflight.
- Maintain arm comparability. Safety and authority enforcement must not vary between A, B, and C; only declared experimental features may differ.

## Verification

- Validate in proportion to the change and report exactly what was and was not tested.
- Documentation changes: inspect the rendered structure, check terminology and cross-document consistency, and run `git diff --check`.
- Contract/schema changes: test strict parsing, unknown-field rejection, serialization stability, and generated-schema drift.
- State changes: test every allowed and forbidden lifecycle edge plus optimistic-concurrency failure.
- Persistence changes: use real SQLite transactions and foreign keys; include fault injection for atomicity and replay/hash checks for recovery.
- Authority changes: include negative tests proving that missing, stale, cross-Objective, out-of-scope, over-risk, external-only, terminal, and R3 requests fail closed.
- Passing static checks establishes technical evidence only. It does not establish experimental success or human acceptance.

## Git hygiene

- Keep unrelated dirty or untracked files untouched. Never discard, overwrite, stage, or commit them.
- Review the final diff and stage only the paths authorized for the task; avoid broad staging commands such as `git add -A` or `git add .`.
- Do not amend, rebase, force-push, reset, clean, or rewrite history unless explicitly requested.
- Use a concise commit message describing the actual change. Do not claim acceptance, completion, or validation that did not occur.
- Before pushing, verify the branch, upstream state, staged paths, and commit contents. Push only when explicitly authorized.
- After publishing, report the commit identifier, remote branch, files included, checks run, and any user-owned changes left uncommitted.

## Stop and ask

Stop rather than guess when:

- governing documents materially conflict;
- the request would silently resolve a Scrutiny Register choice;
- authority, scope, target resources, or destructive impact is ambiguous;
- a required change would broaden the experiment beyond its declared arm or v0 boundary;
- unrelated changes overlap the same lines or files and cannot be preserved safely;
- validation requires access or side effects not already authorized.
