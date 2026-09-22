# M1 pilot results — 1,800 customers

Verified locally on 20 September 2026, Python 3.14.5. Generator/feature/split versions: `1.0.0`; source-table schema: `0.1.0`. All scenarios and records are fictional. **No models have been fitted and no predictive performance is claimed.**

## Pilot decision

The predeclared minimum was 50 rows and 10 positive/10 negative labels per main partition. The 600-customer seed-3501 pilot produced 2,470 eligible snapshots but only 8 validation and 7 test positives. This triggered the one permitted increase to 1,800 customers, with the generator and seeds unchanged. All three declared generator seeds pass at that size. Split seed remains 3501 throughout.

The original failed pilot is preserved under `artifacts/m1`; it is not silently overwritten. Its manifest predates completion of some pipeline code, but its simulator source hash is identical to the final simulator. Later runs retain their own full source-hash records.

## Primary cohort

The simulator generated 1,800 customers and 212,014 attempts over `[2032-01-01, 2032-11-01)`. Of 9,000 candidate snapshots, 7,288 were eligible and 1,712 were excluded as inactive. No candidates were history-incomplete or censored under the configured schedule; tests cover both exclusion paths. The main date/group policy omitted another 4,011 eligible rows. All eligible rows remain available to the diagnostic reference.

## Main split support across seeds

Positive = a snapshot with zero successful transactions in its following 30 days. Training has repeated customer snapshots; validation and test each have one snapshot per customer.

| Generator seed | Partition | Rows | Customers | Positives | Negatives | Dormancy rate |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| 3501 | train | 2,700 | 1,022 | 293 | 2,407 | 10.85% |
| 3501 | validation | 304 | 304 | 32 | 272 | 10.53% |
| 3501 | test | 273 | 273 | 20 | 253 | 7.33% |
| 3502 | train | 2,654 | 1,004 | 274 | 2,380 | 10.32% |
| 3502 | validation | 282 | 282 | 30 | 252 | 10.64% |
| 3502 | test | 265 | 265 | 29 | 236 | 10.94% |
| 3503 | train | 2,654 | 1,004 | 262 | 2,392 | 9.87% |
| 3503 | validation | 284 | 284 | 42 | 242 | 14.79% |
| 3503 | test | 261 | 261 | 31 | 230 | 11.88% |

All pairwise customer overlaps are **zero** in each main split. Training labels mature by 1 July 2032, before validation on 1 August. Validation labels mature by 31 August, before test on 1 October.

## Primary subgroup support

Sparse means fewer than 20 rows or fewer than five of either label. These are disclosure thresholds, not assurances of statistical power; model metrics and uncertainty intervals belong to M4.

| Partition | Slice type | Slice | Rows | Positives | Dormancy rate | Sparse |
| --- | --- | --- | ---: | ---: | ---: | --- |
| train | Archetype | sporadic | 864 | 168 | 19.44% | no |
| train | Archetype | steady | 981 | 31 | 3.16% | no |
| train | Archetype | tapering | 855 | 94 | 10.99% | no |
| train | Activity | high | 1456 | 66 | 4.53% | no |
| train | Activity | low | 297 | 78 | 26.26% | no |
| train | Activity | medium | 947 | 149 | 15.73% | no |
| validation | Archetype | sporadic | 95 | 20 | 21.05% | no |
| validation | Archetype | steady | 128 | 5 | 3.91% | no |
| validation | Archetype | tapering | 81 | 7 | 8.64% | no |
| validation | Activity | high | 159 | 6 | 3.77% | no |
| validation | Activity | low | 45 | 13 | 28.89% | no |
| validation | Activity | medium | 100 | 13 | 13.00% | no |
| test | Archetype | sporadic | 88 | 13 | 14.77% | no |
| test | Archetype | steady | 110 | 1 | 0.91% | yes |
| test | Archetype | tapering | 75 | 6 | 8.00% | no |
| test | Activity | high | 140 | 2 | 1.43% | yes |
| test | Activity | low | 35 | 9 | 25.71% | no |
| test | Activity | medium | 98 | 9 | 9.18% | no |

## Diagnostic random reference

This split uses all eligible snapshots across the five dates and allows related customers across partitions. It is **not deployment-valid**. A future random-minus-temporal score difference mixes chronology, group overlap, sample size and cohort composition; its sign is not predetermined.

| Partition | Rows | Positives | Dormancy rate |
| --- | ---: | ---: | ---: |
| train | 4372 | 456 | 10.43% |
| validation | 1457 | 152 | 10.43% |
| test | 1459 | 153 | 10.49% |

Shared-customer counts: train / test = 964; train / validation = 991; validation / test = 575.

## Verification and replay

- `make test`: 33 passing tests, including hand-calculated features, future mutation, half-open window boundaries, inactive/history/censoring exclusions, same-day gaps, schema/FK/duplicate rejection, predictor allowlisting and adversarial split checks.
- Package-source and file hashes, output row counts, source-manifest linkage and serialized membership-to-snapshot joins are checked in the pipeline tests. Network connections are blocked during the end-to-end replay test.
- The primary 1,800-customer command was repeated with `.venv/bin/python`; all nine output files were byte-identical. The existing virtual environment has no project runtime dependencies installed. The default pipeline uses the standard library only.
- Increasing population size preserves existing customer streams; extending the horizon preserves all historical events. Both properties are tested.
- Optional editable installation and other Python versions have not been validated. Generated bundles are ignored by Git; this document preserves aggregate evidence.

```sh
make test
PYTHONPATH=src python3 -m scuba prepare --customers 1800 --seed 3501 --output artifacts/m1-benchmark
PYTHONPATH=src python3 -m scuba prepare --customers 1800 --seed 3502 --output artifacts/m1-seed-3502
PYTHONPATH=src python3 -m scuba prepare --customers 1800 --seed 3503 --output artifacts/m1-seed-3503
```

Commands require new output directories. A repeat uses a new path and compares file bytes; existing bundles are never overwritten. A failed main-support check returns exit code 1 with its audit retained.

## Evidence identifiers

Each bundle has source and derived manifests with complete configuration, schemas, coverage, seeds and file hashes. Root manifest SHA-256:

| Run | Local bundle | SHA-256 |
| --- | --- | --- |
| 600-customer pilot | `artifacts/m1` | `ab83b519d18f113fa1b833fe68bef728d9f250d0cf9af949b1929aa00d268b0d` |
| 1,800 customers / seed 3501 | `artifacts/m1-benchmark` | `ec90d40fbaf44dcd197c7093aa3a60bd3bd47f30e9ac294fc391ba5d2902a526` |
| 1,800 customers / seed 3502 | `artifacts/m1-seed-3502` | `1a67960698cb85992e750ee3ff868e4964dd09c3b6d4e7afbb4a13de65aaa375` |
| 1,800 customers / seed 3503 | `artifacts/m1-seed-3503` | `285263c1fcdf6a80e409c7973e433b01297ee5a63f65039d977171b4d585dda7` |

## Original pilot handoff to M2

Use the frozen feature allowlist and membership files. Fit preprocessing only on training rows, select settings only on validation, and keep test predictions for the final evaluation. Add and lock the actual model dependencies at that stage. The small number of test positives and sparse subgroup labels remain limitations; passing support thresholds does not establish model quality or readiness for real-world use.
