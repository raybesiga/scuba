# Financial Stress source package

Unchanged files supplied by the user on 21 September 2026 for the Prior Labs
TabPFN-3.5 hackathon. Source: Zindi, **Beginner Track: Financial Stress Prediction
Challenge (September Edition)**. [Challenge and attribution source](https://zindi.world/competitions/financial-stress-prediction-challenge-2026-09-01),
[data page](https://zindi.world/competitions/financial-stress-prediction-challenge-2026-09-01/data).
No individual dataset author was established in the supplied material.

The challenge rules pasted by the user state: “You are allowed to access, use and
share challenge data for any commercial, non-commercial, research or education
purposes, under a CC-BY SA 4.0 license.” Declared data licence:
[Creative Commons Attribution-ShareAlike 4.0 International](https://creativecommons.org/licenses/by-sa/4.0/).
The source package remains under its source terms, not the project's Apache-2.0
code licence. Preserve this attribution and licence in copies and adaptations;
identify modifications. The supplied notebook is retained unchanged as reference
material and is never executed by our pipeline.

`manifest.json` pins the original five files by length and SHA-256. All originals
are stored intact under `files/`. Verify or restore offline:

```sh
PYTHONPATH=src python3 -m scuba.source_bundle --bundle datasets/financial-stress --verify
PYTHONPATH=src python3 -m scuba.source_bundle --bundle datasets/financial-stress --output artifacts/financial-stress/source
```

40,000 labelled rows, 30,000 unlabelled rows, 182 predictors. Real versus synthetic
origin is not established. IDs identify snapshots; dates and a separate persistent
customer key are absent. See the [experiment contract](../../docs/explanation/FINANCIAL_STRESS.md).
Public delivery and hosted uploads are separate actions from local preparation.
