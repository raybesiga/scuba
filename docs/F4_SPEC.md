# F4 — frozen final evaluation and submission preparation

Frozen before final-holdout model evaluation on 21 September 2026.

The operator, decision, source, grain, feature timing, target, baseline, slices,
fallback and known limitations remain those in the
[Financial Stress contract](explanation/FINANCIAL_STRESS.md). Success is a
reproducible final comparison and an understandable customer-care demo. The
primary metric remains log loss; AUROC, AP, Brier, calibration, fixed 5%/10%
capture, FP/FN and cohort support are guardrails. Do not tune to final results or
claim intervention benefit, temporal separation or unique-customer separation.
No Airflow/MLflow service is introduced.

## Frozen evaluation

- Fit each local model on the original 24,000 training snapshots, with all 182
  predictors and exactly the F2 settings. Reuse the verified TabPFN-3.5-Plus
  fitted resource where available. Do not add validation rows to training.
- Score the original 8,000-row final partition once. Preserve the 8,000 validation
  rows and their results. No threshold/calibration change, feature selection,
  early stopping or tuning follows final access.
- Pin source manifests, the F2 settings and model identity, prepared file hashes,
  dependency lock and execution source before opening final rows for scoring.
- Primary final evidence is point metrics. Any uncertainty analysis must state
  its row-level sampling assumption because persistent customer IDs are absent.
- Hosted continuation: propose one final-feature upload and one prediction using
  the existing fitted resource; no training upload or fit, no IDs/final labels,
  and no automatic retry. Obtain fresh metadata-only limits/cost information.
  The previous approved validation plan excluded final rows; complete a concrete
  final request plan before requesting upload/budget approval.

## Full-data run and delivery

After recording final results, a distinct inference run can fit all 40,000 labelled
snapshots and score the supplied 30,000 unlabelled snapshots. That run is not an
additional quality evaluation. Prepare its schema, source hashes, model settings,
resource/estimate plan and output contract; do not silently execute a larger
hosted upload under final-evaluation approval.

Prepare an Apache-2.0 code submission with separately attributed CC BY-SA 4.0 data
and adaptations, portable frozen prediction evidence, runnable instructions and a
short demo script. Nedbank data/history must be excluded from the public delivery
candidate while its source conditions remain unresolved. Do not rewrite the local
repository history or publish/submit without explicit approval.

F4 remains in progress until the verified hosted final comparison, clean-checkout
reproduction and submission review are complete. Do not relabel validation as final.
