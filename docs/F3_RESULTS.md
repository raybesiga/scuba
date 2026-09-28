# Financial Stress: operator workspace

The workspace turns verified TabPFN-3.5-Plus predictions into a customer-care
review list. The initial F3 implementation completed on 21 September 2026;
the interface now also includes the separate final-holdout comparison.

## Operator workflow

1. Choose 400 or 800 records for review. Highest predicted stress probabilities
   come first; ID breaks ties.
2. Search, sort or page within that fixed shortlist.
3. Open a record to inspect six months of activity. The latest month is compared
   with its average over the preceding five months.
4. Export the entire shortlist, regardless of search, sorting or page.

Individual outcome labels, age and gender are excluded from the review rows and
CSV exports. The app does not contact customers or select an offer. Activity
changes provide context for review, not a causal explanation of the prediction.

## Reading the evidence

The review workspace uses the 8,000 validation records. At 800 reviews, TabPFN
finds 565 stress cases versus XGBoost's 529. The final-holdout tab uses a separate
8,000-record sample and shows 542 versus 512. Headline cards follow the active
view and review capacity.

The equal-capacity comparison separates records inside the shortlist from stress
cases outside it. Calibration shows mean predictions, observed stress and their
gap in percentage points. Group audits report sample size and use the same global
shortlist, without group-specific thresholds.

## Age and gender check

Local models were refitted on the same training rows with age and gender removed:

| Local model | All features log loss | Without age/gender | Difference |
| --- | ---: | ---: | ---: |
| Constant prior | 0.422709 | 0.422709 | 0.000000 |
| Logistic regression | 0.371897 | 0.372029 | +0.000132 |
| XGBoost | 0.301892 | 0.302851 | +0.000959 |
| CatBoost | 0.326119 | 0.326887 | +0.000768 |

Removing these fields changed aggregate log loss by less than 0.001. Individual
predictions may still change. TabPFN was not rerun without these fields, and
other inputs may act as proxies. This check does not establish fairness.
[Saved exclusion result](reference/financial-stress-without-age-gender-v1.json).

## Implementation and verification

The interface uses Radix Themes with light/dark modes, square cards and tables,
keyboard-accessible controls and tables that scroll within their own regions on
small screens. The [UI guide](../report-ui/README.md) describes the build.

The exporter verifies source manifests, prediction hashes, row alignment, model
identity and recomputed metrics. Initial acceptance passed 134 Python tests,
nine UI tests, TypeScript and formatting. Browser checks covered desktop and
390-pixel mobile layouts, both themes, budget controls, search, sorting,
pagination, detail views and complete CSV downloads.

The original [F3 manifest](reference/financial-stress-dashboard-v1.json) records
that milestone. Use the [current run guide](how-to/FINANCIAL_STRESS.md) to rebuild
the complete Financial Stress demo with final results.
