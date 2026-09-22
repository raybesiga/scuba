# Integration learning and observations

Documentation reviewed 20 September 2026; integration evidence updated 21 September 2026. Authentication, limits/estimate requests, synthetic uploads and standard fit succeeded. Two separately approved prediction requests returned HTTP/JSON success but failed the local response contract. The latest isolates a model-identifier mismatch and preserves 2,407 valid probability rows as unverified evidence. No accepted TabPFN scores or deployment exist; consumption is uncertain.

## Official learning path

| Step | Official source | What to learn or verify |
| --- | --- | --- |
| 1 | [Overview](https://docs.priorlabs.ai/overview) | In-context prediction model and supported workflow. |
| 2 | [Quickstart](https://docs.priorlabs.ai/quickstart) | Local versus hosted package; probability outputs and authentication. |
| 3 | [Cookbook](https://github.com/PriorLabs/tabpfn-cookbook), [XGBoost recipe](https://docs.priorlabs.ai/cookbook/tabpfn_vs_xgboost) | Comparator structure; use only our generated inputs. Recipe page retrieval was unavailable in this review; revisit before comparator implementation. |
| 4 | [REST API](https://docs.priorlabs.ai/api-reference/getting-started) | Current JSON upload/fit/predict sequence and model-limit preflight. |
| 5 | [Models](https://docs.priorlabs.ai/models), [selection](https://docs.priorlabs.ai/models/selecting-model-version) | Pin resolved variant and settings; do not rely on moving defaults. |
| 6 | [Metering](https://docs.priorlabs.ai/api-reference/metering), [rate limits](https://docs.priorlabs.ai/api-reference/rate-limits) | Estimate tokens; distinguish usage budget from request throttling. |
| 7 | [Changelog](https://docs.priorlabs.ai/changelog), [3.5 release](https://docs.priorlabs.ai/changelog/tabpfn-3.5) | Check client compatibility and changed defaults before every benchmark freeze. |
| 8 | [Microsoft Foundry](https://docs.priorlabs.ai/integrations/foundry) | Endpoint/authentication differences and version availability; documentation review only. |
| 9 | [SageMaker](https://docs.priorlabs.ai/integrations/sagemaker) | Endpoint, GPU/payload constraints and Thinking access; documentation review only. |

## Initial observations — documentation only

- **Variant identity:** quickstart uses hosted Plus; local `tabpfn` uses base. REST documents `v3.5_default` as Plus and `v3.5-fast_default` as Fast. The 3.5 changelog also mentions API base availability. Resolve the base selector against the current client/model catalogue before implementing; never relabel Plus as base.
- **Version drift:** the release documents `tabpfn` 9.0.0 and `tabpfn-client` 0.6.0. Fast is alpha. Record actual installed and server-reported versions; these are starting references, not tested project dependencies.
- **Usage planning:** metering supports estimates using dimensions/settings without uploading rows. Thinking fits and predictions share token budgets; standard fits and uploads have no separate token charge. Timed-out work may still be charged. The documented temporary promotion ends on 29 September, before our deadline, so later estimates must be refreshed.
- **Failure handling proposal:** no automatic retries of ambiguous billable operations. For explicit rate-limit responses, bounded backoff (at most two retries) must fit the approved budget/deadline and respect server reset guidance; quota exhaustion stops the run. Record outcome/status without tokens, signed URLs or payloads.
- **Cloud documentation mismatch:** the Foundry setup still links a 3-Plus model while the 3.5 changelog announces 3.5 availability. Verify the deployed version if this route is ever tested. Existing endpoints do not automatically upgrade. SageMaker describes 3.5-Plus and separate enterprise access for Thinking; endpoint compute costs differ from hosted API tokens.

## Evidence log for future runs

Add one row per observation with: date, source/route, exact version, attempted step, expected behaviour, observed behaviour, sanitised evidence path, elapsed effort, impact and next action. Classify evidence as `docs_only`, `local_dependency_resolution`, `offline_source_audit`, `offline_plan`, `offline_mock`, `live_metadata_only`, `live_attempt` or `live_verified`. Metadata-only evidence does not establish model execution. Keep model scores in benchmark output, and usability/authentication/limits/retry observations here. Unavailable variants get explicit skip reasons, not zero scores. Foundry/SageMaker are learning paths, not planned resource deployments.


## M3 implementation observations — 20–21 September 2026

| Route/step | Evidence class | Observed outcome | Next action |
| --- | --- | --- | --- |
| Quickstart and model selection | docs_only | Hosted default is Plus; explicit Fast/Thinking settings recorded. Base identity not confirmed for this REST adapter. | Confirm reported model metadata during a live run. |
| Python SDK 0.6.0 | local_dependency_resolution | SDK scikit-learn/pandas upper bounds conflict with frozen M2 pins; optional REST dependencies resolve without changing them. | Use REST now; isolate an SDK environment if later needed. |
| REST upload/fit/predict | offline_mock | Full Plus/Fast/Thinking flows, duplicate uploads, response validation and failure handling pass. The approved live path reached prediction but failed its response contract; offline success did not establish live conformance. | Preserve the failure and require a new budget approval before another prediction. |
| Secrets | offline_mock | Explicit local loading, environment precedence and safe missing/invalid-key errors pass. | Keep the token in ignored `.env`, never in chat or tracked files. |
| Full-size payload plans | offline_plan | All three seeds fit the local contract; primary plan and row map replay byte for byte in a fresh environment. | Primary Plus passed live limits; other variants/seeds need their own reviewed estimates. |
| Authenticated limits/estimate, 21 September | live_metadata_only | Primary Plus passes all returned limits. Estimate: 10,000 tokens, `quota_v3`; limits 1.038 s, estimate 0.510 s. Zero rows uploaded. Evidence: `artifacts/m3-plus-online-preflight/manifest.json`. | Approval was given; a further potentially billable attempt needs a new budget approval. |
| Usage reporting | docs_only | Estimate endpoint supplies token estimates and pricing version; published prediction response omits per-operation charges. | Record unavailable actual tokens honestly until separate usage evidence exists. |
| Required GCS Host header, 21 September | live_attempt | First attempt stopped before upload. Sanitised metadata inspection identified the required Host header. The tested correction permits it only when it matches the storage URL. | Keep conflicting hosts and credential headers rejected. |
| Primary Plus prediction, 21 September | live_attempt | 3,040,588 synthetic bytes uploaded; fit and prediction HTTP/JSON requests succeeded. Local prediction contract failed, exact mismatch not retained. Potential charge unknown. Evidence: `artifacts/m3-plus-seed-3501-live-verified/manifest.json`; the directory name does not denote success. | Per-field diagnostics and quarantined evidence are now implemented. Obtain a new budget approval before retrying. |
| Additional approved Plus attempt, 21 September | live_attempt | Fresh estimate 10,000 tokens; one prediction request. All checks passed except model-identifier equality. Preserved 2,407 valid probability rows in `artifacts/m3-plus-seed-3501-attempt-3/unverified_response.json`; no accepted scores. Returned identifier value was omitted by this diagnostic version. | Confirm alias/checkpoint identity before accepting results. Recognisable identifier capture is now tested; no further prediction is approved. |
| Response evidence and source audit, 21 September | offline_source_audit / offline_mock | Metadata persists before validation; 77 tests and Ruff pass. Pinned source hashes and actual mocked request JSON confirm REST/SDK fit-envelope differences. Approved plan is byte-identical; historical live evidence unchanged. Zero TabPFN calls. | Local preparation complete; resolve live model identity and server interpretation. See [request-contract audit](M3_REQUEST_CONTRACT.md). |

See [M3 evidence](M3_RESULTS.md) for exact payload counts, plan hashes and remaining gates. No mock probabilities are reported as model benchmark scores.
