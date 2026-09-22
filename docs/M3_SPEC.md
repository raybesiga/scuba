# M3 — TabPFN integration protocol

Declared before API use, 20 September 2026. M3 builds an offline-tested integration and prepares a reviewable live run. M2 model scores and the main test cohort remain frozen.

## Iteration compact

- Goal: integrate an explicitly identified TabPFN-3.5 variant through the current REST upload/fit/predict flow and record integration evidence separately from scores.
- Decision and owner: the project owner assesses integration effort and approves any external upload and token budget; no operational customer decisions.
- Success: deterministic local preflight; tested payload, limits, probability and failure contracts; a live validation run only when credentials, access and upload/budget approval are available. Unavailable routes have explicit reasons and no invented scores.
- Guardrails: only frozen first-principles M1 train/validation inputs, exactly 11 predictors, training labels only, no test scoring, no automatic authentication, no secret values or signed URLs in logs/artifacts.
- Unacceptable mistakes: relabelling Plus as base, silently downgrading model or local dependencies, sending IDs/dates/archetypes/validation labels, mistaking estimates for actual tokens, retrying ambiguous billable work.
- Tradeoffs: REST avoids SDK dependency conflicts. The current SDK 0.6.0 caps scikit-learn at 1.9.0 and pandas at 2.3.3; M2 pins 1.9.1 and 3.0.6. Local base weights and GPU execution are outside this iteration until access/hardware are verified.
- Data and grain: frozen M1 manifests, one customer/date snapshot; training April–June and validation August 2032 with disjoint customer groups. Primary seed 3501, sensitivity 3502/3503 remain available.
- Timing and target: preceding 60-day predictors for currently active customers; no successful events over the next 30 days. The [experiment](EXPERIMENT.md) is unchanged.
- Baselines/signals/slices: M2 baselines and predictor allowlist unchanged. Subgroup uncertainty, final test scores and random reference remain M4.
- Orchestration: local CLI and manifests; no Airflow, MLflow, deployment or cloud-resource creation.
- Fallback: fail or skip explicitly; preserve completed local artifacts; never substitute a different variant. No automatic retry of API failures in the initial adapter.
- Risks: hosted versions/default aliases may move; estimates are not hard billing caps; timeouts may still consume tokens; Thinking may change fitted settings. Require fresh live limits and metering before an approved upload.

## Scope and approval boundary

The default preflight uses no network and requires no token. It produces a manifest describing exactly which synthetic rows, fields, byte sizes and hashes would be sent. Model-bound payloads exclude identifiers and synthetic flags; their local sidecar manifest marks every payload and row range synthetic, while original snapshots and saved predictions retain row-level synthetic flags.

An explicit metadata preflight may load `TABPFN_TOKEN` from the environment or the repository `.env` and request only model limits and dimension/settings-based cost estimates. It must not prepare uploads, fit or predict. The environment takes precedence; `.env` is ignored by Git, `.env.example` is committed with an empty placeholder, and no key is printed.

A new upload/fit/predict execution requires an explicit upload flag, a positive approved token budget, and the exact preflight plan. Recheck input hashes, model limits and cost immediately before upload; stop if anything no longer fits. Never treat an elapsed approval wait as permission. A missing key, unresolved variant or unsupported contract must stop before upload.

A prediction-only continuation is a separate approved operation. `tabpfn-continue` defaults to offline review. It binds the saved fitted-model and validation-upload IDs to a pinned historical manifest, reconstructs the original plan from frozen inputs and rejects changed plans. The source must be a failed Plus validation run with a prediction-contract error; a prior continuation cannot be chained. Mock sources cannot be used for real requests. `--allow-predict` and a positive estimate ceiling enable fresh limits/estimate checks followed by at most one prediction per invocation. There is no upload or refit path. Expired resources, excessive estimates and API failures stop execution; another invocation requires another approval.

The diagnostic continuation may retain an unrecognised returned identity without accepting it. Save sanitised response evidence and its hash before validation; unknown identities still produce no accepted scores. Use that observed response to investigate any alias-to-checkpoint mapping offline. Do not certify earlier predictions from a later response.

## Model and request policy

Use a fixed model seed 3501 and eight estimators for standard predictions; no local scaling, imputation or category encoding. Preserve raw categorical strings and missing numeric values. The first proposed live run is primary-seed validation only. Each additional variant/seed requires a reviewed budget; hosted Plus is labelled separately. Thinking uses medium effort, log-loss objective and a 300-second fit budget if enabled; estimate both fit and prediction costs.

Prefer complete validation inference in one request when server row/cell/row-pair limits permit. Do not silently subsample, change the cohorts or split billable requests to bypass limits. Stop for review instead. Record requested and server-returned settings; never claim an immutable checkpoint identity when the server reports only an alias.

HTTP requests use TLS verification, bounded timeouts and no automatic redirects or retries. API credentials go only to the fixed Prior Labs API origin; signed storage uploads carry only required storage headers. Validate the response dimensions, binary class ordering, finite probabilities, probability sums and model metadata before saving scores. Record sanitised failure categories and whether billing is uncertain; never persist raw error bodies.

## Acceptance and commits

Test secrets precedence/absence, disabled network by default, payload allowlist and provenance, changed-plan rejection, each published model limit, stale/over-budget estimates, authentication/validation/quota/rate-limit errors, timeouts, signed-upload header separation, response shape/class order and failure artifacts. Run `make check` on each staged snapshot. Group commits into protocol/dependencies/secrets, preflight, transport/adapter and runner/evidence. Keep M3 in progress until live evidence or a concrete documented access skip satisfies its acceptance criteria.
