"""
Append-only experiment log management.

See DesignDoc.md section 2.2: "Append-only experiment log"
There is exactly one ground-truth file (experiments.jsonl) where every
iteration writes one JSON line. Earlier lines are NEVER rewritten.

This module provides:
1. Append-only log writing
2. Log reading and filtering
3. History rendering (compact vs full)
"""

import json
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from .paths import EXPERIMENTS_LOG, ensure_directories


@dataclass
class ExperimentEntry:
    """A single entry in the experiment log."""
    iter: int
    batch: int
    ts: str
    artifact_hash: str
    parent: int | None  # Parent iteration number, or None for initial
    plan_id: str
    rationale: str
    artifact: str  # Full artifact text
    metrics_train: dict[str, float]
    metrics_dev: dict[str, float]
    metrics_test: dict[str, float]
    stage_a_summary: str | None = None  # Disagreement generalization
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ExperimentEntry":
        """Create from dictionary."""
        return cls(**data)


def append_entry(entry: ExperimentEntry) -> None:
    """
    Append a single entry to the experiment log.
    
    This is an atomic operation - the entry is written as a single line.
    See DesignDoc.md section 2.3: "Crash- and Ctrl+C-safe"
    """
    ensure_directories()
    
    with open(EXPERIMENTS_LOG, "a") as f:
        f.write(json.dumps(entry.to_dict()) + "\n")


def read_log() -> list[ExperimentEntry]:
    """Read all entries from the experiment log."""
    if not EXPERIMENTS_LOG.exists():
        return []
    
    entries = []
    with open(EXPERIMENTS_LOG, "r") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    data = json.loads(line)
                    entries.append(ExperimentEntry.from_dict(data))
                except json.JSONDecodeError as e:
                    print(f"Warning: Failed to parse log line: {e}")
    
    return entries


def get_entry_by_iter(iter_num: int) -> ExperimentEntry | None:
    """Get a specific entry by iteration number."""
    entries = read_log()
    for entry in entries:
        if entry.iter == iter_num:
            return entry
    return None


def get_best_entry_by_dev_kappa() -> ExperimentEntry | None:
    """Get the entry with the best dev kappa."""
    entries = read_log()
    if not entries:
        return None
    
    return max(entries, key=lambda e: e.metrics_dev.get("kappa", 0))


def get_entries_by_batch(batch_num: int) -> list[ExperimentEntry]:
    """Get all entries for a specific batch."""
    entries = read_log()
    return [e for e in entries if e.batch == batch_num]


def get_last_iteration() -> int:
    """Get the last iteration number, or 0 if log is empty."""
    entries = read_log()
    if not entries:
        return 0
    return max(e.iter for e in entries)


def get_last_batch() -> int:
    """Get the last batch number, or 0 if log is empty."""
    entries = read_log()
    if not entries:
        return 0
    return max(e.batch for e in entries)


def render_history_compact(
    entries: list[ExperimentEntry],
    full_count: int = 5,
) -> str:
    """
    Render history in compact format for LLM context.
    
    See DesignDoc.md section 6: "History rendering: compact vs full"
    
    - Best-so-far: Full text + metrics + summary
    - Last N iterations: Full text + metrics + summary
    - Everything else: One line per entry
    """
    if not entries:
        return "No previous iterations."
    
    lines = []
    
    # Find best so far
    best = max(entries, key=lambda e: e.metrics_dev.get("kappa", 0))
    
    # Get last N entries
    last_n = entries[-full_count:] if len(entries) >= full_count else entries
    
    # Set of entries to render fully
    full_entries = set(e.iter for e in last_n) | {best.iter}
    
    # Render best so far first
    lines.append("=== BEST SO FAR ===")
    lines.append(render_entry_full(best))
    lines.append("")
    
    # Render in iteration order
    for entry in sorted(entries, key=lambda e: e.iter):
        if entry.iter in full_entries:
            lines.append(render_entry_full(entry))
        else:
            lines.append(render_entry_compact(entry))
    
    return "\n".join(lines)


def render_entry_full(entry: ExperimentEntry) -> str:
    """Render a single entry with full artifact text."""
    metrics_str = f"train: κ={entry.metrics_train.get('kappa', 0):.3f} " \
                  f"dev: κ={entry.metrics_dev.get('kappa', 0):.3f} " \
                  f"test: κ={entry.metrics_test.get('kappa', 0):.3f}"
    
    lines = [
        f"--- iter={entry.iter} batch={entry.batch} parent={entry.parent} plan={entry.plan_id} ---",
        f"Rationale: {entry.rationale}",
        f"Metrics: {metrics_str}",
        "Artifact:",
        "<PROMPT>",
        entry.artifact,
        "</PROMPT>",
    ]
    
    if entry.stage_a_summary:
        lines.append(f"Stage-A summary: {entry.stage_a_summary}")
    
    return "\n".join(lines)


def render_entry_compact(entry: ExperimentEntry) -> str:
    """Render a single entry in compact one-line format."""
    return (
        f"iter={entry.iter} batch={entry.batch} parent={entry.parent} "
        f"plan={entry.plan_id} "
        f"train-κ={entry.metrics_train.get('kappa', 0):.3f} "
        f"dev-κ={entry.metrics_dev.get('kappa', 0):.3f} "
        f"test-κ={entry.metrics_test.get('kappa', 0):.3f} "
        f"rationale={entry.rationale[:100]}..."
    )


def get_plan_statistics(entries: list[ExperimentEntry]) -> dict[str, dict[str, Any]]:
    """
    Compute aggregate statistics per plan_id.
    
    Returns dict mapping plan_id to:
    - proposed: Number of times proposed
    - won: Number of times it was the best in its batch
    - mean_delta_dev: Mean delta in dev kappa
    """
    plan_stats: dict[str, dict[str, Any]] = {}
    
    # Group by batch
    batches: dict[int, list[ExperimentEntry]] = {}
    for entry in entries:
        if entry.batch not in batches:
            batches[entry.batch] = []
        batches[entry.batch].append(entry)
    
    # Find winner in each batch
    batch_winners: dict[int, str] = {}
    for batch_num, batch_entries in batches.items():
        best = max(batch_entries, key=lambda e: e.metrics_dev.get("kappa", 0))
        batch_winners[batch_num] = best.plan_id
    
    # Compute stats
    for entry in entries:
        plan = entry.plan_id
        if plan not in plan_stats:
            plan_stats[plan] = {
                "proposed": 0,
                "won": 0,
                "deltas": [],
            }
        
        plan_stats[plan]["proposed"] += 1
        
        if batch_winners.get(entry.batch) == plan:
            plan_stats[plan]["won"] += 1
        
        # Compute delta from parent
        if entry.parent is not None:
            parent = get_entry_by_iter(entry.parent)
            if parent:
                delta = entry.metrics_dev.get("kappa", 0) - parent.metrics_dev.get("kappa", 0)
                plan_stats[plan]["deltas"].append(delta)
    
    # Compute mean deltas
    for plan, stats in plan_stats.items():
        if stats["deltas"]:
            stats["mean_delta_dev"] = sum(stats["deltas"]) / len(stats["deltas"])
        else:
            stats["mean_delta_dev"] = 0.0
        del stats["deltas"]  # Remove raw deltas
    
    return plan_stats
