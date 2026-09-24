# SCUBA roadmap

Planning date: 20 September 2026. Submission deadline: **6 October 2026, 23:59 CEST** (23:59 Africa/Blantyre), confirmed against the user-supplied hackathon terms.

Active status: **Financial Stress F0–F3 complete for the local validation demo; F4 final evaluation and local submission preparation are complete. The full-data service run returned predictions, with a column-count verification issue unresolved; publication review remains. Nedbank modelling is deferred.**

Preserved synthetic benchmark status: **M0–M5 complete for the approved technical scope; delivery review remains.** Final local temporal tests, diagnostic random-reference evaluations and 72 timing fits cover all three frozen seeds. The approved primary TabPFN-3.5-Plus final-test prediction is verified and included in the standalone report. TabPFN-3.5-Plus AP is 0.3601 versus CatBoost 0.3522 and XGBoost 0.3487; paired intervals against both include zero. All 117 Python tests and Ruff checks pass; four UI tests, TypeScript and formatting also pass. The [Radix report](RADIX_REPORT.md) uses the requested light/dark palette; its TypeScript and formatting checks also pass. The [dashboard overview](DASHBOARD.md), [one-command rebuild](DEMO_REBUILD.md) and [demo storyboard](DEMO_STORYBOARD.md) are complete. A fresh dependency installation reproduced identical dashboard bytes; see [M5 results](M5_RESULTS.md). Spoken delivery still needs presenter rehearsal. Additional hosted variants, random-reference and sensitivity runs were not budgeted; actual token charges are unavailable. See [hosted final results and scope closure](M4_HOSTED_FINAL_RESULTS.md), [local final results](M4_FINAL_RESULTS.md) and [checkpoint resolution](M3_CHECKPOINT_RESOLUTION.md).

## Release readiness update — 24 September 2026

- Complete: equal-capacity operator comparison, final paired uncertainty and
  fresh-dependency release verification. 158 Python tests and 18 UI tests pass;
  all eight rebuilt demo files match the staged release byte-for-byte.
- Ready for review: updated two-minute demo script and private release package.
- Remaining: presenter rehearsal, final owner review, authorised public release
  and hackathon submission. The full-data metadata issue remains separate and
  its predictions remain excluded from this demo.

See [release readiness](RELEASE_READINESS.md) and
[final uncertainty](F4_UNCERTAINTY_RESULTS.md).

## Active priority — Financial Stress

Decision confirmed by the user on 21 September 2026: **Prior Labs first, Financial
Stress first.** The first use case predicts the released 30-day liquidity-stress
outcome and helps a customer-care operator prioritise a review list. This is a
separate experiment from both Nedbank forecasting and the completed M0–M5
synthetic dormancy benchmark. See the [Financial Stress contract](explanation/FINANCIAL_STRESS.md).

| Milestone | Status | Acceptance criteria |
| --- | --- | --- |
| F0 — source package and contract | Complete (local scope) | Pin the five supplied files, provenance, declared data licence and audit; record the 30-day target and row-holdout limitations. |
| F1 — frozen partitions and local baselines | Complete | Reproducible 24,000/8,000/8,000 train/validation/final split; training-only preprocessing; constant-prior and logistic validation metrics; sealed final evaluation; offline checks. |
| F2 — TabPFN-3.5 comparison | Complete | Tree baseline and verified TabPFN model identity on the same frozen evaluation rows; explicit training subset if required; probabilities, calibration, review-budget capture and recorded cost/runtime. Prepare a bounded hosted-run plan before upload. |
| F3 — customer-care workflow | Complete (local validation demo) | Radix interface with review capacity, ranked snapshots, observed monthly trends and a review-list export. Cohort checks and local-baseline age/gender exclusion comparison (TabPFN exclusion run not performed); actions labelled as operator policy, not demonstrated treatment benefit. |
| F4 — final evidence and Prior Labs submission | In progress (final comparison verified; publication pending) | Freeze settings, evaluate the reserved holdout, verify clean-checkout reproduction and input access, review attribution and public repository contents, prepare the demo and submission. Publishing requires approval. |

