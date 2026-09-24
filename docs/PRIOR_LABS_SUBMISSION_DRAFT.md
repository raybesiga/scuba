# Prior Labs submission draft

Status: local review draft. Repository: https://github.com/raybesiga/scuba (private).
Public release and hackathon submission remain pending.

Primary theme: **Build an extension or app**. Secondary fit: **Take on a hard problem**.

## Project name

SCUBA — mobile-money signals for customer care

## Description

SCUBA turns six months of mobile-money activity into a focused customer-care
review list. An operator chooses a review capacity, inspects ranked snapshots and
their monthly transaction context, and exports a shortlist for human review.
TabPFN-3.5-Plus supplies the probabilities that drive the workflow.

The prototype uses the Zindi Financial Stress Prediction Challenge's supplied
30-day liquidity-stress outcome. It compares TabPFN-3.5-Plus with XGBoost, CatBoost,
logistic regression and a constant-prior reference on frozen train, validation
and final partitions. On the reserved 8,000-row holdout, TabPFN achieved log loss
0.2799 versus XGBoost's 0.3073 and found 542 of 1,200 labelled stress cases within
an 800-snapshot shortlist, versus XGBoost's 512. A post-hoc paired row-bootstrap
95% interval for those 30 additional cases is 9 to 50, assuming independent rows.
The practical proposition is more relevant support reviews within the same
workload. Retention, revenue and customer outcomes require an operator pilot.

The Radix workspace connects these predictions to an operator decision while
making evidence inspectable: full model comparisons, probability calibration with
bin sizes, cohort diagnostics, source provenance and server-reported checkpoint
identity. Saved predictions allow the demo to rebuild offline without another
API call. A separate original synthetic benchmark remains available as an archive.

The demo prioritises review; it does not contact customers, decide credit
eligibility or claim that an offer or outreach will improve outcomes. The dataset
has no observation dates or persistent customer identifier, so the evaluation is
a row holdout. Its real/synthetic origin and operational label definition remain
unverified. Those limits are visible in the product.

Original code is Apache-2.0. The Financial Stress source data and adaptations retain
the declared CC BY-SA 4.0 licence and Zindi attribution. The separately explored
Nedbank source data and local repository history are excluded from the proposed
public delivery snapshot.

## Two-minute recording walkthrough

The updated [recording walkthrough](FINANCIAL_STRESS_WALKTHROUGH.md) contains
word-for-word narration, timed screen cues, the judging-criteria mapping and a
reference table separating validation from final-holdout results.

It is prepared for review and rehearsal in Cap; no recording has been made.
The supplied submission screenshot labels the optional video field “YouTube URL”.
Public release and hackathon submission remain pending.
