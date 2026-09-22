# M4 — evaluation protocol v1

Declared 21 September 2026, after observing M2/M3 aggregate validation scores and before final test scoring. The [experiment contract](EXPERIMENT.md) remains authoritative. This is not a blinded preregistration: model validation rankings are already known.

## Iteration compact

- Goal: evaluate uncertainty, probability calibration and fixed outreach budgets, then prepare a reproducible comparison report.
- Decision and owner: the project owner assesses benchmark evidence and integration effort; no real customer or operational decision follows from synthetic results.
- Success metric: reproducible average precision (AP), with paired customer-bootstrap differences; no required winner.
- Guardrails: log loss, Brier score, calibration, capture/lift, errors, slice support, point-in-time windows, disjoint customer groups and explicit evidence status.
- Unacceptable mistakes: fitting on test outcomes, treating validation differences as final results, selecting only favourable slices/seeds, accepting unverified predictions or inferring deployment value.
- Tradeoffs: assess raw probability calibration without fitting a calibrator in this protocol. Keep the M2/M3 settings unchanged; any later calibration experiment needs a dated protocol amendment before test access.
- Sources and grain: frozen first-principles M1 bundles; one synthetic customer/date snapshot. Primary seed 3501, sensitivity seeds 3502/3503, split seed 3501.
- Feature timing and target: preceding 60-day predictors; currently active means success in the preceding 30 days; target is zero successes in the following 30 days. No feature or label changes.
- Baselines/signals: constant prior, logistic regression, XGBoost (primary tree comparator), CatBoost (challenger), hosted Plus requested with the accepted server-reported checkpoint. Exactly 11 existing predictors.
- Slices: all declared archetypes and low/medium/high successful-activity groups, including empty groups; metadata never enters predictors.
- Execution: local CLI, JSON artifacts and report; no Airflow or MLflow. No imports that authenticate and no API calls in evaluation.
- Fallback: reject changed hashes, keys, labels, non-synthetic or unaccepted runs. Preserve previous artifacts; each output directory must be new.
- Risks: synthetic distribution assumptions, one hosted seed, small subgroups, multiple exploratory comparisons, conditional bootstrap uncertainty and uncontrolled historical timing.

## First implementation: saved validation evidence only

Read the four completed M2 comparator predictions for each frozen seed, plus the M3 offline-revalidated live response for primary seed 3501. Pin their manifest hashes in the invocation, verify prediction hashes and join by exact snapshot keys and labels to frozen validation rows. Row order must not affect results. Reject missing, duplicate or extra rows. Preserve source hashes, model labels and original metrics; do not train, tune, fit a calibrator, consume test outcomes or make remote requests.

Current Plus predictions exist only for seed 3501. Seeds 3502/3503 contain local comparators only; report that absence rather than silently pooling unmatched runs. Fast/Thinking remain unexecuted because additional budgets were not approved. Local base execution remains outside this hosted integration scope.

## Point estimates and fixed decisions

- AP is the stepwise average-precision definition, with all equal-score rows handled together. It is unavailable for empty or single-class slices. Log loss clips probabilities to float64 machine epsilon; Brier is mean squared probability error. Both remain meaningful for nonempty single-class slices.
- Reliability uses ten fixed bins: `[0, 0.1)`, …, `[0.9, 1]`. Record count, mean probability and observed positive fraction; empty-bin means are null. ECE is the sample-weighted absolute bin gap. These are calibration diagnostics, not fitted recalibration.
- The fixed threshold is `p >= 0.5`. Report TP, FP, TN and FN.
- At fractions 0.05 and 0.10, select exactly `ceil(fraction * n)` rows by descending probability with ascending `(customer_id, prediction_date)` ties. Capture is selected positives / all positives; lift is selected positive fraction / cohort prevalence. Report the effective fraction, boundary score and confusion counts. For no positives, capture/lift are null. A tied boundary score alone is not a deployable threshold.
- Apply top fractions within each slice. These describe a separate within-slice budget, not allocation from the global selected set.
- Each slice records rows, unique customers, positives, negatives and prevalence. Flag sparse support when fewer than 50 rows or fewer than 10 observations of either label; flags do not suppress computable estimates.

## Uncertainty and comparisons

Use 1,000 nonparametric customer-cluster bootstrap draws, RNG seed 4401, sampling the original number of unique customers with replacement and carrying all their rows. Sort snapshot keys before resampling. Reuse the same draw across all models in each cohort/slice. Validation currently has one row per customer, but the implementation must preserve whole clusters for repeated snapshots.

Report 95% percentile AP intervals using linear quantiles at 0.025 and 0.975. Record attempted, valid and single-class draw counts. If fewer than 80% of draws have both classes, report the interval unavailable. Empty/single-class original slices have no AP interval. These are conditional on the fitted models and observed synthetic customers; they exclude refitting and generator uncertainty.

The primary paired comparison is hosted Plus minus XGBoost AP on seed 3501. Report hosted Plus minus CatBoost as secondary, and each learned model minus XGBoost as descriptive context on all available seeds. Compute interval endpoints from paired draw-wise differences, not differences of interval endpoints. Do not report p-values or declare a general winner. Slice intervals and comparisons are exploratory, without multiplicity adjustment. Sensitivity seeds remain separate summaries, not pooled independent customer draws.

## Later M4 steps and test boundary

1. Verify this offline evaluation slice and record validation findings, including unfavourable results and missing routes.
2. Keep model settings, raw-probability treatment, 0.5 threshold, top budgets and metrics frozen before implementing final temporal test inference. Local models may refit only on the original training partition; validation is not added to training. Test results cannot change these choices.
3. Implement the predeclared stratified random-row reference as a diagnostic after the main evaluation choices are frozen. Report overlaps, support/prevalence and signed random-minus-temporal differences, with lower-is-better directions explicit. Do not use random-reference results to retune the main pipeline.
4. Prepare explicit uploaded-row and token budgets for hosted test, random-reference, other variants or sensitivity seeds. Existing one-prediction approvals are consumed. Offline evaluation needs no new paid operation.
5. For controlled local timing, use three fresh-process fits/predictions per model and seed, one thread, with loading/imports reported separately; compare medians and ranges. Label cache warmth explicitly. Hosted timing repetition needs its own budget. Existing single-run latency remains observational.
6. Build the standalone report from verified artifacts, with a synthetic banner, missing-evidence labels, reliability plots, uncertainty, capture/lift, slice support and integration notes. M4 completes only when final evaluation/report work is performed or each unavailable route has a concrete documented reason.

## Verification and atomic commits

Use hand-calculated ranking/calibration/confusion examples, tied and endpoint scores, empty/single-class/sparse slices, whole-customer bootstrap tests, paired identical-model checks and tampered-input rejection. Confirm deterministic replay, unchanged inputs, zero API requests and no test scoring. Run `make check` for each staged snapshot. Commit protocol, metric/uncertainty tools, saved-evidence runner and measured results separately where dependencies permit.
