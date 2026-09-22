import assert from "node:assert/strict";
import test from "node:test";
import {
  shortlist,
  searchSnapshots,
  reviewCsv,
  totalActivity,
} from "./src/stress.ts";

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
