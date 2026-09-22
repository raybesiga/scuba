"""Standalone local HTML report from pinned final evaluation artifacts."""

import html
import json

from scuba.artifacts import file_hash, write_json

NAMES = {
    "constant_prior": "Constant prior",
    "logistic_regression": "Logistic regression",
    "xgboost": "XGBoost",
    "catboost": "CatBoost",
    "hosted_plus": "TabPFN-3.5-Plus",
}
COLORS = {
    "constant_prior": "#849096",
    "logistic_regression": "#bc7729",
    "xgboost": "#087e8b",
    "catboost": "#7552a0",
    "hosted_plus": "#a83d64",
}


def fmt(value, percent=False):
    if value is None:
        return "Unavailable"
    return f"{value:.1%}" if percent else f"{value:.4f}"


def table(headers, rows):
    return (
        "<table><thead><tr>"
        + "".join(f"<th>{html.escape(str(h))}</th>" for h in headers)
        + "</tr></thead><tbody>"
        + "".join(
            "<tr>" + "".join(f"<td>{html.escape(str(c))}</td>" for c in row) + "</tr>"
            for row in rows
        )
        + "</tbody></table>"
    )


def metric_rows(overall):
    rows = []
    for name, model in overall["models"].items():
        ci, top = model["ap_interval"], model["top_budgets"]["0.1"]
        rows.append(
            [
                NAMES.get(name, name),
                fmt(model["average_precision"]),
                f"[{fmt(ci['lower'])}, {fmt(ci['upper'])}]",
                fmt(model["log_loss"]),
                fmt(model["brier_score"]),
                fmt(model["ece_10_bins"]),
                fmt(top["capture"], True),
                fmt(top["lift"]),
            ]
        )
    return rows


def reliability_chart(overall):
    # Native vector chart embedded in the report; no CDN or plotting dependency.
    svg = [
        '<svg viewBox="0 0 500 340" role="img" aria-label="Calibration reliability diagram">',
        '<path d="M50 20V290H470 M50 290L470 20" fill="none" stroke="#bdc8cb"/>',
    ]
    for name, model in overall["models"].items():
        color = COLORS[name]
        points = " ".join(
            f"{50 + 420 * b['mean_probability']:.2f},{290 - 270 * b['observed_fraction']:.2f}"
            for b in model["reliability"]
            if b["rows"]
        )
        svg.append(f'<polyline points="{points}" fill="none" stroke="{color}" stroke-width="2"/>')
        for b in model["reliability"]:
            if b["rows"]:
                svg.append(
                    f'<circle cx="{50 + 420 * b["mean_probability"]:.2f}" cy="{290 - 270 * b["observed_fraction"]:.2f}" r="4" fill="{color}"><title>{html.escape(NAMES[name])}: n={b["rows"]}, predicted={b["mean_probability"]:.3f}, observed={b["observed_fraction"]:.3f}</title></circle>'
                )
    svg += [
        '<text x="50" y="309">0</text><text x="460" y="309">1</text><text x="20" y="25">1</text><text x="20" y="292">0</text><text x="160" y="332">Mean predicted probability</text><text x="50" y="14">Observed dormancy fraction</text></svg>'
    ]
    legend = " ".join(
        f'<span style="color:{COLORS[n]}">● {html.escape(NAMES[n])}</span>'
        for n in overall["models"]
    )
    return "".join(svg) + f'<p class="legend">{legend}</p>'


