# Final-holdout uncertainty and operator comparison

24 September 2026. Post-hoc analysis under [the addendum](F4_UNCERTAINTY_SPEC.md),
using the existing verified final predictions. No model fitting or API requests.

| TabPFN-3.5-Plus minus XGBoost | Observed difference | Paired 95% interval |
| --- | ---: | ---: |
| Mean log loss | −0.02740 | −0.03248 to −0.02235 |
| Stress cases found in 400 reviews | +19 | +3.0 to +36.0 |
| Stress cases found in 800 reviews | +30 | +9.0 to +50.0 |

All three intervals exclude zero in TabPFN's favour under the independent-row
sampling assumption. The primary comparison remains log loss; these correlated
intervals are marginal, not a simultaneous multiple-comparison guarantee.
They do not measure retraining variability, temporal generalisation, distinct
customer performance or the effectiveness of customer support.

The dashboard now compares TabPFN with a selected baseline at equal review
capacity, showing found stress cases, reviews without stress and missed cases.
The final-holdout view includes the paired XGBoost intervals. Validation and final
results remain separate; the review list continues to use validation snapshots.

## Reproduce

```sh
PYTHONPATH=src .venv/bin/python -m scuba.financial_demo build --evidence evidence --output rebuilt-demo
```

In the development repository, use
`artifacts/financial-stress/portable-evidence-v1` for `--evidence`.
The build verifies evidence first, recomputes 2,000 paired row-bootstrap resamples
with seed 3501, and includes results and source hashes in `evidence.json`.
