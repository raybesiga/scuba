# N0 — Nedbank source packaging results

Date: 21 September 2026. Status: **complete for local source preservation and
offline reconstruction**. This is not a completed model experiment or permission
to publish the source data.

## Preserved inputs

All ten user-supplied files are pinned in
[`datasets/nedbank/manifest.json`](../datasets/nedbank/manifest.json), totalling
300,806,759 original bytes. The transaction ZIP is stored as eight ordered parts;
the largest part is 41,943,040 bytes (40 MiB). Nine other originals are stored
unchanged. Neither Git LFS nor a remote download is needed to reconstruct them.

The original README, dictionary, notebook and scorer are preserved. The source
ZIPs remain byte-identical, including their macOS metadata; only the three named
Parquet members are extracted by the project restore command. Source documentation
and scripts are reference material, not executable instructions for this project.

## Verification performed

Both commits were verified using a temporary checkout exported from Git's index,
independent of later working-tree edits and using the already-installed Python
environment. No dependency resolution or dataset upload was performed.

- Submission/scope documentation commit: `make check` passed Ruff lint, format
  checks and 117 tests.
- Data/restore candidate: `make check` passed Ruff lint, format checks and 120
  tests. Three new tests cover exact restoration, corruption/missing parts at each
  integrity layer, safe paths, duplicate names and refusal to overwrite output.
- `python -m scuba.source_bundle --verify` checked all ten originals, every stored
  part and three uncompressed Parquet members.
- `python -m scuba.source_bundle --output <new temporary directory>` reconstructed
  the package from staged files. All ten resulting originals were independently
  SHA-256 compared with the user's supplied Downloads files and matched.
- The final documentation-only additions were checked against the verified code
  and manifest hashes and their local links were checked in the final staged copy.
- `git diff --cached --check` passed.

Verified source hashes:

| File | SHA-256 |
| --- | --- |
| `src/scuba/source_bundle.py` | `420f0508ff66895e91e963524b7cce72ab72a528a1607ec85768ec31c0d8c5b7` |
| `tests/test_source_bundle.py` | `6b27803ff6748289a11135f0165c8823e9a978e41ca653dab33629f30f798f66` |
| `datasets/nedbank/manifest.json` | `685e4abfa403efb323c64341c112fa51871bbf123950e0255ca90e810db75bbb` |

Normal tests use tiny invented byte fixtures rather than any customer records.
The UI is unchanged; its existing results remain synthetic. No new UI checks or
model fits were needed for this source-packaging change.

## Limits and next milestone

The CSV audit established 8,360 unique labelled customers and 3,584 unique,
disjoint test customers, with matching submission-template IDs. Labels are finite,
non-negative integers, minimum 1, median 102, maximum 1,794; none are zero.

Archive integrity is established; Parquet row counts, coverage, temporal semantics,
duplicates and feature availability still require N1's audit. No claim of
anonymisation, real-world predictive quality, intervention benefit or source-rights
clearance follows from these checks. Public distribution remains pending resolution
of the source retention condition recorded in
[submission requirements](HACKATHON_SUBMISSION.md). No push, publication,
hosted-data upload or hackathon submission was performed.
