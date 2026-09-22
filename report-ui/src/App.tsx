import { isValidElement, useState } from "react";
import {
  displayedSortValue,
  sortRowIndices,
  type SortValue,
  type SortDirection,
} from "./sorting";
import { Dashboard } from "./Dashboard";
import {
  Badge,
  Box,
  Button,
  Callout,
  Container,
  Flex,
  Heading,
  SegmentedControl,
  Select,
  Separator,
  Table,
  Tabs,
  Text,
  Theme,
  Tooltip,
} from "@radix-ui/themes";
import {
  ArrowDownIcon,
  ArrowUpIcon,
  CaretSortIcon,
  CheckCircledIcon,
  InfoCircledIcon,
  MoonIcon,
  SunIcon,
} from "@radix-ui/react-icons";
import type { Cohort, Evaluation, Report, Run } from "./types";
const names: Record<string, string> = {
  hosted_plus: "TabPFN-3.5-Plus",
  catboost: "CatBoost",
  xgboost: "XGBoost",
  logistic_regression: "Logistic regression",
  constant_prior: "Constant prior",
};
const order = [
  "hosted_plus",
  "catboost",
  "xgboost",
  "logistic_regression",
  "constant_prior",
];
const num = (v: number | null, d = 4) =>
  v === null ? "Unavailable" : v.toFixed(d);
const pct = (v: number | null) =>
  v === null ? "Unavailable" : `${(v * 100).toFixed(1)}%`;
const count = (v: number) => v.toLocaleString("en-US");
const ci = (v: { lower: number | null; upper: number | null }) =>
  v.lower === null ? "Unavailable" : `[${num(v.lower)}, ${num(v.upper)}]`;
