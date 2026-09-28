# Synthetic dormancy benchmark archive

This earlier experiment predicts 30-day dormancy in fictional mobile-money
customers. It is separate from the Financial Stress hackathon use case.
Its results do not validate the Financial Stress model.

The benchmark used 15,000 simulated customers for each of three seeds. The main
split separates both customers and time; the random-row split is diagnostic only.
On the primary test, TabPFN-3.5-Plus had average precision 0.3601 versus XGBoost
0.3487. Their paired interval included zero, and both found 81 of 233 positive
outcomes in a 226-record shortlist.

## Browse the archive

| Purpose | Record |
| --- | --- |
| Data and evaluation contract | [Experiment](EXPERIMENT.md) |
| Initial population checks | [Pilots](M1_PILOT_RESULTS.md), [15,000-customer cohort](M1_RESULTS.md) |
| Local validation | [Protocol](M2_SPEC.md), [results](M2_RESULTS.md) |
| Hosted integration | [Results](M3_RESULTS.md), [checkpoint resolution](M3_CHECKPOINT_RESOLUTION.md) |
| Final comparison | [Local results](M4_FINAL_RESULTS.md), [hosted results](M4_HOSTED_FINAL_RESULTS.md) |
| Other diagnostics | [Validation](M4_RESULTS.md), [request audit](M3_REQUEST_CONTRACT.md) |
| Presentation | [Dashboard](DASHBOARD.md), [rebuild](DEMO_REBUILD.md), [historical script](DEMO_STORYBOARD.md) |
| Reproduction evidence | [M5 verification](M5_RESULTS.md) |

The dated milestone records retain their original protocols, measurements and
verification counts. Statements about “next steps” describe the project at that
date. Use the [Financial Stress recording walkthrough](FINANCIAL_STRESS_WALKTHROUGH.md)
for the current submission.

## Synthetic benchmark provenance

SCUBA synthetic benchmark data is entirely fictional, produced by newly written deterministic Python code. The generator accepts only configuration (seed, customer count and invented time range); it does not accept input datasets. No source records or empirical distributions are used. Identifiers, calendar dates, product/channel/region names, amounts and event statuses are invented.

## Benchmark generator v1

`scuba.simulation` version `1.0.0` is the benchmark generator. A separate SHA-256-derived random stream for each `(seed, customer_id)` controls invented steady, tapering and sporadic archetypes; customer-specific activity rates, values and product preferences; daily active/disengaging/dormant state transitions and reactivation; temporary random shocks; mild calendar variation; and probabilistic failures/reversals. An active day can contain multiple attempts. Amounts are positive integer fictional minor units. No state or label is copied into a historical feature. Dormancy is derived only from future successful events.

These hand-set mechanisms create noisy, overlapping behaviours; they are not fitted to records or population statistics. Per-customer streams preserve existing customer records when population size increases. No random draw depends on the requested coverage end, so extending the future cannot alter earlier events. Same-version replay is tested; cross-version/runtime equivalence is not assumed.

Selected population: **15,000 customers**, approved by the user before model fitting to improve outcome/subgroup support. The earlier 600-customer pilot failed positive-label support and the 1,800-customer pilot passed; both are preserved. The explicit 15,000-customer decision supersedes the pilot cap without changing behavioural assumptions or selecting a different seed. All three expanded runs pass support checks, the primary run replays byte for byte, and each original 1,800-customer cohort retains unchanged records and main-split membership. Primary generator seed: `3501`; sensitivity seeds: `3502`, `3503`; fixed split seed: `3501`. Invented coverage is `[2032-01-01, 2032-11-01)` UTC. All customers are observable for the entire coverage period.

`make prepare` writes a new bundle under `artifacts/m1-15000-seed-3501`. `sources/manifest.json` records source schema version `0.1.0`, generator version `1.0.0`, seed, full configuration/coverage, observed event range, Python version, package-source hashes, counts and CSV hashes. `manifest.json` records feature/split versions `1.0.0`, source-manifest hash, predictor allowlist, window and eligibility rules, schedule, split seed and derived-file schemas/hashes. All customer, event, snapshot, exclusion and membership rows carry `is_synthetic=true`. Gap features with insufficient observations use empty CSV fields as nulls. The JSON audit is explicitly classified as synthetic and contains counts, not model scores.

## Preserved M0 smoke fixture

`scuba.generator` version `0.1.0` is a **smoke fixture**, not the benchmark simulator. A local `random.Random(seed)` chooses each customer's fixed fictional attributes, then simulates at most one attempt per day. Steady, tapering and sporadic archetypes use hand-set daily attempt probabilities; tapering activity declines through the invented period. Attempt values are positive integer fictional minor units; statuses are generated probabilistically. These simplistic assumptions exist to test reproducibility and schema. They are not calibrated behavioural estimates.

Default seed: `3501`; default customers: `60`; default coverage: `[2032-01-01, 2032-11-01)` UTC. This command remains a small schema/replay fixture; benchmark snapshots use the separate v1 simulator above.

## Generated bundle

Run `python -m scuba generate --output artifacts/smoke` with the package available as described in the README. It writes `customers.csv`, `events.csv` and `manifest.json` to a new directory and refuses to overwrite an existing one. Both CSVs mark every row `is_synthetic=true`. The manifest records:

- classification `synthetic`, purpose `smoke_fixture`, generator version and seed;
- complete field/type schema and schema version;
- configured start-inclusive/end-exclusive coverage and observed event range;
- customer/event row counts, SHA-256 file hashes, generator/contract source hashes;
- all generation parameters and Python version for replay.

The manifest omits wall-clock generation time and absolute paths so repeated runs on the same Python version produce identical bytes. CSV ordering, UTF-8 encoding, LF newlines and JSON key ordering are fixed. Replay across Python versions must be checked rather than assumed. Generated bundles live under ignored `artifacts/`; no generated data is committed by default.

## Versioning and interpretation

M1 uses the Python standard library only, with no third-party runtime dependencies to lock. M2 uses uv with exact model dependency pins and a committed lock. Model-run manifests additionally record the lock hash, current recursive package-source hashes, consumed M1 input hashes, exact model settings, seeds, runtime, cohort identities and timing. The frozen M1 manifests retain their historical source provenance. All saved prediction rows remain marked synthetic. See [M2 results](M2_RESULTS.md). Record all seeds and runs, including unsuccessful and skipped runs. Any changed generator assumptions require a version increment and a new manifest; do not tune the generator using test-set model rankings. `M1_PILOT_RESULTS.md` preserves the initial pilots; `M1_RESULTS.md` records the expanded benchmark. Generated bundles remain local and ignored by Git; the report contains aggregate evidence only.

Synthetic results establish that the software works under specified invented assumptions. They do not establish population prevalence, fairness, commercial benefit or real-world predictive accuracy. The pipeline is local by default; any future dataset upload requires explicit approval.
