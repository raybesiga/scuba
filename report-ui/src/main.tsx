import { createRoot } from "react-dom/client";
import { App } from "./App";
import { FinancialStressApp } from "./FinancialStress";
import type { StressReport } from "./stress";
import type { Report } from "./types";
import "@radix-ui/themes/styles.css";
import "./palette.css";
import "./styles.css";
const data = JSON.parse(
  document.getElementById("report-data")!.textContent!,
) as Report | StressReport;
createRoot(document.getElementById("root")!).render(
  "dataset" in data && data.dataset === "financial_stress" ? (
    <FinancialStressApp data={data} />
  ) : (
    <App data={data as Report} />
  ),
);
