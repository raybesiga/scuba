# M3 model identity review — PAL and Gemini

Reviewed 21 September 2026. Advisory diagnosis and recovery plan; no additional TabPFN upload, fit or prediction was made. M3 remains in progress and preserved probabilities remain unverified. See [live evidence](M3_RESULTS.md).

The review below describes the pre-fix state. Its local diagnostic and request-audit actions are now completed in the [offline request-contract audit](M3_REQUEST_CONTRACT.md). Live identity verification remains unresolved.

## Consultation and evidence boundary

The user requested PAL MCP consensus with Gemini. Applied the local `okestreta-pal-workflows` skill. PAL `consensus` consulted `gemini-2.5-pro`, followed by a `chat` challenge in the same continuation: `64ca2ef6-70b9-4839-af89-4f7d5e07efd7`. An attempted `gemini-3-pro-preview` consultation returned provider HTTP 404 (retired model), despite PAL listing it as available. It supplied no assessment. This is agreement between the local analysis and one successful Gemini reviewer after challenge, not independent agreement between two successful external models.

Shared evidence comprised the integration source/test files, aggregate synthetic dimensions, request settings, pass/fail diagnostics, known protocol differences and billing constraints. No credentials, environment values, signed URLs, dataset rows, probabilities, resource IDs, account details or sensitive logs were shared. Model advice is not runtime proof.

## Diagnosis and disagreements resolved

Both analyses consider server-side alias resolution a leading explanation: `v3.5_default` may be reported as a concrete checkpoint. The existing validator requires an exact echo of the requested alias, and the mock fixture echoes it. However, the actual returned value and type from the historical attempt were not retained. Alias expansion is not proven; malformed identity metadata, API-contract drift or incorrect routing remain possible.

Gemini initially asserted 9/10 confidence, suggested broad prefix matching, and proposed certifying old probabilities from a later successful call. These suggestions were challenged. Gemini then explicitly withdrew the unsupported confidence and agreed that broad prefixes can accept the wrong family/variant, and that later success cannot certify an earlier response. The consolidated policy is to retain strict rejection until a specifically evidenced mapping can be applied. An exact alias-to-checkpoint mapping can be added when supported; arbitrary family resemblance cannot replace it.

Local source inspection also confirms a request-contract discrepancy: our documented REST fit body has top-level `task` and `tabpfn_config`, whereas SDK 0.6.0 serializes a nested `task_config` directly to `/tabpfn/fit`. This merits an offline contract audit. It does not establish that the live server ignored our requested configuration; matching prediction metadata on other settings does not resolve the fit-schema question.

## Consolidated recovery sequence

1. **Complete evidence capture before any validation.** Retain typed, bounded model identity and package-version evidence independently of whether their values pass acceptance. Redact credentials, URL user information, queries and fragments; do not assume that matching a filename regex is the only useful representation. Record omissions, original type, truncation and normalization explicitly. Test unexpected strings, checkpoint filenames, URI/path forms, nulls, lists, missing fields and hostile secret-bearing values. Current narrow regex capture is still incomplete.
2. **Audit requests offline.** Compare exact fit and prediction JSON from our adapter with the published REST contract and the pinned SDK serialization. Preserve the discrepancy; do not silently change settings or rebuild the approved plan. Use an isolated SDK environment only if static inspection cannot answer the serialization question, without downgrading frozen M2 dependencies or making inference calls.
3. **Seek evidence tied to the original run.** The read-only data-summary endpoint returned no dataset metadata, and the inspected fit-status schema has no checkpoint identity. Vendor confirmation or a recoverable original metadata record could establish the model used. Contacting the vendor requires a separate instruction to send that message. A later model response alone cannot rehabilitate the saved probabilities.
4. **Only then consider one approved continuation.** If historical identity remains unrecoverable, prepare an explicit prediction-only continuation using retained fitted/validation-upload IDs if still valid. Preserve the complete permitted response before acceptance and allow offline revalidation. Reuse avoids upload/refit work, but does not establish a lower prediction charge: the documented minimum is 10,000 tokens. Refresh the estimate and obtain a new explicit approval. Stop after that request; do not loop on failures.

Acceptance must distinguish the requested selector, the observed identifier, evidence establishing their relationship, and the final verification status. Recovering old results requires authoritative evidence tied to that original prediction/configuration. A new response is a separate result. Neither model advice nor a plausible alias pattern is enough to mark M3 complete.

## Advisory code review

PAL also emitted a partial implementation suggestion. It was not applied. A local adversarial check demonstrated that its proposed URL sanitizer removes query/fragment fields but retains username/password information in the URL authority. It also omitted the required `urlunsplit` import. The snippet was moved outside the repository; implementation must be independently designed and tested. This reinforces the distinction between useful model advice and verified code.

References: [official client 0.6.0](https://pypi.org/project/tabpfn-client/0.6.0/), [REST quickstart](https://docs.priorlabs.ai/api-reference/getting-started), [model selection](https://docs.priorlabs.ai/models/selecting-model-version), [metering](https://docs.priorlabs.ai/api-reference/metering). Public documentation and downloaded official SDK source informed the review; no external dataset was used.
