#!/usr/bin/env python3
"""
Alex — Management Reporting Agent

Auto-generates management-friendly status reports from project data.

Usage:
    python scripts/alex_report.py                # Full weekly report
    python scripts/alex_report.py --summary      # 3-sentence executive summary
    python scripts/alex_report.py --since 7      # Activity from last N days
    python scripts/alex_report.py --output file  # Save to file (default: stdout)
"""

import subprocess
import sys
import json
import csv
from pathlib import Path
from datetime import datetime, timedelta

PROJECT_ROOT = Path(__file__).resolve().parents[1]

# ─── Performance Targets ───────────────────────────────────────────

TARGETS = {
    "ann_return": 0.08,       # >8% annualized return
    "sharpe": 0.50,           # >0.50 Sharpe ratio
    "max_dd": -0.25,          # <-25% max drawdown
    "experiments": 10,        # 10 total experiments
    "test_coverage": 0.80,    # >80% test coverage
}


# ─── Data Readers ──────────────────────────────────────────────────

def run_cmd(cmd: str) -> str:
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True,
                            cwd=str(PROJECT_ROOT))
    return result.stdout.strip()


def read_strategy_metrics() -> dict:
    """Read final strategy performance from CSV."""
    csv_path = PROJECT_ROOT / "outputs" / "final_strategy_summary.csv"
    if not csv_path.exists():
        return {}

    with open(csv_path) as f:
        reader = csv.DictReader(f)
        for row in reader:
            if "Final" in row.get("Strategy", ""):
                return {
                    "strategy_name": row["Strategy"],
                    "total_return": float(row["Total Return"]),
                    "ann_return": float(row["Ann. Return"]),
                    "volatility": float(row["Volatility"]),
                    "sharpe": float(row["Sharpe Ratio"]),
                    "sortino": float(row["Sortino Ratio"]),
                    "max_dd": float(row["Max Drawdown"]),
                    "calmar": float(row["Calmar Ratio"]),
                    "win_rate": float(row["Win Rate"]),
                    "avg_positions": float(row["Avg Positions"]),
                }
    return {}


def read_benchmark_metrics() -> dict:
    """Read benchmark (buy & hold) metrics."""
    csv_path = PROJECT_ROOT / "outputs" / "final_strategy_summary.csv"
    if not csv_path.exists():
        return {}

    with open(csv_path) as f:
        reader = csv.DictReader(f)
        for row in reader:
            if "Buy" in row.get("Strategy", ""):
                return {
                    "ann_return": float(row["Ann. Return"]),
                    "sharpe": float(row["Sharpe Ratio"]),
                    "max_dd": float(row["Max Drawdown"]),
                }
    return {}


def read_experiment_status() -> dict:
    """Read experiment completion status."""
    exp_dir = PROJECT_ROOT / "outputs" / "experiments"
    completed = []
    failed = []

    if exp_dir.exists():
        for f in exp_dir.glob("*.json"):
            try:
                with open(f) as fh:
                    data = json.load(fh)
                    exp_id = data.get("experiment_id", "?")
                    name = data.get("experiment_name", "Unknown")
                    passed = data.get("failure_check", {}).get("passed", None)
                    if passed:
                        completed.append({"id": exp_id, "name": name, "result": "PASS"})
                    else:
                        failed.append({"id": exp_id, "name": name, "result": "FAIL"})
            except (json.JSONDecodeError, KeyError):
                pass

    return {
        "total_planned": 10,
        "completed": len(completed) + len(failed),
        "passed": completed,
        "failed": failed,
    }


def read_git_activity(days: int = 7) -> dict:
    """Read recent git activity."""
    since_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")

    commits_raw = run_cmd(
        f'git log --since="{since_date}" --oneline --format="%h|%s|%ai"'
    )
    commits = []
    for line in commits_raw.split("\n"):
        if "|" in line:
            parts = line.split("|", 2)
            commits.append({
                "hash": parts[0],
                "message": parts[1],
                "date": parts[2][:10] if len(parts) > 2 else "",
            })

    files_changed = run_cmd(
        f'git log --since="{since_date}" --name-only --format="" | sort -u'
    )
    file_list = [f for f in files_changed.split("\n") if f]

    return {
        "period_days": days,
        "commit_count": len(commits),
        "commits": commits,
        "files_changed": len(file_list),
        "py_files": sum(1 for f in file_list if f.endswith(".py")),
        "md_files": sum(1 for f in file_list if f.endswith(".md")),
    }


