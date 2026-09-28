# Financial Stress: source audit and initial baselines

Recorded 21 September 2026. This is the initial two-model validation result.
The [five-model validation](F2_RESULTS.md) and [final holdout](F4_RESULTS.md)
subsequently completed the comparison.

## Source and split

The [source package](../datasets/financial-stress/README.md) retains five original
files and their checksums. Training data contain 40,000 snapshots, 6,000 positive
labels and 182 predictors. The separate inference file contains 30,000 unlabelled
snapshots. The supplied notebook was not executed.

The audit found no missing cells, duplicate IDs, identical feature rows or matching
train/inference feature fingerprints. These checks do not establish unique people.
The fixed stratified split contains 24,000 training, 8,000 validation and 8,000
final records, each with 15% positive labels. Dates and persistent customer keys
are absent. See the [preparation manifest](reference/financial-stress-preparation-v1.json).

## Initial validation

| Model | Log loss ↓ | AUROC ↑ | Average precision ↑ | Brier ↓ | Stress cases captured reviewing 800 snapshots |
| --- | --- | --- | --- | --- | --- |
| Constant training prevalence | 0.422709 | 0.500000 | 0.150000 | 0.127500 | 136 / 1,200 (11.33%) |
| Logistic regression | 0.371897 | 0.756975 | 0.390954 | 0.111657 | 366 / 1,200 (30.50%) |

The logistic shortlist contains 366 stress records and 434 without stress;
834 stress cases remain outside it. The constant prior assigns every record the
same probability, so its shortlist follows the ID tie-break rather than a learned
ranking. Preprocessing used training rows only; no class weighting or tuning was
applied. [Full metrics and settings](reference/financial-stress-baseline-v1.json).

## Recorded verification

At this milestone, Ruff and 125 offline tests passed. Repeated preparation
produced byte-identical partitions; repeated fitting reproduced predictions and
metrics. An independent staged checkout reproduced the results. Tests covered
source corruption, invalid schemas and labels, ID overlap, row-order stability,
training-only transforms and exclusion of final/inference data from baseline scoring.

For current reproduction, follow the [run guide](how-to/FINANCIAL_STRESS.md).
