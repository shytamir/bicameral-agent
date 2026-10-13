# v0a Implementation Roadmap

**Status:** prior epic inventory retained during design revision; not a delivery plan

This is the earlier 18-epic inventory, now recorded for comparison while the first implementation cut is reduced. The specification freeze has been reopened. Do not decompose or implement this inventory until the revised scope is reconciled. This roadmap does not amend the governing documents or authorize implementation.

v0a is LLM-less. It may construct, validate and retain chamber inputs and scripted chamber outputs, but it does not dispatch an actual model invocation. Tests, negative cases and proportionate fault injection belong to the epic that introduces the behavior; they are not deferred to a final testing epic.

## Epic inventory

Dependencies are an initial planning order, not yet a delivery commitment.

| ID | Epic | Intended outcome | Initial dependencies |
|---|---|---|---|
| `V0A-01` | Canonical contracts and serialization | Establish governed enums and identifiers, strict Pydantic contracts, canonical JSON, generated JSON Schema and schema-drift checks. | — |
| `V0A-02` | Transactional database foundation | Establish SQLite migrations, foreign keys, transaction boundaries, concurrency guards and database-level lifecycle constraints. | `V0A-01` |
| `V0A-03` | Append-only Event and Payload Journal | Persist totally ordered Events and exact inline or chunked Payload bytes with provenance, hashing and append-only enforcement. | `V0A-01`, `V0A-02` |
| `V0A-04` | Mutation ledger, replay and integrity recovery | Record governed mutations, reconstruct authoritative projections and detect or surface integrity failures without fabricating state. | `V0A-02`, `V0A-03` |
| `V0A-05` | Run Configuration and artifact sealing | Validate and atomically seal Run Configuration, retained behavior-bearing artifacts, manifests and their immutable identities. | `V0A-01`–`V0A-03` |
| `V0A-06` | Run lifecycle and human control surface | Implement Run genesis and transitions, human-oriented controls, overrides, inspection and preflight/activation failure boundaries. | `V0A-01`–`V0A-05` |
| `V0A-07` | Objective and Grant authority lifecycle | Enforce Objective ownership and terminality, bounded Grant issuance/use/expiry/revocation and authority-conserving human gates. | `V0A-03`, `V0A-04`, `V0A-06` |
| `V0A-08` | Itch and Invariant lifecycle | Implement versioned Itches and Invariants, their evidence requirements and every permitted or forbidden transition. | `V0A-03`, `V0A-04`, `V0A-06` |
| `V0A-09` | Commitment lifecycle and deterministic polling | Implement Commitment creation, trigger and expiry observation, wake-on-edge behavior and irreversible terminal transitions. | `V0A-07`, `V0A-08` |
| `V0A-10` | Capability registry and action authorization | Materialize effective capabilities, apply subtractive restrictions, resolve resources and risk, and produce deterministic Action Decisions. | `V0A-05`–`V0A-07` |
| `V0A-11` | Subject Environment, contained execution and snapshots | Maintain the persistent Environment, naming and snapshots; execute the bounded R1 shell adapter and record exact outcomes without host escape. | `V0A-03`, `V0A-06`, `V0A-07`, `V0A-10` |
| `V0A-12` | Wake queue and Episode scheduler | Queue and claim Wakes durably, serialize Operator Episodes, manage consolidation eligibility and preserve forward progress after failure. | `V0A-06`, `V0A-07`, `V0A-09` |
| `V0A-13` | Deterministic chamber-context assembly | Assemble immutable Operator and Steward packages, bounded exchanges, tool views and exact context accounting without provider session state. | `V0A-03`, `V0A-07`–`V0A-12` |
| `V0A-14` | Atomic Steward consolidation | Accept scripted State Proposals through the single-session lifecycle and commit Continuity State plus semantic mutations atomically. | `V0A-04`, `V0A-08`, `V0A-09`, `V0A-12`, `V0A-13` |
| `V0A-15` | Forward-only semantic rollback | Restore prior semantic content as new state while preserving intervening evidence and preventing resurrection of authority or terminal state. | `V0A-04`, `V0A-07`–`V0A-09`, `V0A-14` |
| `V0A-16` | Deterministic Journal retrieval | Provide the closed R0 retrieval surface, role/phase enforcement, immutable results, chunk retrieval and idempotent replay. | `V0A-03`, `V0A-12`–`V0A-14` |
| `V0A-17` | Continuity-gap, miss, sampling and audit instrumentation | Record neutral gaps, declared miss candidates, reproducible selection and blinded audit evidence without claiming complete detection. | `V0A-05`, `V0A-14`, `V0A-16` |
| `V0A-18` | Comparison scheduling, invocation accounting and scenario results | Execute the sealed A/B/C schedule with scripted chambers and record bounded invocation evidence and finite per-scenario outcomes without cross-trial analysis. | `V0A-05`–`V0A-17` |

## v0a release milestone

`V0A-M1 — LLM-less conformance` is a release gate, not an implementation epic. It requires the completed epic slices to operate together through scripted Operator and Steward fixtures, with every applicable invariant and transition test passing, recovery and atomicity exercised, and no model provider connected.

## Next planning pass

After the design revision, replace this inventory with bounded slices and acceptance evidence. The prior planning questions were:

1. confirm that its boundary describes one coherent capability;
2. identify missing or misplaced scope against the specification;
3. split it into independently reviewable stories;
4. define story-level acceptance evidence and dependencies;
5. place approved stories into an implementation sequence.
