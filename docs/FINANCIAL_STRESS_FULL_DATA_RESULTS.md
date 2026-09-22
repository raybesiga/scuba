# Financial Stress full-data execution — column-count check unresolved

**Latest status, 22 September:** the user-authorised single diagnostic prediction
reused the existing fitted model and test upload. Its complete HTTP 200 response
again reports 184 columns and returns exactly the same 30,000 probability pairs.
No uploads or fits occurred. Full-data acceptance remains unresolved; no further
prediction attempt is planned. Submission preparation proceeds with the separately
verified final holdout and validation workflow.

22 September 2026. The user explicitly approved the full payload to Prior Labs.
One full-data fit and one prediction completed at the service, returning 30,000
binary probability rows. Local acceptance remains blocked: the uploaded tables
have **182 features**, but the response reports **184 columns**. No accepted
prediction CSV was exported, no dashboard was replaced and no submission occurred.

## What ran

- TabPFN-3.5-Plus, eight estimators, seed 3501, unchanged F2/F4 settings.
- All 40,000 labelled training snapshots, including the former validation/final
  rows, and all 30,000 unlabelled Test.csv snapshots. IDs were excluded from uploads.
- Fresh estimate: 15,728 service tokens; execution guard: 20,000. Actual charges
  are not reported by the response. One potentially billed prediction was made.
- Fitted resource: `01a0c8a8-0389-75a0-be50-e22621f0af37`.
- Test upload: `01a0c8a8-362f-7b03-beab-23073b521c97`.
- Server-reported checkpoint:
  `/app/tabpfn_models/tabpfn-v3.5-20260909.safetensors`.
- Completed request sequence: 118.63 seconds overall; training-feature upload
  40.92 seconds, fit 13.52 seconds, test-feature upload 29.46 seconds, prediction
  30.88 seconds. These are single observed timings, not controlled benchmarks.

The first transfer attempt timed out after 30 seconds while uploading training
features, before labels, fitting or prediction. The upload path incorrectly used
the short metadata timeout. The fix gives signed data transfers a 180-second
idle timeout, retaining 10-second connect and 30-second metadata/stream idle
timeouts. One deliberate recovery attempt used the same approved plan and passed
the transfer stage. There was no prediction retry.

[First attempt](reference/financial-stress-full-data-attempt-v1.json),
[completed service sequence and failed local acceptance](reference/financial-stress-full-data-attempt-v2.json),
[approved plan](reference/financial-stress-full-data-plan-v1.json).

## Evidence and remaining uncertainty

The saved response passes probability shape, finite values, range, row sums,
30,000-row metadata, binary class order, classification task, package-version
format, server-reported checkpoint identity and all requested model settings.
Only the equality check for column count fails.

An independent CSV-reader audit reconstructed the approved payload bytes and
checked every row: 40,000 training feature rows and 30,000 inference rows each
have exactly 182 fields; all 40,000 training-label rows have one field. Payload
hashes match the approved plan. No ID or label is present in either feature table.
There is no change in feature dtype, missingness presence or categorical
cardinality between the original training subset and all labelled training rows.
This rules out a local accidental ID/target upload or malformed row width.

[Payload audit](reference/financial-stress-full-data-payload-audit-v1.json) and
[response diagnostic](reference/financial-stress-full-data-diagnostic-v1.json)
retain these observations without publishing the raw probability matrix.
Filtered response evidence is preserved locally at
`artifacts/financial-stress/full-data-hosted-v2/response_evidence.json` and is
bound to the manifest by SHA-256. It remains unverified evidence. This file is
not the complete original HTTP response: the capture code retained valid
probabilities and an allowlist of metadata/configuration fields only.

Three hypotheses were considered:

