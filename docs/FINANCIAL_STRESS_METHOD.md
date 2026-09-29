# Financial Stress: inputs, evaluation and limits

SCUBA estimates the probability of the supplied `liquidity_stress_next_30d` label
and ranks records for customer-care review. A record is one customer snapshot;
the supplied ID does not establish a persistent identity across snapshots.

## Inputs

The dataset contains 40,000 labelled records and 30,000 unlabelled inference
records. The model uses all 182 supplied predictors, excluding ID and target.
These include monthly transaction counts and amounts, payments, transfers,
balances, activity frequency and profile fields. M1 is the latest month and M6
the oldest. Profile fields include age, gender, region, segment and earning pattern.
See the [data dictionary](../datasets/financial-stress/files/data_dictionary.csv).

The monthly chart in the app shows transaction context. It is one view of the
record, not a feature-importance explanation. Its baseline is average transaction
count over M6–M2, compared with M1. Dataset amounts have no independently verified
currency or unit conversion.

## Evaluation

| Partition | Records | Stress cases | Purpose |
| --- | ---: | ---: | --- |
| Training | 24,000 | 3,600 | Fit models and preprocessing |
| Validation | 8,000 | 1,200 | Compare models and demonstrate the review workflow |
| Final holdout | 8,000 | 1,200 | Evaluate the frozen settings separately |

The split is stratified by label, fixed at seed 3501 and stable under source-row
reordering. It separates rows, not dates or verified people. The original
[experiment contract](explanation/FINANCIAL_STRESS.md) and [final protocol](F4_SPEC.md)
record the decisions made before evaluation.

TabPFN-3.5-Plus, XGBoost, CatBoost, logistic regression and a constant prior use
the same training records. Preprocessing fits only on training data. Model
settings were fixed; there was no hyperparameter search, early stopping or
adjustment after viewing final outcomes. Validation records were not added to
training for the final comparison.

## What the measures mean

- **Log loss:** the primary measure of probability quality; lower is better.
- **AUROC and average precision:** ranking quality; higher is better. Average
  precision also depends on the prevalence of stress in the evaluation group.
- **Brier score:** average squared probability error; lower is better.
- **Calibration gap:** observed stress rate minus mean prediction within a
  probability range. The summary weights absolute gaps by group size.
- **Cases found:** labelled stress records in the top 5% or 10% by predicted
  probability. Each model selects 400 or 800 records; ID breaks tied scores.

Search, sorting and pagination change the display, not the shortlist membership.
Exports include the full selected shortlist. Group audits count membership in
the global shortlist; they do not apply separate group thresholds.

The [final comparison](F4_RESULTS.md) uses different records from the
[validation comparison](F2_RESULTS.md). The app's review list and exports use
validation records. Observed outcome labels are excluded from individual review
rows and CSV exports.

## Limits

Dates and persistent customer identifiers are unavailable. The dataset's
real/synthetic origin, exact label construction and feature availability at
prediction time have not been independently established. Results therefore do
not establish future performance or performance on entirely new people.

The [uncertainty analysis](F4_UNCERTAINTY_RESULTS.md) resamples rows after the
models are fitted and assumes those rows are independent. It does not include
retraining or temporal variation.

Removing age and gender changed local-baseline log loss by less than 0.001.
That does not establish unchanged individual predictions or fairness. TabPFN
was not rerun without these fields, and other inputs may act as proxies.

The app supports human review. It does not establish which support offer works,
automate contact or make a credit decision. Customer benefit requires a pilot
that measures actual support outcomes.
