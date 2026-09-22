# Preserved SCUBA synthetic evaluation dashboard

The active Financial Stress workspace is documented in [F3 results](F3_RESULTS.md).
This page records the preserved synthetic dashboard.

Built 21 September 2026 using the Okestreta product UX trust audit, platform UX writing and verification skills. The current standalone artifact is `artifacts/m5-dashboard/index.html`. It uses the previously approved Radix UI and custom light/dark palette.

## Decision contract

- Reader: benchmark reviewer or project owner assessing model evidence and integration effort.
- Decision: understand the observed model differences, their uncertainty and the outcomes found at the two frozen review budgets. This is not an operational customer-scoring interface.
- Product object: a frozen synthetic evaluation, with a primary temporal test and separate diagnostic/validation evidence.
- Control: switch between the predeclared 5% and 10% budgets; inspect complete metrics, uncertainty, random-reference overlap and source evidence.
- Accountability: every displayed value traces to a saved evaluation. No interaction trains a model, changes a threshold or makes a service request.
- Value: a reviewer can inspect quality, shortlist outcomes and validity without first reading a long results document. No real-customer benefit is claimed.

## Design decisions

The earlier report put a large introductory heading and a long sequence of tables before the comparison. The chosen overview makes model uncertainty and review capacity the central modules. A condensed report-only layout was considered but still buried the fixed-budget comparison; a generic live operations dashboard was rejected because this project has no live customers, interventions or operational metrics.

The model chart shows actual AP values and 95% intervals on a common zero-based scale. The paired TabPFN-3.5-Plus–XGBoost interval is stated separately: overlapping marginal intervals alone are not the test of a model difference. The complete comparisons, including TabPFN-3.5-Plus–CatBoost, remain in the final-test view.

The capacity module exposes only the two budgets frozen before test access. At 5%, TabPFN-3.5-Plus captures 50 positives among 113 selected customers, with 63 false positives. At 10%, it captures 81 among 226, with 145 false positives. Counts for XGBoost and CatBoost use the same budget. Capture differences remain descriptive; no capture confidence interval or intervention benefit is invented.

The cohort module shows train, validation and test in temporal order with customer and snapshot counts. The diagnostic module exposes 8,017 overlapping random-reference train/test customers beside a direct inspection link. Evidence and timing are a separate drilldown. Dashboard links reset the detail seed to primary and move keyboard focus and the viewport to the selected tab.

The top-level overview always describes seed 3501. Sensitivity seeds remain available in detailed views with their missing hosted evidence explained. Cards group distinct comparison, review-budget and audit tasks; nested decorative cards were removed. Typography is restrained, familiar controls use Radix, and both color modes retain the requested tokens.

Detail sections group their heading, explanation and visual in a Radix Box. Section spacing applies between groups; headings sit 8px above their explanations, followed by 16px before the table or chart. This prevents the parent layout from adding its larger section gap between each element.

Both overview panel rows use the same two-thirds/one-third desktop split and stack on smaller screens. Panels share a background within each theme. The model comparison has no accent top border, and its uncertainty note has no side border.

## Table interaction

All detail tables use Radix Themes `Table`. Names, counts and point metrics support ascending/descending sorting; the third activation restores source order. Confidence interval columns are not sortable. AP and other metric sorts use source precision, with stable ties and unavailable values last. Header buttons support keyboard activation, `aria-sort` and Radix tooltips that explain metric direction and the sort cycle. Tables and their scroll containers have zero border radius in both themes.

## Verification and limits

- All 117 Python tests and Ruff checks pass; three sorting tests, one standalone-build test, TypeScript and Prettier pass through `make ui-check`.
- Dashboard evidence is byte-identical to the prior Radix report. Two builds produce identical HTML, JSON and manifests. Source hashes are recorded in `artifacts/dashboard-verification.json` and the presentation manifest.
- Browser checks cover desktop and 390-pixel mobile layouts in light/dark mode, zero document overflow, fixed-budget counts, keyboard activation, metric/random-reference/evidence links, numeric sort/reverse/reset and visible uncertainty. Focused sorting tests cover unavailable values and equal-score stability. Computed table, surface and wrapper radii are all 0px.
- No additional dependency, model run, API request, dataset upload or publication was required.
- This verifies a local presentation workflow, not live operational readiness. Empty or unverified evaluations are rejected by the existing builder rather than represented as successful dashboard results.

Rebuild with `make demo`, following the [offline rebuild procedure](DEMO_REBUILD.md). [M5 technical acceptance](M5_RESULTS.md) is complete, including the clean-environment replay and [storyboard](DEMO_STORYBOARD.md). Spoken rehearsal and delivery review remain.
