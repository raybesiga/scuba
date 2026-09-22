# M4 validation evaluation results

**Status: validation evaluation complete. M4 subsequently completed for the approved scope; see [hosted final results](M4_HOSTED_FINAL_RESULTS.md).** Updated 21 September 2026. The new offline tools evaluated saved predictions for all three frozen seeds under [M4 protocol v1](M4_SPEC.md). Hosted Plus is available for seed 3501 only. No model was trained, no API request was made and no test prediction was produced.

Plus retains the highest observed primary AP, but both paired AP-difference intervals against the tree comparators include zero. This evidence does not establish a stable advantage. At the primary 10% review budget, Plus identifies 95 of 269 positive outcomes versus CatBoost’s 93 and XGBoost’s 92. These are synthetic validation diagnostics, not intervention effects or deployment results.

## Primary calibration and ranking

There are 2,407 primary validation customers and 269 positives (11.18%). Intervals use 1,000 paired customer-cluster bootstrap draws, seed 4401. Each interval conditions on the existing fitted model and this simulated cohort.

| Model | AP | 95% AP interval | Log loss | Brier | ECE (10 bins) |
| --- | --- | --- | --- | --- | --- |
| Constant prior | 0.1118 | [0.1001, 0.1234] | 0.3502 | 0.0993 | 0.0036 |
| Logistic regression | 0.2956 | [0.2525, 0.3493] | 0.3053 | 0.0895 | 0.0159 |
| XGBoost | 0.3510 | [0.2999, 0.4105] | 0.2825 | 0.0848 | 0.0130 |
| CatBoost | 0.3562 | [0.3019, 0.4171] | 0.2832 | 0.0847 | 0.0078 |
| Hosted Plus requested | 0.3734 | [0.3141, 0.4355] | 0.2743 | 0.0831 | 0.0076 |

ECE is a coarse, bin-dependent calibration diagnostic. The constant prior has low ECE but weak ranking, so calibration alone does not select the best model. Raw probabilities are unchanged; no calibrator was fitted.

| Paired comparison | AP difference | 95% paired interval |
| --- | --- | --- |
| Hosted Plus requested − XGBoost | +0.0224 | [-0.0018, +0.0469] |
| Hosted Plus requested − CatBoost | +0.0172 | [-0.0043, +0.0379] |
| CatBoost − XGBoost | +0.0053 | [-0.0123, +0.0232] |
| Logistic regression − XGBoost | -0.0554 | [-0.0938, -0.0112] |

All 1,000 primary draws contained both classes. These are paired difference intervals; overlap between separate model intervals was not used to assess a difference. Slice comparisons are exploratory, without multiplicity correction.

## Fixed review budgets and errors

All top-5% selections contain 121 customers; top-10% selections contain 241. Ties use snapshot keys. Counts below are TP / FP / FN. Lift compares the selected positive fraction with overall prevalence.

| Model | Top 5% capture | Top 5% lift | Top 5% TP / FP / FN | Top 10% capture | Top 10% lift | Top 10% TP / FP / FN |
| --- | --- | --- | --- | --- | --- | --- |
| Constant prior | 3.7% | 0.74 | 10 / 111 / 259 | 8.9% | 0.89 | 24 / 217 / 245 |
| Logistic regression | 17.5% | 3.48 | 47 / 74 / 222 | 32.3% | 3.23 | 87 / 154 / 182 |
| XGBoost | 19.7% | 3.92 | 53 / 68 / 216 | 34.2% | 3.42 | 92 / 149 / 177 |
| CatBoost | 19.3% | 3.85 | 52 / 69 / 217 | 34.6% | 3.45 | 93 / 148 / 176 |
| Hosted Plus requested | 19.3% | 3.85 | 52 / 69 / 217 | 35.3% | 3.53 | 95 / 146 / 174 |

At the fixed 0.5 threshold, Plus has TP=32, FP=17, TN=2,121 and FN=237. It captures fewer positives than the top-budget policies because it selects only 49 customers. The threshold is not changed after seeing this result. Constant-prior top-budget rankings come entirely from deterministic tie-breaking; realised lift need not equal one.

## Primary subgroup support

All declared primary slices pass the protocol’s support flag, but some intervals remain wide. In particular, the steady archetype has only 31 positive outcomes. AP values across groups have different prevalence baselines and should not be read as a causal or fairness ranking.

