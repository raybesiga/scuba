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
