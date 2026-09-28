# Full-data inference: column metadata unresolved

Recorded 22 September 2026. A separate TabPFN-3.5-Plus fit on all 40,000 labelled
records returned predictions for 30,000 unlabelled records. Local acceptance
failed because the server reported **184 columns** for an upload containing
**182 features**. These outputs are excluded from the demo and performance claims.

## What was verified

An independent CSV audit checked every row of the exact uploaded bytes. Both
feature tables have 182 fields, their hashes match the approved plan, and neither
contains ID or target. Labels were uploaded separately. The response passes
row count, binary class order, finite probability, range, row-sum, settings and
reported model-identity checks. Only column-count equality fails.

| Run | Feature columns uploaded | Probability matrix | Columns reported |
| --- | ---: | ---: | ---: |
| Validation | 182 | 8,000 × 2 | 182 |
| Final holdout | 182 | 8,000 × 2 | 182 |
| Full-data inference | 182 | 30,000 × 2 | 184 |

The two probability columns represent classes 0 and 1. Treating them as extra
input columns does not explain the earlier responses, which also return two
probabilities but report 182 columns.

## Diagnostic outcome

One authorised diagnostic reused the existing fitted model and prediction upload,
with complete response capture. It returned the same 30,000 probability pairs
bit for bit and again reported 184 columns. Its three top-level fields were
`prediction`, `metadata` and `timings`; no named feature schema was present.

Reported categorical indices `[179, 180, 181]` point to numerical balance fields
in the uploaded order. A transformed representation or incorrect server metadata
could explain the discrepancy, but neither cause is established. Provider
clarification of what `test_set_num_cols` measures remains necessary.

The original response logger retained selected fields only. The later capture
fix preserves complete redacted response bodies privately before validation.
It cannot recover fields omitted from the original run. No acceptance check was
waived, and no further prediction is planned.

## Execution record

The run used 182 predictors, eight estimators and seed 3501. An initial training
upload timed out before fitting or prediction; a corrected transfer timeout
allowed a deliberate recovery attempt. The completed sequence took 118.63 seconds,
including a 30.88-second prediction. The later diagnostic prediction took 27.91
seconds. These are single observations, not controlled speed benchmarks.

Each prediction had a 15,728-token estimate; actual charges were unavailable.
Resource identifiers and private response bodies remain outside this summary.

- [Approved plan](reference/financial-stress-full-data-plan-v1.json)
- [Initial timeout](reference/financial-stress-full-data-attempt-v1.json) and
  [completed sequence](reference/financial-stress-full-data-attempt-v2.json)
- [Payload audit](reference/financial-stress-full-data-payload-audit-v1.json)
  and [follow-up checks](reference/financial-stress-full-data-followup-v1.json)
- [Response structure audit](reference/financial-stress-response-structure-audit-v1.json)
- [Complete-response diagnostic](reference/financial-stress-complete-response-diagnostic-v1.json)
- [Runner and capture procedure](how-to/FINANCIAL_STRESS_FULL_DATA.md)

The separately verified [final holdout](F4_RESULTS.md) remains the quality evidence
for the earlier 24,000-row fit. Unlabelled inference cannot establish accuracy,
calibration or cases found, even if its metadata is later resolved.
