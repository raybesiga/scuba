# M3 integration evidence

**Status: complete for the primary hosted integration — 21 September 2026.** The approved prediction-only continuation captured the exact server checkpoint; a source-backed alias-resolution fix enabled offline acceptance of that response. Primary validation average precision is **0.373397**, log loss **0.274317** and Brier score **0.083117**. This is hosted Plus requested with a server-reported v3.5 checkpoint, not a local base run or an attestation of remote weight bytes. Three separately approved predictions have now been made; the first two remain unverified. No further paid prediction was needed for the fix. The main test cohort is untouched. See [checkpoint resolution](M3_CHECKPOINT_RESOLUTION.md) for the diagnosis, source pins and acceptance boundary.

## Implemented and verified

The `tabpfn-preflight` command prepares a deterministic plan without loading credentials or using the network. `--online` explicitly enables limits and dimension/settings-based estimate requests only. `tabpfn-run` requires an approved plan, `--allow-upload` and a positive `--max-estimated-tokens` ceiling; it reconstructs the payloads, rejects changed plans and refreshes limits/estimates before uploading. Existing output directories cannot be overwritten.

The REST adapter follows the current JSON upload/fit/predict contract and returns dormancy probabilities. It preserves raw categorical strings and missing numeric features. It checks all published row/cell/class/byte-size/row-pair limits; separates API authentication from signed storage uploads; handles duplicate uploads; checks probability shape, bounds, sums and returned model settings; and records sanitised errors without automatically retrying. Fit/predict requests use a 330-second elapsed-time guard plus bounded reads; a read in progress can extend past the elapsed guard by at most its 30-second read timeout. Thinking requests specify medium effort, log loss and a 300-second server fit budget.

Local `.env` support is explicit. The environment takes precedence; the loader does not search parent directories, interpolate other variables or print values. `.env` is ignored by Git and the tracked `.env.example` contains an empty `TABPFN_TOKEN` placeholder. The created local `.env` has owner-only file permissions. The local key is configured and authenticated successfully; its value is never included in evidence.

## Approved primary run

| Item | Prepared value |
| --- | --- |
| Route | REST; hosted TabPFN-3.5-Plus, separately labelled from base |
| Requested selector | `v3.5_default` |
| Settings | 8 estimators; seed 3501; `fit_preprocessors`; no local tuning/calibration |
| Frozen input | M1 generator seed 3501; split seed 3501 |
| Training | 22,183 snapshots, 8,405 customers, 2,399 positive outcomes |
| Validation | 2,407 snapshots/customers, 269 positive outcomes |
| Training feature payload | 2,704,895 bytes; 11 predictors |
| Training label payload | 44,378 bytes; `dormant_30d` only |
| Validation feature payload | 291,315 bytes; the same 11 predictors |
| Total approved upload | 3,040,588 bytes, entirely synthetic; uploaded on the second attempt |
| Excluded from upload | Customer IDs, dates, archetypes, activity/provenance metadata, validation labels and the main test cohort |
| Token estimate | 10,000 tokens from live preflight on 21 September 2026; pricing version `quota_v3` |
| Actual tokens | Unknown for the three separately approved prediction requests; metadata preflight is free. Published prediction-response schema omits per-operation charges |
| Plan SHA-256 | `038e27c7de8105869fb08735c7adb9c584f76f5f517df5d1c881f3108b44e532` |

The local plan is `artifacts/m3-plus-preflight/plan.json`. A companion `row_provenance.csv` retains the synthetic marker and snapshot identity for each of the 24,590 training/validation rows; it is never uploaded. Original M1 rows and any future saved predictions retain their synthetic flags. Payloads are model-input views of those marked rows, not new source data.

A matching plan and row map were rebuilt byte for byte using a fresh Python 3.14.5 environment installed offline from the uv cache. Full-size local plans also exist for primary Fast/Thinking and sensitivity-seed Plus; this does not approve additional uploads or runs.

| Plan | SHA-256 |
| --- | --- |
| Fast / 3501 | `71b40f183c0c56b08fbbc7f3393cbe1908095b91520b7cd00e1e97f93da93481` |
| Thinking / 3501 | `05a4dc5ec810d81d557ff5002de5ecdc820fd400b06eeae11422c7dd7b625a11` |
| Plus / 3502 | `18c5f93c2636b4ee788ee1f43f331884ada293c34bb3f738d7db4dbe5bb3d692` |
| Plus / 3503 | `8cfeb8dda35b030a0d90dfff710649af53d863f4715c637c796ad9dc8fdfba1a` |

