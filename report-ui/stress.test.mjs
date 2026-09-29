import assert from "node:assert/strict";
import test from "node:test";
import {
  shortlist,
  searchSnapshots,
  reviewCsv,
  totalActivity,
  activityBaselineSummary,
  predictionGap,
  calibrationNarrative,
  operatorComparison,
  captureIntervalInterpretation,
} from "./src/stress.ts";
import { sortRowIndices } from "./src/sorting.ts";

test("capture intervals including zero do not establish an advantage", () => {
  for (const [lower, upper] of [
    [-6, 15],
    [0, 15],
    [-6, 0],
    [0, 0],
  ]) {
    assert.equal(
      captureIntervalInterpretation(lower, upper),
      "The interval includes zero, so an advantage is not established.",
    );
  }
});

test("capture intervals exclude zero on either side using unrounded bounds", () => {
  for (const [lower, upper] of [
    [3, 36],
    [9, 50],
    [-15, -6],
    [0.01, 15],
    [-6, -0.01],
  ]) {
    assert.equal(
      captureIntervalInterpretation(lower, upper),
      "The interval excludes zero.",
    );
  }
});

function narrativeMetrics() {
  return Object.fromEntries(
    [
      ["tabpfn_3_5_plus", 0.01, 45, 24],
      ["xgboost", 0.03, 40, 25],
      ["catboost", 0.05, 35, 20],
      ["logistic_regression", 0.02, 30, 15],
      ["constant_prior", 0, 10, 5],
    ].map(([name, ece, ten, five]) => [
      name,
      {
        ece_10_bins: ece,
        top_budgets: {
          0.1: { selected: 100, tp: ten },
          0.05: { selected: 50, tp: five },
        },
        reliability: [
          {
            lower: 0,
            upper: 0.1,
            rows: 800,
            mean_probability: 0.04,
            observed_fraction: 0.05,
          },
          {
            lower: 0.5,
            upper: 0.6,
            rows: 40,
            mean_probability: 0.55,
            observed_fraction: 0.7,
          },
          {
            lower: 0.9,
            upper: 1,
            rows: 0,
            mean_probability: null,
            observed_fraction: null,
          },
        ],
      },
    ]),
  );
}
test("calibration narrative orders trained models by measured gap and excludes the constant prior", () => {
  const metrics = narrativeMetrics();
  const result = calibrationNarrative(metrics, "tabpfn_3_5_plus");
  assert.equal(
    result.comparison,
    "Average calibration gap in percentage points (lower is better): TabPFN-3.5-Plus 1.0; Logistic regression 2.0; XGBoost 3.0; CatBoost 5.0.",
  );
  metrics.xgboost.ece_10_bins = 0.005;
  assert.match(
    calibrationNarrative(metrics, "xgboost").comparison,
    /better\): XGBoost 0.5; TabPFN-3.5-Plus 1.0/,
  );
});
test("calibration narrative uses the supplied partition and selected model, including sparse ranges", () => {
  const metrics = narrativeMetrics();
  metrics.tabpfn_3_5_plus.ece_10_bins = 0.008;
  metrics.catboost.reliability = [
    {
      lower: 0.1,
      upper: 0.2,
      rows: 500,
      mean_probability: 0.15,
      observed_fraction: 0.2,
    },
    {
      lower: 0.8,
      upper: 0.9,
      rows: 3,
      mean_probability: 0.85,
      observed_fraction: 0.5,
    },
  ];
  const result = calibrationNarrative(metrics, "catboost");
  assert.match(result.comparison, /TabPFN-3.5-Plus 0.8/);
  assert.equal(
    result.selected,
    "CatBoost’s largest mismatch: 85.0% predicted versus 50.0% observed stress (80–90% range; 3 records).",
  );
});
test("calibration narrative excludes empty and missing bins without changing their order", () => {
  const metrics = narrativeMetrics();
  const bins = metrics.tabpfn_3_5_plus.reliability;
  const original = structuredClone(bins);
  assert.match(
    calibrationNarrative(metrics, "tabpfn_3_5_plus").selected,
    /50–60% range; 40 records/,
  );
  assert.deepEqual(bins, original);
  metrics.tabpfn_3_5_plus.reliability = [original[2]];
  assert.match(
    calibrationNarrative(metrics, "tabpfn_3_5_plus").selected,
    /no populated probability ranges/,
  );
});

test("prediction gaps use unrounded probabilities and distinguish both directions", () => {
  assert.deepEqual(predictionGap(0.5484, 0.6502), {
    absolute: (0.6502 - 0.5484) * 100,
    value: "+10.2 pp",
    label: "Underestimated",
    color: "amber",
  });
  assert.equal(predictionGap(0.033, 0.03).value, "−0.3 pp");
  assert.equal(predictionGap(0.033, 0.03).label, "Overestimated");
  assert.equal(predictionGap(0.033, 0.03).color, "jade");
  // Rounding each probability first would incorrectly produce a 0.1 pp gap.
  assert.equal(predictionGap(0.14649, 0.14651).value, "≈0.0 pp");
});
test("near-zero gaps are neutral at displayed precision and empty bins stay unavailable", () => {
  for (const observed of [0.5, 0.50049, 0.49951]) {
    const gap = predictionGap(0.5, observed);
    assert.equal(gap.value, "≈0.0 pp");
    assert.equal(gap.label, "Approximately equal");
    assert.equal(gap.color, "gray");
  }
  assert.equal(predictionGap(0.5, 0.50051).value, "+0.1 pp");
  assert.equal(predictionGap(0.5, 0.49949).value, "−0.1 pp");
  for (const [mean, observed] of [
    [null, null],
    [0.5, null],
    [null, 0.5],
  ]) {
    assert.equal(predictionGap(mean, observed).absolute, null);
    assert.equal(predictionGap(mean, observed).value, "Unavailable");
  }
});
test("absolute gap sorting prioritises large errors in either direction and keeps empty bins last", () => {
  const gaps = [
    [0.2, 0.25],
    [0.4, 0.1],
    [null, null],
    [0.8, 1],
    [0.5, 0.50001],
  ].map(([mean, observed]) => predictionGap(mean, observed).absolute);
  assert.deepEqual(sortRowIndices(gaps, "descending"), [1, 3, 0, 4, 2]);
  assert.deepEqual(sortRowIndices(gaps, "ascending"), [4, 0, 3, 1, 2]);
});

