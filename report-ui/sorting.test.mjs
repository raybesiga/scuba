import assert from "node:assert/strict";
import { test } from "node:test";
import { displayedSortValue, sortRowIndices } from "./src/sorting.ts";
test("numeric sorting uses full precision and preserves equal-score source order", () => {
  const values = [0.36005951, 0.348711, 0.352158, 0.36005952, 0.348711];
  assert.deepEqual(sortRowIndices(values, "descending"), [3, 0, 2, 1, 4]);
  assert.deepEqual(sortRowIndices(values, "ascending"), [1, 4, 2, 0, 3]);
  assert.equal(values[0], 0.36005951);
});
test("missing values remain last for either direction", () => {
  assert.deepEqual(
    sortRowIndices([null, 2, null, 1], "ascending"),
    [3, 1, 0, 2],
  );
  assert.deepEqual(
    sortRowIndices([null, 2, null, 1], "descending"),
    [1, 3, 0, 2],
  );
  assert.deepEqual(sortRowIndices([], "ascending"), []);
});
test("displayed counts, signed metrics, percentages and timing medians are numeric", () => {
  assert.equal(displayedSortValue("8,017"), 8017);
  assert.equal(displayedSortValue("-0.0195"), -0.0195);
  assert.equal(displayedSortValue("34.8%"), 34.8);
  assert.equal(displayedSortValue("1.400 [1.200, 1.900]"), 1.4);
  assert.equal(displayedSortValue("Unavailable"), null);
  assert.deepEqual(
    sortRowIndices(["XGBoost", "CatBoost", "TabPFN-3.5-Plus"], "ascending"),
    [1, 2, 0],
  );
});
