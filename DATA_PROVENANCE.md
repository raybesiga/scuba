# Data provenance

## Dataset boundaries

The original M0–M5 benchmark below remains entirely synthetic. The user authorised an independent Nedbank dataset integration on 21 September 2026 for the Prior Labs hackathon. Those supplied source files are described by their publisher as anonymised real banking data; this is a publisher statement, not an independent anonymisation audit. They must not be marked synthetic or used to retrofit the frozen benchmark results. The [Nedbank source manifest](datasets/nedbank/manifest.json) records exact original, part and extracted-member hashes. The [source package](datasets/nedbank/README.md) records source URLs, original attribution and licence, and the unresolved retention condition. See [submission requirements](docs/HACKATHON_SUBMISSION.md).

## Active Financial Stress experiment

The user supplied five September Financial Stress challenge files and selected
this as the first Prior Labs use case on 21 September 2026. The
[source package](datasets/financial-stress/README.md) preserves their original
bytes and declared CC BY-SA 4.0 attribution; its manifest records hashes. Real
versus synthetic origin is unverified. It must remain separate from Nedbank and
M0–M5. Features cover M1 (most recent) through M6; the released label is next-30-day
liquidity stress. Snapshot IDs and a stratified row holdout cannot establish
chronological or person-level separation. See the
[contract](docs/explanation/FINANCIAL_STRESS.md).

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

M1 uses the Python standard library only, with no third-party runtime dependencies to lock. M2 uses uv with exact model dependency pins and a committed lock. Model-run manifests additionally record the lock hash, current recursive package-source hashes, consumed M1 input hashes, exact model settings, seeds, runtime, cohort identities and timing. The frozen M1 manifests retain their historical source provenance. All saved prediction rows remain marked synthetic. See [M2 results](docs/M2_RESULTS.md). Record all seeds and runs, including unsuccessful and skipped runs. Any changed generator assumptions require a version increment and a new manifest; do not tune the generator using test-set model rankings. `docs/M1_PILOT_RESULTS.md` preserves the initial pilots; `docs/M1_RESULTS.md` records the expanded benchmark. Generated bundles remain local and ignored by Git; the report contains aggregate evidence only.

Synthetic results establish that the software works under specified invented assumptions. They do not establish population prevalence, fairness, commercial benefit or real-world predictive accuracy. The pipeline is local by default; any future dataset upload requires explicit approval.
