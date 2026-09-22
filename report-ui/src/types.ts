export type Interval = { lower: number | null; upper: number | null };
export type Budget = {
  tp: number;
  fp: number;
  fn: number;
  tn: number;
  selected: number;
  capture: number | null;
  lift: number | null;
};
export type Model = {
  average_precision: number | null;
  log_loss: number;
  brier_score: number;
  ece_10_bins: number;
  ap_interval: Interval;
  positives: number;
  rows: number;
  sparse: boolean;
  prevalence: number;
  "threshold_0.5": { tp: number; fp: number; fn: number; tn: number };
  top_budgets: Record<string, Budget>;
  reliability: {
    rows: number;
    mean_probability: number | null;
    observed_fraction: number | null;
  }[];
};
export type Cohort = {
  rows: number;
  customers: number;
  models: Record<string, Model>;
  paired_comparisons: Record<
    string,
    {
      candidate: string;
      reference: string;
      ap_difference: number;
      interval: Interval;
    }
  >;
};
export type Evaluation = {
  overall: Cohort;
  slices: Record<string, Record<string, Cohort>>;
};
export type Audit = {
  partitions: Record<
    string,
    {
      rows: number;
      customers: number;
      positives: number;
      dormancy_rate: number;
    }
  >;
  customer_overlap_counts: Record<string, number>;
};
export type Run = {
  evaluation: {
    generator_seed: number;
    regime: string;
    split_audit: Audit;
    evaluations: Record<string, Evaluation>;
  };
  manifest: {
    models: Record<
      string,
      {
        timing_summary: Record<
          string,
          { median: number; min: number; max: number }
        >;
      }
    >;
  };
};
export type Report = {
  classification: "synthetic";
  source_manifest_sha256: string;
  validation: Evaluation;
  hosted: Evaluation & {
    integration: {
      stages: { stage: string; elapsed_seconds: number }[];
      fresh_preflight: { estimated_total_tokens: number };
      approved_estimate_budget: number;
      checkpoint_identity: { reported_model_path: string };
    };
  };
  runs: Run[];
  sources: unknown;
};
