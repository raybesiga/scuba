# Financial Stress release readiness

The Financial Stress model comparison and operator demo are complete. The clean
repository and package are prepared locally. Public publication and hackathon
submission remain pending.

## Evidence

- TabPFN-3.5-Plus finds 542 stress cases versus XGBoost's 512 in equally sized
  800-record final-holdout shortlists. [Final results](F4_RESULTS.md).
- The paired 95% interval for the 30-case gain is 9–50, assuming independent rows.
  [Uncertainty analysis](F4_UNCERTAINTY_RESULTS.md).
- The app supports 400/800-record capacity selection, model comparison, record
  inspection and full-shortlist export. Validation and final results stay separate.

## Recorded release verification

On 24 September 2026, an independent staged checkout installed fresh locked
Python and UI dependencies using Python 3.14.5 and Node 24. Installation downloaded
missing packages; subsequent checks and replay ran offline.

- Ruff lint and format checks, plus 158 Python tests, passed.
- Eighteen UI tests, TypeScript and formatting passed.
- All eight rebuilt demo files matched the packaged output byte for byte.
- Browser checks covered both capacities, model selection, uncertainty and
  validation/final separation.

On 28 September, an isolated staged checkout passed the same 158 Python and 18 UI
tests using existing locked dependencies. Local validation, final and age/gender
exclusion predictions matched the saved evidence byte for byte. All eight demo
files also matched. The run guide and active documentation links were checked.

The separate full-data inference discrepancy remains unresolved;
its outputs are excluded from the dashboard and performance claims.

## Remaining delivery

1. Review and record the [walkthrough](FINANCIAL_STRESS_WALKTHROUGH.md).
2. Publish the reviewed clean repository when authorised and check public access.
3. Submit its URL and [description](PRIOR_LABS_SUBMISSION_DRAFT.md), with the optional video.

Customer-outcome improvement is a subsequent pilot question, not a completed
result or a prerequisite for demonstrating this prototype.
