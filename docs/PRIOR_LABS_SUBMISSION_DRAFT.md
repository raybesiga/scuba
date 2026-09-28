# Hackathon project description

Prepared for the submission form. Publication and form submission are pending.
Repository: <https://github.com/raybesiga/scuba>, currently prepared privately.

## Project name

SCUBA · Financial Stress Predictor

## Description

SCUBA helps customer-care teams find more financial-stress cases within the same
review workload. TabPFN-3.5-Plus estimates the supplied 30-day liquidity-stress
outcome from 182 predictors: six months of transactions and balances, activity
frequency and customer profile information. An operator chooses a review
capacity, inspects ranked records and exports a shortlist for human review.

We compared TabPFN with XGBoost, CatBoost, logistic regression and a constant prior
using the same 24,000 training records and fixed settings. On the reserved
8,000-record final holdout, TabPFN found 542 stress cases in an 800-record shortlist,
compared with XGBoost's 512. Its log loss was 0.2799 versus 0.3073. A post-hoc
paired bootstrap gives a 95% interval of 9–50 additional cases, assuming independent
records. The holdout contains 1,200 stress cases in total.

The app connects that comparison to an operator's workload: choose 400 or 800
reviews, inspect recent activity against each record's own baseline, and export
the selected list. Model comparisons, calibration and group audits remain
inspectable. The interactive list uses a separate validation sample; final results
have their own tab.

The repository includes input data, locked dependencies, tests and verified
prediction evidence. The dashboard rebuilds offline without an API key or another
hosted prediction. Original code is Apache-2.0; the Zindi Financial Stress data
and adaptations retain their declared CC BY-SA 4.0 licence and attribution.

This is a row-holdout prototype: dates and persistent customer identifiers are
unavailable, and the dataset's real/synthetic origin and exact stress definition
are unverified. The app supports review rather than selecting offers or contacting
customers. Improved customer outcomes remain a question for an operator pilot.

## Presentation

Primary theme: **Build an extension or app**. Secondary fit: **Take on a hard problem**.
The [two-minute walkthrough](FINANCIAL_STRESS_WALKTHROUGH.md) contains narration,
screen cues and the judging-criteria mapping. The optional video field in the
supplied form asks for a YouTube URL.