## Authenticated metadata preflight — 21 September 2026

`artifacts/m3-plus-online-preflight/manifest.json` records `live_metadata_only` evidence and `awaiting_upload_and_budget_approval` status for the same primary plan hash. The authenticated limits request took 1.038 seconds and the dimension/settings estimate took 0.510 seconds. Both succeeded; zero rows were uploaded and no fit or prediction was requested.

The live limits permit 1,000,000 training rows, 1,000,000 prediction rows, 200,000,000 cells in either table, 20,000 columns, 160 classes, 250,000,000,000 train/prediction row pairs and 5,368,709,120 bytes per dataset. The primary plan passes every limit. These are observed account/service limits, not a model-quality claim or a guarantee of future availability.

The service estimated 10,000 tokens for one `v3.5` prediction with 22,183 training rows, 2,407 validation rows, 11 raw columns and 8 estimators, using pricing version `quota_v3`. Standard fit and uploads carry no separate token charge under the documented contract. The user approved a ceiling of 10,000 estimated tokens; execution rechecked the estimate before upload. Any future approved execution will stop before upload if its fresh estimate exceeds its ceiling. This ceiling cannot guarantee actual billing. No currency cost or available account balance is inferred from the estimate.

## Approved execution and failure evidence — 21 September 2026

The user explicitly approved the primary Plus upload and 10,000-token estimate ceiling. Both attempts used the exact approved plan and frozen inputs. No other variant, sensitivity seed or test cohort was sent.

1. `artifacts/m3-plus-seed-3501-live`, source commit `e761057`: preflight and upload preparation succeeded, but the adapter rejected a required GCS `Host` header. No payload upload, fit or prediction occurred. A metadata-only diagnostic confirmed `storage.googleapis.com` and the required header names without exposing signed URLs or header values. Commit `3b577fa` permits `Host` only when it exactly matches the validated storage URL authority. Regression tests reject conflicting hosts, ports and duplicate Host headers; the valid-header test fails against the old transport.
2. `artifacts/m3-plus-seed-3501-live-verified`, source commit `3b577fa`: all three payload uploads and standard fit succeeded. Exactly one prediction request returned HTTP/JSON success, then local validation raised `prediction_contract`. Despite its prospectively chosen directory name, this is a **failed live attempt**, not verified model evidence. Its manifest says `status=failed`, `evidence=live_attempt`, `billing_uncertain=true`. The original adapter did not retain the rejected response or individual check outcomes; the precise mismatch cannot be recovered from this attempt. No retry followed the billable request.

The second attempt recorded 3.181 s for training-feature upload, 0.536 s for label upload, 3.968 s for fit, 1.290 s for validation-feature upload and 4.846 s for prediction; all recorded HTTP stages total 15.836 s. These are one-attempt transport measurements, not a controlled model speed comparison or a successful scoring result.

| Attempt | Manifest SHA-256 |
| --- | --- |
| Before upload-header correction | `1cfe6223e6056280efc4aa01f798c4ab7640867f784506b1692175d39707fa69` |
| Prediction contract failure | `f1af66fadf9969fd4f497664ad73e8b9ff0e2c4e8dd5cd7ddc33f6948cd7df05` |

`artifacts/m3-live-attempt-verification.json` independently reconciles plan/input hashes, source hashes against each run's commit, row provenance and the absence of accepted predictions/metrics. Historical manifests are unchanged.

Commit `345af7a` introduced diagnostics without weakening acceptance checks. Failed runs retain the fresh estimate and fitted/upload resource identifiers. Rejected prediction responses retain only per-field pass/fail and presence checks, plus a probability matrix if it independently passes shape, finite-value, bounds and sum checks. This separate `unverified_response.json` is marked unverified and synthetic, bound to the plan hash, and is never scored automatically. Arbitrary remote strings and raw error bodies are excluded. This improvement cannot restore the discarded live response or establish its exact failure cause.

## Additional approved attempt — model identity isolated

