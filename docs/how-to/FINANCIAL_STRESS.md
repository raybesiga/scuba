# Prepare and evaluate Financial Stress locally

Use the existing locked `models` dependencies (`uv sync --locked --extra models`
for initial installation). The following commands are offline and do not load
credentials. Run from the repository root; choose new output directories for
repeat runs. The source notebook is not executed.

```sh
PYTHONPATH=src .venv/bin/python -m scuba.financial_stress prepare --output artifacts/financial-stress/prepared-v1
PYTHONPATH=src .venv/bin/python -m scuba.financial_stress baseline --prepared artifacts/financial-stress/prepared-v1 --output artifacts/financial-stress/baseline-v1
```

Preparation verifies source hashes, checks schemas/IDs/labels, freezes row
partitions and records membership and file hashes. Baseline evaluation checks the
training and validation file hashes, fits preprocessing on training only, and
writes validation probabilities and metrics. It does not open the final partition
or score the challenge's unlabelled Test.csv. Outputs remain local and ignored.

`metrics.json` contains log loss, AUROC, average precision, Brier, calibration,
5%/10% review-budget outcomes, settings, runtime and evidence hashes. Predictions
refer to snapshot IDs, not independently verified unique customers. No actual
customer contact, offer or eligibility decision is performed.

See the [contract](../explanation/FINANCIAL_STRESS.md),
[source attribution](../../datasets/financial-stress/README.md) and
[roadmap](../ROADMAP.md). Test with `make check`; tests use invented fixtures.

## Compare local models and prepare TabPFN

Use the existing prepared directory; do not regenerate the frozen partitions.

```sh
PYTHONPATH=src .venv/bin/python -m scuba.financial_comparison compare --prepared artifacts/financial-stress/prepared-v1 --output artifacts/financial-stress/comparison-v1
PYTHONPATH=src .venv/bin/python -m scuba.financial_comparison preflight --prepared artifacts/financial-stress/prepared-v1 --output artifacts/financial-stress/preflight-offline-v1
```

The first command evaluates prior, logistic regression, XGBoost and CatBoost on
identical validation rows. The second saves a deterministic hosted plan without
credentials or network calls. It includes payload hashes and sizes, not raw rows.

An explicitly requested `preflight --online` checks current limits and token
estimates using dimensions/settings only. It loads the local API token; it does
not upload records, fit or predict. Inspect `preflight.json` and `plan.json` before
approving an upload and positive estimate ceiling. The runner rechecks the estimate
immediately before uploading; it stops if that ceiling is exceeded.

Once the specific plan and token ceiling are approved, use:

```sh
PYTHONPATH=src .venv/bin/python -m scuba.financial_comparison run-hosted \
  --prepared artifacts/financial-stress/prepared-v1 \
  --approved-plan artifacts/financial-stress/preflight-verified-v1/plan.json \
  --output artifacts/financial-stress/hosted-validation-v1 \
  --allow-upload --max-estimated-tokens 10000
```

This exact plan and 10,000-token estimate ceiling were approved and executed on
21 September 2026. The saved output now exists; this is the historical invocation,
not an instruction to make another paid request. The runner reconstructs and
checks the approved payloads, then makes one prediction attempt. It retains permitted response diagnostics before
accepting model identity, probabilities and metrics. A failure is saved in
`manifest.json`; it makes no paid retry. Do not rerun a failed paid attempt without
checking its evidence and obtaining any necessary new approval. Nothing reads the
reserved final partition or sends validation labels/IDs to the service.

The estimate is in service tokens, not money; actual charges may not be reported.
See the [F2 protocol](../F2_SPEC.md) and [current results](../F2_RESULTS.md).

## Build the Financial Stress workspace

The local F3 dashboard uses saved, pinned validation evidence. It does not call
TabPFN or read `final.csv`. With the locked Python/UI dependencies installed and
these retained artifacts available, build into a new output directory:

