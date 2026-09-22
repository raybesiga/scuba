# M3 checkpoint identity resolution

21 September 2026. The approved prediction-only continuation reused the retained fitted model and validation upload. The estimate was 10,000 tokens (`quota_v3`); actual per-operation tokens remain unavailable. Recorded stages are limits (0.924 s), estimate (0.244 s) and one prediction (4.773 s). It made no upload or fit request and no retry.

## Observed failure and evidence

The server returned 2,407 valid binary probability rows, classes `[0, 1]`, eight estimators, seed 3501, `fit_preprocessors`, billing family `v3.5`, execution mode `standard`, cache outcome `not_requested` and package version `8.5.0`. The only failed check compared requested alias `v3.5_default` with returned path `/app/tabpfn_models/tabpfn-v3.5-20260909.safetensors`. The original manifest remains failed under that historical check.

| Evidence | SHA-256 |
| --- | --- |
| `artifacts/m3-plus-prediction-continuation-1/manifest.json` | `f20d2b3a9b43cde82c6f6f75aeb4ec81dbe62ae9e72de019c4c9430da44fef1b` |
| Same directory, `response_evidence.json` | `ed6eefad450881a7aa558d30a950f4e17928006f6351e235fc040b59117fed2f` |

## Source-backed interpretation

Three pieces of official evidence support accepting the reported identity for this response:

1. The [model-selection guide](https://docs.priorlabs.ai/models/selecting-model-version.md) explicitly selects hosted Plus with `v3.5_default` in REST `tabpfn_config`. Retrieved 21 September; source SHA-256 `576f5bed4e63eca3a4adfcc6af266fe847c17fd926339f88bb99fabdcfa77039`.
2. The [official client 0.6.0](https://pypi.org/project/tabpfn-client/0.6.0/) defines version-default aliases and explains that the server resolves each to its current checkpoint. Its extracted `tabpfn_client/estimator.py` SHA-256 is `9b626b4e75fc91fce546cdc2e07213ffb0fd5f51edfdd2d28f41ab286b590403`; the wheel hash is pinned in the [request audit](M3_REQUEST_CONTRACT.md).
3. The [official model loader at commit c70b6ef](https://github.com/PriorLabs/TabPFN/blob/c70b6ef0488858d32244c52222abfc0c5be207d6/src/tabpfn/model_loading.py#L192) names exactly `tabpfn-v3.5-20260909.safetensors` as the default v3.5 checkpoint and separately names Fast. Source SHA-256 `756597f4795978dea96762828b262a7f182ef1bb4219c736bf9618ed5d9e7b54`. The [official model card](https://huggingface.co/Prior-Labs/tabpfn_3_5) corroborates that filename.

Together with the authenticated response's billing family, execution mode and matching settings, this supports an alias-resolution explanation for this continuation. Exact alias equality was too strict. This is a documented interpretation of server-reported identity, not independent attestation of remote checkpoint bytes. The OSS mapping does not expose proprietary Plus internals. Keep the benchmark label **hosted Plus requested; server-reported v3.5 checkpoint**, distinct from local base execution. The reported package version remains `8.5.0`; the source used to identify the checkpoint does not prove which server implementation is installed.

## Bounded fix and offline recovery

Policy `plus-checkpoint-20260909-v1` accepts only the exact observed absolute path for the Plus alias, with billing family `v3.5`, standard execution and explicit integer classes `[0, 1]`. All original shape, probability, task, row/column, package and requested-setting checks still apply. Unknown paths, alternative directories, dates, Fast/multiclass files, transformed strings and missing supporting metadata fail. Exact requested aliases remain supported; returned classes, when present, must match even on that path.

The offline revalidation script hashes the source manifest and response, reconstructs the original plan from frozen inputs, restores only retained metadata and recomputes checks. It writes a separate result with evidence label `offline_revalidated_live_response`. No token is loaded and no API request occurs. The original failed manifest and older unverified predictions remain unchanged; this response cannot certify them.

```sh
PYTHONPATH=src .venv/bin/python scripts/revalidate_tabpfn_response.py \
  --input artifacts/m1-15000-seed-3501 \
  --source artifacts/m3-plus-prediction-continuation-1 \
  --source-manifest-sha256 f20d2b3a9b43cde82c6f6f75aeb4ec81dbe62ae9e72de019c4c9430da44fef1b \
  --output artifacts/m3-plus-continuation-revalidated
```

Use a new output directory for any local replay. This command has no online mode. See [M3 results](M3_RESULTS.md) for verification and measured metrics. The fit-envelope discrepancy remains a documentation/SDK compatibility observation; this prediction-only experiment cannot determine how the server interprets every fit format.
