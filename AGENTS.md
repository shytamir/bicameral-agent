# AGENTS.md

## Authority

- Read the repository documents relevant to the task before making substantive changes.
- This file governs agent workflow only. It is subordinate to the project's Architecture, Operating Constitution and Execution Protocol, and Executable Specification.
- Do not use `AGENTS.md` to record project status, repeat management state, or establish product policy.
- If documents conflict, follow the more authoritative project document and surface the conflict. Never settle it silently in code, prompts, tests, defaults, or this file.

## Working discipline

- Begin read-only: inspect `git status`, the current branch, recent history, and the exact files in scope.
- Treat existing tracked and untracked changes as user-owned. Preserve them unless the user explicitly includes them in the task.
- Make the smallest coherent change that satisfies the request. Avoid opportunistic cleanup, adjacent rewrites, speculative features, and new documents that were not requested.
- Use established project terminology consistently. Do not rename governed concepts casually.
- Do not add dependencies, services, generated artifacts, runtime infrastructure, or machine-specific configuration without explicit need and authorization.
- Never commit secrets, credentials, local databases, payloads, logs, model caches, or private machine paths.
- Repository work does not authorize live experiments, external writes, workstation changes, or broader machine inspection.

## Implementation guard rails

- Implement only an authorized slice; a specification or plan is not by itself implementation authorization.
- Do not invent rules that alter what the process may believe, remember, promise, or do. Escalate such choices to the governing document.
- Keep policy-bearing behavior explicit and testable. Prefer typed contracts, closed transitions, explicit configuration, and visible failure over heuristic defaults.
- Preserve the documented separation between cognitive proposals and deterministic authority enforcement.
- Preserve append-only evidence, provenance, atomic state transitions, and forward-moving recovery semantics wherever the implemented slice touches them.
- Do not connect an LLM before the deterministic contracts and invariants required by that slice have executable tests.

## Verification

- Validate in proportion to risk and report exactly what was and was not tested.
- Documentation changes: check terminology, links, cross-document consistency, rendered structure where relevant, and `git diff --check`.
- Contract or schema changes: test strict parsing, unknown-field rejection, serialization stability, and schema-generation drift.
- State or persistence changes: use real database constraints and transactions; test allowed and forbidden transitions, failure atomicity, and recovery.
- Authority changes: include negative tests for absent, stale, terminal, cross-scope, over-risk, external-only, and prohibited authorization paths.
- Static validation is technical evidence, not proof of experimental success or human acceptance.

## Git hygiene

- Review the final diff and stage only authorized paths. Do not use broad staging when unrelated changes exist.
- Do not discard changes, clean the tree, amend, rebase, reset, force-push, or rewrite history unless explicitly requested.
- Use a concise commit message that describes the actual change without overstating acceptance or validation.
- Before pushing, verify the branch, upstream state, staged paths, and commit contents. Push only when explicitly authorized.
- After publishing, report the commit, remote branch, included files, checks run, and remaining user-owned changes.

## Stop conditions

Stop and ask when scope or authority is materially ambiguous, governing documents conflict, destructive impact is unclear, unrelated edits overlap the required lines, or validation needs access or side effects not already authorized.