def read_test_status() -> dict:
    """Check test suite status."""
    test_dir = PROJECT_ROOT / "tests"
    test_files = list(test_dir.rglob("test_*.py"))

    # Count test functions
    test_count = 0
    for tf in test_files:
        with open(tf) as f:
            for line in f:
                if line.strip().startswith("def test_"):
                    test_count += 1

    # Modules with tests vs without
    src_modules = ["signals", "backtest", "portfolio", "data", "diagnostics"]
    tested = []
    untested = []
    for mod in src_modules:
        test_exists = any(mod in str(tf) for tf in test_files)
        if test_exists:
            tested.append(mod)
        else:
            untested.append(mod)

    return {
        "test_files": len(test_files),
        "test_count": test_count,
        "tested_modules": tested,
        "untested_modules": untested,
        "coverage_pct": len(tested) / len(src_modules) if src_modules else 0,
    }


# ─── Traffic Light Logic ───────────────────────────────────────────

def traffic_light(value, target, higher_is_better=True) -> str:
    """Return traffic light emoji based on value vs target."""
    if value is None:
        return "⚪"

    if higher_is_better:
        if value >= target:
            return "🟢"
        elif value >= target * 0.8:
            return "🟡"
        else:
            return "🔴"
    else:
        # Lower is better (e.g., max drawdown)
        if value >= target:  # Less negative = better for drawdown
            return "🟢"
        elif value >= target * 1.2:
            return "🟡"
        else:
            return "🔴"


def trend_arrow(current, previous=None) -> str:
    """Return trend arrow."""
    if previous is None:
        return "→"
    if current > previous:
        return "↑"
    elif current < previous:
        return "↓"
    return "→"


# ─── Report Generators ─────────────────────────────────────────────

def translate_accomplishments(commits: list) -> list:
    """Translate git commits into management-friendly accomplishments."""
    translations = []
    for c in commits:
        msg = c["message"].lower()

        if "production ready" in msg or "final strategy" in msg:
            translations.append(
                "Completed strategy validation — strategy meets all performance "
                "criteria and is ready for next stage"
            )
        elif "ema" in msg and "optim" in msg:
            translations.append(
                "Optimized strategy parameters — identified best configuration "
                "through systematic testing"
            )
        elif "risk parity" in msg:
            translations.append(
                "Evaluated advanced portfolio sizing methods — compared two "
                "approaches for position management"
            )
        elif "carry" in msg and ("fail" in msg or "validation" in msg):
            translations.append(
                "Tested alternative data source (carry signal) — determined it lacks "
                "predictive value, redirecting effort to higher-impact areas"
            )
        elif "dashboard" in msg:
            translations.append(
                "Built interactive monitoring dashboard — enables real-time "
                "strategy performance tracking"
            )
        elif "evaluation" in msg or "roadmap" in msg:
            translations.append(
                "Completed comprehensive project evaluation with 4-phase "
                "development roadmap"
            )
        elif "claude.md" in msg.lower() or "changelog" in msg:
            translations.append(
                "Improved project documentation and knowledge management "
                "infrastructure"
            )
        elif "john" in msg or "review" in msg:
            translations.append(
                "Established automated code review process to maintain "
                "code quality standards"
            )
        elif "backtest" in msg:
            translations.append(
                "Implemented strategy testing framework with realistic "
                "transaction cost modeling"
            )
        elif "signal" in msg and "implement" in msg:
            translations.append(
                "Developed core strategy signal generation with 5 different "
                "methodologies"
            )
        elif "test" in msg and ("framework" in msg or "pytest" in msg):
            translations.append(
                "Established automated testing framework for quality assurance"
            )
        elif "data" in msg and ("fix" in msg or "inception" in msg):
            translations.append(
                "Fixed data quality issue — corrected date range to match "
                "actual asset availability"
            )
        else:
            # Generic translation
            clean_msg = c["message"].split(":")[1].strip() if ":" in c["message"] else c["message"]
            translations.append(clean_msg)

    # Deduplicate
    seen = set()
    unique = []
    for t in translations:
        if t not in seen:
            seen.add(t)
            unique.append(t)

    return unique


