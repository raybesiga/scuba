# Financial Stress Predictor: dashboard walkthrough

Follow these steps to inspect the model results and customer-care workflow.
Start with the [setup guide](how-to/FINANCIAL_STRESS.md#run-the-saved-demo).
The dashboard replays saved predictions and needs no API key.

## 1. Compare results at the same workload

Open **Final holdout** and select **Top 10% · 800 reviews** and **XGBoost**.

TabPFN finds **542 stress cases**, compared with **512 for XGBoost** and
**472 for CatBoost**, in equally sized 800-record shortlists. That is 30 and
70 additional cases respectively, without increasing the review workload.

The other 258 records in TabPFN's shortlist did not have stress. Another 658
stress cases remain outside it. The estimated gain over XGBoost is 9–50 cases
at 95% confidence, assuming independent records. Expand **How certain is this
result?** for the method and limitations.

Scroll to **Final holdout: how the models compare** to inspect all five models.
They used the same training and evaluation records. TabPFN has the lowest log
loss and highest AUROC in this comparison.

## 2. Inspect an individual record

Open **Review workspace**, then select a record in the review list. Compare
its latest monthly activity with its own preceding five-month baseline.

TabPFN uses 182 inputs: six months of transaction counts, amounts and balances,
alongside activity frequency and customer profile information. The activity
chart shows one part of that context; it does not explain the model's prediction.

This workspace uses a separate validation sample, so the counts differ from
**Final holdout**:

| View | Records evaluated | Shortlist | TabPFN stress cases found | XGBoost stress cases found |
| --- | ---: | ---: | ---: | ---: |
| Final holdout · 10% | 8,000 | 800 | 542 | 512 |
| Review workspace / validation · 10% | 8,000 | 800 | 565 | 529 |
| Final holdout · 5% | 8,000 | 400 | 315 | 296 |

Each evaluation set contains 1,200 labelled stress cases.

## 3. Export the shortlist

Choose a review capacity and click **Export 800 snapshots** (or 400 at 5%).
The export includes the full selected shortlist. A care team could use it to
verify each customer's circumstances and consider appropriate support.
The demo does not contact customers or choose an offer.

## 4. Check the evidence and limits

Open **Data & limitations** and follow the evidence links in the [README](../README.md).
The repository includes saved results and reproduction instructions.

These results come from a stratified row holdout. Dates and persistent customer
identifiers are unavailable, so performance on future periods or entirely new
customers has not been established. Whether this prioritisation improves
customer outcomes still needs testing with an operator.
