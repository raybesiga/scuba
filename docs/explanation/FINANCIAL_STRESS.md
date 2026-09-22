# Financial Stress

Decision: 21 September 2026. The user selected customer financial stress as the
first operator use case. Nedbank transaction-volume forecasting is a later,
independent use case. A future use-case selector can connect the two; it must not
present forecasting as available before its own evaluation and workflow exist.
The existing synthetic dormancy dashboard remains a separate historical demo.

## Iteration compact and contract v1

- Goal: demonstrate TabPFN-3.5 in a reproducible customer-care prioritisation workflow.
- Operator decision / owner: a customer-care operator chooses review capacity and
  reviews a ranked list of customer snapshots with observed activity context.
- Success metric: validation log loss (lower is better); no required model winner.
- Guardrails: AUROC, average precision, Brier, calibration bins, top 5%/10% capture,
  false positives and false negatives. Later cohort checks report support alongside metrics.
- Unacceptable mistakes: treating stress as inactivity, claiming causality from
  feature trends, learning offer effectiveness without response labels, or claiming
  dates/customer separation that the files cannot establish.
- Acceptable tradeoff: row-holdout research evidence first; no deployment-valid claim.
- Source: user-supplied September Financial Stress challenge files, pinned by hash
  in `datasets/financial-stress/manifest.json`. Real versus synthetic origin is not
  established. Never add a synthetic flag or mix these records with M0–M5.
- Grain: one supplied customer snapshot, keyed by unique `ID`. ID is excluded from
  predictors; no separate persistent customer key is provided.
- Timing: six monthly summaries, M1 most recent and M6 oldest. No observation dates,
  event times, source freshness SLA or independent label-maturity checks are available.
- Target: released binary `liquidity_stress_next_30d`. The publisher describes the
  following 30 days, but the operational definition of stress is undocumented.
- Baselines: constant training prevalence and logistic regression without class
  weighting, to preserve a probability-quality baseline. All preprocessing fits
  on training rows only. Tree comparators and TabPFN follow on these same partitions.
- Candidate signals: all 182 supplied non-ID, non-target features for the initial
  benchmark, including profile fields. Age/gender usage requires a separate
  exclusion comparison and cohort review before any operational recommendation.
- Evaluation: sort by ID, fixed stratified 60/20/20 split, seed 3501. This gives
  24,000 training, 8,000 validation and 8,000 sealed final-evaluation rows. Split
  membership and feature order are hashed. Label counts are audited in each split;
  final predictions/metrics are not produced during baseline development.
- The supplied unlabelled 30,000-row Test.csv is inference-only, not a local score.
- Feature processing: dictionary types define numeric/categorical branches;
  median imputation and standard scaling for numeric features; most-frequent
  imputation and unknown-tolerant one-hot encoding for categoricals. Train only.
- Review selection: descending probability, ID as deterministic tie-breaker;
  budgets fixed at 5% and 10%, rounding up. This is review prioritisation, not an
  eligibility decision or a demonstrated intervention benefit.
- Evaluation slices: region, segment and earning pattern; age/gender audits and
  feature-exclusion comparison are planned before the operator demo is complete.
- Orchestration: local command-line artifacts now; no Airflow/MLflow dependency.
- Fallback: constant prior / local baselines, explicitly labelled; hosted model
  status must remain unavailable until a verified Financial Stress run exists.
- Known risks: unknown repeated customers/time overlap, undocumented label
  construction and feature availability, unknown dataset realism and representativeness.

## Delivery sequence

F0 pins source bytes, attribution, scope and audit. F1 freezes partitions and
establishes local validation baselines. F2 compares a tree model and verified
TabPFN-3.5, with model identity, settings, training subset (if needed), tokens and
runtime recorded. Prepare a bounded upload/budget plan before a hosted run.
F3 presents review capacity, ranked snapshots and observed monthly trends in the
Radix interface; any suggested care action is operator policy, not model efficacy.
F4 freezes settings, evaluates the sealed holdout once, checks cohorts and
reproduces the submission from a clean checkout. Prior Labs is the submission
priority; a Zindi leaderboard entry is optional later work.

This contract is independent of `docs/EXPERIMENT.md`, which continues to describe
only the frozen synthetic benchmark. No Financial Stress model is yet validated
for real customer decisions.