After a second explicit approval for one additional prediction with the same 10,000-token estimate ceiling, `artifacts/m3-plus-seed-3501-attempt-3` ran using source commit `d139756`. A fresh estimate was again 10,000 tokens (`quota_v3`). It uploaded the same approved 3,040,588 synthetic bytes, fitted and issued exactly one prediction request. All recorded HTTP stages total 22.335 s; prediction took 5.252 s. There were no subsequent billable requests.

The response passed probability shape, finite values, bounds and sums; raw dimensions (2,407 rows, 11 columns); classification task; package-version format; class-order convention; 8 estimators; seed 3501; and `fit_preprocessors`. Only exact equality of the returned `model_path` to the requested alias `v3.5_default` failed. The 2,407 two-class probability rows are preserved in `unverified_response.json`, bound to the approved plan and local synthetic row provenance. They have not been scored or promoted to accepted predictions.

The diagnostic version used here recorded the identifier mismatch and field presence, but omitted the returned identifier value. Therefore this attempt does not establish which checkpoint was returned. The official SDK 0.6.0 source (`tabpfn_client/estimator.py`, default-model-name declaration) explains that version aliases resolve to a server-selected checkpoint. An alias/checkpoint difference is a plausible explanation, not a verified mapping for this response. The [model selection guide](https://docs.priorlabs.ai/models/selecting-model-version) documents `v3.5_default` for Plus but does not establish this response's identity. Do not replace strict verification with a broad family-name match or silently relabel these probabilities as verified Plus results.

Commit `ffaf381` initially retained recognisable aliases and checkpoint filenames. The subsequent offline work documented below broadens capture to sanitised paths and URI forms with explicit type, redaction and omission records. Acceptance checks are unchanged. This correction cannot recover the identifier omitted from the saved response. The prediction-only diagnostic playbook below now defines the next bounded experiment. Acceptance still requires a defensible identity check; no additional run is authorised by the previous one-attempt approval.

| Evidence | SHA-256 |
| --- | --- |
| Attempt 3 manifest | `faff3c45c1bb40099743288f85672149357e7b8cd260e98fae4dff9925ce307b` |
| Preserved unverified response | `fba4f5cc260867683ef6bea2d040b7d1dd4fe69dcc41bf454c4648b2a68e5884` |

`artifacts/m3-attempt-3-verification.json` independently checks the probability matrix, approved plan/input/source hashes, synthetic row provenance, single prediction request and absence of accepted scores. The two potentially charged predictions each had a 10,000-token estimate ceiling; their estimates total 20,000 tokens, which is neither measured usage nor a guaranteed billing cap.

## Verification boundary

`make check` passes Ruff lint/format checks and all 91 current tests in the project environment and isolated staged snapshots. The preceding 65-test suite also passed in a fresh offline-installed environment; the expanded 91-test suite has not been rerun there. Each atomic implementation commit passed its applicable checks from an isolated staged snapshot. Tests use first-principles synthetic fixtures and `httpx.MockTransport`; mocked execution is labelled `offline_mock`, never `live_verified`.

Coverage includes secret precedence/absence and error redaction; no credential/network access in offline planning; allowlisted payloads and row provenance; exact plan/payload reconciliation; every published model limit; estimate/request agreement and estimate-budget rejection; full Plus/Fast/Thinking command flows; HTTP 401/403/422/429/500, rate versus quota categories and timeouts; duplicate-upload reuse; unsafe or expired signed-URL rejection; API-token isolation; class/probability/configuration checks; explicit failure artifacts, quarantined diagnostic evidence and no accepted result file after a failed prediction.

`artifacts/m3-verification.json` records the local plan checks and replay evidence. Dependency lock, source hashes and runtime versions are recorded in each preflight/run manifest. M1 and M2 artifacts remain historical and unchanged; new source/lock hashes do not rewrite earlier evidence.

## Integration findings and remaining work

- **SDK compatibility:** [tabpfn-client 0.6.0](https://pypi.org/project/tabpfn-client/0.6.0/) caps scikit-learn at 1.9.0 and pandas at 2.3.3. M2 pins 1.9.1 and 3.0.6. The resolver verified the conflict; the optional REST route uses httpx 0.28.1 and python-dotenv 1.2.3 while preserving M2 versions. No older SDK is silently used. An SDK execution would need a separately locked environment.
- **Variant identity:** the [selection guide](https://docs.priorlabs.ai/models/selecting-model-version) identifies `v3.5_default` as Plus and `v3.5-fast_default` as Fast. Thinking adds its explicit fit settings. Base is not exposed by this adapter because its distinct hosted identity is not yet confirmed. The SDK's `paper_version` switch was inspected, but that is not evidence of a verified base checkpoint in a live run.
- **Class order:** the reviewed REST schema omitted returned class labels, while SDK 0.6.0 permits them. The continuation explicitly returned integer classes `[0, 1]`, matching the training encoding. The adapter now validates returned classes when present; old responses without them retain the documented sorted-training-label convention.
- **Metering:** [estimates](https://docs.priorlabs.ai/api-reference/metering) are usage predictions, not guaranteed billing caps. The adapter checks a fresh estimate against approval; actual per-operation tokens remain unavailable unless independently verified. A timeout can still be charged, so the adapter stops without retrying. Thinking estimates include both fit and prediction.
- **Further live work:** the one approved continuation has been consumed. Fast, Thinking and Plus sensitivity seeds remain unexecuted because additional variant/seed budgets were not approved. Local base execution is outside this hosted integration scope; no verified local runtime or base comparison is claimed. Future billable operations require their own reviewed scope and budget; no immediate repeat is needed.

M3 meets its initial integration acceptance bar with one accepted primary hosted response, offline-tested transport and recorded variant limits. Final test metrics, calibration, random-reference runs, subgroup uncertainty, capture/lift and controlled timing remain M4. M4 and M5 are still required before submission.

## External diagnostic review

A PAL consensus workflow and follow-up challenge with Gemini 2.5 Pro produced a stricter recovery plan: improve typed metadata capture, audit the REST/SDK request-schema discrepancy offline, seek evidence tied to the original run and only then consider a newly approved continuation. Alias expansion remains a hypothesis. No additional TabPFN call or acceptance-policy change was made. See [model identity review](M3_IDENTITY_REVIEW.md) for the evidence, disagreements, rejected advisory code and continuation ID.

## Local diagnostic and request-format work completed

On 21 September, commits `1ee9a39` and `30933ac` completed the approved offline preparation. New runs persist a hashed `response_evidence.json` before acceptance or scoring; it records requested settings, typed and sanitised observed identity/configuration/package fields, check results and numerically valid probability rows. Missing/null/unexpected types, redaction, omissions and normalization are explicit. Unknown checkpoint identities remain rejected. Credential reflection, URL user information, encoded secrets, malformed metadata and persistence ordering have regression coverage; the two original failure cases fail against the previous adapter.

The pinned REST/SDK source audit and mocked emitted-request comparisons cover Plus, Fast and Thinking. Current requests match the published REST snapshot. SDK 0.6.0 nests fit and Thinking configuration differently and exposes additional optional response metadata; prediction fields we send agree. No request schema, payload, model setting or dependency was silently changed. Sources were inspected without executing the SDK. See [request-contract audit](M3_REQUEST_CONTRACT.md) for source hashes, reproduction commands, field rationale and limits of this evidence.

All 77 tests and Ruff checks pass in the project environment and isolated staged snapshots. The offline full-size primary plan replays byte for byte with SHA-256 `038e27c7de8105869fb08735c7adb9c584f76f5f517df5d1c881f3108b44e532`. Four historical live-evidence hashes are unchanged. `artifacts/m3-local-diagnostics-verification.json` records the checks. This work made zero TabPFN requests, loaded no live credential and consumed no TabPFN tokens.

The local preparation is complete. The live identity mismatch and REST/SDK/server contract interpretation remain unresolved. No historical probability was accepted or rescored. Any further live prediction remains subject to a separately reviewed budget and approval.


## Prediction-only continuation playbook

On 21 September, the offline continuation review was prepared at `artifacts/m3-plus-continuation-review`. Its status is `awaiting_prediction_approval`; this preparation loaded no live credential and made no API request. All 86 tests and Ruff checks pass, including isolated staged snapshots. Tests cover saved-source and plan tampering, missing budget, mock/live separation, evidence persistence before validation, expired resources, unknown identity and no upload/refit/retry. Four historical evidence hashes remain unchanged.

The source is `artifacts/m3-plus-seed-3501-attempt-3`, pinned by manifest SHA-256 `faff3c45c1bb40099743288f85672149357e7b8cd260e98fae4dff9925ce307b`. The reconstructed plan is byte-identical to the original approved plan, SHA-256 `038e27c7de8105869fb08735c7adb9c584f76f5f517df5d1c881f3108b44e532`. `continuation.json` records the exact retained resource IDs and requested settings. Local payload reconstruction checks integrity; it does not send the payloads.

1. Obtain approval for **one prediction-only request**, with a fresh estimate ceiling of **10,000 tokens**. This is an estimate guard, not a guaranteed actual-charge cap.
2. Recheck frozen inputs, the source manifest, model limits and cost. Stop before prediction if any check fails or the estimate exceeds the ceiling.
3. Send one prediction against the retained fitted model and validation upload. Capture permitted response evidence before strict acceptance checks. There are no uploads, fits or automatic retries.
4. If accepted, record validation metrics and requested/reported identity with their limits. If identity differs, inspect the saved value and pinned official sources offline; change acceptance only if the mapping is supported. Never accept a checkpoint merely because its filename resembles the requested model, or retroactively certify an older response.
5. If the resources have expired or the request fails, stop and record the failure. If the captured identity remains ambiguous, prepare a focused vendor question using that evidence. No further paid experiment is implied.

The following command was executed once after explicit approval. It is retained as a historical record; do not repeat it under the consumed approval:

```sh
.venv/bin/scuba tabpfn-continue \
  --input artifacts/m1-15000-seed-3501 \
  --prior-run artifacts/m3-plus-seed-3501-attempt-3 \
  --source-manifest-sha256 faff3c45c1bb40099743288f85672149357e7b8cd260e98fae4dff9925ce307b \
  --output artifacts/m3-plus-prediction-continuation-1 \
  --allow-predict --max-estimated-tokens 10000
```

Omit `--allow-predict` to prepare another offline review, with a different output directory. The live continuation was subsequently executed once, as recorded below. The main test cohort remains untouched.


## Accepted continuation and primary validation result

The single approved prediction completed against the existing resources, with a fresh estimate of 10,000 tokens. The API response was initially rejected by exact alias equality, but its complete permitted metadata survived. Official client alias semantics, a pinned official checkpoint mapping and this response's explicit family/mode/settings support policy `plus-checkpoint-20260909-v1`. Revalidation used that saved response offline, without another fit, upload or prediction. The original failed manifest remains intact.

Accepted output: `artifacts/m3-plus-continuation-revalidated`, evidence `offline_revalidated_live_response`. Manifest SHA-256 `59e030bff20ea8550772d4a8c1da74defdd3572ce991f121e88b14f9210a0a60`; predictions SHA-256 `69d06d98b6999e258c48754b1f90241d712948686712b0fc88ec6566b4766595`.

| Primary validation model | Average precision ↑ | Log loss ↓ | Brier score ↓ |
| --- | --- | --- | --- |
| Constant prior | 0.111757 | 0.350241 | 0.099281 |
| Logistic regression | 0.295563 | 0.305311 | 0.089531 |
| XGBoost | 0.350960 | 0.282502 | 0.084812 |
| CatBoost | 0.356238 | 0.283208 | 0.084687 |
| Hosted Plus requested; reported v3.5 checkpoint | 0.373397 | 0.274317 | 0.083117 |

All use the same 2,407 frozen primary validation customers, with 269 positive outcomes. The local comparator results come from [M2](M2_RESULTS.md). The observed AP difference versus CatBoost is +0.017159; this single synthetic validation cohort does not establish statistical significance or real-world superiority. There was no tuning against these results.

`make check` passes all 91 tests and Ruff checks; each atomic implementation snapshot also passes. Two new regression checks fail against the previous transport: the known checkpoint was rejected and reversed returned classes were not checked. Offline recovery tests reject hash/plan changes, missing or transformed metadata, alternate checkpoints, class errors and invalid probabilities. The saved probabilities, labels, snapshot keys and synthetic flags reconcile for every row; metrics recompute exactly. The four older evidence hashes and both continuation source hashes are unchanged. `artifacts/m3-checkpoint-resolution-verification.json` records these checks; pinned public sources are cached in `artifacts/m3-checkpoint-sources`.

The integration blocker is resolved for this captured response. The REST/SDK fit-envelope discrepancy remains a compatibility observation, and the reported package version `8.5.0` is preserved without claiming it matches the public source release. No vendor message was sent. Further variants, seeds and test predictions remain separately budgeted work.
