import { useState } from "react";
import {
  Badge,
  Box,
  Button,
  Container,
  Flex,
  Grid,
  Heading,
  SegmentedControl,
  Select,
  Table,
  Tabs,
  Text,
  TextField,
  Theme,
} from "@radix-ui/themes";
import {
  ArrowDownIcon,
  ArrowUpIcon,
  CaretSortIcon,
  CheckCircledIcon,
  DownloadIcon,
  MagnifyingGlassIcon,
  MoonIcon,
  SunIcon,
} from "@radix-ui/react-icons";
import { DataTable } from "./App";
import { sortRowIndices, type SortDirection } from "./sorting";
import {
  shortlist,
  searchSnapshots,
  totalActivity,
  stressNames,
  type Snapshot,
  type StressReport,
} from "./stress";
const number = (v: number) => v.toLocaleString("en-US");
const percent = (v: number | null) =>
  v === null ? "Unavailable" : `${(100 * v).toFixed(1)}%`;
const score = (v: number | null) => (v === null ? "Unavailable" : v.toFixed(4));
const familyNames: Record<string, string> = {
  paybill: "Bill payments",
  merchantpay: "Merchant payments",
  transfer_from_bank: "From bank",
  mm_send: "Transfers sent",
  received: "Transfers received",
  deposit: "Cash deposits",
  withdraw: "Cash withdrawals",
};
function Detail({ row }: { row: Snapshot | null }) {
  if (!row)
    return (
      <Box className="dashboard-module">
        <Heading as="h2" size="4">
          Snapshot context
        </Heading>
        <Text as="p" mt="3" color="gray">
          Choose a snapshot from the review list.
        </Text>
      </Box>
    );
  const totals = totalActivity(row),
    max = Math.max(...totals, 1);
  return (
    <Box
      className="dashboard-module snapshot-detail"
      aria-label="Selected snapshot context"
    >
      <Text className="eyebrow">SNAPSHOT CONTEXT</Text>
      <Heading as="h2" size="4" mt="2" className="break-word">
        {row.id}
      </Heading>
      <Text as="p" size="2" color="gray" mt="2">
        {row.region} · {row.segment}
      </Text>
      <Text as="p" size="2" mt="5">
        Estimated 30-day stress probability
      </Text>
      <Heading as="h3" size="7" mt="1">
        {percent(row.probability)}
      </Heading>
      <Text size="1" color="gray">
        TabPFN-3.5-Plus · validation snapshot
      </Text>
      <Heading as="h3" size="3" mt="6">
        Six months of activity
      </Heading>
      <Text as="p" size="2" color="gray" mt="2">
        Monthly transaction counts. M6 is oldest; M1 is most recent.
      </Text>
      <Box
        className="month-bars"
        role="img"
        aria-label={totals
          .map((v, i) => `M${6 - i}: ${v} transactions`)
          .join(", ")}
      >
        {totals.map((v, i) => (
          <Flex key={i} direction="column" align="center" gap="2">
            <Text size="1">{number(v)}</Text>
            <div className="month-bar-space">
              <div style={{ height: `${(100 * v) / max}%` }} />
            </div>
            <Text size="1" color="gray">
              M{6 - i}
            </Text>
          </Flex>
        ))}
      </Box>
      <Text as="p" size="2">
        {number(totals[5])} transactions in M1, compared with{" "}
        {number(totals[4])} in M2.
      </Text>
      <Text as="p" size="1" color="gray" mt="2">
        Observed context, not a causal explanation of the prediction.
      </Text>
      <details className="snapshot-breakdown">
        <summary>View monthly breakdown</summary>
        <div
          className="table-scroll"
          tabIndex={0}
          role="region"
          aria-label="Monthly activity breakdown"
        >
          <Table.Root size="1">
            <Table.Header>
              <Table.Row>
                <Table.ColumnHeaderCell>Activity</Table.ColumnHeaderCell>
                {[6, 5, 4, 3, 2, 1].map((m) => (
                  <Table.ColumnHeaderCell key={m}>M{m}</Table.ColumnHeaderCell>
                ))}
              </Table.Row>
            </Table.Header>
            <Table.Body>
              {Object.entries(row.activity).map(([k, values]) => (
                <Table.Row key={k}>
                  <Table.RowHeaderCell>{familyNames[k]}</Table.RowHeaderCell>
                  {values.map((v, i) => (
                    <Table.Cell key={i}>{number(v)}</Table.Cell>
                  ))}
                </Table.Row>
              ))}
              <Table.Row>
                <Table.RowHeaderCell>Average daily balance</Table.RowHeaderCell>
                {row.balance.map((v, i) => (
                  <Table.Cell key={i}>{v.toFixed(2)}</Table.Cell>
                ))}
              </Table.Row>
            </Table.Body>
          </Table.Root>
        </div>
        <Text as="p" size="1" color="gray">
          Balance is in dataset units; currency and calendar dates are not
          supplied.
        </Text>
      </details>
      <Box mt="5" className="comparison-conclusion">
        <Text size="2" weight="medium">
          Human review comes next
        </Text>
        <Text as="p" size="2" mt="1">
          Verify the customer’s context before considering support. This demo
          does not contact customers or choose an offer.
        </Text>
      </Box>
    </Box>
  );
}
function Review({
  data,
  budget,
  setBudget,
}: {
  data: StressReport;
  budget: string;
  setBudget: (v: string) => void;
}) {
  const [query, setQuery] = useState("");
  const [page, setPage] = useState(0);
  const [selected, setSelected] = useState<string | null>(null);
  const [sort, setSort] = useState<{
    column: "id" | "probability" | "region" | "segment";
    direction: SortDirection;
  } | null>(null);
  const rows = shortlist(data.snapshots, budget),
    filtered = searchSnapshots(rows, query);
  const ordered = sort
    ? sortRowIndices(
        filtered.map((r) => r[sort.column]),
        sort.direction,
      ).map((i) => filtered[i])
    : filtered;
  const pages = Math.max(1, Math.ceil(ordered.length / 15)),
    current = Math.min(page, pages - 1),
    shown = ordered.slice(current * 15, current * 15 + 15);
  const detail = filtered.find((r) => r.id === selected) ?? filtered[0] ?? null;
  const m = data.metrics.tabpfn_3_5_plus.top_budgets[budget],
    x = data.metrics.xgboost.top_budgets[budget];
  function changeSort(column: "id" | "probability" | "region" | "segment") {
    const first = column === "probability" ? "descending" : "ascending";
    setSort(
      sort?.column !== column
        ? { column, direction: first }
        : sort.direction === first
          ? {
              column,
              direction: first === "ascending" ? "descending" : "ascending",
            }
          : null,
    );
    setPage(0);
  }
  return (
    <Flex direction="column" gap="5">
      <Grid columns={{ initial: "1", md: "2fr 1fr" }} gap="5">
        <Box className="dashboard-module">
          <Text className="eyebrow">REVIEW CAPACITY</Text>
          <Heading as="h2" size="5" mt="2">
            A focused list for customer care
          </Heading>
          <Text as="p" color="gray" size="2" mt="2">
            Choose how many snapshots to review. Highest predicted stress
            probabilities come first.
          </Text>
          <Flex wrap="wrap" gap="4" align="center" mt="5">
            <SegmentedControl.Root
              aria-label="Review capacity"
              value={budget}
              onValueChange={(v) => {
                setBudget(v);
                setPage(0);
                setSelected(null);
              }}
            >
              <SegmentedControl.Item value="0.05">
                Top 5% · {number(Math.ceil(data.snapshots.length * 0.05))}
              </SegmentedControl.Item>
              <SegmentedControl.Item value="0.1">
                Top 10% · {number(Math.ceil(data.snapshots.length * 0.1))}
              </SegmentedControl.Item>
            </SegmentedControl.Root>
            <Button asChild>
              <a
                href={`review-${rows.length}.csv`}
                download={`scuba-validation-review-${rows.length}.csv`}
              >
                <DownloadIcon />
                Export {number(rows.length)} snapshots
              </a>
            </Button>
          </Flex>
          <Text as="p" size="1" color="gray" mt="3">
            Export includes the full selected shortlist, regardless of search,
            sorting or page.
          </Text>
        </Box>
        <Box className="dashboard-module">
          <Text className="eyebrow">OBSERVED IN VALIDATION</Text>
          <Heading as="h2" size="8" mt="3">
            {number(m.tp)}{" "}
            <Text size="3" color="gray">
              / {number(data.cohorts.validation.positives)}
            </Text>
          </Heading>
          <Text as="p" size="2" mt="2">
            stress cases found among {number(m.selected)} reviewed snapshots
          </Text>
          <Text as="p" size="2" color="gray" mt="2">
            {m.tp - x.tp} more than XGBoost at the same capacity.
          </Text>
          <Text as="p" size="1" color="gray" mt="3">
            {number(m.fp)} false positives · {number(m.fn)} stress cases outside
            the list. Historical outcomes, not proven outreach benefit.
          </Text>
        </Box>
      </Grid>
      <Grid columns={{ initial: "1", md: "2fr 1fr" }} gap="5" align="start">
        <Box className="dashboard-module review-module">
          <Flex justify="between" align="center" gap="3" wrap="wrap">
            <Heading as="h2" size="4">
              Review list
            </Heading>
            <Badge variant="soft">TabPFN-3.5-Plus</Badge>
          </Flex>
          <Box mt="4">
            <TextField.Root
              aria-label="Search review list"
              placeholder="Search snapshot, region or segment"
              value={query}
              onChange={(e) => {
                setQuery(e.target.value);
                setPage(0);
              }}
            >
              <TextField.Slot>
                <MagnifyingGlassIcon />
              </TextField.Slot>
            </TextField.Root>
          </Box>
          <Text as="p" size="1" color="gray" mt="2" mb="4" aria-live="polite">
            {number(filtered.length)} of {number(rows.length)} shortlisted
            snapshots match. Sorting changes display order only.
          </Text>
          <div
            className="table-scroll review-table"
            role="region"
            aria-label="Ranked review snapshots"
            tabIndex={0}
          >
            <Table.Root variant="surface" size="2">
              <Table.Header>
                <Table.Row>
                  {(
                    [
                      ["id", "Snapshot"],
                      ["probability", "Stress probability"],
                      ["region", "Region"],
                      ["segment", "Segment"],
                    ] as const
                  ).map(([key, label]) => (
                    <Table.ColumnHeaderCell
                      key={key}
                      aria-sort={sort?.column === key ? sort.direction : "none"}
                    >
                      <Button
                        variant="ghost"
                        color="gray"
                        highContrast
                        size="1"
                        className="table-sort-button"
                        aria-label={`Sort by ${label}`}
                        onClick={() => changeSort(key)}
                      >
                        {label}
                        {sort?.column === key ? (
                          sort.direction === "ascending" ? (
                            <ArrowUpIcon />
                          ) : (
                            <ArrowDownIcon />
                          )
                        ) : (
                          <CaretSortIcon />
                        )}
                      </Button>
                    </Table.ColumnHeaderCell>
                  ))}
                </Table.Row>
              </Table.Header>
              <Table.Body>
                {shown.map((r) => (
                  <Table.Row key={r.id} data-selected={r.id === detail?.id}>
                    <Table.RowHeaderCell>
                      <Button
                        size="1"
                        variant="ghost"
                        onClick={() => setSelected(r.id)}
                        aria-pressed={r.id === detail?.id}
                      >
                        {r.id}
                      </Button>
                    </Table.RowHeaderCell>
                    <Table.Cell className="tabular">
                      {percent(r.probability)}
                    </Table.Cell>
                    <Table.Cell>{r.region}</Table.Cell>
                    <Table.Cell>{r.segment}</Table.Cell>
                  </Table.Row>
                ))}
              </Table.Body>
            </Table.Root>
          </div>
          {!filtered.length && (
            <Box py="5">
              <Heading as="h3" size="3">
                No matching snapshots
              </Heading>
              <Text as="p" size="2" color="gray" mt="2">
                Try another search within this shortlist.
              </Text>
              <Button variant="soft" mt="3" onClick={() => setQuery("")}>
                Clear search
              </Button>
            </Box>
          )}
          <Flex justify="between" align="center" gap="3" mt="3">
            <Text size="1" color="gray">
              Page {current + 1} of {pages}
            </Text>
            <Flex gap="2">
              <Button
                variant="soft"
                disabled={current === 0}
                onClick={() => setPage(current - 1)}
              >
                Previous
              </Button>
              <Button
                variant="soft"
                disabled={current + 1 >= pages}
                onClick={() => setPage(current + 1)}
              >
                Next
              </Button>
            </Flex>
          </Flex>
        </Box>
        <Detail row={detail} />
      </Grid>
    </Flex>
  );
}
function Evidence({
  data,
  budget,
  final = false,
}: {
  data: StressReport;
  budget: string;
  final?: boolean;
}) {
  const [model, setModel] = useState("tabpfn_3_5_plus"),
    [dimension, setDimension] = useState("region");
  const models = Object.keys(stressNames),
    metrics = final ? data.final_evaluation!.metrics : data.metrics,
    cohort = final ? data.final_evaluation!.cohort : data.cohorts.validation,
    m = metrics[model],
    groups = (
      final ? data.final_evaluation!.cohort_audit : data.cohort_audit
    ).filter((r) => r.dimension === dimension);
  return (
    <Flex direction="column" gap="6">
      <Box>
        <Heading as="h2" size="5">
          {final
            ? "Final holdout: how the models compare"
            : "How the models compare"}
        </Heading>
        <Text as="p" color="gray" size="2" mt="2" mb="4">
          Same {number(data.cohorts.train.rows)} training snapshots and{" "}
          {number(cohort.rows)} {final ? "final-holdout" : "validation"}{" "}
          snapshots. Fixed recipes; lower log loss is better.{" "}
          {final
            ? "These rows were reserved until settings were frozen. Results are point estimates."
            : "These are point estimates, not final-test results."}
        </Text>
        <DataTable
          label="Financial Stress model comparison"
          headers={[
            "Model",
            "Log loss ↓",
            "AUROC ↑",
            "Average precision ↑",
            "Brier ↓",
            "Captured ↑",
          ]}
          rows={models.map((k) => {
            const v = metrics[k];
            return [
              stressNames[k],
              score(v.log_loss),
              score(v.roc_auc),
              score(v.average_precision),
              score(v.brier_score),
              `${v.top_budgets[budget].tp} / ${number(cohort.positives)}`,
            ];
          })}
          sortValues={models.map((k) => {
            const v = metrics[k];
            return [
              stressNames[k],
              v.log_loss,
              v.roc_auc,
              v.average_precision,
              v.brier_score,
              v.top_budgets[budget].tp,
            ];
          })}
        />
        <Text size="1" color="gray">
          Capture uses the {Number(budget) * 100}% review capacity selected in
          the workspace.
        </Text>
      </Box>
      <Grid columns={{ initial: "1", md: "2fr 1fr" }} gap="5" align="start">
        <Box>
          <Flex justify="between" align="center" gap="3" wrap="wrap">
            <Heading as="h2" size="4">
              Do probabilities match outcomes?
            </Heading>
            <Select.Root value={model} onValueChange={setModel}>
              <Select.Trigger aria-label="Calibration model" />
              <Select.Content>
                {models.map((k) => (
                  <Select.Item key={k} value={k}>
                    {stressNames[k]}
                  </Select.Item>
                ))}
              </Select.Content>
            </Select.Root>
          </Flex>
          <Text as="p" size="2" color="gray" mt="2" mb="4">
            For groups assigned similar probabilities, compare the average
            prediction with the fraction that experienced stress.
          </Text>
          <DataTable
            label="Calibration with group sizes"
            headers={[
              "Predicted range",
              "Snapshots",
              "Mean prediction",
              "Observed stress",
            ]}
            rows={m.reliability.map((b) => [
              `${Math.round(b.lower * 100)}–${Math.round(b.upper * 100)}%`,
              number(b.rows),
              percent(b.mean_probability),
              percent(b.observed_fraction),
            ])}
            sortValues={m.reliability.map((b) => [
              b.lower,
              b.rows,
              b.mean_probability,
              b.observed_fraction,
            ])}
          />
        </Box>
        <Box className="dashboard-module">
          <Heading as="h3" size="4">
            Read the group size too
          </Heading>
          <Text as="p" size="2" mt="3">
            If a group averages 30% predicted risk, roughly 30% should
            experience stress for the probabilities to be well calibrated.
          </Text>
          <Text as="p" size="2" color="gray" mt="3">
            Small groups can fluctuate sharply. This table shows their support
            explicitly; it does not provide confidence intervals.
          </Text>
          <Text as="p" size="2" mt="4">
            Calibration error: <strong>{percent(m.ece_10_bins)}</strong>
          </Text>
          <Text as="p" size="1" color="gray" mt="1">
            Weighted absolute gap across ten fixed bins.
          </Text>
        </Box>
      </Grid>
      <Box>
        <Flex justify="between" align="center" gap="3" wrap="wrap">
          <Heading as="h2" size="4">
            Check performance across groups
          </Heading>
          <Select.Root value={dimension} onValueChange={setDimension}>
            <Select.Trigger aria-label="Audit grouping" />
            <Select.Content>
              {[
                ["region", "Region"],
                ["segment", "Segment"],
                ["earning_pattern", "Earning pattern"],
                ["gender", "Gender"],
                ["age_band", "Age band"],
              ].map(([k, v]) => (
                <Select.Item key={k} value={k}>
                  {v}
                </Select.Item>
              ))}
            </Select.Content>
          </Select.Root>
        </Flex>
        <Text as="p" size="2" color="gray" mt="2" mb="4">
          TabPFN-3.5-Plus. Review counts use the global shortlist; no
          group-specific threshold. Descriptive audit, not a fairness guarantee.
        </Text>
        <DataTable
          label="Group performance audit"
          headers={[
            "Group",
            "Snapshots",
            "Stress cases",
            "AUROC ↑",
            "Log loss ↓",
            "Reviewed",
            "Captured",
          ]}
          rows={groups.map((g) => [
            g.group + (g.sparse ? " · limited support" : ""),
            number(g.rows),
            number(g.positives),
            score(g.roc_auc),
            score(g.log_loss),
            number(g.budgets[budget].selected),
            number(g.budgets[budget].captured),
          ])}
          sortValues={groups.map((g) => [
            g.group,
            g.rows,
            g.positives,
            g.roc_auc,
            g.log_loss,
            g.budgets[budget].selected,
            g.budgets[budget].captured,
          ])}
        />
      </Box>
      {!final && (
        <Box>
          <Heading as="h2" size="4">
            Sensitivity to age and gender
          </Heading>
          <Text as="p" size="2" color="gray" mt="2" mb="4">
            Local models refitted on the same rows with age and gender omitted.
            TabPFN has not been rerun without these fields. Other predictors may
            still act as proxies.
          </Text>
          <DataTable
            label="Local feature exclusion comparison"
            headers={[
              "Local model",
              "All features · log loss ↓",
              "Without age / gender ↓",
              "Difference",
            ]}
            rows={Object.entries(data.ablation).map(([k, v]) => [
              stressNames[k],
              score(data.metrics[k].log_loss),
              score(v.log_loss),
              score(v.log_loss - data.metrics[k].log_loss),
            ])}
            sortValues={Object.entries(data.ablation).map(([k, v]) => [
              stressNames[k],
              data.metrics[k].log_loss,
              v.log_loss,
              v.log_loss - data.metrics[k].log_loss,
            ])}
          />
        </Box>
      )}
    </Flex>
  );
}
export function FinancialStressApp({ data }: { data: StressReport }) {
  const [theme, setTheme] = useState<"light" | "dark">("light"),
    [budget, setBudget] = useState("0.1");
  return (
    <Theme
      appearance={theme}
      accentColor="violet"
      grayColor="sage"
      radius="medium"
    >
      <Box className="app-shell">
        <Container size="4" px={{ initial: "4", sm: "6" }}>
          <Flex
            className="topbar"
            align="center"
            justify="between"
            gap="3"
            wrap="wrap"
          >
            <Flex align="center" gap="3">
              <span className="brand-mark">S</span>
              <Text weight="bold">SCUBA</Text>
              <Text size="2" color="gray">
                Customer-care workspace
              </Text>
            </Flex>
            <Flex align="center" gap="3" wrap="wrap">
              <Button asChild variant="ghost" color="gray">
                <a href="archive/index.html">Synthetic benchmark archive</a>
              </Button>
              <SegmentedControl.Root
                size="1"
                value={theme}
                aria-label="Color theme"
                onValueChange={(v) => setTheme(v as "light" | "dark")}
              >
                <SegmentedControl.Item value="light">
                  <SunIcon /> Light
                </SegmentedControl.Item>
                <SegmentedControl.Item value="dark">
                  <MoonIcon /> Dark
                </SegmentedControl.Item>
              </SegmentedControl.Root>
            </Flex>
          </Flex>
          <Flex
            className="dashboard-heading"
            justify="between"
            align="end"
            gap="4"
            wrap="wrap"
          >
            <Box>
              <Flex gap="3" align="center">
                <Text className="eyebrow">SCUBA / FINANCIAL STRESS</Text>
                <Badge>Validation demo</Badge>
              </Flex>
              <Heading as="h1" size="7" mt="4">
                Customer care, with earlier signals.
              </Heading>
              <Text as="p" color="gray" mt="3">
                Six months of activity · predicted financial stress in the next
                30 days
              </Text>
            </Box>
            <Box className="workspace-status">
              <Text as="p" size="2">
                <CheckCircledIcon />{" "}
                {data.final_evaluation
                  ? "Final holdout verified"
                  : "Verified model comparison"}
              </Text>
              <Text as="p" size="1" color="gray" mt="2">
                {data.final_evaluation
                  ? "Final results available · no live customer actions"
                  : "Final holdout reserved · no live customer actions"}
              </Text>
            </Box>
          </Flex>
          <Grid columns={{ initial: "1", sm: "3" }} gap="4" mb="5">
            <Box className="fact">
              <Text size="2" color="gray">
                Validation snapshots
              </Text>
              <Heading as="h2" size="6" mt="2">
                {number(data.cohorts.validation.rows)}
              </Heading>
              <Text size="2" color="gray">
                {number(data.cohorts.validation.positives)} labelled stress
                cases ·{" "}
                {percent(
                  data.cohorts.validation.positives /
                    data.cohorts.validation.rows,
                )}
              </Text>
            </Box>
            <Box className="fact">
              <Text size="2" color="gray">
                Leading validation model
              </Text>
              <Heading as="h2" size="5" mt="2">
                TabPFN-3.5-Plus
              </Heading>
              <Text size="2" color="gray">
                {score(data.metrics.tabpfn_3_5_plus.log_loss)} log loss ·{" "}
                {Object.keys(data.metrics).length} models compared
              </Text>
            </Box>
            <Box className="fact">
              <Text size="2" color="gray">
                Evaluation basis
              </Text>
              <Heading as="h2" size="5" mt="2">
                Held-out snapshots
              </Heading>
              <Text size="2" color="gray">
                Dates and distinct customers unverified
              </Text>
            </Box>
          </Grid>
          <Tabs.Root defaultValue="review">
            <Box className="tabs-scroll">
              <Tabs.List aria-label="Financial Stress sections">
                <Tabs.Trigger value="review">Review workspace</Tabs.Trigger>
                <Tabs.Trigger value="evidence">Model evidence</Tabs.Trigger>
                {data.final_evaluation && (
                  <Tabs.Trigger value="final">Final holdout</Tabs.Trigger>
                )}
                <Tabs.Trigger value="about">Data & limitations</Tabs.Trigger>
              </Tabs.List>
            </Box>
            <Tabs.Content
              value="review"
              style={{ paddingTop: "var(--space-5)" }}
            >
              <Review data={data} budget={budget} setBudget={setBudget} />
            </Tabs.Content>
            <Tabs.Content
              value="evidence"
              style={{ paddingTop: "var(--space-5)" }}
            >
              <Evidence data={data} budget={budget} />
            </Tabs.Content>
            {data.final_evaluation && (
              <Tabs.Content
                value="final"
                style={{ paddingTop: "var(--space-5)" }}
              >
                <Evidence data={data} budget={budget} final />
              </Tabs.Content>
            )}
            <Tabs.Content
              value="about"
              style={{ paddingTop: "var(--space-5)" }}
            >
              <Grid columns={{ initial: "1", md: "2fr 1fr" }} gap="5">
                <Box className="dashboard-module">
                  <Heading as="h2" size="5">
                    What this demo can establish
                  </Heading>
                  <Text as="p" mt="3">
                    Predictions were evaluated on{" "}
                    {number(data.cohorts.validation.rows)} labelled snapshots
                    excluded from model fitting. All five models received the
                    same {number(data.cohorts.train.rows)} training snapshots
                    and {data.features} predictors.
                  </Text>
                  <Text as="p" mt="3">
                    The target is the supplied 30-day liquidity-stress label.
                    Its operational definition and the dataset’s real or
                    synthetic origin have not been independently established.
                  </Text>
                  <Text as="p" mt="3">
                    Observation dates and persistent customer identifiers are
                    absent. This is a row holdout, not proof of future
                    performance or separation between people. The{" "}
                    {number(data.cohorts.final.rows)}-row final holdout{" "}
                    {data.final_evaluation
                      ? "has now been evaluated separately with frozen settings. The review workspace continues to show validation snapshots."
                      : "remains untouched."}
                  </Text>
                  <Text as="p" mt="3">
                    Care actions are operator policy. Predictions do not
                    establish which offer would help, treatment benefit, or
                    suitability for a credit decision.
                  </Text>
                  <Text as="p" size="2" color="gray" mt="4">
                    Source:{" "}
                    <a href="https://zindi.world/competitions/financial-stress-prediction-challenge-2026-09-01">
                      Zindi Financial Stress Prediction Challenge, September
                      Edition
                    </a>
                    . Declared data licence:{" "}
                    <a href="https://creativecommons.org/licenses/by-sa/4.0/">
                      CC BY-SA 4.0
                    </a>
                    . Displayed data is adapted into monthly views, predictions
                    and aggregate diagnostics by SCUBA; those data adaptations
                    retain CC BY-SA 4.0. Original SCUBA code: Apache-2.0.
                  </Text>
                  <Button asChild variant="soft" mt="4">
                    <a
                      href="evidence.json"
                      download="scuba-financial-stress-evidence.json"
                    >
                      Download local evidence
                    </a>
                  </Button>
                  <Text as="p" size="1" color="gray" mt="2">
                    Includes the displayed snapshot activity and probabilities.
                    No network request or model run is triggered.
                  </Text>
                </Box>
                <Box className="dashboard-module">
                  <Text className="eyebrow">ROADMAP</Text>
                  <Heading as="h2" size="4" mt="2">
                    One use case at a time
                  </Heading>
                  <Text as="p" mt="3" size="2">
                    Financial Stress is the active workflow. Nedbank
                    transaction-volume forecasting is planned for later.
                  </Text>
                  <Text as="p" mt="3" size="2" color="gray">
                    The synthetic dormancy benchmark is preserved as an archive.
                    Its metrics are separate from this dataset.
                  </Text>
                  <Heading as="h3" size="3" mt="5">
                    Model identity
                  </Heading>
                  <Text as="p" size="2" mt="2">
                    TabPFN-3.5-Plus
                  </Text>
                  <Text
                    as="p"
                    className="break-word"
                    size="1"
                    color="gray"
                    mt="2"
                  >
                    {data.identity.reported_model_path}
                  </Text>
                  <Text as="p" size="1" color="gray" mt="2">
                    Server-reported checkpoint checked against our reviewed
                    identity policy.
                  </Text>
                </Box>
              </Grid>
            </Tabs.Content>
          </Tabs.Root>
          <Text
            as="p"
            size="1"
            color="gray"
            style={{ paddingBlock: "var(--space-6)" }}
          >
            SCUBA · Financial Stress validation demo · Review support, not
            automated customer decisions
          </Text>
        </Container>
      </Box>
    </Theme>
  );
}
