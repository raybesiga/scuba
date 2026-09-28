# Rebuild the frozen demo

Synthetic benchmark archive. This dated record is separate from the
[Financial Stress entry](README.md). Status and test counts describe that milestone.

Audience: a reviewer or presenter rebuilding the saved SCUBA results locally.

This procedure rebuilds the presentation from verified M4 evidence. It does not regenerate the benchmark, refit models or replay paid predictions. The hosted response remains a saved observation. The original 19-file synthetic evidence bundle must accompany this historical
rebuild. The Financial Stress release includes an already-built synthetic archive;
its current rebuild is described in the [run guide](how-to/FINANCIAL_STRESS.md).

## Prerequisites

- Python 3.14.5, uv, Node 24 and npm. Other runtime versions remain unverified.
- The repository and its `uv.lock` and `report-ui/package-lock.json`.
- The 19 original inputs listed in `demo-inputs.json`, either in this repository's `artifacts` directory or an exported evidence bundle.
- Cached dependencies for offline installation, or a separately authorised initial installation.

Select Node 24.13.0 in your version manager and confirm `node --version` before installation. Some shells select a different Node version when the checkout directory changes. Install the locked dependencies into new local directories:

```sh
uv sync --offline --locked --python 3.14.5 --extra models --extra tabpfn
npm ci --prefix report-ui --offline --ignore-scripts --no-audit --no-fund
```

The optional platform package supplies the esbuild executable; the successful build verifies that it is available without package installation scripts. A cache miss must be resolved before an offline rehearsal. Do not silently enable network access.

If the packages were cached outside uv's default cache, add `--cache-dir /path/to/cached-packages` to the installation command. The recorded rehearsal used the existing project cache at `/private/tmp/scuba-uv-cache`. It installed new package directories; it did not reuse the working checkout's virtual environment or `node_modules`.

## One-command rebuild

From the repository root:

```sh
make demo
```

Expected result: `artifacts/m5-demo/index.html`, `evidence.json` and `manifest.json`. Open the HTML locally or serve only its output directory. The page uses embedded assets and data. The build never loads `.env` or contacts the model API.

The output directory must be new. Keep previous results and choose another directory for a replay:

```sh
make demo DEMO_OUTPUT=artifacts/m5-demo-replay
```

Compare the three output files byte for byte. Identical source and dependency versions must produce identical files. The presentation manifest records UI source, dependency lock and output hashes. The existing report gate verifies completed evaluations and cohort consistency after the pinned input hashes pass.

## Transfer evidence to a fresh checkout locally

Export only the pinned inputs to a new directory:

```sh
PYTHONPATH=src .venv/bin/python -m scuba.demo export-evidence --output /tmp/scuba-demo-evidence
```

This is a local copy, not an upload. It includes aggregate evaluations and source manifests. It excludes `.env`, raw customer/event tables, prediction payloads and unrelated files. Keep the bundle local unless sharing is explicitly approved.

In the fresh checkout, install the locked dependencies, then run:

```sh
make check
make ui-check
make demo EVIDENCE_ROOT=/tmp/scuba-demo-evidence
make demo EVIDENCE_ROOT=/tmp/scuba-demo-evidence DEMO_OUTPUT=artifacts/m5-demo-replay
```

No source path rewriting is required. Evidence retains its original relative paths inside the bundle. Missing or changed evidence fails before the build creates output. Restore the original bundle rather than editing its expected hashes to make a check pass.

## Reproducing the scientific work

Presentation replay proves that the saved evidence can be checked and displayed on a fresh dependency installation. It does not independently reproduce hosted model execution or measured latency.

For the original synthetic bundle, use a separate checkout of development commit
`8abfc39` with Python 3.14.5. That commit belongs to the development repository
and is not included in the clean release history. Run its `scuba prepare` command for 15,000 customers with each seed 3501, 3502 and 3503, keeping split seed 3501. The historical source hashes are part of those manifests; regenerating from current sources is not an exact M1 replay. Then follow [local comparator results](M2_RESULTS.md) and [frozen final evaluation instructions](M4_FINAL_RESULTS.md) against the original plans and approved hashes. Local timing varies by machine. A new hosted run requires separate approval and cannot reproduce the server's historical state exactly.
