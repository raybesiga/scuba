# M2 — local comparator protocol

Declared before model fitting, 20 September 2026. This milestone implements reproducible local comparators; final test evaluation belongs to M4.

## Iteration compact

- Goal: establish constant-prior, logistic regression, XGBoost and CatBoost comparators on frozen M1 inputs.
- Decision and owner: the project owner compares modelling and integration effort; no customer action or deployment is authorised.
- Success: all four models produce finite, repeatable validation probabilities on identical rows for all three declared generator seeds, with reproducible settings and provenance. No required winner.
- Guardrails: train-only transforms, no test fitting/scoring, allowlisted predictors, synthetic inputs only, fixed candidate budget, no network in tests or training.
- Unacceptable mistakes: using future outcomes or metadata as predictors, tuning the generator to scores, hiding failed runs, claiming synthetic scores establish real-world utility.
- Acceptable tradeoffs: one fixed candidate per learned model; CPU, one thread; no search or calibration in M2. Native categorical treatment for CatBoost is intentional.
- Data: existing 15,000-customer M1 bundles for generator seeds 3501/3502/3503, fixed split seed 3501. Verify manifest and consumed-file hashes; preserve historical generator provenance.
- Grain: unique customer and prediction-date snapshot. Features use the preceding 60 days; active in preceding 30 days; label is no success in the following 30 days. See [experiment](EXPERIMENT.md).
- Signals: exactly the 11 existing predictors; IDs, dates, labels, archetype, activity and provenance remain metadata.
- Slices: archetype/activity support is recorded in M1; slice metrics and customer-bootstrap intervals belong to M4.
- Baseline: constant training prevalence, followed by logistic regression; tree comparators use the same rows and label.
- Airflow/MLflow: not applicable; local manifests and prediction files are sufficient.
- Fallback: fail explicitly and preserve completed per-model outputs; never silently substitute a model. Existing M1 bundles remain intact.
- Risks: synthetic mechanisms constrain interpretation; repeated training snapshots are correlated; timings depend on hardware and cache state; dependency/runtime changes can affect replay.

## Frozen candidates

Model seed is 3501 for every dataset. No candidate is selected from test performance.

| Model | Fixed configuration | Preprocessing |
| --- | --- | --- |
| Constant prior | Training positive fraction | None |
| Logistic regression | C=1, solver=lbfgs, max_iter=2000, tol=0.0001 | Numeric median imputation, standard scaling; one-hot categories with unknowns ignored |
| XGBoost | 300 trees, depth 4, learning rate 0.05, subsample 0.9, colsample_bytree 1, binary:logistic, hist, CPU, n_jobs=1 | Numeric median imputation; train-fitted one-hot categories with unknowns ignored |
| CatBoost | 300 iterations, depth 4, learning rate 0.05, Logloss, CPU, thread_count=1, no output files | Native string categories and native numeric missing values |

Unspecified estimator defaults are frozen by exact package versions and recorded in run metadata. Median imputation retains all-empty numeric columns using a zero fallback. There are no class weights, resampling, early stopping, calibration or threshold selection in M2. All fitted transforms use training rows only.

## Execution and evidence

Load main temporal train and validation rows only into model tables. The shared snapshot file also stores test rows: hash verification necessarily reads its bytes, but test feature/label values must never enter fitting or scoring. Check membership completeness and the existing group/date rules. Defer random-reference model runs to M4 because their training rows can overlap the main temporal test cohort.

Report validation average precision, log loss and Brier score as development checks, without final-test claims. Persist ordered validation predictions with snapshot keys, labels and synthetic flags; all models must share that order. Record input hashes, feature order, exact configuration, model/dependency versions, lockfile and recursive source hashes, runtime/hardware, seeds, preprocessing/fit/predict/end-to-end times, one repetition and unspecified cache warmth. Same-environment primary replay must reproduce predictions and metrics exactly; elapsed times are excluded from equality checks. No model persistence or external service is required.

Use uv with a committed dependency lock; install once, then execute locally without a resolver or network. Atomic commits group dependencies/protocol, shared baselines, each tree adapter, runner/integration checks, and measured results. Test every staged snapshot in isolation before committing. Mark M2 complete only after all three datasets and the primary replay pass.
