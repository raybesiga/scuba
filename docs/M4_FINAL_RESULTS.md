# M4 final local results

Recorded 21 September 2026. **Local final evaluation, random reference and timing are complete. M4 is now complete for the approved scope; see the subsequent [hosted final-test results](M4_HOSTED_FINAL_RESULTS.md) and combined report.** All data are synthetic; these results demonstrate the workflow, not real-customer performance.

The [frozen final protocol](M4_FINAL_PROTOCOL.md) was recorded before test inference. It retains the original M2 recipes, training partitions, raw probabilities and thresholds. See the separate [validation results](M4_RESULTS.md) for hosted Plus; its validation AP must not be compared directly with local test AP.

## Final test results

The main split separates customers and time. The primary test contains 2,260 customers and 233 positives; customer overlap with both training and validation is zero. Each sensitivity seed has its own frozen cohort.

| Seed | Test rows | Positives | Logistic AP | XGBoost AP | CatBoost AP |
| --- | --- | --- | --- | --- | --- |
| 3501 | 2260 | 233 | 0.2712 | 0.3487 | 0.3522 |
| 3502 | 2272 | 231 | 0.2504 | 0.3050 | 0.3101 |
| 3503 | 2298 | 244 | 0.2679 | 0.3351 | 0.3404 |

Primary CatBoost minus XGBoost AP is **+0.0034**, with paired 95% customer-bootstrap interval **[−0.0167, +0.0281]**. This does not establish a clear lead. These intervals describe evaluation-customer uncertainty conditional on the fitted models, not training variation or real-world generalisation.

| Primary model | Log loss | Brier | ECE | 5% captured / 233 | 10% captured / 233 | TP / FP / FN / TN at 0.5 |
| --- | --- | --- | --- | --- | --- | --- |
| catboost | 0.2538 | 0.0771 | 0.0177 | 47 | 80 | 14 / 12 / 219 / 2015 |
| constant_prior | 0.3320 | 0.0925 | 0.0050 | 8 | 17 | 0 / 0 / 233 / 2027 |
| logistic_regression | 0.2868 | 0.0850 | 0.0302 | 35 | 73 | 9 / 28 / 224 / 1999 |
| xgboost | 0.2551 | 0.0778 | 0.0121 | 44 | 81 | 18 / 10 / 215 / 2017 |

The 5% and 10% review budgets select 113 and 226 customers respectively. At the frozen 0.5 threshold, CatBoost detects only 14 of 233 positives. Its 10% review budget captures 80; XGBoost captures 81. Review-budget metrics and threshold errors answer different questions. No threshold was retuned after seeing these results.

## Diagnostic random reference

| Seed | Logistic AP | XGBoost AP | CatBoost AP |
| --- | --- | --- | --- |
| 3501 | 0.3118 | 0.3682 | 0.3853 |
| 3502 | 0.2859 | 0.3675 | 0.3676 |
| 3503 | 0.2966 | 0.3686 | 0.3756 |

The primary random test has 12,024 snapshots from 8,583 customers; 8,017 of those customers also occur in random training. It mixes dates and differs in cohort size and composition. Higher random-reference AP is diagnostic only and cannot isolate a causal leakage effect. Differences are kept with their actual sign: primary CatBoost AP increases by 0.0332, while log loss worsens by 0.0195. Primary XGBoost 10% capture also decreases. The report and JSON preserve all declared signed metric differences.

## Controlled local timing

All four models ran in three separate sequential Python processes for each of three seeds and two regimes: **72 fits**. Every repetition produced byte-identical test and validation predictions. All temporal validation predictions matched their original M2 hashes. Test prediction preceded validation; transformations and estimators fit only training rows.

Primary temporal timings below are median [minimum, maximum] seconds. Measurements use Python 3.14.5 on macOS arm64 with one model thread. OS file caches were not flushed. Process wall time includes imports, data verification, preprocessing, metrics and file writes; these are local measurements, not portable service-latency estimates.

| Model | Estimator fit | Test estimator prediction | Process wall |
| --- | --- | --- | --- |
| catboost | 3.7541 [3.5482, 6.4674] | 0.0090 [0.0054, 0.0092] | 5.3539 [4.9080, 7.8725] |
| constant_prior | 0.0044 [0.0042, 0.0093] | 0.0003 [0.0002, 0.0029] | 1.5157 [1.4286, 1.9328] |
| logistic_regression | 0.0051 [0.0051, 0.0102] | 0.0001 [0.0001, 0.0002] | 1.3680 [1.3455, 1.4158] |
| xgboost | 0.1666 [0.1650, 0.1739] | 0.0026 [0.0026, 0.0039] | 1.4878 [1.4842, 1.4997] |

