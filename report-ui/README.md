# SCUBA interface

The React and Radix Themes interface presents the Financial Stress Predictor.
It lets an operator choose a review capacity, inspect ranked records and their
monthly activity, export the shortlist and compare model evidence. The earlier
synthetic benchmark remains a separate archive.

## Build and check

Use Node 24 and the committed npm lockfile. From the repository root:

```sh
npm ci --prefix report-ui --ignore-scripts
make ui-check
```

Installation requires package access unless dependencies are cached. Checks run
locally. To format the interface sources, use `npm --prefix report-ui run format`.
For the complete verified build, follow the
[Financial Stress run guide](../docs/how-to/FINANCIAL_STRESS.md#portable-final-demo).

The Python builder validates the evidence before invoking `build.mjs`. The output
embeds React, styles and data in standalone HTML, with adjacent JSON evidence,
checksums and review CSVs. The page requires JavaScript and makes no model request.
Its content policy forbids network connections.

## Source map

| File | Purpose |
| --- | --- |
| `src/FinancialStress.tsx` | Review workspace, model evidence and final results |
| `src/stress.ts` | Review selection, summaries and formatting |
| `src/styles.css` | Shared layout and component styles |
| `src/palette.css` | Custom light/dark colour tokens |
| `build.mjs` | Standalone bundling |

## Interface rules

Validation review records stay separate from final-holdout results. Search,
sorting and pagination operate within the fixed shortlist; exports include the
whole shortlist. No control fits a model or changes saved probabilities.

Tables use Radix components with square corners, keyboard-accessible sort controls
and labelled horizontal scrolling regions. Colour is supplemented by text.
Prediction-gap badges use amber for underestimated stress, jade for overestimated
stress and grey for gaps that round to zero.

The custom [Radix palette](https://www.radix-ui.com/colors/custom?accent-light=101075&gray-light=D0D5D2&accent-dark=1863DC&gray-dark=EDEDED&bg-dark=0F151C)
was captured on 21 September 2026. Light accent is `#101075`; dark accent is
`#1863DC` on `#0F151C`. The generated sRGB scales are stored in `src/palette.css`.
The grey inputs seed perceptual scales rather than directly setting every surface.
