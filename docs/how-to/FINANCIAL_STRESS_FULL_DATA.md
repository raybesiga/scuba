# Full-data inference and response capture

This separate experiment fits TabPFN-3.5-Plus on all 40,000 labelled records and
scores 30,000 unlabelled records. It uses 182 predictors, eight estimators and
seed 3501. The [completed service run](../FINANCIAL_STRESS_FULL_DATA_RESULTS.md)
remains unaccepted because reported column metadata disagrees with the upload.
It is not needed to reproduce the hackathon demo.

## Prepare a plan

With locked dependencies installed, this command verifies original files and
creates a local plan without uploading data:

```sh
PYTHONPATH=src .venv/bin/python -m scuba.financial_inference \
  --bundle datasets/financial-stress \
  --prepared artifacts/reproduce-prepared \
  --output artifacts/full-data-plan-review
```

The prepared split comes from the [local run guide](FINANCIAL_STRESS.md#reproduce-local-model-fitting).
The plan pins source hashes, feature order, payload hashes, settings and output
schema. A new execution needs its own upload and token approval.

The historical execution used `financial_inference_run run` with `--approved-plan`,
`--allow-upload` and `--max-estimated-tokens 20000`. Its observed estimate was
15,728 tokens. Those values describe the 22 September run, not a current estimate
or permission to repeat it. The runner checks a fresh estimate and makes one
prediction attempt. Inspect evidence before repeating a potentially billed failure.

## Inspect the complete response locally

The full-data runner writes `prediction_response.private.json` before validating
HTTP status, JSON or model metadata. It retains the complete body, including unknown
fields and probability arrays, with explicit credential and URL redaction.
Non-JSON responses are retained as redacted text. This is not a byte-exact network
transcript: JSON is reserialised, and URL user information, queries and fragments
are removed. Request headers are not archived.

The archive is written atomically with owner-only permissions (`0600`), cannot
overwrite earlier evidence and is ignored by Git. Its filename, hash, status,
format and redaction count appear in the run manifest. It remains private and
is excluded from the demo exporter. Archive-write failure stops acceptance without
retrying the prediction; a timeout before the complete body arrives produces no
complete archive.

The first full-data run predates this capture fix. Its discarded fields cannot
be restored. A later authorised diagnostic captured a complete response and
confirmed the unresolved metadata discrepancy.

## Verify a saved run offline

Use the actual output directory of the retained run:

```sh
PYTHONPATH=src .venv/bin/python -m scuba.financial_inference_run verify \
  --output artifacts/financial-stress/full-data-hosted-v2
```

The historical full-data directory is local development evidence, not part of the
release package. The verifier checks hashes, original ID order, row count,
class order, reported identity, settings and response/prediction agreement.
It makes no service request. The unresolved run is expected to fail acceptance;
do not change its expected feature count to force success.

An accepted output would contain `ID` and `probability_stress_30d` in original
Test.csv order. These records have no outcome labels, so they cannot provide
quality, calibration or capture metrics. Use the separate
[final holdout](../F4_RESULTS.md) for model-quality evidence.
