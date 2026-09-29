# Synthetic benchmark: hosted integration results

Recorded 21 September 2026. This archived experiment is separate from
[Financial Stress](README.md). One captured primary validation response was
accepted after an offline model-identity review. Two earlier responses remain
unverified and were not scored.

## Accepted validation result

All models use the same 2,407 synthetic validation customers, with 269 positive
outcomes. Training used 22,183 snapshots and 11 predictors. Settings and cohorts
were unchanged after viewing results.

| Primary validation model | Average precision ↑ | Log loss ↓ | Brier score ↓ |
| --- | --- | --- | --- |
| Constant prior | 0.111757 | 0.350241 | 0.099281 |
| Logistic regression | 0.295563 | 0.305311 | 0.089531 |
| XGBoost | 0.350960 | 0.282502 | 0.084812 |
| CatBoost | 0.356238 | 0.283208 | 0.084687 |
| Hosted Plus requested; reported v3.5 checkpoint | 0.373397 | 0.274317 | 0.083117 |

The observed AP difference versus CatBoost was +0.017159. Subsequent
[paired uncertainty](M4_RESULTS.md) did not establish a clear advantage.
The [final test](M4_HOSTED_FINAL_RESULTS.md) is a separate evaluation.

## Integration findings

The REST adapter checks payload hashes, limits, probability shape and bounds,
class order, reported model identity and requested settings. Offline planning
loads no credentials. Hosted execution requires a matching plan, an explicit
upload flag and a positive estimate ceiling; ambiguous requests are not retried.

The first transfer stopped on a required storage `Host` header. A correction
permits the header only when it matches the validated storage authority.
Two later predictions returned valid probabilities but failed exact model-alias
equality. Their loggers omitted the returned identifier, so those responses
could not be accepted retrospectively.

One separately authorised prediction-only continuation preserved the returned
checkpoint. Official alias semantics and the pinned checkpoint mapping supported
a narrow identity policy. Revalidation accepted that captured response offline,
without another prediction. The [resolution](M3_CHECKPOINT_RESOLUTION.md) records
the source evidence and limits; the [request audit](M3_REQUEST_CONTRACT.md) records
the separate REST/SDK envelope discrepancy.

Accepted output classification: `offline_revalidated_live_response`.
Manifest SHA-256: `59e030bff20ea8550772d4a8c1da74defdd3572ce991f121e88b14f9210a0a60`.
Predictions SHA-256: `69d06d98b6999e258c48754b1f90241d712948686712b0fc88ec6566b4766595`.
Historical failure evidence was retained unchanged.

## Verification and scope

At completion, Ruff and 91 offline tests passed in the working environment and
independent staged snapshots. Checks covered credential separation, changed plans,
limits, response validation, failure evidence and mock/live separation. Saved
predictions reconciled to every expected row and reproduced the metrics exactly.

The accepted continuation requested `v3.5_default`, eight estimators and seed
3501. It reported the reviewed v3.5 checkpoint and standard execution. This checks
server-reported identity, not remote weight bytes. Each authorised prediction
had a 10,000-token estimate; actual charges were unavailable.

Fast, Thinking and hosted sensitivity runs were not performed. The verified
[Financial Stress integration](INTEGRATION_NOTES.md) subsequently reused this
adapter with its own data, plans and evaluation.
