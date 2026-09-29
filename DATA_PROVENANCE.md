# Data provenance

## Financial Stress: the hackathon dataset

Source: Zindi's **Beginner Track: Financial Stress Prediction Challenge
(September Edition)**. Five original files were supplied on 21 September 2026:
training records, unlabelled test records, a submission template, a data dictionary
and a starter notebook. They remain unchanged under
[datasets/financial-stress](datasets/financial-stress/README.md).

The source manifest records each file's byte length and SHA-256. The challenge
rules supplied with the data declare CC BY-SA 4.0. The notebook is reference
material and is not executed by SCUBA.

There are 40,000 labelled and 30,000 unlabelled records, with 182 predictors.
The released target is `liquidity_stress_next_30d`. Monthly fields cover M1
(latest) to M6 (oldest). The real/synthetic origin is unverified; records are not
labelled as synthetic by this project.

SCUBA creates fixed train/validation/final partitions, model predictions,
aggregate diagnostics and review exports. These are adaptations of the source
data and retain CC BY-SA 4.0 attribution. The data and original SCUBA code have
separate [licence scopes](LICENSE_SCOPE.md).

## Separate historical work

The [synthetic dormancy benchmark](docs/SYNTHETIC_ARCHIVE.md) uses newly generated
fictional records. Its identifiers, dates, categories and event mechanisms were
invented, with no external records or fitted population distributions. Every
source and derived row is marked synthetic, and manifests retain provenance.
It is not combined with Financial Stress evidence.

A deferred Nedbank forecasting experiment is retained only in the development
repository. Its source files and the development Git history are excluded from
the hackathon release. It supplies no evidence for the Financial Stress results.
