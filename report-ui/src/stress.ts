export const stressNames: Record<string, string> = {
  tabpfn_3_5_plus: "TabPFN-3.5-Plus",
  xgboost: "XGBoost",
  catboost: "CatBoost",
  logistic_regression: "Logistic regression",
  constant_prior: "Constant prior",
};
export function predictionGap(mean: number | null, observed: number | null) {
  if (mean === null || observed === null)
    return {
      absolute: null,
      value: "Unavailable",
      label: "",
      color: "gray" as const,
    };
  const gap = (observed - mean) * 100;
  const magnitude = Math.abs(gap).toFixed(1);
  if (magnitude === "0.0")
    return {
      absolute: Math.abs(gap),
      value: "≈0.0 pp",
      label: "Approximately equal",
      color: "gray" as const,
    };
  return {
    absolute: Math.abs(gap),
    value: `${gap > 0 ? "+" : "−"}${magnitude} pp`,
    label: gap > 0 ? "Underestimated" : "Overestimated",
    color: gap > 0 ? ("amber" as const) : ("jade" as const),
  };
}
export type Snapshot = {
  id: string;
  probability: number;
  region: string;
  segment: string;
  earning_pattern: string;
  activity: Record<string, number[]>;
  balance: number[];
};
export type StressMetric = {
  log_loss: number;
  roc_auc: number | null;
  average_precision: number | null;
  brier_score: number;
  ece_10_bins: number;
  top_budgets: Record<
    string,
    { selected: number; tp: number; fp: number; fn: number; capture: number }
  >;
  reliability: {
    lower: number;
    upper: number;
    rows: number;
    mean_probability: number | null;
    observed_fraction: number | null;
  }[];
};
export type AuditGroup = {
  dimension: string;
  group: string;
  rows: number;
  positives: number;
  prevalence: number;
  mean_probability: number;
  log_loss: number;
  roc_auc: number | null;
  sparse: boolean;
  budgets: Record<string, { selected: number; captured: number }>;
};
export function calibrationNarrative(
  metrics: Record<string, StressMetric>,
  budget: string,
  selectedModel: string,
) {
  const count = (value: number) => value.toLocaleString("en-US");
  const gap = (key: string) => (100 * metrics[key].ece_10_bins).toFixed(1);
  const others = ["logistic_regression", "xgboost", "catboost"]
    .sort((a, b) => metrics[a].ece_10_bins - metrics[b].ece_10_bins)
    .map((key) => `${gap(key)} for ${stressNames[key]}`);
  const comparison =
    `TabPFN-3.5-Plus has an average calibration gap of ${gap("tabpfn_3_5_plus")} percentage points, ` +
    `compared with ${others.slice(0, -1).join(", ")} and ${others.at(-1)}. Lower means closer agreement with observed stress.`;
  const plus = metrics.tabpfn_3_5_plus.top_budgets[budget];
  const reference = metrics.xgboost.top_budgets[budget];
  const difference = plus.tp - reference.tp;
  const change =
    difference === 0
      ? "the same number as XGBoost"
      : `${count(Math.abs(difference))} ${difference > 0 ? "more" : "fewer"} than XGBoost`;
  const review = `At ${count(plus.selected)} reviews, TabPFN-3.5-Plus finds ${count(plus.tp)} stress cases: ${change} at the same capacity.`;
  const populated = metrics[selectedModel].reliability.filter(
    (bin) =>
      bin.rows > 0 &&
      bin.mean_probability !== null &&
      bin.observed_fraction !== null,
  );
  const largest = [...populated].sort(
    (a, b) =>
      Math.abs(b.observed_fraction! - b.mean_probability!) -
      Math.abs(a.observed_fraction! - a.mean_probability!),
  )[0];
  const selected = largest
    ? `${stressNames[selectedModel]}’s largest observed gap is in the ${Math.round(largest.lower * 100)}–${Math.round(largest.upper * 100)}% range: ` +
      `${(100 * largest.mean_probability!).toFixed(1)}% predicted versus ${(100 * largest.observed_fraction!).toFixed(1)}% observed stress, across ${count(largest.rows)} snapshots.`
    : `${stressNames[selectedModel]} has no populated probability ranges to compare.`;
  return { comparison, review, selected };
}
export type StressReport = {
  dataset: "financial_stress";
  status: "verified_validation";
  classification: string;
  cohorts: Record<string, { rows: number; positives: number }>;
  features: number;
  metrics: Record<string, StressMetric>;
  snapshots: Snapshot[];
  cohort_audit: AuditGroup[];
  ablation: Record<string, StressMetric>;
  sources: Record<string, string>;
  identity: { requested_alias: string; reported_model_path: string };
  final_evaluated: false;
  final_evaluation?: {
    status: "verified_final";
    cohort: { rows: number; positives: number };
    metrics: Record<string, StressMetric>;
    cohort_audit: AuditGroup[];
  };
};
export function shortlist(rows: Snapshot[], budget: string) {
  if (budget !== "0.05" && budget !== "0.1")
    throw new Error("Unsupported review capacity");
  return [...rows]
    .sort(
      (a, b) =>
        b.probability - a.probability ||
        (a.id < b.id ? -1 : a.id > b.id ? 1 : 0),
    )
    .slice(0, Math.ceil(Number(budget) * rows.length));
}
export function searchSnapshots(rows: Snapshot[], query: string) {
  const q = query.trim().toLowerCase();
  return rows.filter((r) =>
    [r.id, r.region, r.segment].some((v) => v.toLowerCase().includes(q)),
  );
}
function csvCell(value: string | number) {
  // Neutralise spreadsheet formula prefixes in source-provided text fields.
  const text =
    typeof value === "string" && /^[\s]*[=+\-@]/.test(value)
      ? "'" + value
      : String(value);
  return '"' + text.replaceAll('"', '""') + '"';
}
export function reviewCsv(rows: Snapshot[]) {
  const headers = [
    "snapshot_id",
    "probability_stress_30d",
    "review_rank",
    "region",
    "segment",
    "model",
    "evidence_partition",
  ];
  return (
    [
      headers,
      ...rows.map((r, i) => [
        r.id,
        r.probability,
        i + 1,
        r.region,
        r.segment,
        "TabPFN-3.5-Plus",
        "validation_demo",
      ]),
    ]
      .map((row) => row.map(csvCell).join(","))
      .join("\r\n") + "\r\n"
  );
}
export function totalActivity(row: Snapshot) {
  return Array.from({ length: 6 }, (_, i) =>
    Object.values(row.activity).reduce((sum, v) => sum + v[i], 0),
  );
}
