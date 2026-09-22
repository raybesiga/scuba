# Run full-data Financial Stress inference

This is a separate inference run after the frozen final evaluation. It fits
TabPFN-3.5-Plus on all 40,000 labelled snapshots and scores the 30,000 unlabelled
snapshots, using all 182 predictors, eight estimators and seed 3501. IDs remain
local. The original data licence and source limitations continue to apply.

The operator decision remains customer-care review prioritisation. The output
is a probability for each supplied snapshot, not an offer recommendation or an
automatic customer action. Successful execution means verified model identity,
30,000 finite probabilities in [0, 1], exact original Test.csv ID order, and
retained evidence. There are no labels for these rows, so no quality, calibration,
capture or intervention-benefit metrics can be computed. Use the separate
[final holdout comparison](../F4_RESULTS.md) for model-quality evidence; that
comparison evaluated a model fitted on 24,000 rows, not this new 40,000-row fit.

## Execute the reviewed plan

**Historical invocation:** the user approved and ran this plan on 22 September.
The first attempt timed out during upload; a recovery attempt completed the
service prediction but failed local column-count validation. See the
[execution record](../FINANCIAL_STRESS_FULL_DATA_RESULTS.md). The command below
is documentation, not authorisation to issue another request.

The [plan](../reference/financial-stress-full-data-plan-v1.json) pins source hashes,
feature order, settings, payload hashes and output schema. Initial dependencies
must already be installed. The runner checks the plan and recorded final result
before loading credentials, then checks fresh limits and the estimate before any
upload. The 22 September metadata-only preflight estimated 15,728 service tokens.

The following invocation requires explicit approval for this full payload and
destination. It makes one prediction attempt and does not retry automatically.
Use a new output directory; an existing attempt cannot be overwritten.

```sh
PYTHONPATH=src .venv/bin/python -m scuba.financial_inference_run run \
  --bundle datasets/financial-stress \
  --prepared artifacts/financial-stress/prepared-v1 \
  --approved-plan artifacts/financial-stress/full-data-plan-v1/plan.json \
  --output artifacts/financial-stress/full-data-hosted-v1 \
  --allow-upload --max-estimated-tokens 20000
```

The estimate guard permits headroom above the observed estimate. It is not a
row cap, model-quality setting or guarantee of actual billing. No inputs are
truncated. Credentials are read locally and are not written into artifacts.
Signed data uploads allow up to 180 seconds of network inactivity for a transfer;
metadata and prediction-stream idle reads retain their 30-second timeout. The
connection timeout remains 10 seconds. No transport retry is automatic.

If the run fails, inspect its sanitised manifest and saved response evidence.
Do not repeat a potentially billed request merely because the output is missing.
The existing validation dashboard and final evidence remain available.

## Inspect the complete response locally

New full-data runs save `prediction_response.private.json` as soon as the entire
prediction HTTP body has arrived, before checking the HTTP status, parsing the
response for execution, or validating model metadata. The archive contains the
HTTP status and complete response body, with credential redaction. JSON field
names, unfamiliar values, nested objects, feature-name lists, timings and all
probability rows survive; there is no field allowlist or preview truncation.
Non-JSON bodies are retained as redacted text. This is not a byte-exact transcript:
JSON is reserialised, credentials are redacted, and URL userinfo, query strings
and fragments are removed. Request headers are never archived.

The file is created atomically with owner-only permissions (`0600`), cannot
overwrite earlier evidence, and is ignored by Git. It is separate from filtered
`response_evidence.json` and is not included in the demo exporter. It may contain
provider-returned data, so keep it local. The manifest's
`complete_response_archive` entry records its filename, SHA-256, HTTP status,
body format and redaction count; offline verification checks the archive hash.

A timeout before the full body arrives produces no complete-response archive.
A local archive-write failure stops acceptance and never triggers another
prediction. The historical full-data response predates this change: discarded
fields cannot be restored from its filtered evidence, and no request was rerun
to test this fix.

## Verify the output offline

```sh
PYTHONPATH=src .venv/bin/python -m scuba.financial_inference_run verify \
  --output artifacts/financial-stress/full-data-hosted-v1
```

The verifier checks hashes, original ID order, row count, class order,
server-reported model identity, settings and exact agreement between retained
response probabilities and `predictions.csv`. The CSV has columns `ID` and
`probability_stress_30d`, preserving the original Test.csv order. It does not
contain training labels. The manifest records provenance, runtime and integration
evidence. Verification does not call the service or fit a model.

This workflow does not publish files, submit to either competition or replace the
validation dashboard. Any later interface for these unlabelled predictions must
distinguish them from the observed outcomes in the existing validation workspace.
