# M1 results — 15,000-customer benchmark

Synthetic benchmark archive. This dated record is separate from the
[Financial Stress entry](README.md). Status and test counts describe that milestone.

Verified locally on 20 September 2026 with Python 3.14.5. Experiment contract v1.1; generator/feature/split versions 1.0.0; source-table schema 0.1.0. All records and scenarios are fictional. **No models have been fitted and no predictive performance is claimed.**

## Population decision

The user approved a fixed 15,000-customer population before baseline fitting, to increase positive-outcome and subgroup support. This explicitly supersedes the earlier pilot cap. Behavioural assumptions, dates, generator seeds 3501/3502/3503, and split seed 3501 are unchanged. Population size is configuration recorded in each manifest, not a change to the generator mechanism.

The [600/1,800-customer pilot report](M1_PILOT_RESULTS.md) and its original local bundles remain preserved. The larger population improves precision within this invented scenario; it does not establish real-world realism or statistical power.

## Primary cohort

Generated **15,000 customers and 1,749,740 events** over `[2032-01-01, 2032-11-01)`. Of 75,000 candidate snapshots, **60,109 were eligible**, representing 14,599 distinct customers. Another 14,891 snapshots were excluded as inactive. No scheduled candidates were history-incomplete or censored; tests exercise those exclusion paths.

The main group/date policy omits 33,259 additional eligible snapshots. All eligible rows remain in the diagnostic random-reference pool. Eleven predictors use historical activity only; latent archetypes and audit metadata stay outside model inputs.

## Main split support across seeds

Positive means no successful transactions in the following 30 days. Training has repeated customer snapshots; validation and test each have one snapshot per customer. Counts are not independent event observations.

| Generator seed | Partition | Snapshots | Customers | Positives | Negatives | Dormancy rate |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| 3501 | train | 22,183 | 8,405 | 2,399 | 19,784 | 10.81% |
| 3501 | validation | 2,407 | 2,407 | 269 | 2,138 | 11.18% |
| 3501 | test | 2,260 | 2,260 | 233 | 2,027 | 10.31% |
| 3502 | train | 22,068 | 8,373 | 2,329 | 19,739 | 10.55% |
| 3502 | validation | 2,382 | 2,382 | 273 | 2,109 | 11.46% |
| 3502 | test | 2,272 | 2,272 | 231 | 2,041 | 10.17% |
| 3503 | train | 22,121 | 8,367 | 2,310 | 19,811 | 10.44% |
| 3503 | validation | 2,397 | 2,397 | 251 | 2,146 | 10.47% |
| 3503 | test | 2,298 | 2,298 | 244 | 2,054 | 10.62% |

All three seeds pass the original feasibility thresholds (50 rows and 10 of each label per main partition). Pairwise customer overlap is **zero** throughout the main splits. Training labels mature by 1 July 2032, before validation on 1 August; validation labels mature by 31 August, before test on 1 October.

Primary test support increased from 273 customers / 20 positives in the pilot to **2,260 customers / 233 positives**. One positive outcome changes capture by about **0.43 percentage points**, compared with 5 points in the pilot. Top-5% and top-10% budgets select 113 and 226 customers. These are granularity calculations, not measured model scores.

## Primary subgroup support

Sparse means fewer than 20 snapshots or fewer than five of either label. Passing this flag is not a statistical-power guarantee; model metrics and uncertainty intervals remain M4 work.

