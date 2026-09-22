# Financial Stress F2 — verified five-model validation comparison

21 September 2026. **Complete: four local comparators and TabPFN-3.5-Plus evaluated
on the same frozen validation rows.** The user authorised the reviewed hosted run
by instructing us to proceed. One prediction completed and passed offline evidence
verification. The final holdout has not been evaluated. See the [protocol](F2_SPEC.md).

## Validation comparison

Every model uses the same 24,000 training snapshots, 182 raw predictors and 8,000
validation snapshots (1,200 stress cases). No training subset, class weighting,
validation tuning or early stopping. Preprocessing fits on training rows only.

| Model | Log loss ↓ | AUROC ↑ | Average precision ↑ | Brier ↓ | Stress cases captured among 800 reviewed |
| --- | --- | --- | --- | --- | --- |
| TabPFN-3.5-Plus | **0.269368** | **0.887691** | **0.662456** | **0.080786** | **565 / 1,200 (47.08%)** |
| XGBoost | 0.301892 | 0.862231 | 0.598056 | 0.090769 | 529 / 1,200 (44.08%) |
| CatBoost | 0.326119 | 0.843393 | 0.565147 | 0.098019 | 502 / 1,200 (41.83%) |
| Logistic regression | 0.371897 | 0.756975 | 0.390954 | 0.111657 | 366 / 1,200 (30.50%) |
| Constant prior | 0.422709 | 0.500000 | 0.150000 | 0.127500 | 136 / 1,200 (11.33%) |

TabPFN-3.5-Plus has the best observed log loss, AUROC, average precision, Brier
score and review capture in this validation comparison. At 10% review capacity,
it captures 36 more stress cases than XGBoost among the same 800 reviewed snapshots
and produces 235 false positives. At 5%, it captures 334 of 1,200 cases among 400
reviewed snapshots, with 66 false positives.

These are descriptive validation results, not a tuned leaderboard, a statistical
significance claim or final-holdout performance. The prior's tied scores are ordered
by ID. Age/gender exclusion, cohort checks and final evaluation remain later steps.
Source timing, identity and label-definition limitations in the contract still apply.

[Combined verified metrics and audit](reference/financial-stress-verified-comparison-v1.json).
[Hosted execution and model identity](reference/financial-stress-hosted-validation-v1.json).

[Full local metrics, settings, timing and hashes](reference/financial-stress-comparison-v1.json).
Reported timings are single local measurements, not controlled service benchmarks.

## Executed TabPFN plan

- Service: Prior Labs TabPFN REST API; Plus alias `v3.5_default`, eight estimators,
  seed 3501, standard prediction. One fit and one prediction attempt; no paid retry.
- Training: 24,000 feature rows and their binary training labels.
- Prediction: 8,000 validation feature rows; 182 raw columns, including the profile
  fields specified in the contract. No snapshot IDs or validation labels uploaded.
- Excluded: all final-holdout rows and the unlabelled challenge Test.csv.
- Payload: 28,837,641 bytes across training features, training labels and validation
  features. Origin is labelled external challenge data, real/synthetic unverified.
- Live limit check accepts this complete cohort; no subsampling is needed.
- Live estimate: **10,000 tokens**, pricing version `quota_v3`. This is not an
  actual charge, currency amount, guaranteed billing cap or account credit balance.
- Plan SHA-256: `b30b83427a7fecb6c439e0ec47d54fed4159afeb3f85cc71d00a084a814a36d0`.

[Plan](reference/financial-stress-hosted-plan-v1.json) and
[metadata-only live preflight](reference/financial-stress-preflight-v1.json).
The runner requires a matching plan, explicit upload flag and positive approved
estimate ceiling before loading credentials. It refreshes limits/estimate before
upload and validates response dimensions, class order, probabilities and model
identity before accepting metrics. Diagnostics survive failed identity checks.

## Verification

- Ruff lint/format and 129 offline tests pass; tests use invented records only.
- Repeat local runs produce identical validation predictions and metrics.
- An independently exported staged snapshot passes all 129 tests and reproduces
  the full local comparison and live-estimated plan without a final.csv file.
- Offline planning produces the same plan as the live-estimated request.
- Mock REST tests cover approval/changed-plan rejection before credentials, budget
  rejection before upload, one prediction attempt, native source classification,
  model-identity failure with retained diagnostics, and no final-holdout reads.
- The live preflight sent only shapes/settings to the limits and estimate endpoints.
  It made no upload, fit or prediction request.

- The approved live run performed one training upload, fit, validation upload and
  prediction. Reported checkpoint: `/app/tabpfn_models/tabpfn-v3.5-20260909.safetensors`,
  accepted by the existing reviewed `plus-checkpoint-20260909-v1` identity policy.
  This verifies server-reported identity, not independent checkpoint-byte attestation.
- End-to-end hosted time was 58.07 seconds; fit 10.67 seconds and prediction 13.87
  seconds, including their request overhead. Upload time is included in the total.
  No cold/warm equivalence with local timings is claimed.
- Offline verification rechecked plan/input/response/prediction hashes, all 8,000
  row IDs and labels, saved response identity and probability dimensions. It
  independently recomputed all five models' log loss, AUROC, AP, Brier and 5%/10%
  capture using scikit-learn and direct ranked counts. Exactly one predict stage
  was recorded; verification made no network calls.
- XGBoost's saved CSV uses its native float32 representation. Verification restores
  that dtype before float64 metric calculation; parsing it directly as float64
  changes log loss by approximately 2.7e-12. No saved evidence was modified.

F2 is complete. Next is F3: the Financial Stress customer-care interface, cohort
checks and the planned feature-exclusion comparison. The current browser dashboard
still shows the archived synthetic experiment. See the [run procedure](how-to/FINANCIAL_STRESS.md).