## Evidence and reproduction

The standalone report is `artifacts/m4-final-report/index.html`; its companion `report.json` records source hashes and signed gaps. Each source run contains complete metrics, reliability bins, review-budget and threshold errors, paired uncertainty, all declared archetype/activity slices and timing repetitions. Source predictions retain synthetic provenance.

All 110 tests, Ruff lint and formatting checks pass. Each thematic commit is checked as an isolated staged snapshot. Full evaluation/bootstrap replay, frozen input hashes, complete memberships and every prediction repetition are independently verified offline in `artifacts/m4-final-verification.json`. Report HTML/JSON replay byte for byte. Desktop visual checks cover layout, primary-seed navigation, reliability charts and subgroup expansion.

The executed final loader, worker, runner, evaluation and model sources remain unchanged across runs. Whole-package source inventories can also include report/integration modules being developed alongside the runs; those modules were not executed by the timed local workers.

| Seed / regime | Evaluation SHA-256 |
| --- | --- |
| temporal-3501 | `13c5cbb45f18a588bd160da87846c07059df428baa7dffca0dc7fa9dc0731752` |
| random_reference-3501 | `ef83706ef705a9b42893513ddea8016d8787b85c3c39a27e0b87577d35e4291d` |
| temporal-3502 | `c7c185799fa59f5ea94611c4d85f7fd74529ed5aba6b512323dcfd2a974d317c` |
| random_reference-3502 | `7fb5df9a88373bfe6771c97e2b08833c6b8890bb1dfaa8f3e2e3ba20dda7211d` |
| temporal-3503 | `b96d9726b82c19186142b258eb5cff48927dbc48a1ea238fdc0d4998bec63b47` |
| random_reference-3503 | `a290d2a538dd9988391f872887df60185ed4ebd1535dd6a23924df67bbd2fdbd` |

Reproduce primary local inference from the saved frozen plan into a new directory (no network or credentials):

```sh
PYTHONPATH=src .venv/bin/python -m scuba final-run \
  --input artifacts/m1-15000-seed-3501 \
  --plan artifacts/m4-final-plan-3501/plan.json \
  --plan-sha256 690e41ea476c2860cb6213a1e4b531861cf8bc9971ba0c7f61d62bbff2db93bc \
  --regime temporal \
  --output artifacts/m4-final-temporal-primary-repeat
```

Use `--regime random_reference` for the diagnostic run. For another seed, use its matching input and frozen plan/hash. Prediction bytes must match; timing values will vary. Rebuild the report from the six pinned source references with `scuba.final_report.build_report`; a single-command clean-environment demo rebuild remains M5 work.

## Primary hosted test plan — subsequently executed

The following plan was approved and executed once; the approval is consumed. See [accepted hosted evidence](M4_HOSTED_FINAL_RESULTS.md). The preserved offline review at `artifacts/m4-hosted-test-review/plan.json` is ready. It specifies one **268,433-byte CSV containing 2,260 synthetic rows and 11 features** uploaded to the Prior Labs TabPFN service, followed by one Plus prediction against the retained fitted resource. Customer IDs, dates and test labels stay local. There is no training upload, fit, automatic retry, variant change or hosted sensitivity run.

The proposed **10,000-token estimate ceiling** is provisional. Execution refreshes service limits and the estimate before uploading; it stops if the estimate exceeds the ceiling. This is not a verified credit balance or guaranteed billing cap. Actual token charges remain unavailable unless separately reported. No paid request or upload was made while preparing these final local results.

Historical execution command (already completed; do not reuse the consumed approval):

```sh
PYTHONPATH=src .venv/bin/python -m scuba.hosted_final \
  --plan artifacts/m4-hosted-test-review/plan.json \
  --plan-sha256 8b3dbec37458cbf588d114760e2dea43048964776ddd098a05ca1dd5b79aef0b \
  --output artifacts/m4-hosted-test-live \
  --allow-upload --max-estimated-tokens 10000
```

An expired resource, failed estimate, timeout or identity mismatch stops execution and preserves sanitised evidence; it does not trigger a refit or retry. If accepted, evaluate the saved Plus test predictions against the same primary local test cohort, add paired uncertainty and update the report. That comparison is now complete and recorded in the subsequent hosted results.
