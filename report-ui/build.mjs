import { build } from "esbuild";
import { shortlist, reviewCsv } from "./src/stress.ts";
import { createHash } from "node:crypto";
import { readFile, writeFile, mkdir, readdir } from "node:fs/promises";
import { fileURLToPath } from "node:url";
import path from "node:path";
const root = path.dirname(fileURLToPath(import.meta.url));
const [input, output] = process.argv.slice(2);
if (!input || !output)
  throw new Error(
    "Usage: node report-ui/build.mjs DATA.json NEW_OUTPUT_DIRECTORY",
  );
const raw = await readFile(input, "utf8");
const data = JSON.parse(raw);
const stress = data.dataset === "financial_stress";
if (
  stress
    ? data.status !== "verified_validation" ||
      !data.snapshots?.length ||
      !data.metrics?.tabpfn_3_5_plus ||
      data.final_evaluated !== false
    : data.classification !== "synthetic" ||
      !data.hosted ||
      data.runs?.length !== 6
)
  throw new Error(
    "Verified validation or complete synthetic report data required",
  );
const result = await build({
  entryPoints: [path.join(root, "src/main.tsx")],
  bundle: true,
  write: false,
  outdir: "out",
  minify: true,
  format: "iife",
  platform: "browser",
  target: ["es2022"],
  define: { "process.env.NODE_ENV": '"production"' },
  legalComments: "inline",
});
const js = result.outputFiles.find((f) => f.path.endsWith(".js")).text;
const css = result.outputFiles.find((f) => f.path.endsWith(".css")).text;
const embedded = JSON.stringify(data).replaceAll("<", "\\u003c");
if (/<\/script/i.test(js) || /<\/style/i.test(css))
  throw new Error("Unsafe embedded asset terminator");
const html = `<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><meta http-equiv="Content-Security-Policy" content="default-src 'none'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; img-src data:; connect-src 'none'; font-src 'none'; base-uri 'none'; form-action 'none'"><title>SCUBA · ${stress ? "Financial Stress" : "Model evaluation"}</title><style>${css}</style></head><body><div id="root"></div><noscript>This interactive Radix report requires JavaScript. The adjacent evidence.json contains the complete verified results.</noscript><script id="report-data" type="application/json">${embedded}</script><script>${js}</script></body></html>`;
await mkdir(path.dirname(output), { recursive: true });
await mkdir(output, { recursive: false });
await writeFile(path.join(output, "index.html"), html);
await writeFile(path.join(output, "evidence.json"), raw);
const sha = (s) => createHash("sha256").update(s).digest("hex");
const reviewExports = {};
if (stress) {
  for (const budget of ["0.05", "0.1"]) {
    const rows = shortlist(data.snapshots, budget);
    const name = `review-${rows.length}.csv`;
    const csv = reviewCsv(rows);
    await writeFile(path.join(output, name), csv);
    reviewExports[name] = sha(csv);
  }
}
const sourceHashes = {};
for (const name of [
  "build.mjs",
  ...(await readdir(path.join(root, "src"))).sort().map((n) => "src/" + n),
]) {
  sourceHashes[name] = sha(await readFile(path.join(root, name)));
}
await writeFile(
  path.join(output, "manifest.json"),
  JSON.stringify(
    {
      status: "complete",
      classification: data.classification,
      presentation: "Radix Themes",
      source_manifest_sha256: data.source_manifest_sha256,
      html_sha256: sha(html),
      evidence_sha256: sha(raw),
      ui_source_sha256: sourceHashes,
      ui_lock_sha256: sha(await readFile(path.join(root, "package-lock.json"))),
      network_requests_in_build: 0,
      ...(stress ? { review_exports_sha256: reviewExports } : {}),
    },
    null,
    2,
  ) + "\n",
);
console.log(
  JSON.stringify({
    status: "complete",
    output,
    html_bytes: Buffer.byteLength(html),
  }),
);
