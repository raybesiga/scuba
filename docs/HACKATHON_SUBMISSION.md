# Prior Labs submission requirements and current scope

Recorded 21 September 2026. The canonical reference for this checklist is the
[unchanged terms supplied by the user](reference/TABPFN_3_5_HACKATHON_TERMS.txt).
Retaining the text is not an action accepting terms or submitting an entry.

## Submission contract

| Clause | Requirement | Current evidence / remaining work |
| --- | --- | --- |
| 3.1 | TabPFN-3.5 must be core to the project. | Verified TabPFN-3.5-Plus runs exist for the synthetic benchmark. Verified Financial Stress TabPFN-3.5-Plus validation results are recorded in [F2](F2_RESULTS.md). |
| 3.2 | Repository contains runnable code/instructions and input data, or a public input-data URL. | The [Financial Stress source package](../datasets/financial-stress/README.md) contains the five supplied originals with offline verification. Local preparation and baselines replay from a staged checkout; TabPFN validation is verified; the [operator UI](F3_RESULTS.md), [final holdout](F4_RESULTS.md) and portable evidence replay are complete. Login-only download access is not a verified public-data URL. |
| 3.3 | Hold the necessary rights to use and publish submitted material. | Financial Stress rules supplied by the user state CC BY-SA 4.0. Preserve attribution. The separate Nedbank history has an unresolved retention condition and must be reviewed before public delivery. |
| 3.5 | Public source repository under Apache-2.0 and an understandable project description. | Apache-2.0 added for original project code; third-party material retains its terms. Public delivery is not authorised by local commit approval. |
| 3.6 | Submit by 6 October 2026, 23:59 CEST. | Same local deadline in Africa/Blantyre (UTC+2). |
| 4.2 | TabPFN showcase 50%; creativity/practical value 30%; technical quality/reproducibility 20%. | The working operator workflow, five-model final comparison and portable replay demonstrate these criteria; [submission description](PRIOR_LABS_SUBMISSION_DRAFT.md) is prepared. |

## Product and experiment direction

Decision owner: a customer-care operator choosing which customer snapshots to
review. Financial Stress is the first use case: TabPFN-3.5 predicts the supplied
30-day stress label from six months of summaries; the workflow prioritises review
capacity and shows observed activity context. No learned offer effectiveness or
causal explanation is claimed. See the [contract](explanation/FINANCIAL_STRESS.md)
and [milestones F0–F4](ROADMAP.md).

Nedbank transaction-volume forecasting is deferred. A future use-case selector
will connect both implemented workflows. The synthetic benchmark remains separate
historical evidence, and does not validate either external dataset.

Financial Stress uses a frozen stratified row holdout because dates and persistent
customer identifiers are unavailable. Its label mechanics and real/synthetic
origin are unverified. Keep these limitations visible in the final demo.

The Financial Stress source rules supplied by the user declare CC BY-SA 4.0 reuse
for commercial, non-commercial, research and educational purposes. Source files
remain under that licence with attribution, separate from Apache-2.0 project code.
The user-authorised Financial Stress training/validation upload and single hosted
prediction are complete; public delivery has not occurred.

## Deferred Nedbank source terms and publication status

Source: [Nedbank Transaction Volume Forecasting Challenge](https://zindi.world/competitions/nedbank-transaction-volume-forecasting-challenge)
and its [data page](https://zindi.world/competitions/nedbank-transaction-volume-forecasting-challenge/data).
The user supplied the downloaded package and explicitly requested local Git
inclusion on 21 September 2026. There is no recorded permission to upload the
records to Prior Labs, publish the repository, or submit an entry yet.

On 21 September 2026 the challenge page listed CC-BY SA 4.0 and also stated:
“You agree to delete the data within 30 days of competition close.” Its listed
close is 3 May 2026. The supplied README repeats CC-BY SA 4.0 but does not resolve
that condition. Record updated source-owner permission or applicable revised terms
before public distribution. The Prior Labs terms do not grant rights to third-party
datasets. See [licence scope](../LICENSE_SCOPE.md).

The supplied scorer consumes raw counts and applies `log1p` internally; the Zindi
website asks for transformed submission values. Our operator UI and local count
evaluation should use raw counts. Entering the Zindi competition is not our goal.

## F4 delivery state

The reserved final comparison and portable offline evidence are verified. The
full-data 40,000/30,000 run returned predictions with a 15,728-token estimate;
[acceptance remains unresolved](FINANCIAL_STRESS_FULL_DATA_RESULTS.md) because
the server reports 184 columns for the verified 182-column upload.
The single complete-response diagnostic reproduced the same predictions and
column count. It did not explain the discrepancy. Further inference is stopped;
the public demo uses the separately verified validation/final-holdout evidence.
Public repository creation and form submission remain
unperformed. A public delivery candidate must exclude Nedbank source data and the
local repository history. The [F4 record](F4_RESULTS.md) and
[submission draft](PRIOR_LABS_SUBMISSION_DRAFT.md) state the current scope.