const label = (name: string) => names[name] ?? name.replaceAll("_", " ");
const modelNames = (c: Cohort) => order.filter((n) => n in c.models);
function Note({ children }: { children: React.ReactNode }) {
  return (
    <Callout.Root size="2" variant="soft">
      <Callout.Icon>
        <InfoCircledIcon />
      </Callout.Icon>
      <Callout.Text>{children}</Callout.Text>
    </Callout.Root>
  );
}
function cellText(value: React.ReactNode): string {
  if (typeof value === "string" || typeof value === "number")
    return String(value);
  if (Array.isArray(value)) return value.map(cellText).join("");
  if (isValidElement<{ children?: React.ReactNode }>(value))
    return cellText(value.props.children);
  return "";
}
export function DataTable({
  headers,
  rows,
  label: caption,
  sortValues,
  sortOptions,
}: {
  headers: string[];
  rows: React.ReactNode[][];
  label: string;
  sortValues?: SortValue[][];
  sortOptions?: Record<
    number,
    { firstDirection: SortDirection; description: string }
  >;
}) {
  const [sort, setSort] = useState<{
    column: number;
    direction: SortDirection;
  } | null>(null);
  const indices = sort
    ? sortRowIndices(
        rows.map((row, i) =>
          sortValues
            ? sortValues[i][sort.column]
            : displayedSortValue(cellText(row[sort.column])),
        ),
        sort.direction,
      )
    : rows.map((_, i) => i);
  function changeSort(column: number) {
    const first: SortDirection =
      sortOptions?.[column]?.firstDirection ??
      (headers[column].includes("↑") ? "descending" : "ascending");
    if (sort?.column !== column) setSort({ column, direction: first });
    else if (sort.direction === first)
      setSort({
        column,
        direction: first === "ascending" ? "descending" : "ascending",
      });
    else setSort(null);
  }
  return (
    <Box
      className="table-scroll"
      tabIndex={0}
      role="region"
      aria-label={caption}
    >
      <Table.Root variant="surface" size="2">
        <Table.Header>
          <Table.Row>
            {headers.map((h, column) => {
              const sortable = !/interval/i.test(h);
              const active = sort?.column === column;
              return (
                <Table.ColumnHeaderCell
                  key={h}
                  aria-sort={
                    sortable ? (active ? sort.direction : "none") : undefined
                  }
                >
                  {sortable ? (
                    <Tooltip
                      content={
                        sortOptions?.[column]?.description ??
                        `${h.includes("↑") ? "Higher is better. " : h.includes("↓") ? "Lower is better. " : ""}Activate to sort, reverse, then restore source order.`
                      }
                    >
                      <Button
                        variant="ghost"
                        color="gray"
                        highContrast
                        size="1"
                        className="table-sort-button"
                        aria-label={`Sort by ${h.replace(/[↑↓]/g, "").trim()}`}
                        onClick={() => changeSort(column)}
                      >
                        {h.replace(/[↑↓]/g, "").trim()}
                        {active ? (
                          sort.direction === "ascending" ? (
                            <ArrowUpIcon />
                          ) : (
                            <ArrowDownIcon />
                          )
                        ) : (
                          <CaretSortIcon />
                        )}
                      </Button>
                    </Tooltip>
                  ) : (
                    h
                  )}
                </Table.ColumnHeaderCell>
              );
            })}
          </Table.Row>
        </Table.Header>
        <Table.Body>
          {indices.map((i) => (
            <Table.Row key={i}>
              {rows[i].map((v, j) =>
                j === 0 ? (
                  <Table.RowHeaderCell key={j}>{v}</Table.RowHeaderCell>
                ) : (
                  <Table.Cell key={j}>{v}</Table.Cell>
                ),
              )}
            </Table.Row>
          ))}
        </Table.Body>
      </Table.Root>
    </Box>
  );
}
function Scores({ cohort }: { cohort: Cohort }) {
  return (
    <DataTable
      label="Model quality metrics"
      sortValues={modelNames(cohort).map((n) => {
        const m = cohort.models[n];
        return [
          label(n),
          m.average_precision,
          null,
          m.log_loss,
          m.brier_score,
          m.ece_10_bins,
          m.top_budgets["0.1"].capture,
          m.top_budgets["0.1"].lift,
        ];
      })}
      headers={[
        "Model",
        "AP ↑",
        "95% AP interval",
        "Log loss ↓",
        "Brier ↓",
        "ECE ↓",
        "10% capture ↑",
        "10% lift ↑",
      ]}
      rows={modelNames(cohort).map((n) => {
        const m = cohort.models[n];
        return [
          <Flex gap="2" align="center">
            <span className={`model-dot ${n}`} />
            {label(n)}
          </Flex>,
          num(m.average_precision),
          ci(m.ap_interval),
          num(m.log_loss),
          num(m.brier_score),
          num(m.ece_10_bins),
          pct(m.top_budgets["0.1"].capture),
          num(m.top_budgets["0.1"].lift),
        ];
      })}
    />
  );
}
function Pairs({ cohort }: { cohort: Cohort }) {
  return (
    <Box>
      <Heading size="4" mb="2">
        How certain is the difference?
      </Heading>
      <Text as="p" color="gray" mb="4">
        An interval crossing zero leaves the ordering uncertain. These draws
        reuse the same customers for each model.
      </Text>
      <DataTable
        label="Paired average precision differences"
        sortValues={Object.values(cohort.paired_comparisons).map((p) => [
          `${label(p.candidate)} − ${label(p.reference)}`,
          p.ap_difference,
          null,
        ])}
        headers={["Comparison", "AP difference", "95% paired interval"]}
        rows={Object.values(cohort.paired_comparisons).map((p) => [
          `${label(p.candidate)} − ${label(p.reference)}`,
          num(p.ap_difference),
          ci(p.interval),
        ])}
      />
    </Box>
  );
}
function Reliability({ cohort }: { cohort: Cohort }) {
  return (
    <Box>
      <Heading size="4" mb="2">
        Probability calibration
      </Heading>
      <Text as="p" color="gray" mb="4">
        Predictions closer to the diagonal agree more closely with observed
        dormancy. Bins with few customers are less stable.
      </Text>
      <Box className="chart">
        <svg
          viewBox="0 0 620 340"
          role="img"
          aria-label="Reliability diagram showing predicted probabilities and observed dormancy"
        >
          <text x="55" y="12">
            Observed dormancy fraction
          </text>
          <path d="M55 20V290H585" className="axis" />
          <path d="M55 290L585 20" className="diagonal" />
          {[0, 0.25, 0.5, 0.75, 1].map((v) => (
            <g key={v}>
              <text x={55 + v * 530} y="309" textAnchor="middle">
                {v}
              </text>
              <text x="42" y={295 - v * 270} textAnchor="end">
                {v}
              </text>
            </g>
          ))}
          {modelNames(cohort).map((n, i) => {
            const points = cohort.models[n].reliability.filter(
              (b) =>
                b.rows &&
                b.mean_probability !== null &&
                b.observed_fraction !== null,
            );
            return (
              <g key={n} className={`series ${n}`}>
                <polyline
                  points={points
                    .map(
                      (b) =>
                        `${55 + b.mean_probability! * 530},${290 - b.observed_fraction! * 270}`,
                    )
                    .join(" ")}
                  fill="none"
                  strokeWidth="2"
                  strokeDasharray={i === 0 ? "none" : `${7 - i} ${i + 1}`}
                />
                {points.map((b, j) => (
                  <circle
                    key={j}
                    cx={55 + b.mean_probability! * 530}
                    cy={290 - b.observed_fraction! * 270}
                    r="3.5"
                  >
                    <title>
                      {label(n)}: {b.rows} customers; predicted{" "}
                      {num(b.mean_probability, 3)}, observed{" "}
                      {num(b.observed_fraction, 3)}
                    </title>
                  </circle>
                ))}
              </g>
            );
          })}
          <text x="310" y="333" textAnchor="middle">
            Mean predicted probability
          </text>
        </svg>
        <Flex gap="4" wrap="wrap" mt="3">
          {modelNames(cohort).map((n) => (
            <Text size="2" key={n}>
              <span className={`model-dot ${n}`} /> {label(n)}
            </Text>
          ))}
        </Flex>
      </Box>
    </Box>
  );
}
function Errors({ cohort }: { cohort: Cohort }) {
  return (
    <Box>
      <Heading size="4" mb="2">
        Capture and errors
      </Heading>
      <Text as="p" color="gray" mb="4">
        Capture counts are out of{" "}
        {count(Object.values(cohort.models)[0].positives)} positives. Error
        counts use the frozen probability threshold of 0.5.
      </Text>
      <DataTable
        label="Capture and error counts"
        headers={[
          "Model",
          "5% captured",
          "10% captured",
          "True positives",
          "False positives",
          "False negatives",
          "True negatives",
        ]}
        rows={modelNames(cohort).map((n) => {
          const m = cohort.models[n],
            c = m["threshold_0.5"];
          return [
            label(n),
            m.top_budgets["0.05"].tp,
            m.top_budgets["0.1"].tp,
            c.tp,
            c.fp,
            c.fn,
            c.tn,
          ];
        })}
      />
    </Box>
  );
}
function Subgroups({ evaluation }: { evaluation: Evaluation }) {
  const [field, setField] = useState("activity_level");
  const [model, setModel] = useState(modelNames(evaluation.overall)[0]);
  return (
    <Box>
      <Flex align="center" justify="between" gap="4" wrap="wrap" mb="4">
        <Box>
          <Heading size="4">Inspect a subgroup</Heading>
          <Text color="gray" size="2">
            Exploratory intervals; review budgets apply within each slice.
          </Text>
        </Box>
        <Flex gap="2" wrap="wrap">
          <Select.Root value={field} onValueChange={setField}>
            <Select.Trigger aria-label="Subgroup category" />
            <Select.Content>
              <Select.Item value="activity_level">Activity level</Select.Item>
              <Select.Item value="archetype">Archetype</Select.Item>
            </Select.Content>
          </Select.Root>
          <Select.Root value={model} onValueChange={setModel}>
            <Select.Trigger aria-label="Subgroup model" />
            <Select.Content>
              {modelNames(evaluation.overall).map((n) => (
                <Select.Item value={n} key={n}>
                  {label(n)}
                </Select.Item>
              ))}
            </Select.Content>
          </Select.Root>
        </Flex>
      </Flex>
      <DataTable
        label="Subgroup metrics"
        sortValues={Object.entries(evaluation.slices[field] ?? {}).map(
          ([k, c]) => {
            const m = c.models[model];
            return [
              label(k),
              c.customers,
              m.positives,
              m.average_precision,
              null,
              m.top_budgets["0.1"].capture,
              m.sparse ? "Sparse" : "Meets minimum",
            ];
          },
        )}
        headers={[
          "Slice",
          "Customers",
          "Positives",
          "AP",
          "95% AP interval",
          "10% capture",
          "Support",
        ]}
        rows={Object.entries(evaluation.slices[field] ?? {}).map(([k, c]) => {
          const m = c.models[model];
          return [
            label(k),
            count(c.customers),
            m.positives,
            num(m.average_precision),
            ci(m.ap_interval),
            pct(m.top_budgets["0.1"].capture),
            m.sparse ? "Sparse" : "Meets minimum",
          ];
        })}
      />
      <Text as="p" size="2" color="gray" mt="3">
        Different prevalences affect AP. Meeting minimum support does not imply
        a precise estimate.
      </Text>
    </Box>
  );
}
function EvaluationView({ evaluation }: { evaluation: Evaluation }) {
  return (
    <Flex direction="column" gap="7">
      <Scores cohort={evaluation.overall} />
      <Pairs cohort={evaluation.overall} />
      <Reliability cohort={evaluation.overall} />
      <Errors cohort={evaluation.overall} />
      <Subgroups evaluation={evaluation} />
    </Flex>
  );
}
function SplitAudit({ run }: { run: Run }) {
  return (
    <Box>
      <Heading size="4" mb="3">
        Cohort audit
      </Heading>
      <DataTable
        label="Cohort sizes and prevalence"
        sortValues={Object.entries(run.evaluation.split_audit.partitions).map(
          ([k, v]) => [
            label(k),
            v.rows,
            v.customers,
            v.positives,
            v.dormancy_rate,
          ],
        )}
        headers={["Partition", "Rows", "Customers", "Positives", "Prevalence"]}
        rows={Object.entries(run.evaluation.split_audit.partitions).map(
          ([k, v]) => [
            label(k),
            count(v.rows),
            count(v.customers),
            count(v.positives),
            pct(v.dormancy_rate),
          ],
        )}
      />
      <Box mt="4">
        <DataTable
          label="Customer overlap between partitions"
          headers={["Partitions", "Shared customers"]}
          rows={Object.entries(
            run.evaluation.split_audit.customer_overlap_counts,
          ).map(([k, v]) => [k.replace("__", " / "), count(v)])}
        />
      </Box>
    </Box>
  );
}
function Timing({ run }: { run: Run }) {
  const keys = [
    "imports_seconds",
    "load_verify_seconds",
    "estimator_fit_seconds",
    "test_estimator_predict_seconds",
    "process_wall_seconds",
  ];
  return (
    <Box>
      <Heading size="4" mb="2">
        Local timing
      </Heading>
      <Text as="p" color="gray" mb="4">
        Seconds: median [min, max] across three sequential fresh processes. One
        model thread; OS file caches were not flushed. Process time includes
        preparation and writes.
      </Text>
      <DataTable
        label="Local timing observations"
        sortValues={order
          .filter((n) => n in run.manifest.models)
          .map((n) => [
            label(n),
            ...keys.map((k) => run.manifest.models[n].timing_summary[k].median),
          ])}
        headers={[
          "Model",
          "Imports",
          "Load / verify",
          "Estimator fit",
          "Test prediction",
          "Process total",
        ]}
        rows={order
          .filter((n) => n in run.manifest.models)
          .map((n) => [
            label(n),
            ...keys.map((k) => {
              const t = run.manifest.models[n].timing_summary[k];
              return `${num(t.median, 3)} [${num(t.min, 3)}, ${num(t.max, 3)}]`;
            }),
          ])}
      />
    </Box>
  );
}
export function App({ data }: { data: Report }) {
  const [appearance, setAppearance] = useState<"light" | "dark">("light");
  const [seed, setSeed] = useState("3501");
  const [view, setView] = useState("overview");
  const run = (regime: string) =>
    data.runs.find(
      (r) =>
        String(r.evaluation.generator_seed) === seed &&
        r.evaluation.regime === regime,
    )!;
  const temporal = run("temporal"),
    random = run("random_reference");
  const chosen =
    seed === "3501" ? data.hosted : temporal.evaluation.evaluations.test;
  const integration = data.hosted.integration;
  return (
    <Theme
      appearance={appearance}
      accentColor="violet"
      grayColor="gray"
      radius="medium"
      scaling="100%"
    >
      <Box className="app-shell">
        <Container size="4" px={{ initial: "4", sm: "6" }}>
          <Flex
            className="topbar"
            align="center"
            justify="between"
            wrap="wrap"
            gap="3"
          >
            <Flex align="center" gap="3">
              <Box className="brand-mark">S</Box>
              <Text weight="bold" size="3">
                SCUBA
              </Text>
              <Separator orientation="vertical" size="1" />
              <Text color="gray" size="2">
                Evaluation workspace
              </Text>
            </Flex>
            <SegmentedControl.Root
              aria-label="Color theme"
              value={appearance}
              onValueChange={(v) => setAppearance(v as "light" | "dark")}
              size="1"
            >
              <SegmentedControl.Item value="light">
                <Flex align="center" gap="2">
                  <SunIcon />
                  Light
                </Flex>
              </SegmentedControl.Item>
              <SegmentedControl.Item value="dark">
                <Flex align="center" gap="2">
                  <MoonIcon />
                  Dark
                </Flex>
              </SegmentedControl.Item>
            </SegmentedControl.Root>
          </Flex>
          <Flex
            asChild
            className="dashboard-heading"
            justify="between"
            align="end"
            wrap="wrap"
            gap="4"
          >
            <header>
              <Box>
                <Flex gap="2" align="center" mb="3">
                  <Text size="1" className="eyebrow">
                    SCUBA / BENCHMARK
                  </Text>
                  <Badge variant="soft">Entirely synthetic</Badge>
                </Flex>
                <Heading as="h1" size="7">
                  Model evaluation
                </Heading>
                <Text as="p" color="gray" size="3" mt="2">
                  30-day dormancy · fictional mobile-money customers
                </Text>
              </Box>
              <Flex direction="column" gap="1" className="workspace-status">
                <Text size="2" weight="medium">
                  <CheckCircledIcon /> M4 evaluation complete
                </Text>
                <Text size="1" color="gray">
                  Approved scope · frozen results
                </Text>
              </Flex>
            </header>
          </Flex>
          <Tabs.Root value={view} onValueChange={setView}>
            <Box className="tabs-scroll">
              <Tabs.List aria-label="Report sections">
                <Tabs.Trigger value="overview">Overview</Tabs.Trigger>
                <Tabs.Trigger value="final">Final test</Tabs.Trigger>
                <Tabs.Trigger value="reference">Random reference</Tabs.Trigger>
                <Tabs.Trigger value="validation">Validation</Tabs.Trigger>
                <Tabs.Trigger value="evidence">Evidence & timing</Tabs.Trigger>
              </Tabs.List>
            </Box>
            <Flex justify="between" align="center" wrap="wrap" gap="3" my="5">
              <Box>
                <Heading size="5">
                  {
                    (
                      {
                        overview: "Primary evaluation",
                        final: "Later, unseen customers",
                        reference: "What changes when rows are mixed?",
                        validation: "Validation before the final test",
                        evidence: "Trace each result to its source",
                      } as Record<string, string>
                    )[view]
                  }
                </Heading>
                <Text size="2" color="gray">
                  {view === "overview"
                    ? "Seed 3501 · held-out temporal test · five models"
                    : view === "validation"
                      ? "Primary seed 3501 · saved development predictions"
                      : `Seed ${seed}${seed === "3501" ? " · primary" : " · sensitivity, local models only"}`}
                </Text>
              </Box>
              {view !== "validation" && view !== "overview" && (
                <Select.Root value={seed} onValueChange={setSeed}>
                  <Select.Trigger aria-label="Evaluation seed" />
                  <Select.Content>
                    <Select.Item value="3501">Primary · 3501</Select.Item>
                    <Select.Item value="3502">Sensitivity · 3502</Select.Item>
                    <Select.Item value="3503">Sensitivity · 3503</Select.Item>
                  </Select.Content>
                </Select.Root>
              )}
            </Flex>
            <Tabs.Content value="overview">
              <Dashboard
                data={data}
                onNavigate={(tab) => {
                  setSeed("3501");
                  setView(tab);
                  requestAnimationFrame(() => {
                    const target = document.querySelector<HTMLElement>(
                      '[role="tab"][aria-selected="true"]',
                    );
                    target?.focus({ preventScroll: true });
                    target?.scrollIntoView({
                      block: "start",
                      behavior: "instant",
                    });
                  });
                }}
              />
            </Tabs.Content>
            <Tabs.Content value="final">
              <Flex direction="column" gap="6">
                <Note>
                  {seed === "3501"
                    ? "TabPFN-3.5-Plus has higher observed AP. Paired 95% intervals against XGBoost and CatBoost include zero, so this does not establish a clear lead."
                    : "Local sensitivity results use the same frozen recipes. No hosted upload or prediction budget was approved for this seed."}{" "}
                  Synthetic results demonstrate the evaluation workflow, not
                  real-world accuracy or intervention value.
                </Note>
                <EvaluationView key={`final-${seed}`} evaluation={chosen} />
                <SplitAudit run={temporal} />
              </Flex>
            </Tabs.Content>
            <Tabs.Content value="reference">
              <Flex direction="column" gap="6">
                <Note>
                  This diagnostic split mixes dates and allows customer overlap.
                  Differences also reflect cohort composition and size; they are
                  not causal leakage effects or deployment-valid estimates.
                  Hosted random-reference inference was not budgeted.
                </Note>
                <Scores cohort={random.evaluation.evaluations.test.overall} />
                <Box>
                  <Heading size="4" mb="3">
                    Random minus temporal
                  </Heading>
                  <DataTable
                    label="Signed metric differences"
                    sortValues={modelNames(
                      temporal.evaluation.evaluations.test.overall,
                    ).map((n) => {
                      const a =
                          temporal.evaluation.evaluations.test.overall.models[
                            n
                          ],
                        b =
                          random.evaluation.evaluations.test.overall.models[n];
                      return [
                        label(n),
                        b.average_precision! - a.average_precision!,
                        b.log_loss - a.log_loss,
                        b.brier_score - a.brier_score,
                        b.ece_10_bins - a.ece_10_bins,
                        b.top_budgets["0.1"].capture! -
                          a.top_budgets["0.1"].capture!,
                        b.top_budgets["0.1"].lift! - a.top_budgets["0.1"].lift!,
                      ];
                    })}
                    headers={[
                      "Model",
                      "AP ↑",
                      "Log loss ↓",
                      "Brier ↓",
                      "ECE ↓",
                      "10% capture ↑",
                      "10% lift ↑",
                    ]}
                    rows={modelNames(
                      temporal.evaluation.evaluations.test.overall,
                    ).map((n) => {
                      const a =
                          temporal.evaluation.evaluations.test.overall.models[
                            n
                          ],
                        b =
                          random.evaluation.evaluations.test.overall.models[n];
                      const ds = [
                        b.average_precision! - a.average_precision!,
                        b.log_loss - a.log_loss,
                        b.brier_score - a.brier_score,
                        b.ece_10_bins - a.ece_10_bins,
                        b.top_budgets["0.1"].capture! -
                          a.top_budgets["0.1"].capture!,
                        b.top_budgets["0.1"].lift! - a.top_budgets["0.1"].lift!,
                      ];
                      return [
                        label(n),
                        ...ds.map((v) => (v >= 0 ? "+" : "") + num(v)),
                      ];
                    })}
                  />
                  <Text color="gray" size="2">
                    ↑ Higher is better. ↓ Lower is better. Differences retain
                    their actual sign.
                  </Text>
                </Box>
                <SplitAudit run={random} />
                <Pairs cohort={random.evaluation.evaluations.test.overall} />
                <Reliability
                  cohort={random.evaluation.evaluations.test.overall}
                />
                <Errors cohort={random.evaluation.evaluations.test.overall} />
                <Subgroups
                  key={`random-${seed}`}
                  evaluation={random.evaluation.evaluations.test}
                />
              </Flex>
            </Tabs.Content>
            <Tabs.Content value="validation">
              <Flex direction="column" gap="6">
                <Note>
                  These are saved primary validation predictions, distinct from
                  final test results. Validation TabPFN-3.5-Plus AP also has
                  paired intervals spanning zero against both tree models. Model
                  recipes and thresholds were frozen before test inference.
                </Note>
                <EvaluationView evaluation={data.validation} />
              </Flex>
            </Tabs.Content>
            <Tabs.Content value="evidence">
              <Flex direction="column" gap="6">
                <Note>
                  Every result is synthetic and tied to frozen inputs. All 72
                  local fit repetitions reproduced their predictions. Temporal
                  validation predictions matched M2. Offline evaluation added no
                  API calls.
                </Note>
                <Timing run={temporal} />
                <Timing run={random} />
                <Box>
                  <Heading size="4" mb="2">
                    Hosted integration · primary seed only
                  </Heading>
                  <Text as="p" color="gray" mb="4">
                    One approved feature upload and one prediction reused the
                    fitted resource. These are single latency observations, not
                    a controlled comparison against local fits.
                  </Text>
                  <DataTable
                    label="Hosted latency"
                    sortValues={integration.stages.map((s) => [
                      label(s.stage),
                      s.elapsed_seconds,
                    ])}
                    headers={["Stage", "Seconds"]}
                    rows={integration.stages.map((s) => [
                      label(s.stage),
                      num(s.elapsed_seconds, 3),
                    ])}
                  />
                  <Text as="p" size="2">
                    Fresh estimate:{" "}
                    {count(integration.fresh_preflight.estimated_total_tokens)}{" "}
                    tokens. Approved estimate ceiling:{" "}
                    {count(integration.approved_estimate_budget)} tokens. Actual
                    charges and credit balance are unavailable.
                  </Text>
                  <Text
                    as="p"
                    size="2"
                    color="gray"
                    mt="3"
                    className="break-word"
                  >
                    Reported checkpoint:{" "}
                    {integration.checkpoint_identity.reported_model_path}.
                    Checkpoint bytes were not independently attested.
                  </Text>
                </Box>
                <Box>
                  <Heading size="4" mb="3">
                    Scope and limits
                  </Heading>
                  <DataTable
                    label="Unrun routes"
                    headers={["Route", "Evidence status"]}
                    rows={[
                      [
                        "Hosted random reference and sensitivity",
                        "Not run; no approved budgets",
                      ],
                      [
                        "Hosted Fast and Thinking",
                        "Not run; no approved variant budgets",
                      ],
                      [
                        "Local base model",
                        "Outside approved hosted integration scope",
                      ],
                      [
                        "Repeated hosted timing",
                        "Not run; approval covered one prediction",
                      ],
                      [
                        "Real-customer benefit",
                        "Not measured; all data are synthetic",
                      ],
                    ]}
                  />
                </Box>
                <Box>
                  <Heading size="4" mb="3">
                    Source integrity
                  </Heading>
                  <Text as="p" size="2" color="gray" mb="3">
                    This presentation is rebuilt from the verified M4 report
                    sources. Its data are embedded locally; controls do not
                    contact the model service.
                  </Text>
                  <Button
                    variant="soft"
                    onClick={() => {
                      const blob = new Blob([JSON.stringify(data, null, 2)], {
                        type: "application/json",
                      });
                      const url = URL.createObjectURL(blob);
                      const a = document.createElement("a");
                      a.href = url;
                      a.download = "scuba-report-evidence.json";
                      a.click();
                      URL.revokeObjectURL(url);
                    }}
                  >
                    <ArrowDownIcon />
                    Save report evidence
                  </Button>
                  <Box asChild className="source-json" mt="4">
                    <pre>{JSON.stringify(data.sources, null, 2)}</pre>
                  </Box>
                </Box>
              </Flex>
            </Tabs.Content>
          </Tabs.Root>
          <Separator size="4" my="7" />
          <Flex asChild direction="column" gap="2" pb="6">
            <footer>
              <Flex align="center" gap="2">
                <CheckCircledIcon />
                <Text size="2" weight="medium">
                  Frozen recipes. Explicit uncertainty. Reproducible evidence.
                </Text>
              </Flex>
              <Text size="1" color="gray">
                95% AP intervals: 1,000 customer-cluster bootstrap draws, seed
                4401. Conditional on fitted models; exploratory subgroup
                comparisons are not adjusted for multiplicity.
              </Text>
              <Text size="1" color="gray">
                SCUBA · entirely synthetic · Radix UI
              </Text>
            </footer>
          </Flex>
        </Container>
      </Box>
    </Theme>
  );
}
