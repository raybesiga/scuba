# M5 demo build and rehearsal results

21 September 2026. **M5 technical acceptance is complete:** one-command presentation rebuild, a 2–3 minute storyboard and clean-environment replay pass. Spoken delivery has not been recorded or timed; the presenter must practise it before recording or submission. No publication or submission has occurred.

## Clean checkout evidence

The rehearsal extracted tracked files from commit `9abfd32fc4273df96e4c7ad6b439752a173b542c` into a new temporary checkout. It exported the 19 allowlisted inputs (2,536,042 bytes) from the original saved evidence. No `.env`, raw customer/event tables or prediction upload payloads were copied.

| Check | Observed result |
| --- | --- |
| Runtime | Python 3.14.5; Node 24.13.0; npm 11.6.2; uv 0.11.7; macOS arm64 |
| Python installation | New `.venv`; `uv sync --offline --locked --extra models --extra tabpfn`, explicitly selecting Python 3.14.5 and the existing project cache |
| UI installation | New `node_modules`; `npm ci --offline --ignore-scripts --no-audit --no-fund`; 89 packages installed |
| Python checks | Ruff lint and format pass; all 117 tests pass |
| UI checks | Four tests, TypeScript and Prettier pass |
| First build / replay | 0.242 / 0.222 seconds; both succeed from the separately exported evidence root |
| Byte comparison | HTML, evidence and manifest identical across builds |
| Evidence preservation | Embedded evidence byte-identical to the prior dashboard |
| Negative check | Altered validation evidence rejected before any output directory was created |
| Remote work | No API calls, uploads, new hosted predictions or full benchmark refits |

The installation used existing offline download caches, not empty caches or a different operating system. Python's interpreter binary was already installed; package directories were created afresh. The local machine receipt and step logs are retained in `artifacts/m5-clean-rehearsal.json` and its recorded temporary workspace.

| Output | SHA-256 |
| --- | --- |
| `index.html` | `581a2253ad48e6565f4a2714af87030d4d67b54ec36845432432ef410ca447fe` |
| `evidence.json` | `a738dd7e472f5a15e4f5b9af12777d1f29ac3f636e446b66f5499c32f310b5f2` |
| `manifest.json` | `2744611df8eac61678821c99739fa3293cde7793037d1e9f70f5b2ba87ccb68d` |

## What the rehearsal found

The initial clean build failed because the report builder created its output directory without first creating the missing `artifacts` parent. The working checkout had hidden this assumption. The builder now creates parent directories and still refuses to overwrite an existing report. Its regression test fails against the previous builder and passes after the fix.

The default uv cache lacked the pinned CatBoost wheel. The existing project cache at `/private/tmp/scuba-uv-cache` supplied it offline. A fresh directory also selected Node 25 through the shell; the final rehearsal explicitly selected Node 24.13.0. These setup requirements are recorded in the [rebuild procedure](DEMO_REBUILD.md).

## Browser route and delivery budget

The served preview was updated with the clean checkout's output. Browser inspection verified the scenario and cohort counts, paired uncertainty statement, Top 5% and Top 10% controls, hosted checkpoint/consumption disclosures, and return to Overview.

The navigation check took 38.21 seconds, including automation/inspection overhead and one corrected ambiguous locator for a count shown twice. This is not a spoken demo timing. The [storyboard](DEMO_STORYBOARD.md) contains 318 spoken words: approximately 127–136 seconds at 150–140 words per minute. Adding the observed navigation time gives a planning estimate of 2:45–2:54; target 2:50. The presenter should shorten pauses if spoken rehearsal exceeds three minutes.

## Remaining delivery checks

- Practise the spoken script and record the actual duration.
- Confirm the organiser's current submission format, rules, deadline and timezone before delivery.
- Review the exact materials intended for sharing. Publication, pushing and submission require explicit approval.

The clean replay checks saved results and presentation integrity. It does not independently attest hosted checkpoint bytes, reproduce historical server behaviour, measure actual token charges or demonstrate real-customer benefit.