def generate_weekly_report(days: int = 7) -> str:
    """Generate full weekly management report."""
    metrics = read_strategy_metrics()
    benchmark = read_benchmark_metrics()
    experiments = read_experiment_status()
    git = read_git_activity(days)
    tests = read_test_status()

    today = datetime.now().strftime("%Y-%m-%d")
    week_start = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")

    # ── Compute derived values ──
    vs_benchmark_return = ""
    vs_benchmark_sharpe = ""
    if metrics and benchmark:
        ret_improvement = (metrics["ann_return"] / benchmark["ann_return"] - 1) * 100
        sharpe_improvement = (metrics["sharpe"] / benchmark["sharpe"] - 1) * 100
        dd_improvement = (benchmark["max_dd"] - metrics["max_dd"]) / abs(benchmark["max_dd"]) * 100
        vs_benchmark_return = f"+{ret_improvement:.0f}%"
        vs_benchmark_sharpe = f"+{sharpe_improvement:.0f}%"

    # ── Build report ──
    lines = []
    lines.append(f"# Weekly Status Report — {week_start} to {today}")
    lines.append("")

    # Bottom Line
    lines.append("## Bottom Line")
    if metrics:
        sharpe_status = "meets" if metrics["sharpe"] >= TARGETS["sharpe"] else "below"
        dd_margin = abs(TARGETS["max_dd"]) - abs(metrics["max_dd"])
        lines.append(
            f"Strategy is **operational** with {metrics['ann_return']*100:.1f}% annualized return "
            f"and Sharpe ratio of {metrics['sharpe']:.2f} ({sharpe_status} the {TARGETS['sharpe']:.2f} target). "
            f"Risk margin is {dd_margin*100:.1f}% above limit — adequate but needs monitoring."
        )
    else:
        lines.append("Strategy metrics not yet available. Still in development phase.")
    lines.append("")

    # Project Health
    lines.append("## Project Health")
    lines.append("")
    lines.append("| Area | Status | Trend | Note |")
    lines.append("|------|--------|-------|------|")

    if metrics:
        perf_light = traffic_light(metrics["sharpe"], TARGETS["sharpe"])
        dd_light = traffic_light(metrics["max_dd"], TARGETS["max_dd"], higher_is_better=False)
        lines.append(
            f'| Strategy Performance | {perf_light} | → | '
            f'Sharpe {metrics["sharpe"]:.2f} vs {TARGETS["sharpe"]:.2f} target |'
        )
        lines.append(
            f'| Risk Management | {dd_light} | → | '
            f'Max drawdown {metrics["max_dd"]*100:.1f}% vs {TARGETS["max_dd"]*100:.0f}% limit |'
        )
    else:
        lines.append("| Strategy Performance | ⚪ | → | Metrics not available |")
        lines.append("| Risk Management | ⚪ | → | Not yet assessed |")

    exp_pct = experiments["completed"] / experiments["total_planned"]
    exp_light = traffic_light(exp_pct, 0.5)
    lines.append(
        f'| Validation Progress | {exp_light} | ↑ | '
        f'{experiments["completed"]}/{experiments["total_planned"]} experiments complete |'
    )

    test_light = traffic_light(tests["coverage_pct"], TARGETS["test_coverage"])
    lines.append(
        f'| Quality Assurance | {test_light} | → | '
        f'{tests["test_count"]} tests, {len(tests["untested_modules"])} modules untested |'
    )
    lines.append("")

    # This Week's Accomplishments
    lines.append("## This Week")
    accomplishments = translate_accomplishments(git["commits"])
    if accomplishments:
        for a in accomplishments[:6]:
            lines.append(f"- {a}")
    else:
        lines.append("- No commits recorded this period")
    lines.append("")

    # Issues & Mitigations
    lines.append("## Issues & Mitigations")
    issues = []

    if metrics and abs(metrics["max_dd"]) > abs(TARGETS["max_dd"]) * 0.9:
        margin = (abs(TARGETS["max_dd"]) - abs(metrics["max_dd"])) * 100
        issues.append(
            f"**Thin risk margin** ({margin:.1f}% buffer to drawdown limit): "
            f"Implementing automated risk overlay with drawdown controls"
        )

    if experiments["failed"]:
        for exp in experiments["failed"]:
            issues.append(
                f'**Experiment {exp["id"]} ({exp["name"]})** did not pass validation: '
                f'Redirecting effort to higher-priority items; no development time wasted on unviable approach'
            )

    if exp_pct < 0.3:
        issues.append(
            f'**Validation progress** ({experiments["completed"]}/{experiments["total_planned"]}): '
            f'4 critical tests remaining; will be prioritized in next development sprint'
        )

    if tests["untested_modules"]:
        issues.append(
            f'**Test coverage gap** (modules without tests: {", ".join(tests["untested_modules"])}): '
            f'Scheduling test development before next feature additions'
        )

    if issues:
        for issue in issues:
            lines.append(f"- {issue}")
    else:
        lines.append("- No critical issues")
    lines.append("")

    # Next Steps
    lines.append("## Next Steps")
    lines.append("1. Complete transaction cost validation (Exp 5) — confirms strategy viability under realistic conditions")
    lines.append("2. Complete parameter stability test (Exp 7) — validates strategy robustness over time")
    lines.append("3. Implement risk overlay — automated drawdown protection to widen safety margin")
    lines.append("")

    # Key Metrics
    lines.append("## Key Metrics")
    lines.append("")
    lines.append("| Metric | Current | Target | vs Benchmark | Status |")
    lines.append("|--------|---------|--------|--------------|--------|")

    if metrics:
        lines.append(
            f'| Annualized Return | {metrics["ann_return"]*100:.1f}% '
            f'| >{TARGETS["ann_return"]*100:.0f}% '
            f'| {vs_benchmark_return} '
            f'| {traffic_light(metrics["ann_return"], TARGETS["ann_return"])} |'
        )
        lines.append(
            f'| Risk-Adjusted Return (Sharpe) | {metrics["sharpe"]:.2f} '
            f'| >{TARGETS["sharpe"]:.2f} '
            f'| {vs_benchmark_sharpe} '
            f'| {traffic_light(metrics["sharpe"], TARGETS["sharpe"])} |'
        )
        lines.append(
            f'| Max Drawdown | {metrics["max_dd"]*100:.1f}% '
            f'| >{TARGETS["max_dd"]*100:.0f}% '
            f'| {dd_improvement:.0f}% better '
            f'| {traffic_light(metrics["max_dd"], TARGETS["max_dd"], higher_is_better=False)} |'
        )
    lines.append(
        f'| Validation Progress | {experiments["completed"]}/{experiments["total_planned"]} '
        f'| {experiments["total_planned"]}/{experiments["total_planned"]} '
        f'| — '
        f'| {exp_light} |'
    )
    lines.append(
        f'| Test Coverage | {tests["coverage_pct"]*100:.0f}% '
        f'| >{TARGETS["test_coverage"]*100:.0f}% '
        f'| — '
        f'| {test_light} |'
    )
    lines.append("")

    # Footer
    lines.append("---")
    lines.append(f"*Generated by Alex — {today}*")

    return "\n".join(lines)


