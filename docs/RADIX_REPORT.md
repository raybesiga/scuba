# Radix report presentation

Updated 21 September 2026 at the user's request. The report now uses Radix Themes with the supplied custom light/dark palette. The current artifact is `artifacts/m4-radix-report/index.html`; the prior M4 report and all prediction/evaluation evidence remain preserved.

The interface uses Radix tabs for final test, random reference, validation and evidence; Radix selectors for seed and subgroup inspection; and Radix theme switching, tables, callouts and layout components. The primary result summary remains labelled independently of the selected detail seed. Synthetic-data status, paired uncertainty and unavailable hosted routes remain explicit.

The custom palette's exact sRGB scales were copied from the rendered Radix generator output. Light accent is `#101075`; dark accent is `#1863DC` on `#0F151C`. The supplied gray colors are generator inputs, not literal text or background replacements. Distinct chart colors use Radix tokens with line patterns and numerical tables. See [palette provenance and build instructions](../report-ui/README.md).

## Verification

- All 114 Python tests and Ruff checks pass. TypeScript and Prettier checks pass separately through `make ui-check`.
- Every embedded evaluation equals its saved source, including all six local runs, hosted final comparison and primary validation.
- Two standalone builds produce byte-identical HTML, evidence JSON and manifests. UI source hashes and the exact npm lock are recorded in the presentation manifest.
- Browser checks cover both themes on desktop and 390-pixel mobile width, no document overflow, scrollable table regions, keyboard tab navigation, seed changes, subgroup selection, validation separation and signed random-reference differences.
- Computed dark theme values match the requested accent and background. No browser errors were observed. The output embeds its code, styles and data and forbids network connections through its content policy.
- Each thematic commit is checked in an isolated staged snapshot, using the locked installed UI tools. This verifies source isolation, not a fresh dependency installation; clean-environment rehearsal remains M5 work.

Evidence record: `artifacts/radix-ui-verification.json`. The presentation requires JavaScript, with adjacent `evidence.json` available for direct inspection. No new model run, API request, upload or publication was needed.

M4's scientific findings are unchanged. M5 still needs the demo storyboard and clean-environment rehearsal; the standalone Radix builder supplies the report presentation path for that work.
