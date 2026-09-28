# Financial Stress Predictor: recording walkthrough

Recording script · approximately two minutes

**Pitch:** TabPFN helps a customer-care team find more financial-stress cases within the same review workload.

This is the recording version of the pitch. Read the quoted narration; the screen cues are instructions for the presenter. Timing is a guide and still needs a rehearsal.

## Before recording in Cap

- Open the dashboard at <http://127.0.0.1:8880/index.html>. Use one dashboard tab.
- Select **Final holdout**, **Top 10% · 800 reviews**, and **XGBoost**. Start at the headline cards.
- Keep the uncertainty explanation collapsed. Have the clean release README ready in a second tab for the closing shot.
- Hide notifications and unrelated windows. Record only the dashboard and README.

## 0:00–0:25 · The operator's problem

**Screen:** Final holdout headline cards.

> Customer-care teams need to know whom to review first. SCUBA uses TabPFN-3.5-Plus to assess 182 inputs: six months of transaction counts and amounts across bill payments, merchant spending and bank transfers, alongside activity frequency and customer profile information. It combines these inputs to estimate financial-stress risk over the next thirty days and prioritise records for review.

## 0:25–0:55 · Show the advantage

**Screen:** Scroll to “What changes at the same review capacity?” Point to both model rows, then the interval below the table.

> On eight thousand reserved test records, TabPFN identifies five hundred and forty-two stress cases in an eight-hundred-record shortlist. XGBoost identifies five hundred and twelve. That is thirty additional cases at the same workload. The other two hundred and fifty-eight shortlisted records did not have stress. Another six hundred and fifty-eight stress cases remain outside the list. Our estimated gain is nine to fifty cases at ninety-five percent confidence, assuming independent records.

## 0:55–1:10 · Show the wider comparison

**Screen:** Scroll to “Final holdout: how the models compare”. Keep the 800-review setting.

> We compared five models using the same training and test records. TabPFN also leads on probability accuracy and ranking quality. This makes its contribution measurable, beyond a single headline result.

## 1:10–1:40 · Demonstrate the operator workflow

**Screen:** Open **Review workspace**. Scroll to the review list. Select a different snapshot, show its activity and baseline, then click **Export 800 snapshots**. Return to the page after the download.

> Here is how an operator could use it. This workspace uses a separate validation sample, so the counts change. The operator selects a review capacity, opens a record and checks recent activity against that record's own baseline. The shortlist can be exported for a care team to verify the circumstances and consider appropriate support. TabPFN sets the review priority; the operator decides what happens next.

## 1:40–2:00 · Reproducibility and close

**Screen:** Briefly show **Data & limitations**, then the clean release README's setup instructions.

> The demo replays saved predictions offline, with source data, setup instructions and evaluation evidence in the repository. These tests establish performance on held-out records, not future customer outcomes. The next step is an operator pilot. Our proposition is simple: more relevant support reviews within the same workload.

## How the walkthrough addresses the judging criteria

| Criterion supplied by the organiser | What the recording demonstrates |
| --- | --- |
| TabPFN-3.5 showcase · 50% | TabPFN drives the actual shortlist; the final holdout quantifies its advantage over XGBoost and the other baselines. |
| Creativity, originality and practical value · 30% | Model predictions become a capacity choice, a record review and an export for customer care. The distinctive contribution is the operator workflow around the comparison. |
| Technical quality and reproducibility · 20% | Comparable evaluation, separate validation/final results, inspectable evidence and an offline demo replay with setup instructions. |

## Presenter reference

Do not read this table aloud. Use it to check that the visible tab matches the narration.

| Screen | Records evaluated | Shortlist | TabPFN stress cases found | XGBoost stress cases found |
| --- | ---: | ---: | ---: | ---: |
| Final holdout · 10% | 8,000 | 800 | 542 | 512 |
| Review workspace / validation · 10% | 8,000 | 800 | 565 | 529 |
| Final holdout · 5% (optional extra shot) | 8,000 | 400 | 315 | 296 |

Each evaluation set contains 1,200 labelled stress cases. On the final holdout, **542 + 258 = 800 shortlisted records**, while **542 + 658 = 1,200 stress cases across the full test set**.

The opening describes the supplied model inputs, not measured feature importance. The monthly transaction chart shows one view of the record; it does not represent all 182 inputs. Feature examples follow the supplied data dictionary.

The evaluation is a row holdout: dates and persistent customer identifiers are unavailable. The demo replays verified predictions; it does not make a live model request. Transaction changes are context, not an explanation of the model's prediction. Improved customer outcomes still require a pilot.

The supplied submission form labels the optional video field **YouTube URL**. Record in Cap, review the recording, then upload the approved export to YouTube for that field.
