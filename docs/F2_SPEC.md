# F2 — Financial Stress validation comparison

Frozen before tree-model results on 21 September 2026. This extends the
[Financial Stress contract](explanation/FINANCIAL_STRESS.md); the operator decision,
target, source limitations, feature set and final-holdout boundary remain unchanged.

## Comparison

Use the existing 24,000 training and 8,000 validation snapshots, all 182 predictors,
seed 3501 and a single CPU thread for each local model. No tuning or early stopping.
Constant prior and logistic regression retain their F1 settings. XGBoost uses 300
histogram trees, depth 4, learning rate 0.05, subsample 0.9, all columns per tree,
binary logistic objective and log-loss metric. Numeric median imputation and
categorical one-hot encoding fit only on training data; no numeric scaling for
trees. CatBoost uses 300 iterations, depth 4, learning rate 0.05 and Logloss, with
native categorical handling and a fixed missing-category marker. Its numeric
missing values remain native. No class weighting in any model.

TabPFN-3.5-Plus is the first hosted candidate: `v3.5_default`, eight estimators,
seed 3501, standard preprocessing/text systems, no Thinking. Inputs preserve raw
numeric and categorical values. The payload includes training features and labels,
and validation features only. IDs, validation labels, final-holdout rows and the
challenge's unlabelled Test.csv are excluded. Describe these inputs as external
challenge data with unverified real/synthetic origin, not synthetic benchmark data.

First check current service limits and the estimate using dimensions/settings
only. Plan for all training rows; do not silently subsample or split predictions
into separately billable requests. If capacity/cost requires a smaller cohort,
freeze a deterministic training subset and rerun all comparators on it. Obtain
approval for the concrete payload and estimated token ceiling before uploading.
Use one prediction attempt; preserve diagnostic evidence and stop on uncertain
billing or model identity. No automatic paid retries.

## Evidence and acceptance

Primary metric: log loss. Also AUROC, average precision, Brier, ten-bin calibration,
fixed 5%/10% review capture and errors. Rank ties by snapshot ID. Store validation
probabilities, data/feature-order hashes, package versions, source/lock hashes,
settings, fit/predict times and the identity of the training cohort. Timing is one
local run, not a controlled cross-service performance benchmark. Token estimates
are not currency charges or a guarantee of actual billing.

Tests must exercise native categorical prediction, matching row alignment,
reproducibility, corrupted partition rejection, no final-holdout reads, no network
or credentials in offline mode, ID/validation-label exclusion from payloads, and
an explicit upload/budget gate. Use invented fixtures only.

F2 remains in progress until a verified TabPFN Financial Stress prediction is
compared on these same validation rows. Age/gender exclusion and cohort checks are
still planned for F3. Do not select a model using the final holdout.
