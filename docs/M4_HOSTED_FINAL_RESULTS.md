# M4 hosted final-test results

Synthetic benchmark archive. This dated record is separate from the
[Financial Stress entry](README.md). Status and test counts describe that milestone.

Recorded 21 September 2026. **M4 is complete for the approved scope.** The approved feature upload and single Plus prediction succeeded. The saved response was independently revalidated and evaluated offline; the complete report is `artifacts/m4-complete-report/index.html`. [Local final results](M4_FINAL_RESULTS.md) and [validation results](M4_RESULTS.md) remain distinct evidence records.

## Final comparison

All five models score the same 2,260 unseen synthetic customers, including 233 positives. Original training, 11 features, recipes, raw probabilities, thresholds and review budgets remain frozen. Higher observed AP does not establish a general winner.

| Model | AP | Log loss | Brier | ECE | Captured at 5% / 233 | Captured at 10% / 233 |
| --- | --- | --- | --- | --- | --- | --- |
| catboost | 0.3522 | 0.2538 | 0.0771 | 0.0177 | 47 | 80 |
| constant_prior | 0.1031 | 0.3320 | 0.0925 | 0.0050 | 8 | 17 |
| hosted_plus | 0.3601 | 0.2493 | 0.0769 | 0.0158 | 50 | 81 |
| logistic_regression | 0.2712 | 0.2868 | 0.0850 | 0.0302 | 35 | 73 |
| xgboost | 0.3487 | 0.2551 | 0.0778 | 0.0121 | 44 | 81 |

| Paired comparison | AP difference | 95% customer-bootstrap interval |
| --- | --- | --- |
| hosted plus minus xgboost | +0.0113 | [-0.0132, +0.0418] |
| hosted plus minus catboost | +0.0079 | [-0.0129, +0.0301] |

Both paired intervals include zero. Plus captures 81 positives at the 10% budget, equal to XGBoost and one more than CatBoost. At the 5% budget it captures 50, versus CatBoost 47 and XGBoost 44. These capture differences are descriptive point estimates; no capture confidence interval is claimed. At the frozen 0.5 threshold, Plus has TP 17, FP 16, FN 216 and TN 2011. No threshold or model was tuned using final outcomes.

All declared archetype and activity slices are included. None meets the predefined sparse flag, but some have few positives (steady: 21; high activity: 40), so their intervals are wide. Full slice metrics, paired comparisons, reliability bins and confusion counts are in the evaluation JSON. Intervals use 1,000 paired customer-cluster draws, seed 4401; they are conditional on these fitted models and synthetic customers, without multiplicity adjustment.

## Approved request and observed integration

User approval covered one 268,433-byte upload of 2,260 synthetic test-feature rows and one Plus prediction against the existing fitted resource. Only features were uploaded; test labels, identifiers and dates stayed local. The retained training set had 22,183 rows. No refit, training upload, fallback or retry occurred. This one-request approval is now consumed.

The fresh `quota_v3` estimate was **10,000 tokens**, exactly the approved estimate ceiling. Actual charges were not returned and are not inferred from the estimate. This does not establish the account credit balance.

| Stage | Observed seconds |
| --- | --- |
| get_model_limits | 1.024 |
| estimate_cost | 0.280 |
| prepare_test_set_upload | 0.410 |
| upload_final_test_features | 1.570 |
| predict | 5.004 |

Prediction took 5.004 seconds; the recorded network stages total approximately 8.288 seconds. These are single observations with a retained fitted resource, not a controlled speed comparison against fresh local model fits. Client preparation outside these stages is not included in the sum.

Server package version: `8.5.0`. Requested alias: `v3.5_default`. Reported checkpoint: `/app/tabpfn_models/tabpfn-v3.5-20260909.safetensors`. Acceptance used the existing narrow checkpoint policy together with v3.5 billing metadata, standard execution mode, configuration, class order, dimensions and probability checks. This verifies reported identity; checkpoint bytes were not independently attested.

## Verification and artifact integrity

All 112 tests, Ruff lint and formatting checks pass. Each thematic commit is verified in an isolated staged snapshot. New checks reject unverified/mock hosted evidence by default, altered captured responses, mismatched temporal cohorts and report sources. Tests use fictional local fixtures and no external dataset.

Offline replay independently rechecks the captured checkpoint metadata and probability matrix, matches saved probabilities and labels to the frozen test rows, recomputes point metrics, all subgroup diagnostics and paired bootstrap intervals, and rebuilds the report. Comparison and report replay byte for byte. Browser checks verify the hosted comparison table, uncertainty, calibration, capture/errors and subgroup expansion. No API call is made by these checks.

| Artifact | SHA-256 |
| --- | --- |
| Live manifest | `0263beeb279c644e947c109af65d58d30c64173484e91d0d705a277fafe6ac34` |
| Captured response | `bd048f14622f1b6445792a250daf828125562e43e3897b96045bf8267e1a4b62` |
| Test predictions | `2cc19c478b648f16eb845e525d5cfb8c01bc95bd3eac832847a5fcef30dfedd7` |
| Comparison manifest | `42e282f57cc94f65c0686a53141f4e399307088336ac3665e9c567f4da21ad39` |
| Comparison evaluation | `6de3e9277232f0ac272256525b28cba30d11159cfe50e38d89ce000e65051cf1` |
| Report manifest | `48d7ba0ef7bc6e5119a323f75a5638c7e621be68bcb867d3f3fd91694194f93e` |

Verification record: `artifacts/m4-hosted-final-verification.json`. Earlier local, validation and failed integration artifacts remain intact.

Reproduce the hosted comparison locally into a new directory, without credentials or network:

```sh
PYTHONPATH=src .venv/bin/python - <<'PY'
from pathlib import Path
from scuba.hosted_final_evaluation import evaluate_hosted_final
evaluate_hosted_final(
    Path('artifacts/m4-hosted-test-live'),
    '0263beeb279c644e947c109af65d58d30c64173484e91d0d705a277fafe6ac34',
    Path('artifacts/m4-final-temporal-3501'),
    '60eedc87e27e983634473b4125de657483e0986229a586230c98bbc45cd0a5bb',
    Path('artifacts/m4-hosted-final-comparison-repeat'),
)
PY
```

The completed report uses `scuba.final_report.build_report` with the six local references, the primary validation reference and `hosted_ref` pointing to this comparison and its pinned manifest hash. Earlier report artifacts preserve the pre-hosted state.

## Scope closure and next milestone

| Route | Final status / reason |
| --- | --- |
| Local temporal and random reference, seeds 3501–3503 | Complete, with three timing repetitions per model/regime/seed |
| Hosted Plus primary validation and temporal test | Complete and verified |
| Hosted Plus random reference and sensitivity seeds | Not run; no approved upload/prediction budgets |
| Hosted Fast and Thinking | Not run; no approved variant budgets |
| Local base model | Outside the approved hosted integration scope |
| Repeated hosted timing | Not run; approval covered one prediction |
| Actual hosted token charges | Unavailable in the response; estimate preserved separately |

These synthetic results do not establish real-world accuracy or customer benefit.
The subsequent [M5 record](M5_RESULTS.md) documents the completed offline rebuild
and clean-environment verification.
