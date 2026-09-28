# M2 results — local comparators

Synthetic benchmark archive. This dated record is separate from the
[Financial Stress entry](README.md). Status and test counts describe that milestone.

**Status: complete, 20 September 2026.** All four local comparators ran on the frozen 15,000-customer M1 bundles for seeds 3501/3502/3503. All 46 tests pass in both the project environment and a fresh environment installed offline from the uv cache. Primary predictions and metrics replay byte for byte in that fresh environment. These are synthetic validation results; no test cohort was fitted or scored.

## Protocol and cohorts

The [predeclared M2 protocol](M2_SPEC.md) fixed one candidate per model, model seed 3501, one CPU thread, no tuning, no class weighting and no calibration. All models use the same 11 predictors and ordered rows. Logistic regression and XGBoost fit imputation/encoding on training rows only; logistic also scales numeric inputs. CatBoost handles categories and numeric missingness natively. The constant reference uses training prevalence.

| Generator seed | Training rows | Training customers | Training positives | Validation rows/customers | Validation positives |
| --- | ---: | ---: | ---: | ---: | ---: |
| 3501 | 22,183 | 8,405 | 2,399 | 2,407 | 269 |
| 3502 | 22,068 | 8,373 | 2,329 | 2,382 | 273 |
| 3503 | 22,121 | 8,367 | 2,310 | 2,397 | 251 |

Training dates remain April/May/June and validation August 2032, with disjoint customer groups and mature labels. The shared snapshot file is read for hash verification and key reconciliation; test feature/label values are excluded before model tables are built. Diagnostic random-reference model runs are deferred to M4 because their training rows can include main-test customers/dates.

## Validation metrics

Average precision (AP) is the specified PR-AUC; higher is better. Lower log loss and Brier are better. Values below are rounded; local JSON files retain full precision.

| Seed | Model | AP | Log loss | Brier |
| --- | --- | ---: | ---: | ---: |
| 3501 | Constant prior | 0.111757 | 0.350241 | 0.099281 |
| 3501 | Logistic regression | 0.295563 | 0.305311 | 0.089531 |
| 3501 | XGBoost | 0.350960 | 0.282502 | 0.084812 |
| 3501 | CatBoost | 0.356238 | 0.283208 | 0.084687 |
| 3502 | Constant prior | 0.114610 | 0.356471 | 0.101557 |
| 3502 | Logistic regression | 0.330624 | 0.302476 | 0.088945 |
| 3502 | XGBoost | 0.372673 | 0.286930 | 0.085583 |
| 3502 | CatBoost | 0.384328 | 0.283548 | 0.084669 |
| 3503 | Constant prior | 0.104714 | 0.335320 | 0.093749 |
| 3503 | Logistic regression | 0.275875 | 0.293913 | 0.085818 |
| 3503 | XGBoost | 0.342164 | 0.271473 | 0.080814 |
| 3503 | CatBoost | 0.336196 | 0.274097 | 0.081426 |

The learned models improve on the constant check on all three validation datasets. CatBoost has slightly higher AP on seeds 3501/3502; XGBoost has higher AP on 3503 and lower log loss on 3501/3503. These small differences do not establish a consistent winner or statistical significance. XGBoost remains the predeclared primary tree comparator and CatBoost the challenger. No configuration changed after viewing these scores.

## Runtime and provenance

Verified runtime: Python 3.14.5, macOS 26.6.2, ARM64, 10 logical CPUs available; model and numeric-library thread limits set to one. Dependency management uses uv 0.11.7 and committed `uv.lock`. Direct dependencies: numpy 2.5.3, pandas 3.0.6, scikit-learn 1.9.1, XGBoost 3.4.1, CatBoost 1.2.10 and threadpoolctl 3.7.0. The lock also resolves transitive dependencies. Other operating systems and Python versions are unverified.

Primary-run timings in seconds:

| Model | Fit preprocessing | Estimator fit | Prediction preprocessing | Estimator prediction | Model end-to-end |
| --- | ---: | ---: | ---: | ---: | ---: |
| Constant prior | 0.000000 | 0.005022 | 0.000000 | 0.000317 | 0.025885 |
| Logistic regression | 0.020433 | 0.005326 | 0.002241 | 0.000160 | 0.037116 |
| XGBoost | 0.016427 | 0.178288 | 0.002848 | 0.003486 | 0.212271 |
| CatBoost | 0.000000 | 3.689180 | 0.000000 | 0.001644 | 3.700463 |

Input verification/loading took 0.283s and feature-table construction 0.078s; the primary runner body took 4.379s overall. Times exclude process startup/imports, use one repetition per run and have uncontrolled cache warmth/system load; some runs overlapped verification work. They confirm working instrumentation, not a controlled latency comparison. End-to-end model time includes transforms, metrics and artifact work; CatBoost's internal preprocessing is included in estimator time. M4 must define repeated cold/warm measurements before drawing speed conclusions. Local runs used zero API tokens and no uploads.

The manifests record input-file hashes, historical M1 manifest hashes, current recursive model/package source hashes, lock hash, exact settings and resolved tree parameters, dependency/runtime versions, seeds, cohort key hashes and timings. Source provenance for the frozen M1 bundles is retained, not replaced by M2 code hashes.

## Verification and local evidence

- `make test`: all 46 tests pass. Every implementation commit also passed tests from an isolated copy of its staged contents.
- Offline fresh install: `uv sync --offline --locked --extra models` into a new environment using Python 3.14.5; all 46 tests pass there too.
- All three full runs: input hashes, source/lock hashes, row identities, labels, probability bounds, prediction/metric file hashes and constant-prior prevalence verified. Metrics independently recomputed from saved prediction files match exactly.
- Primary replay: all eight prediction/metric files are byte-identical; settings, resolved parameters, classes, cohort keys, source and dependency hashes match. Manifests differ in elapsed timings by design.
- Adversarial tests: altered input files, unapproved manifests and missing/forged memberships are rejected; invalid held-out feature/label values do not affect fitting or predictions; validation-only categories do not enter fitted encoders; failed runs retain completed outputs and record failure; existing outputs cannot be overwritten.

Ignored local evidence directories are `artifacts/m2-seed-3501`, `artifacts/m2-seed-3502`, `artifacts/m2-seed-3503` and `artifacts/m2-primary-replay`. Each contains a manifest and four pairs of prediction/metric files. `artifacts/m2-verification.json` records the aggregate checks. Data/predictions remain local and are not committed.

| Run | Manifest SHA-256 |
| --- | --- |
| 3501 | `f9f201e7ca9fdb698425d5354f49ec42259f01d0e9de838d4a4635efc229b361` |
| 3502 | `48d0465d56a24fbd6e0a7d1be6373c39a0154ab15ea88c6e32cc40be0c3b2cd4` |
| 3503 | `650550b3d5c5f95120a9d1f53a73923c1f9e973f646966e991e5f764ed49fa46` |
| Primary replay | `6f29fc564e6b4c7336851742c90a7acef55157925fd83a68243d28ffaaf7662c` |

## Reproduce and continue

With the existing approved M1 inputs and installed locked dependencies, use a new output directory:

```sh
.venv/bin/scuba benchmark --input artifacts/m1-15000-seed-3501 --output artifacts/m2-primary-repeat
```

Repeat for seeds 3502/3503. M1 root manifests include historical package-source hashes, so regenerating with modified M2 sources creates a different, deliberately rejected manifest. To reconstruct missing frozen bundles, use M1 commit `8abfc39` with Python 3.14.5 and the declared M1 seed/configuration, then run M2 against those bundles. M5 will package the full clean-checkout reproduction workflow.

Hosted integration and final evaluation subsequently completed. See the
[archive guide](SYNTHETIC_ARCHIVE.md).