```sh
PYTHONPATH=src .venv/bin/python -m scuba.financial_dashboard \
  --prepared artifacts/financial-stress/prepared-v1 \
  --local artifacts/financial-stress/comparison-verified-v1 \
  --hosted artifacts/financial-stress/hosted-validation-v1 \
  --ablation artifacts/financial-stress/without-age-gender-v1 \
  --archive artifacts/m5-dashboard-model-names \
  --output artifacts/financial-stress/dashboard-replay
```

Open `index.html` from that folder, or serve that folder locally. It contains
`evidence.json`, `manifest.json`, `review-400.csv`, `review-800.csv` and the preserved
synthetic dashboard under `archive/`. The CSVs contain the entire selected
shortlist, irrespective of display search/sort/page. Evidence JSON includes the
displayed validation features and probabilities; review CSVs omit outcome labels.
Data adaptations retain the source CC BY-SA 4.0 attribution separately from code.

The exporter rejects changed manifests or predictions. The named retained runs
are pinned by the references in `docs/reference`; refitting produces a new run,
including new timing/provenance, rather than silently replacing pinned evidence.
For the completed F4 evidence package, use the portable final demo below.

To perform a separate local age/gender exclusion experiment on the frozen split:

```sh
PYTHONPATH=src .venv/bin/python -m scuba.financial_comparison compare \
  --prepared artifacts/financial-stress/prepared-v1 \
  --output artifacts/financial-stress/without-age-gender-new \
  --exclude-age-gender
```

This refits the three local learned baselines and records the constant-prior
reference. It does not make a hosted call or establish TabPFN's sensitivity to
those fields. See [F3 results](../F3_RESULTS.md) for the accepted run and checks.

## Portable final demo

The completed final comparison can be replayed without credentials or model calls.
Initial dependency installation needs package access unless the locked packages
are already cached; subsequent evidence replay is offline. The verified runtime
uses Python 3.14.5 and Node 24. A fresh offline installation was not verified
because the local cache lacked the CatBoost wheel.
Export a bundle from the retained local evidence:

```sh
PYTHONPATH=src .venv/bin/python -m scuba.financial_demo export \
  --root artifacts/financial-stress \
  --archive artifacts/m5-dashboard-model-names \
  --attribution datasets/financial-stress/README.md \
  --output artifacts/financial-stress/portable-evidence-new
```

Copy that bundle to a clean checkout with the locked dependencies installed, then:

```sh
PYTHONPATH=src .venv/bin/python -m scuba.financial_demo build \
  --evidence artifacts/financial-stress/portable-evidence-new \
  --output artifacts/financial-stress/final-demo-replay
```

The builder checks every allowlisted file, revalidates the hosted response and
independently recomputes final metrics before rebuilding the dashboard. Both
review exports still use validation snapshots. Final holdout metrics appear in
a separate tab. Card corners are square in both themes.

## Prepare a full-data run

This command creates a plan only. It verifies the supplied original files, records
40,000 training rows and 30,000 unlabelled inference rows, and hashes payloads
without writing or uploading them:

```sh
PYTHONPATH=src .venv/bin/python -m scuba.financial_inference \
  --bundle datasets/financial-stress \
  --prepared artifacts/financial-stress/prepared-v1 \
  --output artifacts/financial-stress/full-data-plan-new
```

A full-data refit requires a separate approval and execution step. The approved
22 September attempt returned predictions with a column-count discrepancy;
see [execution status](../FINANCIAL_STRESS_FULL_DATA_RESULTS.md) and the
[runner and verification guide](FINANCIAL_STRESS_FULL_DATA.md). Do not repeat
the paid request merely because local acceptance is pending. Never treat
unlabelled inference output as another model-quality evaluation. The approved
final-holdout execution is already recorded in [F4 results](../F4_RESULTS.md);
do not rerun that billable request merely to rebuild the demo.
