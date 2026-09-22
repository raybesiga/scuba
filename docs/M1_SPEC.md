# M1 implementation compact

## Decision and evidence boundary

Goal: produce a reproducible synthetic customer-snapshot dataset for the experiment in `EXPERIMENT.md`. The eventual demo operator reviews a ranked dormancy watchlist; no customer action is taken. Decision owner: project author (operational owner not applicable). M1 success means correct data and audited splits, not a model score. Baselines and ranking metrics are deferred to M2/M4.

Guardrails: zero future events in predictors, zero customer overlap in the main split, complete history/outcomes, explicit synthetic flags, deterministic replay and source hashes. Unacceptable mistakes: labels or latent state used as predictors, censored customers labelled dormant, hidden source inputs, or selecting seeds for model performance. Acceptable tradeoffs: invented simplified behaviour, modest samples and no production-calibration claims.

Sources: newly written simulator only, coverage `[2032-01-01, 2032-11-01)`, seeds 3501/3502/3503. Grain, signals, timing, labels and slices follow the one-page contract. Region/channel are static; events have immediate final status; there is no ingestion lag. Outputs are local CSV/JSON, with no Airflow, MLflow or external services. Fallback: preserve the M0 smoke command and write each run to a new directory. Known risks: simulator assumptions dominate results; sparse subgroup labels; the random-reference gap mixes cohort, time and group differences.

## Locked implementation choices (before pilot results)

- Benchmark generator v1: per-customer SHA-256-derived random streams, daily active/disengaging/dormant state transitions, stochastic reactivation, independent temporary activity shocks, mild calendar drift, and variable attempts/value/product preferences. Archetypes: steady, tapering, sporadic. They affect transition/rate distributions without directly setting labels. The schedule and coverage end must not influence past events.
- Coverage: all generated customers are observable from the configured start. States are never exported as features. Successful transactions alone establish activity; failed/reversed attempts remain in the rate denominator.
- Feature v1 uses the contract's 11 predictors: nine numeric/boolean signals and two fixed categories. Gap means use consecutive successes contained within each 30-day half (same-day gaps can be zero); no gap crosses the half boundary. Null gaps are written as empty CSV fields. Value amounts use fictional minor units. Merchant adoption is a 0/1 indicator. Predictors are selected through an explicit allowlist.
- Every eligible snapshot is retained in `snapshots.csv`; all candidate exclusions carry a reason. Main split retains only the prescribed dates for each fixed customer group. Other eligible rows are counted as omitted from the main design. Random-reference membership is a separate file so it cannot become a predictor.
- Random reference uses independent seeded class-wise shuffles of canonically sorted snapshot keys: floor 60% train, floor 20% validation, remainder test, per class. If either class has fewer than five rows, fail clearly. Membership is stable under input row reordering.
- Minimum main-partition support: **50 rows, 10 positive and 10 negative labels** in each of train/validation/test. These are pilot feasibility thresholds, not claims of statistical power. Report customer counts separately. Subgroups with fewer than 20 rows or fewer than five of either label receive a sparse-support flag; retain them with counts.
- Start at 600 customers. If any main-partition support threshold fails on primary seed 3501, increase once to **1,800**, keep simulator/seed/split rules unchanged, and record both pilots. Use the final population size for sensitivity seeds 3502/3503. Never inspect model rankings for this decision. If support still fails, expose the limitation instead of silently increasing again.

Validation: hand-calculated feature fixtures, exact interval edges, mutation of future events, inactive/censored cases, duplicate keys/FKs/invalid schema rejection, reordered events, stable per-customer generation and horizon extension, deterministic bundles/hashes, disjoint groups and mature labels, random-reference overlap disclosure, and three-seed cohort audits. No model fitting in M1.

## Benchmark-size revision

After reviewing the pilot support, the user approved **15,000 customers** before any baseline fitting. This explicitly supersedes the earlier pilot-only population cap. The goal is more positive evaluation outcomes and stronger subgroup support; a larger synthetic cohort does not establish real-world realism or statistical power. Population size is fixed rather than drawn randomly between runs.

Keep generator/feature/split versions 1.0.0, all behavioural assumptions, fictional dates, seeds 3501/3502/3503 and split seed 3501 unchanged. Only population configuration and CLI defaults change. Archive the 1,800-customer results separately and create new bundles under `artifacts/m1-15000-seed-<seed>`. Do not overwrite existing pilots. The `prepare` command defaults to 15,000; explicit `--customers` remains available for small tests and pilot replay.

Run all three seeds locally, verify support and group separation, compare all nine files in a primary-seed replay, and confirm the original 1,800 customers retain identical events/snapshots. Report cohort counts, sparse slices and provenance hashes before marking the expanded M1 complete. No model ranking informs population selection. Future model training may use explicitly recorded, training-only context subsampling if needed; no such sampling is part of M1.
