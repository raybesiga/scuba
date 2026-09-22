import assert from "node:assert/strict";
import test from "node:test";
import {
  shortlist,
  searchSnapshots,
  reviewCsv,
  totalActivity,
  predictionGap,
} from "./src/stress.ts";
import { sortRowIndices } from "./src/sorting.ts";

test("prediction gaps use unrounded probabilities and distinguish both directions", () => {
  assert.deepEqual(predictionGap(0.5484, 0.6502), {
    absolute: (0.6502 - 0.5484) * 100,
    value: "+10.2 pp",
    label: "Underestimated",
    color: "amber",
  });
  assert.equal(predictionGap(0.033, 0.03).value, "−0.3 pp");
  assert.equal(predictionGap(0.033, 0.03).label, "Overestimated");
  assert.equal(predictionGap(0.033, 0.03).color, "blue");
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
