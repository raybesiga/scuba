# M3 offline request-contract audit

Reviewed 21 September 2026. **Offline source and emitted-request checks passed; live server interpretation remains unresolved.** This audit made no TabPFN request, loaded no credential and changed no approved payload, model setting or request envelope. M3 remains in progress.

## Sources and reproducibility

The committed fixture `tests/fixtures/tabpfn_contracts_2026_09_20.json` records field declarations and representative Plus/Fast/Thinking requests derived from the previously downloaded [REST OpenAPI snapshot](https://docs.priorlabs.ai/api-reference/openapi.json) and [official SDK 0.6.0 wheel](https://pypi.org/project/tabpfn-client/0.6.0/). It contains invented resource identifiers, no dataset rows and no live resource IDs.

| Source | SHA-256 |
| --- | --- |
| OpenAPI snapshot, downloaded 20 September | `7051f7bce85dfbee02855fd0c6c792f6b595e7172e04fbd6741d634940860a1e` |
| SDK 0.6.0 wheel | `6f38bb7778aeadcc9a551d3c39667b794a8a1798e626ead0c9d9d55beb03f381` |
| SDK `api_models.py` | `af87acb367e2041bb3daea4bb3c394ea645f59bd6257151ec25a8c461f57189c` |
| SDK `client.py` | `3d74c2629fc6a83d045c1a4158079b0bce70d02f018abaecd67842988e630206` |

The audit script verifies these hashes, extracts SDK field declarations using Python's syntax parser and reconciles them with the committed snapshot. It never imports or executes the SDK. The SDK's `_fit` and `_predict` methods serialize their request models using `model_dump(mode="json", exclude_none=True)`; the reference JSON is a source-based reconstruction for our explicit settings, not a claim that the SDK was executed or that its schema matches the live server. No SDK environment, dependency downgrade or new dependency was needed.

With those already-downloaded files, reproduce the source check offline:

```sh
.venv/bin/python scripts/audit_tabpfn_contract_sources.py \
  --openapi /tmp/scuba-tabpfn-openapi.json \
  --sdk-wheel /tmp/scuba-tabpfn-client-0.6.0.whl
```

Use equivalent local paths if the cache files move. The script rejects changed source hashes. Normal `make check` uses only the committed fixture and synthetic mock transport; it does not depend on these temporary files or download anything. The local audit result is `artifacts/m3-request-contract-audit.json`.

## Exact differences

| Concern | Current adapter / published REST snapshot | SDK 0.6.0 source | Decision |
| --- | --- | --- | --- |
| Fit task | Top-level `task` | `task_config.task` | Keep the approved REST form; record discrepancy |
| Fit estimator settings | Top-level `tabpfn_config` | `task_config.tabpfn_config` | Same intended values; different envelopes |
| Thinking fit settings | `thinking_effort`, `thinking_timeout_s`, `thinking_effort_metric` | `thinking_config.effort`, `.timeout_secs`, `.metric` | Preserve explicit medium/300/log-loss choices; no silent translation |
| Fit systems | Top-level `tabpfn_systems` | Same | `preprocessing`, `text`; add `thinking` only for Thinking |
| Prediction | IDs plus `task_config` containing task/config/output type | Same for all fields we send | Exact request JSON agrees for our settings |
| Optional `force_refit` | Declared in REST fit/predict schemas; omitted by adapter | Absent from inspected SDK request models | Do not add it or infer reuse behaviour |
| Response metadata | Rows, columns, task, package version, config | Adds optional billing version, execution mode, cache outcome, classes and top-level estimator count | Retain relevant optional fields as typed diagnostics; availability and billing meaning remain unverified |

Mocked executions capture the actual outgoing fit and prediction bodies for all three supported variants and compare them with the fixture. They also verify that current fit bodies satisfy the REST field envelope and differ from the SDK envelope. This is a field-and-value audit, not a complete JSON Schema validator. A nested SDK fit request is deliberately rejected by the frozen REST fixture; this prevents an unreviewed format switch from appearing to pass.

The discrepancy could reflect compatibility support, documentation drift or different backend handling. A successful HTTP response and matching prediction settings do not prove that every fit field was honoured. This audit does not establish the cause of the historical model-identifier mismatch.

## Rationale for emitted fit and prediction fields

| Field | Rationale |
| --- | --- |
| Fit `train_set_upload_id` | Reference the training features and labels prepared/uploaded in this execution; validated UUID |
| Fit `task` | Explicit binary classification task from the experiment |
| Fit `tabpfn_systems` | Declared hosted preprocessing/text behaviour; explicit Thinking system only for that variant |
| `tabpfn_config.model_path` | Explicit Plus or Fast selector from the reviewed model guide; never infer a different family from a prefix |
| `tabpfn_config.n_estimators` | Fixed eight-estimator protocol and matching cost estimate |
| `tabpfn_config.random_state` | Fixed model seed 3501, independent of generator sensitivity seeds |
| `tabpfn_config.fit_mode` | Explicit `fit_preprocessors`; consistent fit/prediction configuration |
| Thinking effort / timeout / metric | Medium effort, 300-second server fit budget and log-loss objective, only when selected |
| Predict `fitted_train_set_id` | Bind inference to the fitted resource returned by this execution |
| Predict `test_set_upload_id` | API-named test resource contains only our validation features, not the benchmark's main test cohort |
| Predict `task_config.task` | Explicit classification, matching fit |
| Predict `task_config.tabpfn_config` | Repeat the declared selector and settings; do not assume that retained fitted IDs prevent prediction-time overrides |
| Predict `task_config.predict_params.output_type` | Request two-class probabilities for validation scoring |

Upload preparation remains CSV with explicit serialized byte sizes and `use_chunks=false`; the synthetic description labels training data. No identifiers, dates, provenance flags or validation labels enter model matrices. SDK upload serialization uses Parquet and optional CRC32C deduplication; this audit does not change our approved CSV payloads or claim wire-byte equivalence with the SDK.

## Response evidence boundary

New runs write `response_evidence.json` and its manifest hash **before** model-identity validation or scoring. It records requested variant/settings, typed reported identity/settings/package metadata, pass/fail checks and numerically valid probability rows. Missing, null, malformed, redacted, transformed, truncated and unexpected-container cases remain distinguishable. Rejected runs refer to this same file as unverified evidence; accepted predictions remain a separate CSV. Existing historical files are not rewritten.

Only selected metadata fields are captured. Identifier-like paths and URI forms are retained without URL user information, query or fragment values. Known credentials (including percent-encoded forms) and credential markers are redacted; arbitrary prose, control characters, oversized strings and unknown object contents are explicitly omitted. Lists have bounded depth/length. This is a bounded diagnostic policy, not an assertion that every possible secret can be inferred from arbitrary text. Exact-secret redaction is supplied at runtime from the token without persisting it. Unknown model identifiers are captured for investigation and remain rejected by the unchanged identity check.

Source/plan hashes, synthetic provenance and the new response hash bind the local evidence. Capture cannot recover the model name lost in earlier attempts. No old probability file has been rescored, accepted or relabelled.
