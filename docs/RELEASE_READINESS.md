# Financial Stress release readiness

Verified 24 September 2026. The local hackathon candidate is ready for owner
review. Public release and submission are not complete.

## Delivered

- TabPFN-3.5-Plus drives a capacity-limited review list, with individual monthly
  context, search, sorting and CSV export.
- Operators can compare all four baselines at the same 400/800-review capacities.
  Found cases, reviews without stress and missed cases are explicit.
- Final results remain separate from the validation review workspace. Final
  capture is 542 versus XGBoost's 512 in 800 reviews. The paired row-bootstrap
  95% interval for the difference is 9–50 cases; log-loss difference is −0.02740
  (interval −0.03248 to −0.02235). See the post-hoc analysis contract and results.

## Release verification

Exported the exact staged private-repository snapshot into a new temporary
checkout. Installed locked Python dependencies in a new Python 3.14.5 environment
and locked UI dependencies into the snapshot with `npm ci --ignore-scripts`.
Python installation downloaded missing locked wheels from the package registry.
Normal tests and the subsequent rebuild were offline.

- `make check`: Ruff lint/format and 158 tests passed using the fresh Python runtime.
- `make ui-check`: 18 tests, TypeScript and formatting passed with fresh UI packages.
- Rebuild: all eight demo artifacts were byte-identical to the staged delivery.
- Release allowlist: all 227 listed file hashes matched at the behaviour commit.
  Documentation added afterwards is hashed separately in the release manifest.
- Browser: checked final 5%/10% capacities, matching headline cards, the XGBoost
  intervals, CatBoost selection and the validation review workspace.
- Source data, licences and frozen predictions are unchanged. No model service
  calls, new uploads, pushes or publication were performed.

## Remaining before submission

1. Presenter rehearsal and final owner review of the demo and project description.
2. Authorised publication of the clean repository and a final public-access check.
3. Submit the repository link and description; include optional video if recorded.

The separate all-data inference metadata discrepancy is unresolved; those outputs
remain excluded. This does not alter the verified holdout comparison. No claim is
made about improved retention, revenue or customer welfare without an operator
pilot measuring those outcomes.