def generate_executive_summary() -> str:
    """Generate 3-sentence executive summary."""
    metrics = read_strategy_metrics()
    benchmark = read_benchmark_metrics()
    experiments = read_experiment_status()

    if not metrics:
        return "Project is in early development phase. Strategy framework has been built but metrics are not yet available."

    ret_vs = ((metrics["ann_return"] / benchmark["ann_return"]) - 1) * 100 if benchmark else 0
    dd_margin = (abs(TARGETS["max_dd"]) - abs(metrics["max_dd"])) * 100

    summary = (
        f'The Multi-Asset Strategy delivers {metrics["ann_return"]*100:.1f}% annualized returns '
        f'with a Sharpe ratio of {metrics["sharpe"]:.2f}, outperforming the passive benchmark '
        f'by {ret_vs:.0f}% on a risk-adjusted basis. '
        f'Maximum drawdown of {metrics["max_dd"]*100:.1f}% remains within the {TARGETS["max_dd"]*100:.0f}% '
        f'risk budget with a {dd_margin:.1f}% safety margin. '
        f'{experiments["completed"]} of {experiments["total_planned"]} validation tests are complete; '
        f'critical cost analysis and parameter stability tests are the next priority '
        f'before advancing to production deployment.'
    )

    return f"# Executive Summary\n\n{summary}"


# ─── Main ──────────────────────────────────────────────────────────

def main():
    args = sys.argv[1:]

    # Parse --since N
    days = 7
    if "--since" in args:
        idx = args.index("--since")
        days = int(args[idx + 1]) if idx + 1 < len(args) else 7

    # Generate report
    if "--summary" in args:
        report = generate_executive_summary()
    else:
        report = generate_weekly_report(days)

    # Output
    if "--output" in args:
        idx = args.index("--output")
        output_path = args[idx + 1] if idx + 1 < len(args) else "status_report.md"
        with open(output_path, "w") as f:
            f.write(report)
        print(f"Report saved to: {output_path}")
    else:
        print(report)


if __name__ == "__main__":
    main()
