# Financial Stress: five-model validation comparison

Recorded 21 September 2026. All five models used 24,000 training snapshots,
182 predictors and the same 8,000 validation snapshots, including 1,200 stress
cases. Settings were fixed under the [validation protocol](F2_SPEC.md).
There was no tuning, early stopping, class weighting or training subsample.

## Results

| Model | Log loss ↓ | AUROC ↑ | Average precision ↑ | Brier ↓ | Stress cases captured among 800 reviewed |
| --- | --- | --- | --- | --- | --- |
| TabPFN-3.5-Plus | **0.269368** | **0.887691** | **0.662456** | **0.080786** | **565 / 1,200 (47.08%)** |
| XGBoost | 0.301892 | 0.862231 | 0.598056 | 0.090769 | 529 / 1,200 (44.08%) |
| CatBoost | 0.326119 | 0.843393 | 0.565147 | 0.098019 | 502 / 1,200 (41.83%) |
| Logistic regression | 0.371897 | 0.756975 | 0.390954 | 0.111657 | 366 / 1,200 (30.50%) |
| Constant prior | 0.422709 | 0.500000 | 0.150000 | 0.127500 | 136 / 1,200 (11.33%) |

TabPFN-3.5-Plus had the best observed score on all four quality measures.
Its 800-record shortlist found 36 more stress cases than XGBoost: 565 versus 529.
The other 235 shortlisted records did not have stress; 635 stress cases remained
outside the shortlist. At 400 records, TabPFN found 334 cases, with 66 records
without stress and 866 stress cases outside.

These are validation results. The separate [final holdout](F4_RESULTS.md) found
542 versus 512 cases at the 800-record capacity. The app's review workspace and
exports continue to use validation records.

## Hosted configuration

TabPFN-3.5-Plus used the Prior Labs REST API, alias `v3.5_default`, eight estimators,
seed 3501 and standard prediction. One fit and one prediction completed. Uploads
contained training features and labels, and validation features. Snapshot IDs,
validation labels, final records and the unlabelled challenge file were excluded.

The server reported `/app/tabpfn_models/tabpfn-v3.5-20260909.safetensors`, accepted
under the reviewed identity policy. This checks reported identity; it does not
attest remote model bytes. The 58.07-second end-to-end duration was a single
observation, not a controlled comparison with local model speed. The service
estimated 10,000 tokens; actual charges were not reported.

## Evidence and verification

- [Verified comparison](reference/financial-stress-verified-comparison-v1.json)
- [Local metrics and settings](reference/financial-stress-comparison-v1.json)
- [Hosted execution](reference/financial-stress-hosted-validation-v1.json)
- [Request plan](reference/financial-stress-hosted-plan-v1.json) and
  [metadata preflight](reference/financial-stress-preflight-v1.json)

At this milestone, Ruff and 129 offline tests passed, including an independent
staged checkout. Repeated local runs reproduced validation predictions and metrics.
Offline checks reconciled all 8,000 IDs and labels, input and response hashes,
model identity, probability dimensions and all displayed metrics. XGBoost
probabilities were restored to their saved float32 representation before scoring.

See the [run guide](how-to/FINANCIAL_STRESS.md) and
[method and limitations](FINANCIAL_STRESS_METHOD.md).
