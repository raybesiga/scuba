# SCUBA — mobile-money signals for customer care

SCUBA uses **TabPFN-3.5-Plus** to help a customer-care operator prioritise a review
list from six months of mobile-money activity. Choose a review capacity, inspect
ranked snapshots and their activity context, then export a shortlist for human
review. The supplied target is financial stress in the following 30 days.

## Try the demo

Open [demo/index.html](demo/index.html) in a browser. The dashboard is self-contained
and uses saved, verified predictions: no API key or model request is needed.
The review workspace uses validation snapshots; the **Final holdout** tab shows
the separate reserved evaluation. A synthetic benchmark is available in the archive.

## What the model showed

Five models were trained on the same 24,000 rows and evaluated on the same reserved
8,000-row holdout, with settings frozen before evaluation.

| Model | Log loss ↓ | AUROC ↑ | Stress cases found in 800 reviews |
| --- | ---: | ---: | ---: |
| TabPFN-3.5-Plus | 0.2799 | 0.8784 | 542 |
| XGBoost | 0.3073 | 0.8560 | 512 |
| CatBoost | 0.3300 | 0.8384 | 472 |
| Logistic regression | 0.3806 | 0.7410 | 352 |
| Constant prior | 0.4227 | 0.5000 | 126 |

There are 1,200 labelled stress cases in that holdout. TabPFN found 30 more than
XGBoost at the same review capacity. These are observed point estimates, not
proof that outreach changes outcomes. See [full evaluation](docs/F4_RESULTS.md).

## Rebuild and verify

The verified runtime is Python 3.14.5 and Node 24. Dependency installation needs
network access unless the locked packages are cached:

```sh
uv sync --locked --python 3.14.5 --extra models --extra tabpfn
npm ci --prefix report-ui --ignore-scripts
```

Then run offline:

```sh
make check
make ui-check
PYTHONPATH=src .venv/bin/python -m scuba.source_bundle --bundle datasets/financial-stress --verify
PYTHONPATH=src .venv/bin/python -m scuba.financial_demo build --evidence evidence --output rebuilt-demo
```

The rebuild verifies checksums, model identity, row alignment and final metrics
before producing the dashboard. Choose a new output directory for each rebuild.
See [training and evaluation instructions](docs/how-to/FINANCIAL_STRESS.md) to
reproduce the local models. Hosted predictions are optional, separately approved
service calls; credentials belong in an ignored local `.env`, never this repository.

## Data, scope and limitations

The original [Financial Stress files](datasets/financial-stress/README.md) are
included with hashes and attribution. The supplied Zindi rules declare CC BY-SA
4.0 for the data; original SCUBA code is Apache-2.0. Derived data and reference
material retain their applicable source terms. See [licence scope](LICENSE_SCOPE.md).

The dataset has no observation dates or persistent customer identifier. Evaluation
therefore uses a stratified row holdout; distinct customers and temporal separation
are unverified. Real versus synthetic origin and operational label mechanics are
also unverified. SCUBA supports human review, not credit decisions, automated
contact, personalised offer effectiveness or causal explanations.

A separate all-40,000-row fit returned 30,000 unlabelled predictions. Their
column-count metadata remains unresolved after one diagnostic, so those outputs
are **excluded from this demo and its performance claims**. See the
[integration record](docs/FINANCIAL_STRESS_FULL_DATA_RESULTS.md).

Nedbank data, private response archives, credentials and development Git history
are excluded from this delivery snapshot. Historical documentation may mention
the deferred Nedbank experiment. [Project description and demo script](docs/PRIOR_LABS_SUBMISSION_DRAFT.md).
