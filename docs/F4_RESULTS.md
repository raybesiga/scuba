# F4 — final holdout and submission preparation

21 September 2026. The five-model reserved-holdout comparison is verified. The
full-data inference plan and local submission materials are prepared. Public
publication, form submission and the separate full-data inference run have not
occurred as of this 21 September record. **22 September update:** the separately
approved full-data run returned predictions, but acceptance is pending a server
column-count discrepancy; see [full-data execution](FINANCIAL_STRESS_FULL_DATA_RESULTS.md).
See the pre-evaluation [frozen protocol](F4_SPEC.md).

## Reserved-holdout results

All models used the original 24,000 training snapshots, all 182 predictors and
the frozen F2 settings. The 8,000 final snapshots contain 1,200 stress cases.
Validation rows were not added to fitting. No final-result tuning was performed.

| Model | Log loss ↓ | AUROC ↑ | Average precision ↑ | Brier ↓ | Captured in 800 reviews |
| --- | ---: | ---: | ---: | ---: | ---: |
| TabPFN-3.5-Plus | **0.279885** | **0.878436** | **0.627568** | **0.084279** | **542 / 1,200** |
| XGBoost | 0.307282 | 0.855970 | 0.5767 | 0.0928 | 512 / 1,200 |
| CatBoost | 0.329976 | 0.838378 | 0.5447 | 0.0996 | 472 / 1,200 |
| Logistic regression | 0.380570 | 0.741017 | 0.3655 | 0.1139 | 352 / 1,200 |
| Constant prior | 0.422709 | 0.500000 | 0.150000 | 0.127500 | 126 / 1,200 |

TabPFN finds 30 more labelled stress cases than XGBoost within the same 800-row
capacity. Its shortlist has 258 false positives; 658 stress cases remain outside
it. At 5% capacity, TabPFN finds 315 cases in 400 rows. These are holdout point
estimates, not significance or intervention-benefit claims. The split remains a
row holdout with unknown dates and persistent customer linkage.

[Complete verified metrics and cohorts](reference/financial-stress-final-evaluation-v1.json)
include calibration with bin sizes, errors and fixed global-budget capture by
region, segment, earning pattern, gender and age band. The validation age/gender
exclusion experiment remains separate and does not prove TabPFN fairness.

## Hosted execution

The first execution request was rejected by automatic approval review before a
process ran because the final payload needed explicit authorisation. The user then
specifically approved sending 8,000 final feature rows to Prior Labs for one
prediction. One execution completed; no retry or additional fit occurred.

The request reused the verified F2 fitted resource and uploaded only final features:
no IDs, final labels, training data or challenge unlabelled Test.csv. The response
reported `/app/tabpfn_models/tabpfn-v3.5-20260909.safetensors` and passed the reviewed
Plus identity policy. This is server-reported identity, not checkpoint-byte attestation.
End-to-end time was 30.43 seconds, a single observed request rather than a
controlled timing comparison. The live estimate was 10,000 tokens; actual charges
were not reported. The estimate guard does not limit row count or truncate inputs.

[Plan](reference/financial-stress-final-plan-v1.json),
[preflight](reference/financial-stress-final-preflight-v1.json),
[execution](reference/financial-stress-final-hosted-v1.json) and
[frozen protocol](reference/financial-stress-final-protocol-v1.json) are retained.

## Dashboard and reproducibility

- All cards have zero border radius, verified in light and dark modes.
- Final results have a separate **Final holdout** tab. The review workspace and its
  CSV exports continue to use validation snapshots; their figures are not relabelled.
- The final exporter rechecks input/plan/response/prediction hashes, row alignment,
  settings and model identity. All five models' log loss, AUROC, AP and Brier agree
  with independent scikit-learn calculations to 1e-12. Direct ranked counts agree.
- `make check` passes Ruff and **141 offline Python tests**; `make ui-check` passes
  **nine tests**, TypeScript and formatting. Each implementation commit is checked
  from a separate staged checkout. No new dependency was needed.
- The portable evidence bundle contains an explicit file allowlist, source
  attribution and checksums. It excludes credentials and unrelated files. A clean
  staged checkout rebuilt identical HTML, JSON, manifest and both CSV files using
  that portable evidence and the already installed locked dependencies.
- A separate fresh offline dependency installation could not complete because
  the locked CatBoost wheel was absent from the local cache. The rebuild evidence
  therefore verifies replay with installed dependencies, not a fresh offline
  installation. Initial dependency installation requires package access.
- Browser checks confirm final figures, calibration/cohort controls, updated data
  limitations, square cards and a 390-pixel mobile layout without page overflow.

The final presentation is `artifacts/financial-stress/dashboard-final-v1/index.html`;
the active preview at `artifacts/financial-stress/dashboard-v1/index.html` contains
the same build. [Build manifest](reference/financial-stress-dashboard-final-v1.json).
[Rebuild instructions](how-to/FINANCIAL_STRESS.md#portable-final-demo).

## Full-data plan and remaining delivery

The prepared [full-data plan](reference/financial-stress-full-data-plan-v1.json)
fits 40,000 labelled rows and scores the 30,000 unlabelled challenge rows with the
same 182 predictors, Plus configuration and seed. It requires a new fit. Source
hashes, payload hashes/sizes, ID order and output probability contract are pinned.
Metadata-only service checks accept the dimensions and estimate **15,728 tokens**;
[preflight](reference/financial-stress-full-data-preflight-v1.json). That was a
planning-only check on 21 September. The separately approved 22 September
[execution](FINANCIAL_STRESS_FULL_DATA_RESULTS.md) returned predictions and is
awaiting resolution of a server column-count discrepancy before acceptance.

This later inference run cannot supply additional quality metrics because the
30,000 rows lack labels. Its separate upload approval was provided on 22 September. The final
holdout comparison is already complete and remains the model-quality evidence.

[Submission description and demo script](PRIOR_LABS_SUBMISSION_DRAFT.md) are ready
for review. Publish from a reviewed snapshot that excludes Nedbank source files
and local Git history; those materials' public distribution remains unresolved.
Publication and submitting/accepting terms remain user-controlled actions.
