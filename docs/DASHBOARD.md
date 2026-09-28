# Synthetic evaluation dashboard archive

This dashboard presents the earlier fictional dormancy experiment. The current
hackathon app is the [Financial Stress workspace](F3_RESULTS.md).

The synthetic view separates the primary temporal test, validation, diagnostic
random split and integration evidence. Reviewers can change the fixed 5%/10%
review budget and inspect model uncertainty, cohort support and source evidence.
The primary summary uses seed 3501; sensitivity views state missing hosted runs.

The model chart shows average precision and its 95% interval. The paired model
difference is reported separately, since overlap between marginal intervals does
not test a difference. At 10% capacity, TabPFN and XGBoost each find 81 of 233
positive outcomes among 226 selected customers.

Tables support keyboard sorting, stable ties and unavailable values last.
Confidence-interval columns are not sortable. Light/dark themes, labelled table
scroll regions and a stacked mobile layout support inspection on smaller screens.

Recorded checks on 21 September covered 117 Python tests, four UI tests,
TypeScript, formatting, desktop/mobile navigation, keyboard controls and evidence
identity. The [M5 record](M5_RESULTS.md) contains the fresh-environment replay.
See the [historical rebuild guide](DEMO_REBUILD.md) for archived evidence requirements.