def build_report(run_refs, validation_ref, output, *, hosted_ref=None):
    runs, evidence, source_hashes = {}, [], {}
    for folder, expected in run_refs:
        path = folder / "manifest.json"
        if file_hash(path) != expected:
            raise ValueError("report source manifest changed")
        manifest = json.loads(path.read_text())
        if (
            manifest.get("status") != "complete"
            or manifest.get("phase") != "M4_final"
            or manifest.get("classification") != "synthetic"
            or not manifest.get("test_scored")
        ):
            raise ValueError("report requires completed synthetic final runs")
        if file_hash(folder / "evaluation.json") != manifest["evaluation_sha256"]:
            raise ValueError("report evaluation changed")
        result = json.loads((folder / "evaluation.json").read_text())
        key = (result["generator_seed"], result["regime"])
        if (
            key in runs
            or result["regime"] != manifest["regime"]
            or result["plan_sha256"] != manifest["plan_sha256"]
        ):
            raise ValueError("duplicate or mismatched report cohort")
        runs[key] = (result, manifest)
        source_hashes[key] = expected
        evidence.append(
            {
                "run": str(folder),
                "manifest_sha256": expected,
                "evaluation_sha256": manifest["evaluation_sha256"],
            }
        )
    if set(runs) != {
        (seed, regime) for seed in (3501, 3502, 3503) for regime in ("temporal", "random_reference")
    }:
        raise ValueError("report requires both regimes for all three frozen seeds")
    validation_folder, validation_hash = validation_ref
    if file_hash(validation_folder / "manifest.json") != validation_hash:
        raise ValueError("validation evidence changed")
    vm = json.loads((validation_folder / "manifest.json").read_text())
    if (
        vm.get("status") != "complete"
        or vm.get("phase") != "M4_validation_only"
        or vm.get("test_scored") is not False
        or file_hash(validation_folder / "evaluation.json") != vm["evaluation_sha256"]
    ):
        raise ValueError("invalid validation evidence")
    validation = json.loads((validation_folder / "evaluation.json").read_text())
    hosted = None
    hosted_source = None
    if hosted_ref is not None:
        folder, expected = hosted_ref
        if file_hash(folder / "manifest.json") != expected:
            raise ValueError("hosted comparison manifest changed")
        hm = json.loads((folder / "manifest.json").read_text())
        primary_manifest = runs[(3501, "temporal")][1]
        if (
            hm.get("status") != "complete"
            or hm.get("phase") != "M4_hosted_final_comparison"
            or hm.get("classification") != "synthetic"
            or hm.get("evidence") != "live_verified"
            or hm.get("test_scored") is not True
            or hm.get("plan_sha256") != primary_manifest["plan_sha256"]
            or hm.get("local_manifest_sha256") != source_hashes[(3501, "temporal")]
            or file_hash(folder / "evaluation.json") != hm["evaluation_sha256"]
        ):
            raise ValueError("verified matching hosted comparison required")
        hosted = json.loads((folder / "evaluation.json").read_text())
        if (
            hosted["generator_seed"] != 3501
            or hosted["regime"] != "temporal"
            or hosted["plan_sha256"] != primary_manifest["plan_sha256"]
            or hosted["split_audit"] != runs[(3501, "temporal")][0]["split_audit"]
        ):
            raise ValueError("hosted comparison cohort differs")
        hosted_source = {
            "run": str(folder),
            "manifest_sha256": expected,
            "evaluation_sha256": hm["evaluation_sha256"],
            "hosted_manifest_sha256": hm["hosted_manifest_sha256"],
        }
    sections, gaps = [], {}
    headers = [
        "Model",
        "AP ↑",
        "95% AP interval",
        "Log loss ↓",
        "Brier ↓",
        "ECE ↓",
        "10% capture ↑",
        "10% lift ↑",
    ]
    for seed in (3501, 3502, 3503):
        temporal, tm = runs[(seed, "temporal")]
        reference, rm = runs[(seed, "random_reference")]
        if tm["plan_sha256"] != rm["plan_sha256"] or tm["input_files"] != rm["input_files"]:
            raise ValueError("regimes use different frozen plans or inputs")
        main = temporal["evaluations"]["test"]["overall"]
        diagnostic = reference["evaluations"]["test"]["overall"]
        body = [
            f'<section id="seed-{seed}"><h2>Seed {seed} · final temporal test</h2>',
            "<p>Later customers, disjoint from training and validation. Fixed recipes; no test-driven tuning. TabPFN-3.5-Plus final predictions are pending a separate upload/token approval.</p>",
            table(headers, metric_rows(main)),
            "<h3>Reliability of local test probabilities</h3>",
            reliability_chart(main),
        ]
        audits = []
        for label, data in (("Temporal", temporal), ("Random reference", reference)):
            for partition, stats in data["split_audit"]["partitions"].items():
                audits.append(
                    [
                        label,
                        partition,
                        stats["rows"],
                        stats["customers"],
                        stats["positives"],
                        fmt(stats["dormancy_rate"], True),
                    ]
                )
        body += [
            "<h3>Cohorts and overlap</h3>",
            table(["Regime", "Partition", "Rows", "Customers", "Positives", "Prevalence"], audits),
        ]
        body.append(
            table(
                [
                    "Regime",
                    "Train / validation overlap",
                    "Train / test overlap",
                    "Validation / test overlap",
                ],
                [
                    [
                        label,
                        *[
                            data["split_audit"]["customer_overlap_counts"][k]
                            for k in ("train__validation", "train__test", "validation__test")
                        ],
                    ]
                    for label, data in (("Temporal", temporal), ("Random reference", reference))
                ],
            )
        )
        body += [
            '<h3>Random-row reference · diagnostic only</h3><p class="notice">This split mixes dates and allows customer overlap. Differences combine leakage, time shift and cohort composition; they are not causal effects or deployment-valid estimates.</p>',
            table(headers, metric_rows(diagnostic)),
        ]
        gap_rows, gaps[str(seed)] = [], {}
        for name, model in main["models"].items():
            other = diagnostic["models"][name]
            delta = {
                key: other[key] - model[key]
                for key in ("average_precision", "log_loss", "brier_score", "ece_10_bins")
            }
            for q in ("0.05", "0.1"):
                for metric in ("capture", "lift"):
                    delta[f"{metric}_{q}"] = (
                        other["top_budgets"][q][metric] - model["top_budgets"][q][metric]
                    )
            gaps[str(seed)][name] = delta
            gap_rows.append(
                [
                    NAMES[name],
                    *[
                        f"{delta[k]:+.4f}"
                        for k in (
                            "average_precision",
                            "log_loss",
                            "brier_score",
                            "ece_10_bins",
                            "capture_0.1",
                            "lift_0.1",
                        )
                    ],
                ]
            )
        body += [
            "<h3>Signed random-minus-temporal differences</h3>",
            table(
                [
                    "Model",
                    "AP (+ better)",
                    "Log loss (− better)",
                    "Brier (− better)",
                    "ECE (− better)",
                    "10% capture (+ better)",
                    "10% lift (+ better)",
                ],
                gap_rows,
            ),
        ]
        slices = []
        for field, categories in temporal["evaluations"]["test"]["slices"].items():
            for category, cohort in categories.items():
                for name, model in cohort["models"].items():
                    ci = model["ap_interval"]
                    slices.append(
                        [
                            f"{field}: {category}",
                            NAMES[name],
                            cohort["customers"],
                            model["positives"],
                            fmt(model["average_precision"]),
                            f"[{fmt(ci['lower'])}, {fmt(ci['upper'])}]",
                            str(model["sparse"]).lower(),
                        ]
                    )
        body += [
            "<details><summary>Explore local temporal-test subgroups</summary><p>Different subgroup prevalences affect AP. Intervals are exploratory and conditional on fitted models.</p>",
            table(
                ["Slice", "Model", "Customers", "Positives", "AP", "95% interval", "Sparse"], slices
            ),
            "</details>",
        ]
        timings = []
        for label, manifest in (("Temporal", tm), ("Random reference", rm)):
            for name, model in manifest["models"].items():
                t = model["timing_summary"]

                def timing(key):
                    v = t[key]
                    return f"{v['median']:.3f} [{v['min']:.3f}, {v['max']:.3f}]"

                timings.append(
                    [
                        label,
                        NAMES[name],
                        timing("imports_seconds"),
                        timing("load_verify_seconds"),
                        timing("estimator_fit_seconds"),
                        timing("test_estimator_predict_seconds"),
                        timing("process_wall_seconds"),
                    ]
                )
        body += [
            "<h3>Timing · median [min, max] seconds</h3><p>Three sequential fresh Python processes per model and regime; one model thread. OS file caches were not flushed. Test prediction precedes validation. Process wall time includes imports, input checks, transforms, metrics and writes. Full preprocessing times are preserved in the JSON evidence.</p>",
            table(
                [
                    "Regime",
                    "Model",
                    "Imports",
                    "Load / verify",
                    "Estimator fit",
                    "Test estimator predict",
                    "Process wall",
                ],
                timings,
            ),
            "</section>",
        ]
        sections.append("".join(body))
    output.mkdir(parents=True, exist_ok=False)
    summary = {
        "classification": "synthetic",
        "status": "final_complete" if hosted is not None else "local_final_complete_hosted_pending",
        "hosted_final_source": hosted_source,
        "sources": evidence,
        "validation_source_manifest_sha256": validation_hash,
        "random_minus_temporal": gaps,
        "api_requests_in_report_build": 0,
    }
    write_json(output / "report.json", summary)
    page = """<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>SCUBA · Final local evaluation</title><style>body{margin:0;background:#f3f6f5;color:#203335;font:16px/1.5 system-ui,sans-serif}main{max-width:1240px;margin:auto;padding:36px}h1{font-size:42px;letter-spacing:-1.5px}h2{margin-top:44px}h3{margin-top:28px}section{background:white;border:1px solid #d5e0dd;padding:24px;margin:24px 0;border-radius:12px;overflow:auto}table{border-collapse:collapse;width:100%;font-size:13px;margin:20px 0;font-variant-numeric:tabular-nums}th,td{text-align:left;padding:10px;border-bottom:1px solid #dbe3e0}th{background:#e9f2ef}svg{width:min(100%,560px);display:block;background:#fff}svg text{font:12px system-ui;fill:#526466}.notice{border-left:4px solid #bd7725;padding:12px;background:#fff4df}.badge{color:#116959;text-transform:uppercase;letter-spacing:2px;font-weight:700}nav a{display:inline-block;padding:9px 16px;margin-right:8px;background:#164f48;color:white;border-radius:5px;text-decoration:none}.legend{font-size:13px;max-width:600px}.legend span{display:inline-block;margin-right:12px}details{border:1px solid #d5e0dd;padding:12px}summary{cursor:pointer;font-weight:600}footer{font-size:13px;color:#586b68}</style><main><div class="badge">SCUBA · entirely synthetic</div><h1>Final local evaluation</h1><p>Fictional mobile-money dormancy, frozen model recipes, and explicit integration evidence.</p><p class="notice">Local test and diagnostic runs are complete. TabPFN-3.5-Plus is shown below for validation only; its final test result is not available. M4 remains in progress while that comparison is pending.</p><nav><a href="#seed-3501">Primary seed</a><a href="#seed-3502">Seed 3502</a><a href="#seed-3503">Seed 3503</a></nav>"""
    page += (
        "<section><h2>Existing primary validation · distinct from final test</h2><p>Saved validation predictions, including the accepted hosted response. Higher observed TabPFN-3.5-Plus AP did not establish a clear lead: paired intervals against both tree comparators included zero.</p>"
        + table(headers, metric_rows(validation["overall"]))
        + "</section>"
        + (hosted_section(hosted, headers) if hosted is not None else "")
        + "".join(sections)
    )
    page += (
        "<footer><p>AP intervals use 1,000 customer-cluster bootstrap draws, seed 4401. No recalibration or test-driven tuning. Synthetic results demonstrate an evaluation workflow, not real-world performance or intervention value. Fast/Thinking and hosted sensitivity runs have no approved budgets.</p><details><summary>Source integrity records</summary><pre>"
        + html.escape(json.dumps(summary, indent=2))
        + "</pre></details></footer></main></html>"
    )
    if hosted is not None:
        page = page.replace("Final local evaluation", "Final evaluation")
        page = page.replace(
            "Local test and diagnostic runs are complete. TabPFN-3.5-Plus is shown below for validation only; its final test result is not available. M4 remains in progress while that comparison is pending.",
            "M4 evaluation is complete for the approved scope. Primary TabPFN-3.5-Plus and local final-test results are verified. TabPFN-3.5-Plus has higher observed AP, but paired intervals against both tree models include zero. Additional hosted variants, random-reference and sensitivity runs were not budgeted.",
        ).replace(
            "TabPFN-3.5-Plus final predictions are pending a separate upload/token approval.",
            "TabPFN-3.5-Plus is compared separately on the primary seed only; no hosted sensitivity budget was approved.",
        )
    (output / "index.html").write_text(page)
    write_json(
        output / "manifest.json",
        {
            "status": "complete",
            "classification": "synthetic",
            "sources": evidence,
            "html_sha256": file_hash(output / "index.html"),
            "report_sha256": file_hash(output / "report.json"),
        },
    )
    return summary


