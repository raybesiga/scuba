# Financial Stress: reserved final-holdout results

Evaluated 21 September 2026; uncertainty added 24 September. All models used the
original 24,000 training snapshots, 182 predictors and frozen settings. The final
holdout contains 8,000 records, including 1,200 stress cases. Validation records
were not added to training, and final outcomes did not change the settings.

## Model comparison

| Model | Log loss ↓ | AUROC ↑ | Average precision ↑ | Brier ↓ | Captured in 800 reviews |
| --- | ---: | ---: | ---: | ---: | ---: |
| TabPFN-3.5-Plus | **0.279885** | **0.878436** | **0.627568** | **0.084279** | **542 / 1,200** |
| XGBoost | 0.307282 | 0.855970 | 0.5767 | 0.0928 | 512 / 1,200 |
| CatBoost | 0.329976 | 0.838378 | 0.5447 | 0.0996 | 472 / 1,200 |
| Logistic regression | 0.380570 | 0.741017 | 0.3655 | 0.1139 | 352 / 1,200 |
| Constant prior | 0.422709 | 0.500000 | 0.150000 | 0.127500 | 126 / 1,200 |

TabPFN finds **30 more stress cases than XGBoost at the same 800-record review
capacity**. Its shortlist contains 542 records with stress and 258 without.
A further 658 stress cases remain outside the shortlist.

| Review capacity | TabPFN cases found | XGBoost cases found | Additional cases |
| --- | ---: | ---: | ---: |
| 400 records · top 5% | 315 | 296 | 19 |
| 800 records · top 10% | 542 | 512 | 30 |

The [post-hoc uncertainty analysis](F4_UNCERTAINTY_RESULTS.md) gives a paired 95%
interval of 9–50 additional cases at 800 reviews, assuming independent rows.
It measures sampling uncertainty for these fitted models, not future performance
or the effect of customer support.

[Full metrics and group audits](reference/financial-stress-final-evaluation-v1.json)
include calibration, errors and capture by region, segment, earning pattern,
gender and age band. See the [method and limitations](FINANCIAL_STRESS_METHOD.md).

## Hosted execution

One final-feature upload and prediction reused the verified validation fit.
No IDs or final labels were uploaded, and the model was not refitted. The response
passed the reviewed identity policy for the reported checkpoint
`/app/tabpfn_models/tabpfn-v3.5-20260909.safetensors`.

End-to-end time was 30.43 seconds, a single observation. The estimate was 10,000
service tokens; actual charges were not reported. Retained evidence includes the
[protocol](reference/financial-stress-final-protocol-v1.json),
[plan](reference/financial-stress-final-plan-v1.json),
[preflight](reference/financial-stress-final-preflight-v1.json) and
[execution record](reference/financial-stress-final-hosted-v1.json).

## Verification and replay

Offline verification checks input, plan, response and prediction hashes, row
alignment, settings and reported model identity. Recomputed log loss, AUROC,
average precision and Brier scores agreed with independent calculations within
1e-12; ranked case counts matched exactly.

Initial F4 acceptance passed Ruff, 141 Python tests and nine UI tests. The
24 September release check subsequently passed 158 Python and 18 UI tests with
fresh locked dependencies; all eight rebuilt demo files matched byte for byte.
Initial dependency installation needs package access unless packages are cached.

The [run guide](how-to/FINANCIAL_STRESS.md) replays the saved evidence without an
API call. Final results have their own tab; review records and CSV exports use
the separate validation sample.

The [all-data inference experiment](FINANCIAL_STRESS_FULL_DATA_RESULTS.md) remains
excluded because its column metadata is unresolved. Its 30,000 unlabelled records
cannot supply further quality metrics. The results above remain the quality
evidence for the 24,000-row fit.
