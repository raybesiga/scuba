# SCUBA Radix evaluation dashboard

This dashboard helps a reviewer compare synthetic benchmark evidence, uncertainty and integration effort. Its overview pairs model uncertainty with the two frozen review budgets, followed by cohort and evidence inspection. See the [dashboard decision contract](../docs/DASHBOARD.md). It uses real Radix Themes components for layout, tables, tabs, theme switching, selectors and callouts. The model recipes, prediction artifacts and metrics remain in the Python evaluation package.

## Theme

The light and dark sRGB scales in `src/palette.css` come directly from the rendered CSS of the [user-selected Radix custom palette](https://www.radix-ui.com/colors/custom?accent-light=101075&gray-light=D0D5D2&accent-dark=1863DC&gray-dark=EDEDED&bg-dark=0F151C), captured 21 September 2026. Radix names the generated accent scale `violet`; the supplied light accent is `#101075` and dark accent is `#1863DC`. Light background defaults to white; dark background is `#0F151C`. Gray input seeds generate perceptual scales, so `#D0D5D2` and `#EDEDED` are not substituted for every neutral surface. The exact exported sRGB tokens override Radix defaults. No wide-gamut override is applied.

Radix theme tokens also supply distinct chart series colors. Line patterns, model labels and numerical tables keep interpretation independent of color. Controls follow the [Radix Themes setup](https://www.radix-ui.com/themes/docs/overview/getting-started), using the Theme provider and bundled styles.

## Local setup

For the pinned saved demo, use `make demo` from the repository root. Follow the [offline rebuild and evidence export procedure](../docs/DEMO_REBUILD.md) for a fresh checkout. The lower-level builder below remains available for explicit inputs.

Python dependencies remain managed by uv. The optional UI uses Node 24 and an exact npm lockfile. Install its dependencies once (network required unless cached):

```sh
npm ci --prefix report-ui
```

Normal checks and builds use only installed tools:

```sh
make ui-check
npm --prefix report-ui run format
```

The Python presentation entry point verifies the source report, each evaluation and the hosted comparison before invoking the local UI build. It never trains, predicts, loads credentials or contacts the network. Run from the repository root, choosing a new output directory:

```sh
PYTHONPATH=src .venv/bin/python -m scuba.radix_report \
  --source artifacts/m4-complete-report \
  --manifest-sha256 48d7ba0ef7bc6e5119a323f75a5638c7e621be68bcb867d3f3fd91694194f93e \
  --validation-run artifacts/m4-validation-seed-3501 \
  --output artifacts/m5-dashboard
```

`build.mjs` bundles React, Radix, styles and verified data into one standalone HTML file. It also writes `evidence.json` and a manifest pinning the source report, UI sources and npm lock. The HTML has no external assets, fetches or fonts; its content policy forbids network connections. JavaScript is required for the interactive view; JSON evidence remains readable without it. The save-evidence button downloads embedded data locally.

## Evidence and interface boundaries

- The summary always identifies the primary test. Seed selectors change the detailed view; sensitivity results omit hosted models explicitly.
- Final test, diagnostic random reference, validation, and integration evidence have separate Radix tabs. Paired uncertainty and synthetic limits remain visible.
- AP, log loss, Brier, ECE, capture, errors, subgroup support, overlap and timing all come from saved evaluation artifacts. No display control fits models or changes metrics.
- Radix tables have square corners and sortable name/count/point-metric columns. Activate a header to sort, reverse, then restore source order. Confidence intervals remain unsorted; missing values stay last and ties keep source order. Mobile tables scroll within their own labelled regions; keyboard users can focus those regions. Radix controls provide keyboard navigation and visible focus. Reduced motion is respected.
- [M5 technical acceptance](../docs/M5_RESULTS.md) includes a verified clean dependency installation, identical replay and demo storyboard. Spoken rehearsal and delivery review remain. Publishing remains outside the authorized scope.
