# Prior Labs submission draft

Status: private preparation at https://github.com/raybesiga/scuba.
Not publicly accessible and not submitted to the hackathon.

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
an 800-snapshot shortlist, versus XGBoost's 512.

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

## Two-minute demo script

1. **0:00–0:20 — decision.** Open the review workspace. Explain that the operator
   has limited review capacity and a supplied 30-day financial-stress outcome.
   Distinguish snapshots from verified unique customers.
2. **0:20–0:45 — workflow.** Switch from 10% to 5%; show that shortlist size and
   observed validation capture change together. Inspect a snapshot's M6-to-M1
   activity, explaining that the changes are context rather than causal reasons.
3. **0:45–1:05 — action.** Search and sort the shortlist, then export its CSV.
   Explain that human review is the next step; no automatic contact is made.
4. **1:05–1:35 — model evidence.** Return to 10% capacity and open Final holdout.
   Show the 542-versus-512 comparison and lower log loss on rows withheld until
   settings were frozen. Show calibration support and one cohort audit.
5. **1:35–2:00 — reproducibility and limits.** Open Data & limitations. Explain
   the row split, unknown source timing, verified model identity, separate data
   licence and offline rebuild. End on the operator workflow.

The script is prepared but has not been rehearsed or recorded. Video is optional
under the supplied terms. Add the reviewed public repository link when authorised;
do not submit the local development repository with its Nedbank history.
