# Calibration report

Historical report preserved from README at `c432198`. Statements about readiness, permissions and subsequent work describe that reporting point; they do not authorize execution now. Link destinations were adjusted for relocation. See the [report index](index.md) for chronology and later evidence.

## Second live calibration

The owner authorized a batch-stop fix and one new minimal A/B/C block after publication and passing CI. [The new outcome record](2026-10-15-minimal-d0ec3fd.json) identifies exact execution commit **`d0ec3fdee9cbf669a75e3fa3f5bfde0d3c00d994`**, all effective hashes, per-call accounting and the preserved first calibration. The CLI now checks retained UNKNOWN invocations before and after each Run, including recovered calls and terminal Runs, in addition to pauses and welfare holds. Re-running the command cannot advance past that uncertainty.

The new block kept the first task, model, prompts, seed/order 17 and minimal call/token/action limits; only latency ceilings changed to **360 seconds per call and 4,320 seconds per Run**. The per-call allowance covers the previously observed 105-second cold load, 85-second prompt processing and roughly 139 seconds for a full 2,048-token reply at the one observed output rate, with margin. This was a conservative estimate, not a speed guarantee. The Run ceiling allows twelve full call reservations (8 Operator, 2 Steward, 2 communication). No in-run tuning or replacement occurred.

| Arm | Task / closing calls | Summed call seconds | Outcome |
|---|---:|---:|---|
| A | 8 / 1 | 112.625 | Call limit; semantic/journal retrieval, no fixture action |
| B | 8 / 1 | 104.390 | Call limit; two rejected semantic lookups, then journal retrieval/response, no fixture action |
| C | 8 / 1 | 208.502 | Call limit; repeated object-index retrieval, no fixture action |

All **27 calls returned with known outcomes**; all three optional closing calls were recorded. Calls ranged from 6.875 to 116.219 seconds. Provider usage was 103,078 tokens versus 103,050 locally counted: all 27 input counts matched, while provider output counts were one token higher on 26 calls and two higher on one. All three tasks remained incomplete; no Steward call occurred. The batch-stop fix is supported by offline regressions; no uncertain call triggered it in this block.

The model used semantic/journal retrieval to seek service observations instead of the existing fixture `inspect` action. Its retained CONCERN reports described unavailable evidence and difficulty grounding repairs; no pause or withdrawal report occurred. This is evidence of an instruction/interface usability problem, not an arm-efficacy result. The full package should wait for an offline-validated clarification of that observation route and usable task behavior.

The owner reported that the laptop was overheating. The containment check found all Runs already terminal; `ollama stop` was issued and both `ollama ps` and a later metadata-only check confirmed no resident model. No temperatures were measured and no throttling cause is established. Further live work needs suitable thermal operating limits. That calibration task ended without further model calls or local test suites. Both blocks remain dormant, with original records preserved; the new record schedules owner retention review by 2026-11-14 17:58:59 UTC. The full five-Episode package remains SCRIPTED and excluded.