[F0–F1 verification and results](F1_RESULTS.md) record the source audit, baseline
metrics and offline checks. The [F2 comparison protocol](F2_SPEC.md) now governs local trees and hosted preflight.
[Verified five-model comparison](F2_RESULTS.md) is complete. TabPFN-3.5-Plus has
validation log loss 0.2694 versus XGBoost 0.3019, and captures 565 versus 529 of
1,200 stress cases when reviewing 800 snapshots. These are validation point
estimates. [F4 final results](F4_RESULTS.md) are now verified separately: TabPFN
log loss 0.2799 versus XGBoost 0.3073 and 542 versus 512 captured at 10% capacity. [F3 results](F3_RESULTS.md) record
the completed operator workflow and cohort/local feature-exclusion checks.

A Zindi leaderboard submission is optional later work and is not an acceptance
criterion for these milestones. The Financial Stress workspace is now the active
dashboard; the historical synthetic benchmark remains accessible through its archive.
F4 has frozen the recipe and evaluated the reserved holdout. The
[submission draft](PRIOR_LABS_SUBMISSION_DRAFT.md) and portable replay are prepared.
The [full-data run](FINANCIAL_STRESS_FULL_DATA_RESULTS.md) fitted all 40,000 labelled
rows and returned 30,000 unlabelled predictions on 22 September. Local acceptance
is pending: the server reports 184 columns for the verified 182-column upload.
Its outputs remain separate from the frozen quality evaluation and dashboard.
One authorised diagnostic reused those resources with complete response capture:
it returned identical probabilities and the same 184-column count. No additional
prediction is planned. F4 delivery proceeds using the verified reserved holdout;
the full-data output remains explicitly unverified.

## Later use case — Nedbank transaction-volume forecasting

The source package is retained, but further Nedbank modelling is **deferred until
the Financial Stress workflow is complete**. Forecast transaction volume for
operational planning; do not imply cash/float stockout predictions without the
necessary balance and replenishment information. Earlier derived 7/14-day
inactivity experiments are outside the active scope.

| Milestone | Status | Acceptance criteria |
| --- | --- | --- |
| N0 — source package and submission requirements | Complete (local scope) | Supplied files pinned in local Git with exact hashes, original attribution and offline reconstruction. [Verification](N0_RESULTS.md); public distribution remains unresolved. |
| N1 — forecasting data audit and contract | Deferred | Establish historical windows, source timing, the supplied transaction-count outcome and an appropriate evaluation split. |
| N2 — TabPFN forecasting comparison | Deferred | Reproducible regression runs and local comparators on frozen Nedbank cohorts. |
| N3 — forecasting operator workflow | Deferred | Forecast volumes, identify expected peaks and provide grounded planning context. |
| N4 — release verification | Deferred | Resolve source retention/publication conditions and verify clean-checkout replay. |
| Shared use-case selector | Planned after both workflows | Switch between Financial Stress and Transaction-volume forecasting with separate targets, data, metrics and readiness status; never present unimplemented forecasting as available. |

See [submission requirements](HACKATHON_SUBMISSION.md). The historical goal and
milestone record below remain the synthetic experiment's record.

## Goal

Build a polished, reproducible TabPFN-3.5 evaluation demo: identify fictional active mobile-money customers at risk of 30-day dormancy, and show what it takes to integrate the model responsibly. Synthetic performance demonstrates the workflow, not real-world accuracy or intervention value. A model win is not an acceptance requirement.

## Milestones and acceptance

Status reflects progress independently of target dates: **Planned**, **In progress**, **Deferred**, **Blocked**, or **Complete**.

| Target | Milestone | Status | Acceptance criteria |
| --- | --- | --- | --- |
| 20 Sep | M0 — specification and scaffold | Complete | One-page contract, provenance policy, source register, runnable local fixture generator and passing contract tests. No benchmark claims. |
| 21–23 Sep | M1 — generator and snapshots | Complete | Versioned first-principles simulation; deterministic manifests and hashes; all feature boundaries, eligibility, censoring and customer separation tested; cohort counts recorded. |
| 24–26 Sep | M2 — local comparators | Complete | Logistic regression, XGBoost and CatBoost run on identical cohort definitions; train-only preprocessing; validation-only choices; dependency lock and run metadata. |
| 27–29 Sep | M3 — TabPFN integration | Complete | Mock-tested adapter, explicit version/variant and budget preflight; approved live run if access permits; otherwise documented skip, never fabricated scores. |
| 30 Sep–2 Oct | M4 — evaluation and report | Complete | Temporal/grouped and random-reference results, subgroup uncertainty, calibration, capture/lift, errors, latency and consumption; integration observations separate from scores. |
| 3–5 Oct | M5 — demo rehearsal | Complete | One command rebuilds the local report; a 2–3 minute storyboard covers scenario, split audit, results and integration tradeoffs; clean-environment replay passes. |
| 6 Oct | Submission buffer | Planned | Final local review; publication and submission remain subject to explicit approval. |

