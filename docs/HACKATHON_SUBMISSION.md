# Hackathon submission checklist

This checklist summarises the [organiser's terms supplied on 21 September](reference/TABPFN_3_5_HACKATHON_TERMS.txt)
and the submission form supplied on 24 September 2026. The original terms remain
unchanged. Deadline: **6 October 2026, 23:59 CEST** (23:59 Africa/Blantyre).

## Entry

**SCUBA · Financial Stress Predictor** is a visual app built around TabPFN-3.5-Plus.
Its primary theme is “Build an extension or app”, with a secondary fit under
“Take on a hard problem”. These are suggested themes, not separate judging tracks.

| Judging criterion | Weight | Evidence in the entry |
| --- | ---: | --- |
| Showcase of TabPFN-3.5 | 50% | TabPFN drives the shortlist; the final comparison shows its advantage at a fixed review capacity. |
| Creativity, originality and practical value | 30% | Predictions become a capacity choice, record inspection and export for customer care. |
| Technical quality and reproducibility | 20% | Input data, locked dependencies, tests, source attribution and offline replay of verified evidence. |

## Required materials

| Requirement | Status |
| --- | --- |
| TabPFN-3.5 is core to the project | Complete: it supplies the ranking probabilities. |
| Runnable repository with inputs or a public input-data URL | Prepared: source files, saved predictions and [run instructions](how-to/FINANCIAL_STRESS.md) are included. |
| Apache-2.0 original code with applicable data rights | Licence and attribution are documented in [licence scope](../LICENSE_SCOPE.md). |
| Public repository URL | Pending: the clean repository is private until publication is authorised. |
| Understandable project description | [Prepared](PRIOR_LABS_SUBMISSION_DRAFT.md). |
| Optional video | [Recording script](FINANCIAL_STRESS_WALKTHROUGH.md) ready; recording and upload unconfirmed. |
| Submit through the organiser's form | Pending. |

The supplied 24 September screenshot shows terms accepted. It does not show a
submitted entry. The form asks for name, repository URL and project description;
country, YouTube URL and social links are optional.

## Delivery sequence

1. Review the final description and recording.
2. Publish the reviewed clean repository when authorised.
3. Check the public URL and run instructions from a fresh checkout.
4. Submit the repository URL and description; add the optional video link.
5. Verify the entry confirmation before the deadline.

The repository URL is the primary deliverable. An optional ZIP can be attached
to a GitHub Release; do not commit a duplicate ZIP into source history.
The development repository contains deferred Nedbank material and must not be
published as the hackathon repository.

The separate full-data inference outputs remain excluded because their column
metadata is unresolved. The verified [final holdout](F4_RESULTS.md) supplies the
model-quality evidence for this entry.
