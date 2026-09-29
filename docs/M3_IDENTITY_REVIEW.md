# Archived model-identity diagnosis

Recorded 21 September 2026 during the synthetic benchmark. This was an advisory
review before the [checkpoint issue was resolved](M3_CHECKPOINT_RESOLUTION.md).
It is not the current integration status.

A requested external review with Gemini 2.5 Pro examined source code, tests,
request settings and aggregate dimensions. No credentials, dataset rows,
probabilities or live resource IDs were shared. A second requested model was
unavailable and contributed no assessment.

The review identified alias resolution as a possible explanation for a strict
identity mismatch. It did not establish the actual model, because the earlier
logger had discarded the returned identifier. Broad prefix matching and using
a later response to certify an earlier one were rejected.

The resulting approach was to preserve typed response evidence before validation,
audit the REST/SDK request difference offline, and accept only a specifically
evidenced alias-to-checkpoint mapping. A suggested URL sanitizer was also rejected:
it left URL user information intact. The implemented capture was independently
tested rather than copied from that suggestion.

The [request-contract audit](M3_REQUEST_CONTRACT.md) and
[accepted continuation](M3_RESULTS.md) record the verified work that followed.
Model advice was diagnostic input, not proof of runtime behaviour.
