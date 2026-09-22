# SCUBA demo storyboard

Audience: hackathon reviewers. Target duration: 2 minutes 50 seconds, including navigation. Start on Overview, Light theme, primary seed 3501 and Top 10%. Use the [offline rebuild](DEMO_REBUILD.md); no live API call is part of the demo.

## 0:00–0:25 — Scenario

Screen: Overview, heading and summary counts.

> SCUBA asks whether the preceding sixty days of activity can identify an active customer's next thirty days of dormancy. We generated fifteen thousand fictional mobile-money customers from first principles. Every row is synthetic. This demo tests the evaluation and integration workflow; it does not establish real-world accuracy or intervention benefit.

## 0:25–0:50 — Evaluation design

Screen: scroll to Evaluation design. Point to the three cohorts, then the diagnostic panel.

> The main evaluation separates both time and customers. Training, validation and final test use disjoint customer groups, and labels mature before the next evaluation period. The final test contains 2,260 unseen customers, including 233 positive outcomes. The random reference deliberately allows overlap, so we label it diagnostic rather than deployment evidence.

## 0:50–1:25 — Results and uncertainty

Screen: scroll to Model quality. Show the paired interval note.

> TabPFN-3.5-Plus has the highest observed average precision: 0.3601, against CatBoost at 0.3522 and XGBoost at 0.3487. But that small difference is uncertain. The paired ninety-five-percent intervals against both tree models include zero. We show that uncertainty beside the result because an observed ranking alone does not establish a clear lead.

## 1:25–1:50 — Fixed review capacity

Screen: Review capacity. Switch to Top 5%, then back to Top 10%.

> These controls inspect two budgets fixed before we opened the final test. At five percent, TabPFN-3.5-Plus finds fifty positives among 113 selected customers. At ten percent, it finds 81 among 226, with 145 false positives. XGBoost also finds 81 at ten percent. These are descriptive counts, not demonstrated business uplift.

## 1:50–2:30 — Integration tradeoffs

Screen: use Inspect evidence, then scroll to Hosted integration · primary seed only. Keep the checkpoint and consumption limits visible.

> We used REST because the Python SDK conflicted with our frozen dependencies. Our response check initially treated a model alias and its resolved checkpoint path as different identities. We preserved the failure, improved the diagnostics and checked the reported metadata against pinned official sources. A narrow, tested policy accepted the captured response offline. That supports the server-reported identity; it does not independently attest the remote model bytes. Actual token charges were unavailable, so estimates remain labelled as estimates.

## 2:30–2:50 — Reproducibility

Screen: return to Overview.

> The dashboard rebuilds locally with one command from nineteen pinned evidence files. A fresh dependency installation can reproduce the same presentation bytes without another paid prediction. The result is an inspectable experiment, with useful comparisons and explicit limits.

## Presenter checks

- Keep primary seed 3501 selected during the spoken path.
- Use the exact saved numbers above. Do not call TabPFN-3.5-Plus a proven winner.
- Distinguish final-test results from validation and the random reference.
- If asked about Fast, Thinking or hosted sensitivity results, say they were not run because no variant or sensitivity budgets were approved.
- If asked about request formats, explain that prediction-only recovery did not establish how every fit envelope is interpreted. See [checkpoint resolution](M3_CHECKPOINT_RESOLUTION.md) and [request-contract audit](M3_REQUEST_CONTRACT.md).
- If a browser control fails, use the adjacent `evidence.json` and the [final results](M4_HOSTED_FINAL_RESULTS.md). Do not start a live prediction during the demo.
- The time slots are a presentation budget. Browser navigation can be checked automatically; a presenter must still practise the spoken delivery before recording or submission.