| Slice | Customers | Positives | Prevalence | Plus AP | 95% AP interval | Sparse flag |
| --- | --- | --- | --- | --- | --- | --- |
| archetype: sporadic | 811 | 169 | 20.8% | 0.2793 | [0.2328, 0.3358] | false |
| archetype: steady | 930 | 31 | 3.3% | 0.3794 | [0.2115, 0.5566] | false |
| archetype: tapering | 666 | 69 | 10.4% | 0.5328 | [0.4133, 0.6587] | false |
| activity_level: high | 1287 | 61 | 4.7% | 0.4398 | [0.3205, 0.5671] | false |
| activity_level: low | 318 | 87 | 27.4% | 0.3360 | [0.2599, 0.4331] | false |
| activity_level: medium | 802 | 121 | 15.1% | 0.3383 | [0.2598, 0.4224] | false |

Each JSON artifact includes every model’s metrics, reliability-bin support, errors, budget results and AP intervals for every declared archetype and activity slice. Within-slice top budgets are separate hypothetical budgets; they are not the slice composition of the global selected set.

## Sensitivity seeds

| Seed | Validation customers | Positives | Logistic AP | XGBoost AP | CatBoost AP | Hosted Plus |
| --- | --- | --- | --- | --- | --- | --- |
| 3501 | 2407 | 269 | 0.2956 | 0.3510 | 0.3562 | 0.3734 |
| 3502 | 2382 | 273 | 0.3306 | 0.3727 | 0.3843 | Not run; no approved seed budget |
| 3503 | 2397 | 251 | 0.2759 | 0.3422 | 0.3362 | Not run; no approved seed budget |

CatBoost minus XGBoost paired AP intervals include zero on all three seeds; the observed ordering reverses on seed 3503. No hosted seed-sensitivity claim is possible from the single Plus run. Seed summaries remain separate.

## Verification and reproduction

All 100 tests and Ruff checks pass, including isolated staged snapshots. AP/log-loss/Brier examples match the installed scikit-learn implementation; hand calculations cover tied AP thresholds, calibration endpoints, exact budget rounding and confusion counts. Bootstrap checks preserve complete repeated-customer clusters and produce zero paired difference for identical model outputs. Integration tests reject changed hashes, keys, labels, non-synthetic rows, mismatched input cohorts and unaccepted hosted evidence.

All three full-size evaluations and manifests replay byte for byte with network access disabled. Source input and prediction hashes remain unchanged. Reliability counts and confusion counts reconcile to the cohort totals; archetype and activity groups each partition the validation cohort. See `artifacts/m4-validation-verification.json`.

| Seed | Evaluation JSON SHA-256 |
| --- | --- |
| 3501 | `6ddcf68842b1abaf49b1407fba942bc0288ac34b7d26f285880af10ce32f65e1` |
| 3502 | `b4f6b79d541cbb091871134f48290ea60f08fc0ad4522619b1c058fa9349246e` |
| 3503 | `4efc25bf39455a61f2f56f893a0905f3d059dcbc5d55d6d0d9dc6a501f7336d6` |

Reproduce the primary evaluation into a new directory:

```sh
.venv/bin/scuba evaluate \
  --input artifacts/m1-15000-seed-3501 \
  --local-run artifacts/m2-seed-3501 \
  --local-manifest-sha256 f9f201e7ca9fdb698425d5354f49ec42259f01d0e9de838d4a4635efc229b361 \
  --hosted-run artifacts/m3-plus-continuation-revalidated \
  --hosted-manifest-sha256 59e030bff20ea8550772d4a8c1da74defdd3572ce991f121e88b14f9210a0a60 \
  --output artifacts/m4-validation-primary-repeat
```

For seed 3502 or 3503, use that seed’s frozen input and M2 run with its pinned manifest hash, and omit both hosted arguments. Evaluation has no online mode and does not fit models. Outputs contain aggregate synthetic diagnostics; source predictions and row-level provenance remain in their original artifacts.

## Subsequent M4 work

The [final local results](M4_FINAL_RESULTS.md) now complete temporal test inference, the diagnostic random reference, controlled timing and the standalone report. This document remains the validation-only record. The [hosted primary test comparison](M4_HOSTED_FINAL_RESULTS.md) is also complete; M4 is complete for the approved scope. Frozen model settings are unchanged.
