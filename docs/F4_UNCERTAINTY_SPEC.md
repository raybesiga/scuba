# F4 uncertainty addendum

Added after viewing final point estimates, on 24 September 2026. This is a
post-hoc uncertainty analysis, not a new test or model-selection step.

Use the retained 8,000 final rows and frozen predictions. Compare TabPFN-3.5-Plus
with the predeclared primary comparator, XGBoost. Report TabPFN minus XGBoost
for mean log loss and stress cases found at the existing 5% and 10% review budgets.

Use 2,000 ordinary paired row-bootstrap resamples, seed 3501, each of size 8,000
with replacement. Resample the same rows for both models. Re-rank within each
resample at each fixed review capacity; break probability ties by snapshot ID.
Report percentile 95% intervals (2.5th and 97.5th percentiles). Negative log-loss
changes favour TabPFN; positive capture changes favour TabPFN.

Rows are assumed independent. Persistent customer identifiers and dates are
absent, so these are not customer-cluster or time-based intervals. They quantify
sampling variation conditional on the fitted models and this dataset, not
retraining variation, future deployment performance or intervention benefit.
No feature changes, new predictions, tuning or API calls are involved.
