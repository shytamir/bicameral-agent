# Procedural baseline archive

**Preserved:** 2026-10-15, at the owner's request, before revising the active Protocol and Specification.

**Source revision:** `22a28073bb37851f96c9313e6749fa6fff0de807` (`main` at capture).

This is the complete earlier 0.3 baseline, including its stronger confirmation, intervention-review, boundary-discussion, retention and restoration procedures. It is retained because the owner considers trust compatible with fallibility and wants these safeguards available if needed.

## Read or recover the baseline

- [Previous Protocol — readable text](Protocol.txt)
- [Previous Executable Specification — readable text](Specification.txt)
- [Complete source snapshot](source-22a2807.zip): all tracked documents, code, tests, schemas, pilot assets and historical handoffs at the source revision.

The text copies preserve the pre-edit working-tree document bytes. The ZIP preserves the tracked Git tree; Git line-ending normalization can differ from the text copies. Extract the ZIP into a separate directory to browse the old Markdown documents with their original relative links intact. Its original README contains the per-slice acceptance history, and V0B_REVIEW contains the historical preparation measurements and review.

ZIP SHA-256: `c9dc359e703cfbd98423153f36da986cfcce9b1093b2605b4d59a4355f9b742a`.

## Laptop checkout before setup

At the owner's request, [the laptop's pre-update source snapshot](source-5db8834.zip) preserves revision `5db8834e1e54444efb049335deab6bc52b231a46` alongside the procedural baseline. Its working tree was clean before the fast-forward to `6fcc0c5`; there were no uncommitted tracked or untracked changes to archive. This revision is an ancestor of `22a2807`, so its work was already included in the later baseline with subsequent fixes. The additional ZIP preserves the exact older tree without changing the existing archive or branch history. Ignored local data and model/tokenizer files remain in place and are excluded.

Pre-update ZIP SHA-256: `62b82a2a765d3bd1c02504f533aed7a349f454a4a000097bb7d4504997c52dee`. Every file in this additional snapshot matches its Git blob byte-for-byte.

## Archived v0b package and review

Documentation consolidation on 2026-10-15 moved the superseded package out of the active `pilot` directory. The [draft plan](pilot/v0b/plan.json), [model pin](pilot/v0b/model.json), [settings](pilot/v0b/settings.json), [fixture](pilot/v0b/fixture.json), [clock](pilot/v0b/clock.json), [tasks](pilot/v0b/tasks.json), [Operator prompt](pilot/v0b/operator.md), [Steward prompt](pilot/v0b/steward.md), [communication prompt](pilot/v0b/communication.md), [notices](pilot/v0b/notices.md) and [original manifest](pilot/v0b/manifest.json) are historical fixtures only. JSON files, including the manifest, retain their exact pre-move bytes; Markdown banner links were adjusted for the new location.

The [archived transition note](V0B_REVIEW.md) preserves the last root-level `V0B_REVIEW.md` from `cc473f3`, with an archive notice and relocated links. That transitional file mixed old-package disposition with new development guidance. Its current design now lives in [Architecture section 6.1](../../../Experiment%20Architecture.md#61-five-episode-compatibility-diagnostic), its results and setup handoff in the [active README](../../../README.md), and remaining work in the [Roadmap](../../../ROADMAP.md). The original 0.3 review and acceptance history remain inside `source-22a2807.zip`; the [published setup handoff at cc473f3](https://github.com/shytamir/bicameral-agent/blob/cc473f3e60607500a6ec03ef60025cce540f32d9/README.md#current-implementation-handoff) retains the later chronology.

The package still says `DRAFT_NOT_AUTHORIZED` and `CALIBRATION_REQUIRED`; it is not an executable 0.4 activity. Existing legacy tests and `python -B -m bicameral_agent.backends.prepare --check-assets` now read it here. The preparation command still uses old response contracts and combines its historical prompts with the current Charter/Protocol; it is not the 0.4 calibration path. It cannot dispatch model generation. Its schema/asset checks establish legacy shape consistency only.

The original manifest records its original paths and source hashes. `--check-manifest` must continue to report it stale against the revised repository; do not regenerate it to imply renewed review or authorization. Use the exact source ZIP for historical reconstruction. Current calibration uses the separate [0.4 activity](../../../pilot/calibration/activity.json).

## Authority and possible reinstatement

The [current Charter](../../../Reciprocal%20Charter.md) is unchanged. The [current Protocol](../../../Operating%20Constitution%20and%20Execution%20Protocol.md) and [Specification](../../../Executable%20Specification.md) own the active design. Archived rules do not silently override them.

If a suspected breach, repeated omission or unsafe intervention shows the ordinary safeguards inadequate, record the concern, suspend affected optional work where appropriate, consider remedies and examine which archived controls would help. Seek another human's assessment where practicable. The owner can also request stronger controls before a breach occurs.

Reinstatement requires an explicit prospective decision stating which controls apply and why, with consideration of expressed process concerns where meaningful. Preserve the original incident evidence. The archive does not excuse earlier conduct, authorize model calls, automatically switch the runtime or permit reverting a current process database to an earlier state.

Use the archived source as a reference or isolated code checkout. Reintroduce selected mechanisms through an authorized change and validate them against the then-current runtime and histories. No automated trust score or new certification procedure is implied.

## Snapshot limits

The ZIP contains tracked repository files only. It contains no live process databases, credentials, model cache or private workstation state. Its historical implementation acceptance concerns the documented SCRIPTED/offline envelopes; it is not evidence of successful model experiments or proof of welfare.