1. **Extra columns in our upload.** Contradicted by the exact-byte payload audit.
2. **The server reports transformed dimensions.** Plausible, but not established.
   The [preprocessing documentation](https://docs.priorlabs.ai/improving-performance/preprocessing)
   describes feature expansion. It does not explain this specific two-column
   difference. The [public OpenAPI schema](https://docs.priorlabs.ai/api-reference/openapi.json)
   declares `test_set_num_cols` without defining raw versus transformed columns.
3. **Server metadata or resource-binding error.** Not ruled out. The official
   SDK's read-only upload-summary endpoint returned no dataset entries, so it did
   not provide dimensions or feature names for these resources.

The next decisive evidence is the raw and transformed feature schema for the
fitted/test resource IDs above, or a provider clarification of the reported field.
The specific question is: **What does `test_set_num_cols=184` count for this
182-column upload, and why does it differ from earlier responses?** This
diagnostic question is prepared, not sent. No additional prediction is needed to
inspect the saved probabilities or revalidate them after the discrepancy is resolved.
Do not waive the check, change the approved feature count or label these results
verified merely to make the run pass.

### Read-only follow-up

A subsequent call to the official SDK-documented `get_fit_status` endpoint
confirmed that the existing fitted resource completed. Its timings attribute
11.073 seconds to training-data loading/validation/preprocessing and zero to the
fit stage; they do not expose raw or transformed feature schemas. No upload,
fit or prediction was performed by this follow-up.

The current official SDK source still declares `test_set_num_cols` as an integer
without defining its measurement stage; prediction code passes server metadata
through. An exact-field search of the official client's issues found no matches.
The service's root OpenAPI URL redirected to a protected documentation surface;
no access control was bypassed.

The expanded local audit checks all string dtypes, including pandas' `str` dtype:
the five categorical feature sets are identical across the earlier training
subset, all training rows and the unlabelled test rows. Cardinalities are
2, 7, 2, 3 and 3. Neither training version has missing values or constant features,
and no feature crosses the four-value cardinality boundary. These facts do not
identify a specific expansion that would explain the extra two columns.

[Follow-up evidence](reference/financial-stress-full-data-followup-v1.json)
records the findings. A [concrete public question](PRIOR_LABS_COLUMN_COUNT_QUESTION.md)
is drafted for the official client repository, omitting records, account details
and resource IDs. Posting it awaits the user's publication approval. The exact
cause remains unresolved; transformed features and incorrect server metadata are
still hypotheses, not established explanations.

### Response structure investigation and correction

The user's suggestion that the extra two columns might be prediction outputs
was checked against all three retained Financial Stress responses:

| Run | Input columns | Probability matrix | Reported columns |
| --- | ---: | ---: | ---: |
| Validation | 182 | 8,000 × 2 | 182 |
| Reserved holdout | 182 | 8,000 × 2 | 182 |
| Full data | 182 | 30,000 × 2 | 184 |

The two probability columns correspond to reported classes `[0, 1]`: no stress
and stress. Every row sums to one within 0.000000075. They are not a prediction
column and a metadata column. The capture code reads metadata from a separate
object; the published REST response schema likewise separates prediction and
metadata. No local step concatenates the outputs onto the uploaded features.

Counting input columns plus two probability columns fits the full-data arithmetic,
but cannot explain all three runs as a uniform convention. A change in a server
execution path could still account for it; the saved evidence cannot establish
that. All three responses report package version 9.0.0 and the same model settings.

**Correction to the previous explanation:** we cannot say the server supplied no
column names. Our old capture did not inventory unknown response fields, so such
fields could have been discarded. The complete response cannot be reconstructed
from this filtered file. The inspected published REST routes and official SDK do
not identify a read-only method for retrieving that prediction response. MCP
documentation describing download URLs for MCP-generated predictions does not
establish that this REST operation has a retrievable download URL.

Future captures now retain bounded field-name/type/container-size inventories for
the response, metadata and configuration, without retaining unknown field values.
They explicitly state that the raw response is not preserved and count omitted
inventory entries. This fixes the missing field-presence evidence for future
calls; it does not recover past fields or resolve the server's counting behaviour.
Historical evidence files and acceptance rules are unchanged. No new prediction
was made during this investigation.

[Response structure audit](reference/financial-stress-response-structure-audit-v1.json)
records the comparison, probability checks and hashes of the unchanged evidence.
The capture regression verifies that unexpected field presence remains visible,
unknown values and credential-like keys stay excluded, and mismatched column
counts still fail acceptance. `make check` passes 148 offline tests, lint and format.

### Complete response capture fix

The field inventory alone did not fix the loss of unknown values. The full-data
runner now archives the complete received prediction body separately, before
HTTP-status, JSON or model-contract validation. JSON fields and arrays are retained
without filtering or truncation, except for explicit credential and URL redaction;
error and non-JSON bodies are retained too. The private file is created atomically,
cannot overwrite existing evidence, and has a checksum in the run manifest.
Archive-write failures stop acceptance without retrying prediction.

The [capture procedure](how-to/FINANCIAL_STRESS_FULL_DATA.md#inspect-the-complete-response-locally)
explains storage, redaction and verification. Offline regression tests cover
184 feature names and unfamiliar nested values surviving before a column-count
rejection, HTTP/JSON failures, credential redaction, owner-only permissions,
archive tampering and write failure. This changes future full-data captures;
the historical response remains unchanged and its discarded fields remain lost.
No new service request was made for this fix.
`make check` passes Ruff lint, formatting and all 155 offline tests.

## Verification and delivery state

### Authorised complete-response diagnostic

The diagnostic made one prediction request after fresh metadata checks, with an
estimate of 15,728 service tokens. Prediction took 27.91 seconds; actual charges
are unavailable. The complete body was captured privately with zero redactions.
It has exactly three top-level fields: `prediction`, `metadata`, and `timings`.
The metadata contains 11 fields and its model configuration contains 14 fields.
There is no named raw or transformed feature schema in this response.

The returned categorical indices are `[179, 180, 181]`; those positions in the
uploaded feature order are the numerical M4/M5/M6 daily balance columns. This
suggests a processed/reordered representation or incorrect metadata. It does not
identify the additional two columns. The returned inference configuration sets
`TRANSFORM_DATES` and `TRANSFORM_TEXT` to false. These values alone do not describe
all server preprocessing. No acceptance check was waived.

All 30,000 two-class probability pairs are bit-for-bit identical to the earlier
run; maximum absolute difference is zero. All checks other than column count pass.
Reproducibility of these outputs does not by itself prove the column metadata is
correct. The agreed bounded diagnostic is finished; the full-data output stays
outside the public dashboard and submission evidence.

[Sanitised diagnostic record](reference/financial-stress-complete-response-diagnostic-v1.json)
contains the complete metadata/configuration, timings, field names, hashes and
comparison results without publishing predictions or the private response archive.

The timeout regression fails against the previous transfer code and passes after
the fix. `make check` passes Ruff and 146 offline Python tests; `make ui-check`
passes nine UI tests, TypeScript and formatting. The fix was checked independently
from a staged checkout and committed separately.

The [reserved-holdout comparison](F4_RESULTS.md) remains the quality evidence for
the earlier 24,000-row fit. These 30,000 rows have no outcome labels, so even an
accepted full-data output cannot yield new accuracy or capture metrics. The
existing validation dashboard and final-results tab remain unchanged. Full-data
output acceptance and F4 submission review remain open.
