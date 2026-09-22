import assert from "node:assert/strict";
import { createHash } from "node:crypto";
import { mkdtemp, readFile, rm, writeFile } from "node:fs/promises";
import os from "node:os";
import path from "node:path";
import { spawnSync } from "node:child_process";
import { fileURLToPath } from "node:url";
import test from "node:test";

test("standalone builder creates missing parents and refuses to overwrite", async () => {
  const root = await mkdtemp(path.join(os.tmpdir(), "scuba-ui-build-"));
  try {
    const input = path.join(root, "data.json");
    const output = path.join(root, "new-parent", "report");
    await writeFile(
      input,
      JSON.stringify({
        classification: "synthetic",
        hosted: {},
        runs: Array(6).fill({}),
      }),
    );
    const builder = fileURLToPath(new URL("./build.mjs", import.meta.url));
    const run = () =>
      spawnSync(process.execPath, [builder, input, output], {
        encoding: "utf8",
      });
    const first = run();
    assert.equal(first.status, 0, first.stderr);
    assert.match(
      await readFile(path.join(output, "index.html"), "utf8"),
      /<!doctype html>/,
    );
    const manifest = await readFile(path.join(output, "manifest.json"), "utf8");
    assert.equal(JSON.parse(manifest).status, "complete");
    assert.notEqual(run().status, 0);
    assert.equal(
      await readFile(path.join(output, "manifest.json"), "utf8"),
      manifest,
    );
  } finally {
    await rm(root, { recursive: true, force: true });
  }
});

test("Financial Stress builder creates both fixed-capacity CSVs with hashes", async () => {
  const root = await mkdtemp(path.join(os.tmpdir(), "scuba-review-export-"));
  try {
    const input = path.join(root, "data.json"),
      output = path.join(root, "site");
    await writeFile(
      input,
      JSON.stringify({
        dataset: "financial_stress",
        classification: "fixture",
        status: "verified_validation",
        final_evaluated: false,
        metrics: { tabpfn_3_5_plus: {} },
        snapshots: Array.from({ length: 40 }, (_, i) => ({
          id: `FIXTURE-${i}`,
          probability: i / 40,
          region: "Invented",
          segment: "Example",
        })),
      }),
    );
    const builder = fileURLToPath(new URL("./build.mjs", import.meta.url));
    const result = spawnSync(process.execPath, [builder, input, output], {
      encoding: "utf8",
    });
    assert.equal(result.status, 0, result.stderr);
    const manifest = JSON.parse(
      await readFile(path.join(output, "manifest.json"), "utf8"),
    );
    for (const count of [2, 4]) {
      const name = `review-${count}.csv`,
        csv = await readFile(path.join(output, name), "utf8");
      assert.equal(csv.split("\r\n").length, count + 2);
      assert.match(csv, /FIXTURE-39/);
      assert.equal(
        manifest.review_exports_sha256[name],
        createHash("sha256").update(csv).digest("hex"),
      );
    }
  } finally {
    await rm(root, { recursive: true, force: true });
  }
});