def hosted_section(result, headers):
    overall = result["overall"]
    pairs = []
    for pair in overall["paired_comparisons"].values():
        interval = pair["interval"]
        pairs.append(
            [
                NAMES[pair["candidate"]] + " minus " + NAMES[pair["reference"]],
                fmt(pair["ap_difference"]),
                f"[{fmt(interval['lower'])}, {fmt(interval['upper'])}]",
            ]
        )
    errors = []
    for name, model in overall["models"].items():
        c = model["threshold_0.5"]
        errors.append(
            [
                NAMES[name],
                model["top_budgets"]["0.05"]["tp"],
                model["top_budgets"]["0.1"]["tp"],
                c["tp"],
                c["fp"],
                c["fn"],
                c["tn"],
            ]
        )
    slices = []
    for field, categories in result["slices"].items():
        for category, cohort in categories.items():
            model = cohort["models"]["hosted_plus"]
            ci = model["ap_interval"]
            slices.append(
                [
                    field + ": " + category,
                    cohort["customers"],
                    model["positives"],
                    fmt(model["average_precision"]),
                    f"[{fmt(ci['lower'])}, {fmt(ci['upper'])}]",
                    fmt(model["top_budgets"]["0.1"]["capture"], True),
                    str(model["sparse"]).lower(),
                ]
            )
    integration = result["integration"]
    stages = [
        [stage["stage"], f"{stage['elapsed_seconds']:.3f}"] for stage in integration["stages"]
    ]
    return (
        '<section id="hosted-final"><h2>Primary final test · TabPFN-3.5-Plus and local models</h2>'
        "<p>Same 2,260 unseen synthetic customers and 233 positives. Raw probabilities and frozen recipes. Paired intervals measure evaluation-customer uncertainty conditional on these fitted models.</p>"
        + table(headers, metric_rows(overall))
        + "<h3>Paired AP differences</h3>"
        + table(["Comparison", "AP difference", "95% paired interval"], pairs)
        + "<h3>Reliability of final-test probabilities</h3>"
        + reliability_chart(overall)
        + "<h3>Capture and errors</h3><p>Top 5% selects 113 customers; top 10% selects 226. Captured counts are out of 233 positives. TP, FP, FN and TN below use the frozen 0.5 threshold.</p>"
        + table(["Model", "5% captured", "10% captured", "TP", "FP", "FN", "TN"], errors)
        + "<details><summary>Explore TabPFN-3.5-Plus test subgroups</summary><p>Exploratory intervals; budgets are selected within each slice. Complete local and paired subgroup comparisons are preserved in the evaluation JSON.</p>"
        + table(
            ["Slice", "Customers", "Positives", "AP", "95% interval", "10% capture", "Sparse"],
            slices,
        )
        + "</details><h3>Hosted integration observations</h3>"
        + "<p>One approved test-feature upload and one prediction reused the existing fitted resource. No new training upload or refit. Latency is a single observation, not a controlled timing comparison with local fits.</p>"
        + table(["Request stage", "Observed seconds"], stages)
        + "<p>Fresh estimate: "
        + str(integration["fresh_preflight"]["estimated_total_tokens"])
        + " tokens. Approved estimate ceiling: "
        + str(integration["approved_estimate_budget"])
        + " tokens. Actual charges are unavailable in the response. Server-reported checkpoint: "
        + html.escape(integration["checkpoint_identity"]["reported_model_path"])
        + ". Checkpoint bytes were not independently attested. No further API calls were used for evaluation.</p></section>"
    )
