import { useState } from "react";
import {
  Badge,
  Box,
  Button,
  Flex,
  Grid,
  Heading,
  SegmentedControl,
  Separator,
  Text,
} from "@radix-ui/themes";
import {
  ArrowRightIcon,
  CheckCircledIcon,
  InfoCircledIcon,
  LayersIcon,
  PersonIcon,
  ReaderIcon,
} from "@radix-ui/react-icons";
import type { Report } from "./types";
const modelNames: Record<string, string> = {
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
const fmt = (n: number) => n.toLocaleString("en-US");
export function Dashboard({
  data,
  onNavigate,
}: {
  data: Report;
  onNavigate: (tab: string) => void;
}) {
  const [budget, setBudget] = useState("0.1");
  const c = data.hosted.overall,
    models = c.models,
    plus = models.hosted_plus;
  const selected = plus.top_budgets[budget];
  const primary = data.runs.find(
    (r) =>
      r.evaluation.generator_seed === 3501 &&
      r.evaluation.regime === "temporal",
  )!;
  const random = data.runs.find(
    (r) =>
      r.evaluation.generator_seed === 3501 &&
      r.evaluation.regime === "random_reference",
  )!;
  const totalCustomers = Object.values(
    primary.evaluation.split_audit.partitions,
  ).map((p) => p.customers);
  const maxAP =
    Math.ceil(
      Math.max(...order.map((n) => models[n].ap_interval.upper ?? 0)) * 10,
    ) / 10;
  const pair = c.paired_comparisons.hosted_plus_minus_xgboost;
  return (
    <Flex direction="column" gap="5">
      <Grid
        columns={{ initial: "1", sm: "3" }}
        gap="4"
        className="dashboard-facts"
      >
        <Box className="fact">
          <Flex justify="between" align="center">
            <Text color="gray" size="2">
              Final test customers
            </Text>
            <PersonIcon />
          </Flex>
          <Heading size="7" mt="3">
            {fmt(c.customers)}
          </Heading>
          <Text size="2" color="gray">
            {fmt(plus.positives)} became dormant ·{" "}
            {(plus.prevalence * 100).toFixed(1)}%
          </Text>
        </Box>
        <Box className="fact">
          <Flex justify="between" align="center">
            <Text color="gray" size="2">
              Models compared
            </Text>
            <LayersIcon />
          </Flex>
          <Heading size="7" mt="3">
            5
          </Heading>
          <Text size="2" color="gray">
            One hosted model · four local comparators
          </Text>
        </Box>
        <Box className="fact">
          <Flex justify="between" align="center">
            <Text color="gray" size="2">
              Train / test customer overlap
            </Text>
            <CheckCircledIcon />
          </Flex>
          <Heading size="7" mt="3">
            {primary.evaluation.split_audit.customer_overlap_counts.train__test}
          </Heading>
          <Text size="2" color="gray">
            Later test date · separate customer groups
          </Text>
        </Box>
      </Grid>
      <Grid
        columns={{ initial: "1", md: "2fr 1fr" }}
        gap="5"
        className="dashboard-main-grid"
      >
        <Box className="dashboard-module model-comparison">
          <Flex align="start" justify="between" gap="3" mb="5">
            <Box>
              <Text className="eyebrow">MODEL QUALITY</Text>
              <Heading size="5" mt="2">
                A small observed lead.
                <br />
                An uncertain ordering.
              </Heading>
            </Box>
            <Badge variant="soft" color="gray">
              Primary test
            </Badge>
          </Flex>
          <Text as="p" size="2" color="gray" mb="5">
            Average precision (AP), with 95% customer-bootstrap intervals.
            Higher is better.
          </Text>
          <Box
            role="img"
            aria-label={
              "Average precision with 95% intervals: " +
              order
                .map(
                  (n) =>
                    `${modelNames[n]} ${models[n].average_precision?.toFixed(4)}, interval ${models[n].ap_interval.lower?.toFixed(4)} to ${models[n].ap_interval.upper?.toFixed(4)}`,
                )
                .join("; ")
            }
            className="ap-plot"
          >
            {order.map((n) => {
              const m = models[n],
                lo = m.ap_interval.lower,
                hi = m.ap_interval.upper;
              return (
                <Box key={n} className={`ap-row ${n}`}>
                  <Flex justify="between" align="center" gap="2">
                    <Text
                      size="2"
                      weight={n === "hosted_plus" ? "bold" : "medium"}
                    >
                      <span className={`model-dot ${n}`} /> {modelNames[n]}
                    </Text>
                    <Text size="2" className="tabular" weight="bold">
                      {m.average_precision?.toFixed(4)}
                    </Text>
                  </Flex>
                  <svg
                    viewBox="0 0 500 24"
                    preserveAspectRatio="none"
                    aria-hidden="true"
                  >
                    <rect
                      x="0"
                      y="8"
                      width={(500 * (m.average_precision ?? 0)) / maxAP}
                      height="8"
                      rx="4"
                      fill="var(--series)"
                      opacity=".18"
                    />
                    {lo !== null && hi !== null && (
                      <g stroke="var(--series)" strokeWidth="1.5">
                        <path
                          d={`M${(500 * lo) / maxAP} 12H${(500 * hi) / maxAP} M${(500 * lo) / maxAP} 7V17 M${(500 * hi) / maxAP} 7V17`}
                        />
                      </g>
                    )}
                    <circle
                      cx={(500 * (m.average_precision ?? 0)) / maxAP}
                      cy="12"
                      r="4"
                      fill="var(--series)"
                    />
                  </svg>
                  <Text size="1" color="gray">
                    95% interval: {lo?.toFixed(4) ?? "Unavailable"}–
                    {hi?.toFixed(4) ?? "Unavailable"}
                  </Text>
                </Box>
              );
            })}
            <Flex justify="between" className="plot-axis">
              <Text size="1" color="gray">
                0.0
              </Text>
              <Text size="1" color="gray">
                {(maxAP / 2).toFixed(2)}
              </Text>
              <Text size="1" color="gray">
                {maxAP.toFixed(1)} AP
              </Text>
            </Flex>
          </Box>
          <Box className="comparison-conclusion" mt="5">
            <Flex gap="2" align="start">
              <InfoCircledIcon />
              <Box>
                <Text as="p" size="2" weight="medium">
                  TabPFN-3.5-Plus − XGBoost:{" "}
                  {pair.ap_difference >= 0 ? "+" : ""}
                  {pair.ap_difference.toFixed(4)} AP
                </Text>
                <Text as="p" size="2" color="gray">
                  Paired interval [{pair.interval.lower?.toFixed(4)},{" "}
                  {pair.interval.upper?.toFixed(4)}] includes zero. This does
                  not establish a clear lead.
                </Text>
              </Box>
            </Flex>
          </Box>
          <Button variant="ghost" mt="5" onClick={() => onNavigate("final")}>
            Compare all metrics <ArrowRightIcon />
          </Button>
        </Box>
        <Box className="dashboard-module budget-module">
          <Text className="eyebrow">REVIEW CAPACITY</Text>
          <Heading size="5" mt="2" mb="3">
            What does the shortlist find?
          </Heading>
          <Text as="p" size="2" color="gray" mb="4">
            Inspect the two budgets fixed before the final test. No threshold is
            retuned.
          </Text>
          <SegmentedControl.Root
            value={budget}
            onValueChange={setBudget}
            aria-label="Review capacity"
            size="2"
          >
            <SegmentedControl.Item value="0.05">Top 5%</SegmentedControl.Item>
            <SegmentedControl.Item value="0.1">Top 10%</SegmentedControl.Item>
          </SegmentedControl.Root>
          <Box className="budget-highlight" my="5">
            <Text size="2">TabPFN-3.5-Plus captures</Text>
            <Heading size="8" mt="2">
              {selected.tp}
              <Text size="4" weight="regular" color="gray">
                {" "}
                / {plus.positives}
              </Text>
            </Heading>
            <Text as="p" size="2" color="gray" mt="1">
              {((selected.capture ?? 0) * 100).toFixed(1)}% of positive outcomes
            </Text>
            <Separator size="4" my="4" />
            <Flex justify="between">
              <Box>
                <Text as="p" size="1" color="gray">
                  Customers reviewed
                </Text>
                <Text size="3" weight="bold">
                  {fmt(selected.selected)}
                </Text>
              </Box>
              <Box>
                <Text as="p" size="1" color="gray">
                  False positives
                </Text>
                <Text size="3" weight="bold">
                  {selected.fp}
                </Text>
              </Box>
            </Flex>
          </Box>
          <Text as="p" size="2" weight="medium" mb="3">
            Captured at the same capacity
          </Text>
          <Flex direction="column" gap="3">
            {["hosted_plus", "xgboost", "catboost"].map((n) => {
              const b = models[n].top_budgets[budget];
              return (
                <Box key={n} className={n}>
                  <Flex justify="between" mb="1">
                    <Text size="2">{modelNames[n]}</Text>
                    <Text size="2" weight="medium">
                      {b.tp}
                    </Text>
                  </Flex>
                  <Box className="capture-track">
                    <Box
                      style={{
                        width: `${(100 * b.tp) / plus.positives}%`,
                        background: "var(--series)",
                      }}
                    />
                  </Box>
                </Box>
              );
            })}
          </Flex>
          <Text as="p" size="1" color="gray" mt="5">
            These are observed synthetic outcomes, not proven intervention
            benefit. Capture differences have no confidence interval in this
            protocol.
          </Text>
        </Box>
      </Grid>
      <Grid columns={{ initial: "1", md: "2fr 1fr" }} gap="5">
        <Box className="dashboard-module">
          <Flex justify="between" align="center" mb="4">
            <Box>
              <Text className="eyebrow">EVALUATION DESIGN</Text>
              <Heading size="4" mt="2">
                Separated by time and customer
              </Heading>
            </Box>
            <Badge variant="outline">No overlap</Badge>
          </Flex>
          <Grid columns={{ initial: "1", sm: "3" }} gap="4">
            {(["train", "validation", "test"] as const).map((name) => {
              const p = primary.evaluation.split_audit.partitions[name];
              return (
                <Box key={name} className="cohort-step">
                  <Text size="1" color="gray">
                    {name === "train"
                      ? "01 · TRAIN"
                      : name === "validation"
                        ? "02 · VALIDATE"
                        : "03 · TEST"}
                  </Text>
                  <Heading size="5" mt="2">
                    {fmt(p.customers)}
                  </Heading>
                  <Text as="p" size="1" color="gray">
                    customers · {fmt(p.rows)} snapshots
                  </Text>
                  <Box className="cohort-track" mt="3">
                    <Box
                      style={{
                        width: `${(100 * p.customers) / Math.max(...totalCustomers)}%`,
                      }}
                    />
                  </Box>
                  <Text as="p" size="1" color="gray" mt="2">
                    {name === "train"
                      ? "Apr–Jun 2032"
                      : name === "validation"
                        ? "August 2032"
                        : "October 2032"}
                  </Text>
                </Box>
              );
            })}
          </Grid>
          <Text as="p" color="gray" size="1" mt="4">
            Dates and customers are fictional. Features use preceding activity;
            labels use the following 30 days.
          </Text>
        </Box>
        <Box className="dashboard-module">
          <Text className="eyebrow">DIAGNOSTIC CHECK</Text>
          <Heading size="4" mt="2">
            A higher score can hide overlap
          </Heading>
          <Flex align="baseline" gap="3" my="4">
            <Heading size="7">
              {fmt(
                random.evaluation.split_audit.customer_overlap_counts
                  .train__test,
              )}
            </Heading>
            <Text size="2" color="gray">
              shared customers
            </Text>
          </Flex>
          <Text as="p" size="2" color="gray">
            The random reference mixes dates and shares customers between
            training and test. Its scores describe a different evaluation.
          </Text>
          <Button
            variant="ghost"
            mt="5"
            onClick={() => onNavigate("reference")}
          >
            Inspect the random reference <ArrowRightIcon />
          </Button>
        </Box>
      </Grid>
      <Flex
        className="evidence-ribbon"
        align="center"
        justify="between"
        wrap="wrap"
        gap="4"
      >
        <Flex gap="3" align="start">
          <ReaderIcon />
          <Box>
            <Text as="p" size="2" weight="medium">
              Every result has an evidence trail
            </Text>
            <Text as="p" size="2" color="gray">
              Frozen inputs · 72 repeatable local fits · one verified hosted
              test prediction
            </Text>
          </Box>
        </Flex>
        <Button variant="soft" onClick={() => onNavigate("evidence")}>
          Inspect evidence <ArrowRightIcon />
        </Button>
      </Flex>
    </Flex>
  );
}
