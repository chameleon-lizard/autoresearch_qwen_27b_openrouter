"""
Report generation from experiment log.

See DesignDoc.md section 8: "Observability"
The report is auto-regenerated after every batch and provides:
- Per-batch tables
- Plan_id aggregate statistics
- Best-so-far callout
"""

from pathlib import Path

from .history import (
    ExperimentEntry,
    read_log,
    get_best_entry_by_dev_kappa,
    get_plan_statistics,
)
from .paths import EXPERIMENTS_REPORT
from .metrics import metrics_to_string


def generate_report() -> str:
    """
    Generate the experiments report from the log.
    
    Returns the report as a string (also saves to EXPERIMENTS_REPORT).
    """
    entries = read_log()
    if not entries:
        return "# Experiments Report\n\nNo experiments recorded yet."
    
    lines = [
        "# Experiments Report",
        "",
        f"*Generated from {len(entries)} iterations across {max(e.batch for e in entries)} batches*",
        "",
    ]
    
    # Best so far
    best = get_best_entry_by_dev_kappa(entries)
    if best:
        lines.extend([
            "## Best So Far",
            "",
            f"**Iteration {best.iter}** (Batch {best.batch}, Plan: `{best.plan_id}`)",
            "",
            f"- **Dev κ**: {best.metrics_dev.get('kappa', 0):.3f}",
            f"- **Train κ**: {best.metrics_train.get('kappa', 0):.3f}",
            f"- **Test κ**: {best.metrics_test.get('kappa', 0):.3f}",
            f"- **Dev-Test Gap**: {best.metrics_dev.get('kappa', 0) - best.metrics_test.get('kappa', 0):.3f}",
            "",
            f"**Rationale**: {best.rationale}",
            "",
            "```",
            best.artifact,
            "```",
            "",
        ])
    
    # Plan statistics
    plan_stats = get_plan_statistics(entries)
    if plan_stats:
        lines.extend([
            "## Plan Statistics",
            "",
            "Aggregate statistics for each proposal type:",
            "",
            "| Plan | Proposed | Won | Win Rate | Mean Δ Dev κ |",
            "|------|----------|-----|----------|--------------|",
        ])
        
        for plan_id, stats in sorted(plan_stats.items(), key=lambda x: -x[1]["mean_delta_dev"]):
            win_rate = stats["won"] / stats["proposed"] * 100
            lines.append(
                f"| `{plan_id}` | {stats['proposed']} | {stats['won']} | {win_rate:.1f}% | "
                f"{stats['mean_delta_dev']:+.3f} |"
            )
        
        lines.append("")
    
    # Per-batch tables
    batches = {}
    for entry in entries:
        if entry.batch not in batches:
            batches[entry.batch] = []
        batches[entry.batch].append(entry)
    
    lines.append("## Batch Details")
    lines.append("")
    
    for batch_num in sorted(batches.keys()):
        batch_entries = batches[batch_num]
        lines.extend([
            f"### Batch {batch_num}",
            "",
            "| Iter | Parent | Plan | Rationale | Train κ | Dev κ | Test κ | Dev-Test Gap |",
            "|------|--------|------|-----------|---------|-------|--------|--------------|",
        ])
        
        for entry in sorted(batch_entries, key=lambda e: e.iter):
            gap = entry.metrics_dev.get("kappa", 0) - entry.metrics_test.get("kappa", 0)
            rationale_short = entry.rationale[:50] + "..." if len(entry.rationale) > 50 else entry.rationale
            lines.append(
                f"| {entry.iter} | {entry.parent or '—'} | `{entry.plan_id}` | {rationale_short} | "
                f"{entry.metrics_train.get('kappa', 0):.3f} | "
                f"{entry.metrics_dev.get('kappa', 0):.3f} | "
                f"{entry.metrics_test.get('kappa', 0):.3f} | "
                f"{gap:+.3f} |"
            )
        
        lines.append("")
    
    # Dev-test gap trend
    lines.extend([
        "## Dev-Test Gap Trend",
        "",
        "Tracking overfitting to dev set:",
        "",
        "| Iter | Dev κ | Test κ | Gap |",
        "|------|-------|--------|-----|",
    ])
    
    for entry in sorted(entries, key=lambda e: e.iter)[-20:]:  # Last 20 iterations
        gap = entry.metrics_dev.get("kappa", 0) - entry.metrics_test.get("kappa", 0)
        lines.append(
            f"| {entry.iter} | {entry.metrics_dev.get('kappa', 0):.3f} | "
            f"{entry.metrics_test.get('kappa', 0):.3f} | {gap:+.3f} |"
        )
    
    lines.append("")
    
    report = "\n".join(lines)
    
    # Save to file
    with open(EXPERIMENTS_REPORT, "w") as f:
        f.write(report)
    
    return report


def print_report_summary() -> None:
    """Print a brief summary of the current state."""
    entries = read_log()
    if not entries:
        print("No experiments recorded yet.")
        return
    
    best = get_best_entry_by_dev_kappa(entries)
    latest = entries[-1]
    
    print(f"\n{'='*60}")
    print(f"Experiments Summary: {len(entries)} iterations, {max(e.batch for e in entries)} batches")
    print(f"{'='*60}")
    
    if best:
        print(f"\nBest (iter {best.iter}):")
        print(f"  Dev κ: {best.metrics_dev.get('kappa', 0):.3f}")
        print(f"  Test κ: {best.metrics_test.get('kappa', 0):.3f}")
        print(f"  Gap: {best.metrics_dev.get('kappa', 0) - best.metrics_test.get('kappa', 0):+.3f}")
    
    print(f"\nLatest (iter {latest.iter}):")
    print(f"  Dev κ: {latest.metrics_dev.get('kappa', 0):.3f}")
    print(f"  Test κ: {latest.metrics_test.get('kappa', 0):.3f}")
    print(f"  Gap: {latest.metrics_dev.get('kappa', 0) - latest.metrics_test.get('kappa', 0):+.3f}")
    print()
