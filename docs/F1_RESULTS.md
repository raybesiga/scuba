# Financial Stress F0–F1 results

21 September 2026. Prior Labs is the active submission; Nedbank forecasting is
deferred. These results are new Financial Stress validation evidence and are
independent of the frozen synthetic benchmark. TabPFN has not yet run on this data.

## Source and preparation

The five user-supplied files are preserved byte-for-byte in the
[source package](../datasets/financial-stress/README.md), with original SHA-256
checksums, source attribution and the declared CC BY-SA 4.0 licence. Source
notebook contents are retained without execution. Training: 40,000 snapshots,
6,000 positives (15%), 182 predictors. Inference: 30,000 unlabelled snapshots.
No missing cells, duplicate IDs, identical feature rows or matching train/inference
feature fingerprints were found. These checks do not establish unique people.

The frozen seed-3501 stratified split contains 24,000 training rows (3,600 positive),
8,000 validation rows (1,200 positive) and 8,000 reserved final-evaluation rows
(1,200 positive). Dates and persistent customer keys are absent; this is row-holdout
research evidence, not chronological or customer-disjoint evaluation.
[Preparation manifest](reference/financial-stress-preparation-v1.json).

## Validation only

| Model | Log loss ↓ | AUROC ↑ | Average precision ↑ | Brier ↓ | Stress cases captured reviewing 800 snapshots |
| --- | --- | --- | --- | --- | --- |
| Constant training prevalence | 0.422709 | 0.500000 | 0.150000 | 0.127500 | 136 / 1,200 (11.33%) |
| Logistic regression | 0.371897 | 0.756975 | 0.390954 | 0.111657 | 366 / 1,200 (30.50%) |

The logistic review list contains 434 false positives and misses 834 stress cases.
The constant model assigns equal probabilities; its review ordering follows ID,
so the observed capture is a tie-breaking reference, not a learned ranking.
No settings were tuned on these validation results. Numeric/categorical transforms
were fitted only on training rows; logistic regression uses no class weighting.
[Full metrics, calibration, settings and runtime](reference/financial-stress-baseline-v1.json).

All 182 predictors are included in this initial benchmark. The planned age/gender
exclusion comparison and cohort checks remain necessary before completing the
operator demo. The supplied stress definition, actual feature availability at
prediction time and real/synthetic origin remain unverified.

## Verification

- `make check`: Ruff lint, formatting and 125 offline tests pass.
- Source verification reconstructs all five exact original files.
- Two complete local preparations produce byte-identical partitions and membership.
- Two baseline runs produce byte-identical validation probabilities and identical metrics.
- Tests reject corrupt source/partition files, ID overlap, invalid labels and schema
  drift; demonstrate row-order-independent splitting and training-only transforms;
  and prove baseline evaluation does not read final.csv or Test.csv.
- An exported staged snapshot independently passes all 125 tests and reproduces
  the same full-data validation metrics and probability-file hash. The first
  verification launch resolved the virtual-environment interpreter to system Python
  and failed to find Ruff; rerunning with the virtual-environment path passed.
- No hosted calls, credentials, final-evaluation predictions or Zindi submissions.

F0 and F1 are complete for this local scope. Next is F2: a tree comparator and
bounded, verified TabPFN-3.5 comparison. The browser dashboard still shows the
historical synthetic experiment. Reproduce using the
[local instructions](how-to/FINANCIAL_STRESS.md).