## Validation plan

- Unit tests: seed repeatability, schema, event status semantics, window edges, censored labels, no future influence on features, group stability, and manifest integrity.
- Split audit: unique snapshot keys; disjoint customer sets; all training labels mature before validation and all validation labels before test; show discarded rows and cohort prevalence.
- Model checks: constant-prior reference alongside the three learned baselines; finite probability bounds, stable class order, train-only encoders, reproducible seeds and equal comparison budgets.
- Evaluation checks: hand-calculated examples for capture, lift and confusion counts; single-class/empty slices report unavailable values with reasons; customer-cluster bootstrap intervals for repeated snapshots.
- Integration checks: offline fixtures for authentication errors, schema failures, timeouts and quota/rate limits; no network in default tests. Record real evidence only after an approved live run.
- Release check: fresh local environment, exact dependency versions, artifact hashes, complete source/seed/config metadata, accessible report, and a timed demo rehearsal.

## Scope and completion bar

In scope: fictional event simulation, point-in-time customer snapshots, comparison of model quality and integration friction, local HTML/JSON reports, and a demo storyboard. Primary models: logistic regression, XGBoost, CatBoost; TabPFN-3.5 base, Fast and Thinking when available, with TabPFN-3.5-Plus explicitly distinguished. LightGBM is omitted unless a later documented question justifies it. TimesFM is excluded.

Out of scope: operational scoring, real-customer decisions, intervention/causal claims, large tuning searches, dashboards requiring hosted services, cloud deployment, public repositories, publication and uploads without approval.

**Initial handoff complete:** M0 artifacts work locally, tests pass, implemented versus planned work is explicit, and M1 has a concrete next step. **Submission ready:** M1–M5 pass, including at least one verified TabPFN-3.5-family run; spoken delivery is rehearsed; current submission rules are confirmed; final materials are approved for sharing. If access prevents the verified model run, the local workflow can be complete but the TabPFN submission remains incomplete. Fast/Thinking skips must name the reason. No milestone requires TabPFN to outperform a comparator.

## Staged implementation

1. **Generator — complete (`simulation.py`):** v1 implements per-customer activity, stochastic state changes, shocks, failures/reversals and calendar variation. Seeds 3501/3502/3503 are recorded without selecting for model rankings. The M0 `generator.py` smoke fixture remains available.
2. **Snapshots — complete (`features.py`, `splits.py`):** 11 allowlisted predictors, future labels and eligibility exclusions; provenance and slice metadata stay outside model inputs. Grouped temporal and diagnostic random-reference memberships have separate auditable outputs.
3. **Baselines — complete (`models/`):** uv locks pandas/scikit-learn/XGBoost/CatBoost and their dependencies; all four local comparators have reproducible validation-only results across the three frozen M1 datasets. Logistic: imputation, scaling and one-hot encoding. XGBoost: train-fitted encoding. CatBoost: native categorical inputs. Fit all transforms on training rows; bound tuning to validation with the same candidate budget.
4. **TabPFN (`models/tabpfn.py`):** lazy optional dependency, raw categorical feature table, explicit variant, seed/settings and class order, no import-time authentication. Default offline; an approved live run needs a deliberate upload flag plus a token budget. Verify estimator/API contracts against current docs. Log sanitised errors; cache predictions with data/config/model hashes.
5. **Evaluation (`evaluation.py`):** shared probability interface and all specified metrics; freeze thresholds/calibration before test access. Keep label-permutation and constant-prior checks. Diagnose an observed optimism gap without forcing its sign.
6. **Report (`final_report.py`):** local standalone HTML plus machine-readable JSON; synthetic banner, cohort/split audit, model status, slices, reliability plot, top-k table, latency/cost and limitations. Keep integration evidence in its own section sourced from the separate observation log.

Stages are proposals, not unattended scheduled work. Do not commit, push, create external resources, publish or upload data without explicit approval.