| Partition | Slice type | Slice | Snapshots | Positives | Dormancy rate | Sparse |
| --- | --- | --- | ---: | ---: | ---: | --- |
| train | Archetype | sporadic | 6,833 | 1366 | 19.99% | no |
| train | Archetype | steady | 8,340 | 258 | 3.09% | no |
| train | Archetype | tapering | 7,010 | 775 | 11.06% | no |
| train | Activity | high | 12,120 | 581 | 4.79% | no |
| train | Activity | low | 2,466 | 650 | 26.36% | no |
| train | Activity | medium | 7,597 | 1168 | 15.37% | no |
| validation | Archetype | sporadic | 811 | 169 | 20.84% | no |
| validation | Archetype | steady | 930 | 31 | 3.33% | no |
| validation | Archetype | tapering | 666 | 69 | 10.36% | no |
| validation | Activity | high | 1,287 | 61 | 4.74% | no |
| validation | Activity | low | 318 | 87 | 27.36% | no |
| validation | Activity | medium | 802 | 121 | 15.09% | no |
| test | Archetype | sporadic | 756 | 158 | 20.90% | no |
| test | Archetype | steady | 925 | 21 | 2.27% | no |
| test | Archetype | tapering | 579 | 54 | 9.33% | no |
| test | Activity | high | 1,128 | 40 | 3.55% | no |
| test | Activity | low | 302 | 89 | 29.47% | no |
| test | Activity | medium | 830 | 104 | 12.53% | no |

## Diagnostic random reference

The random reference mixes dates and related customers. It is **not deployment-valid**. Its eventual score difference from the main split combines chronology, customer overlap, sample size and cohort composition; the sign is not predetermined.

| Partition | Snapshots | Positives | Dormancy rate |
| --- | ---: | ---: | ---: |
| train | 36,064 | 3,951 | 10.96% |
| validation | 12,021 | 1,317 | 10.96% |
| test | 12,024 | 1,318 | 10.96% |

Shared-customer counts: train / test = 8,017; train / validation = 7,983; validation / test = 4,739.

## Verification and reproducibility

- All 33 tests pass, covering historical boundaries, future-event mutation, eligibility/censoring, hand-calculated features, schema/FKs, grouping, serialized-output reconciliation and offline replay.
- The real `make prepare` command uses the new 15,000-customer default. Explicit small-cohort overrides remain covered by tests. The source and derived manifests record actual population, seeds, versions, schema, coverage and code/file hashes.
- Both sensitivity runs pass. All three bundles match current package-source hashes, their file hashes and source-manifest links.
- The complete primary run was repeated with `.venv/bin/python`; **all nine output files are byte-identical**. No runtime dependencies were added.
- For each seed, the original 1,800 customers retain byte-identical customer/event/snapshot/exclusion records and unchanged main-split membership. Generator, feature, split and contract source hashes match the pilot. Random-reference membership is intentionally recomputed for the larger pool.
- Optional editable installation and other Python versions remain unverified. There were no model fits, API calls or uploads.

```sh
make test
make prepare
PYTHONPATH=src python3 -m scuba prepare --seed 3502 --output artifacts/m1-15000-seed-3502
PYTHONPATH=src python3 -m scuba prepare --seed 3503 --output artifacts/m1-15000-seed-3503
```

Each output directory must be new. Existing pilot and benchmark bundles are never overwritten. `prepare` defaults to 15,000 customers; explicit `--customers` overrides it. A failed main-support check returns exit code 1 with its audit retained.

## Evidence identifiers

Generated bundles and the aggregate verification record remain under ignored `artifacts/`. Root manifest SHA-256:

| Seed | Local bundle | SHA-256 |
| --- | --- | --- |
| 3501 | `artifacts/m1-15000-seed-3501` | `6f073aacfdb3923572c14c756fa1a4de78cc7818f375f2e618da28810b469e29` |
| 3502 | `artifacts/m1-15000-seed-3502` | `98cbe77247191a6f49b8857da41744c076dd223d6c2876d93a2eaada94cea61b` |
| 3503 | `artifacts/m1-15000-seed-3503` | `a7d499a124ffcebc08c1e9a2852546eeaaac4cbe4dfc0a883c9d567f6b4c1801` |

Aggregate validation record: `artifacts/m1-15000-verification.json` (SHA-256 `84da48a95a1578c4c7ce0e28778fd1691741ef8c95d469269ddaa5fa5f1e4c5a`).
