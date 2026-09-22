# F3 — Financial Stress customer-care workspace

Completed 21 September 2026 for the local validation-demo scope defined in
[F3_SPEC.md](F3_SPEC.md). Financial Stress is now the default view of the new
standalone dashboard. The prior synthetic benchmark is preserved under its
`archive/` link. Nedbank forecasting remains planned.

## Delivered workflow

An operator can choose 400 or 800 snapshots, search and sort that fixed shortlist,
inspect a snapshot's six monthly transaction-count totals and family breakdown,
and export the whole shortlist. Months run from oldest M6 to most recent M1;
balances retain unspecified dataset units. Individual observed outcome labels,
age and gender are excluded from the review rows and CSV exports.

The model-evidence tab contains the five-model comparison, calibration bins with
row support, audits by region/segment/earning pattern/gender/age band, and the
local age/gender exclusion comparison. Group capture uses the same global
shortlist as the workspace. No group-specific threshold is applied. The
limitations tab states source attribution, data licence, checkpoint identity,
unknown dates/customer linkage/origin, and the absence of intervention evidence.

The interface uses Radix, the existing requested palette, a white light background,
square tables, compact heading/explainer spacing and consistent 2:1 desktop
modules. Modules stack on mobile. All model names use TabPFN-3.5-Plus.

## Evidence

The frozen F2 comparison is unchanged. TabPFN-3.5-Plus validation log loss remains
0.2694, AUROC 0.8877 and average precision 0.6625. At 10% capacity, the shortlist
contains 565 of 1,200 labelled stress cases in 800 snapshots: 235 false positives
and 635 stress cases outside the shortlist. XGBoost finds 529 at the same capacity.
At 5%, TabPFN-3.5-Plus finds 334 in 400, with 66 false positives and 866 outside.
These are retrospective validation point estimates, not demonstrated care benefits.

The new local exclusion run uses the same 24,000 training and 8,000 validation
rows, fixed recipes and seed, with 180 predictors instead of 182:

| Local model | All features log loss | Without age/gender | Difference |
| --- | ---: | ---: | ---: |
| Constant prior | 0.422709 | 0.422709 | 0.000000 |
| Logistic regression | 0.371897 | 0.372029 | +0.000132 |
| XGBoost | 0.301892 | 0.302851 | +0.000959 |
| CatBoost | 0.326119 | 0.326887 | +0.000768 |

Lower is better. These small observed changes do not establish significance or
fairness. TabPFN was not refitted without these fields; other predictors can carry
proxies. The [pinned exclusion result](reference/financial-stress-without-age-gender-v1.json)
records settings, dependency/source hashes, aligned predictions hash and metrics.

## Verification

- `make check`: Ruff lint/format and all **134 Python tests** passed.
- `make ui-check`: **nine UI/helper/build tests**, TypeScript and Prettier passed.
- Each implementation commit was checked from an independent staged checkout.
  The final staged checkout produced byte-identical HTML, JSON evidence, manifest
  and both CSV exports using the retained frozen input artifacts.
- The exporter verifies pinned source manifests, prediction hashes, IDs and labels,
  recomputes all displayed model metrics, and revalidates the retained hosted
  response against the approved model plan. Changed evidence is rejected.
- Focused tests cover fixed-capacity ties, full-precision sorting, search boundaries,
  CSV quoting/formula prefixes, exclusion of outcome labels, oldest-first monthly
  context, cohort reconciliation and corrupt evidence rejection.
- Browser verification: 1178-pixel desktop and 390-pixel mobile; light and dark;
  no document horizontal overflow on mobile; table radius 0px; 5%/10% selection
  with keyboard activation, ascending numeric sort, pagination, search/no matches,
  snapshot context, monthly expansion, age-band audit, limitations and archive.
- The initial browser-generated CSV was replaced with deterministic saved CSV
  files. The final direct export link produced a confirmed browser download event.
  Both export files have hashes in the presentation manifest.
- No new hosted prediction, upload or final-holdout evaluation occurred. Only the
  local exclusion comparison was refitted. The final 8,000 rows remain reserved.

The local artifact is `artifacts/financial-stress/dashboard-v1/index.html`.
[Presentation manifest](reference/financial-stress-dashboard-v1.json) records its
hashes. [Rebuild instructions](how-to/FINANCIAL_STRESS.md#build-the-financial-stress-workspace)
require the saved F2/F3 artifacts; this staged replay is not a fresh-dependency or
public clean-checkout release test. Packaging the full portable evidence, final
holdout evaluation, publication review and the submission remain F4.