const row = (id, probability, region = "Invented north") => ({
  id,
  probability,
  region,
  segment: "Example segment",
  earning_pattern: "Example",
  activity: { deposit: [1, 2, 3, 4, 5, 6], withdraw: [6, 5, 4, 3, 2, 1] },
  balance: [10, 20, 30, 40, 50, 60],
});
test("capacity uses full precision, deterministic ID ties and leaves input unchanged", () => {
  const rows = Array.from({ length: 40 }, (_, i) => row(`ID-${i}`, 0.1));
  rows[3] = row("B", 0.90000001);
  rows[7] = row("A", 0.90000001);
  rows[9] = row("C", 0.90000002);
  assert.deepEqual(
    shortlist(rows, "0.05").map((r) => r.id),
    ["C", "A"],
  );
  assert.equal(shortlist(rows, "0.1").length, 4);
  assert.equal(rows[3].id, "B");
  assert.throws(() => shortlist(rows, "0.2"), /capacity/);
  assert.deepEqual(shortlist([], "0.05"), []);
});
test("search narrows the fixed shortlist without recruiting lower-ranked rows", () => {
  const rows = Array.from({ length: 20 }, (_, i) => row(`ID-${i}`, i / 20));
  const selected = shortlist(rows, "0.1");
  assert.equal(searchSnapshots(selected, " invented NORTH ").length, 2);
  assert.equal(searchSnapshots(selected, "id-0").length, 0);
  assert.equal(searchSnapshots(selected, "example segment").length, 2);
  assert.equal(selected.length, 2);
});
test("CSV preserves precision and rank, escapes text and excludes observed labels", () => {
  const rows = [
    row('=HYPERLINK("x")', 0.9123456789, "+formula"),
    row("safe", 0.4, "a,b"),
  ];
  const csv = reviewCsv(rows);
  assert.match(csv, /"0.9123456789","1"/);
  assert.ok(csv.includes('"\'=HYPERLINK(""x"")"'));
  assert.ok(csv.includes('"\'+formula"'));
  assert.ok(csv.includes('"a,b"'));
  assert.match(csv, /TabPFN-3.5-Plus/);
  assert.match(csv, /validation_demo/);
  assert.doesNotMatch(
    csv,
    /liquidity_stress_next_30d|observed_outcome|gender|age/,
  );
  assert.equal(csv.split("\r\n").length, 4);
});
test("activity combines counts at matching monthly positions", () => {
  assert.deepEqual(totalActivity(row("A", 0.5)), [7, 7, 7, 7, 7, 7]);
});
test("activity baseline uses each record’s preceding five months, excluding the latest month", () => {
  const record = row("A", 0.5);
  record.activity = { deposit: [29, 24, 25, 27, 37, 45] };
  assert.equal(
    activityBaselineSummary(record),
    "45 transactions in the last month. 16.6 (58.5%) above the monthly baseline of 28.4.",
  );
  record.activity = { deposit: [10, 20, 30, 20, 20, 5] };
  assert.equal(
    activityBaselineSummary(record),
    "5 transactions in the last month. 15 (75%) below the monthly baseline of 20.",
  );
  assert.match(
    activityBaselineSummary(row("B", 0.8)),
    /Matching the monthly baseline of 7/,
  );
});
test("activity baseline handles zero history without inventing a percentage change", () => {
  const record = row("A", 0.5);
  record.activity = { deposit: [0, 0, 0, 0, 0, 5] };
  assert.equal(
    activityBaselineSummary(record),
    "5 transactions in the last month. 5 above the monthly baseline of 0.",
  );
  record.activity.deposit[5] = 0;
  assert.equal(
    activityBaselineSummary(record),
    "0 transactions in the last month. Matching the monthly baseline of 0.",
  );
});

test("operator comparison follows comparator and capacity without claiming intervention benefit", () => {
  const metrics = narrativeMetrics();
  assert.match(
    operatorComparison(metrics, "0.1", "xgboost"),
    /100 reviews.*5 more stress cases than XGBoost/,
  );
  assert.match(
    operatorComparison(metrics, "0.05", "xgboost"),
    /50 reviews.*1 fewer stress cases than XGBoost/,
  );
  assert.match(
    operatorComparison(metrics, "0.1", "catboost"),
    /10 more stress cases than CatBoost/,
  );
  metrics.xgboost.top_budgets["0.1"].tp = 45;
  assert.match(operatorComparison(metrics, "0.1", "xgboost"), /same number/);
});
