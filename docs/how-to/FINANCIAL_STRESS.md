# Run and reproduce Financial Stress

Use the saved demo for the quickest review. Rebuilding the presentation and
fitting local baselines are offline operations once dependencies are installed.
A new hosted TabPFN prediction is a separate operation.

## Run the saved demo

The release checkout includes `demo/` and `evidence/`. From its root, serve the
saved dashboard:

```sh
python3 -m http.server 8880 --bind 127.0.0.1 --directory demo
```

Open <http://127.0.0.1:8880/index.html>. Stop the server with Ctrl+C. No dependency
installation or API key is required for this saved HTML demo.

In the development checkout, the prepared release is under
`artifacts/scuba-private-repo`; run the command from that directory. Its Git
history is separate from the development repository.

## Install locked dependencies

Verified runtimes: Python 3.14.5 and Node 24. Install uv and select Node 24 before
continuing. Run from the checkout root. These installation commands need network
access unless the packages are already cached:

```sh
uv sync --locked --python 3.14.5 --extra models --extra tabpfn
npm ci --prefix report-ui --ignore-scripts
```

For an offline installation, add `--offline` to both commands. Missing cached
packages must be installed before an offline replay can succeed.

## Portable final demo

With dependencies installed, verify the code and source package:

```sh
make check
make ui-check
PYTHONPATH=src .venv/bin/python -m scuba.source_bundle --bundle datasets/financial-stress --verify
```

Then rebuild the dashboard:

```sh
PYTHONPATH=src .venv/bin/python -m scuba.financial_demo build --evidence evidence --output rebuilt-demo
```

In the development checkout, replace `evidence` with
`artifacts/financial-stress/portable-evidence-v1`. Use a new output directory for
each run; the builder refuses to overwrite one.

Expected output: `index.html`, `evidence.json`, `manifest.json`, two review CSVs
and the three-file synthetic archive. The builder checks the evidence allowlist,
checksums, row alignment and model identity, then recomputes final metrics and
the paired uncertainty analysis. It makes no model request.

The review workspace and exports use validation records. The final-holdout tab
shows the separate reserved evaluation. With unchanged code, locked dependencies
and evidence, the rebuild should match the packaged demo byte for byte.

## Reproduce local model fitting

These commands prepare the fixed split from the original source files and fit
all four local comparators on the training partition:

```sh
PYTHONPATH=src .venv/bin/python -m scuba.financial_stress prepare --output artifacts/reproduce-prepared
PYTHONPATH=src .venv/bin/python -m scuba.financial_comparison compare --prepared artifacts/reproduce-prepared --output artifacts/reproduce-validation
```

Expected output includes the prepared train/validation/final partitions and
membership file, then validation predictions and metrics for the constant prior,
logistic regression, XGBoost and CatBoost. The supplied notebook is not executed.

Reproduce the local final-holdout comparison using the bundled preparation and
frozen protocol:

```sh
PYTHONPATH=src .venv/bin/python -m scuba.financial_final local \
  --prepared evidence/prepared-v1 \
  --protocol docs/reference/financial-stress-final-protocol-v1.json \
  --output artifacts/reproduce-final
```

The protocol checks input and execution-source hashes before scoring. Use
`evidence/prepared-v1` here: fresh preparation reproduces the partition bytes, but
records a newer preparation-code hash and cannot pass the frozen manifest check.
In the development checkout, use
`artifacts/financial-stress/portable-evidence-v1/prepared-v1`. Results use the
original model settings; timing and run-provenance fields can differ.
A fresh fit is a new run, not a replacement for the saved evidence bundle.
If hashes fail, inspect the mismatch rather than changing expected hashes.

To repeat the local age/gender exclusion check:

```sh
PYTHONPATH=src .venv/bin/python -m scuba.financial_comparison compare \
  --prepared artifacts/reproduce-prepared \
  --output artifacts/reproduce-without-age-gender --exclude-age-gender
```

This check does not run TabPFN or establish fairness. See [the recorded result](../F3_RESULTS.md).

## Optional hosted execution

Saved predictions are sufficient to reproduce the demo. A new TabPFN run uploads
data to Prior Labs and consumes service tokens. It needs an account, credentials,
data-upload authorisation and an approved estimate ceiling.

First produce an offline plan without loading credentials:

```sh
PYTHONPATH=src .venv/bin/python -m scuba.financial_comparison preflight \
  --prepared artifacts/reproduce-prepared --output artifacts/hosted-plan-review
```

Inspect its feature order, dimensions, settings and payload hashes. An explicit
`preflight --online` additionally checks current limits and the estimate; it sends
metadata only. Store `TABPFN_TOKEN` in the environment or ignored local `.env`.
Never include it in the repository or command output.

`run-hosted` requires `--approved-plan`, `--allow-upload` and a positive
`--max-estimated-tokens`. It rechecks the plan and estimate, makes one prediction
attempt and does not retry automatically. Use `--help` for its complete options.
An estimate ceiling is not an actual billing guarantee. Inspect retained evidence
before deciding whether a failed request should be repeated.

The [full-data runner](FINANCIAL_STRESS_FULL_DATA.md) is a separate experiment.
Its unresolved outputs are not needed for this demo.

## Build the Financial Stress workspace

The current route is the [portable final demo](#portable-final-demo) above. The
original validation-only F3 build is retained in [its milestone record](../F3_RESULTS.md).

To export another copy of the frozen evidence from the development checkout:

```sh
PYTHONPATH=src .venv/bin/python -m scuba.financial_demo export \
  --root artifacts/financial-stress \
  --archive artifacts/m5-dashboard-model-names \
  --attribution datasets/financial-stress/README.md \
  --output artifacts/financial-stress/portable-evidence-new
```

This export needs the original retained run directories. The release checkout
already contains their verified portable copy under `evidence/`.
