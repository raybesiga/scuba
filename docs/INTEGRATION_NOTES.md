# TabPFN integration

SCUBA uses the Prior Labs REST upload, fit and predict workflow. The verified
Financial Stress runs request **TabPFN-3.5-Plus**, alias `v3.5_default`, with eight
estimators and seed 3501. The dashboard replays those saved responses offline.

## Request flow

1. Build an offline plan with feature order, row counts, payload hashes and settings.
2. For a new authorised hosted run, check current service limits and the estimate.
3. Upload training features and labels, fit the resource, then upload prediction
   features. IDs and evaluation labels remain local.
4. Request probabilities once. Validate dimensions, class order, finite values,
   settings and reported model identity before accepting results.

The adapter uses REST because the inspected client 0.6.0 dependency bounds
conflicted with the frozen local-model environment. This is a recorded integration
choice, not a claim about current SDK compatibility. The
[dated request audit](M3_REQUEST_CONTRACT.md) preserves the comparison.

## Identity and failure handling

The server reports a checkpoint path rather than echoing the requested alias.
A narrow [identity policy](M3_CHECKPOINT_RESOLUTION.md) accepts the reviewed path
with matching family, execution mode, class order and settings. Unknown identities
remain rejected. This verifies server-reported metadata, not remote weight bytes.

Credentials are loaded only by explicit online operations, from the environment
or ignored local `.env`. They are not included in logs or exports. Requests use
bounded timeouts and no automatic paid retries. A token estimate is an execution
guard, not a guarantee of the actual charge.

## Evidence status

| Run | Status |
| --- | --- |
| Financial Stress validation · 24,000 fit / 8,000 predictions | [Verified](F2_RESULTS.md) |
| Financial Stress final holdout · same fit / 8,000 predictions | [Verified](F4_RESULTS.md) |
| Separate full-data fit · 40,000 / 30,000 predictions | [Column metadata unresolved](FINANCIAL_STRESS_FULL_DATA_RESULTS.md); excluded from the demo |
| Earlier synthetic benchmark | [Archived integration record](M3_RESULTS.md) |

Only the full-data runner has the later complete-response archive. It retains a
redacted response privately before validation; ordinary evidence exports remain
separate. See the [capture procedure](how-to/FINANCIAL_STRESS_FULL_DATA.md#inspect-the-complete-response-locally).
