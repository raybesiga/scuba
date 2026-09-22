# F3 — Financial Stress review workspace

## Decision contract

A customer-care operator reviews a ranked list of validation snapshots within a
fixed 5% or 10% capacity, inspects observed monthly activity, and exports a list
for human review. This is a research demonstration; it does not contact customers,
recommend credit, or claim that outreach improves outcomes. The product object is
a snapshot review list, not a live case or verified unique person.

The primary view is the review workspace. A report-first landing page was rejected
because it repeats the existing benchmark and hides the operator decision. A live
case-management view was rejected because observation dates, contact channels and
intervention outcomes are absent. The reviewed user feedback sets the visual
constraints: Radix, white light background, square tables, aligned 2:1 modules,
compact section explanations and the full TabPFN-3.5-Plus name.

## Surface and data boundary

- Financial Stress is the landing view. Preserve the existing synthetic benchmark
  as a linked archive with its original data, labels and results. Nedbank remains
  planned; it must not appear as a working second use case.
- Use only the verified F2 validation predictions and the corresponding feature
  rows. No final.csv reads, new hosted calls, source notebook execution or retraining
  is part of dashboard rendering.
- Review budgets select the first 400/800 rows by descending TabPFN probability,
  with ID ties. Search and table sorting operate inside that fixed shortlist and
  never recalculate the evaluation population. Export the full selected shortlist,
  not just a page/search result, and state this beside the export action.
- Retrospective capture/false-positive counts are aggregate validation evidence.
  Do not expose the outcome label as a ranking feature or individual review cue.
- Snapshot detail: six monthly transaction-count series and balance in unspecified
  dataset units, oldest M6 to newest M1. No invented calendar dates or currency.
  Describe changes as observed context, not causal explanations of the score.
- Evidence view: five-model metrics, calibration bins with support counts, cohort
  support/results and local age/gender exclusion comparison. Avoid connecting
  sparse calibration bins with a misleading confidence-like line.
- Audit cohorts: region, segment, earning pattern, gender and fixed age bands
  (18–29, 30–44, 45–59, 60+). Display row/positive support and unavailable AUC for
  single-class groups. Slice capture is measured at the same global review cutoff.
- The age/gender sensitivity check refits only the four local baselines on the same
  frozen rows with those two features omitted. No new TabPFN upload is authorised
  by this local UI work. Clearly label this as a local-model check; it does not
  establish independence from proxies or validate TabPFN fairness.

## Verification

Pin source manifests and probability hashes before export; recompute displayed
metrics and rankings. Reject mismatched IDs, labels, probabilities, changed or
incomplete evidence. Tests use invented snapshots. Exercise budget switching,
search/no matches, numeric sorting, paging, detail selection and CSV output.
Verify desktop and mobile, light/dark, keyboard-accessible controls and no page
horizontal overflow. Check exact counts against F2 and preserve synthetic archive.

F3 is complete for the local demo when these controls, evidence and checks work.
The final holdout and any full-data refit remain F4. No production-readiness or
causal customer-benefit claim follows from this demonstration.
