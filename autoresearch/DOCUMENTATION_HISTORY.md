# History Module Documentation

## Overview

The history module (`history.py`) manages the append-only experiment log
(`experiments.jsonl`). This is the single source of truth for all iterations.

## DesignDoc Reference

See DesignDoc.md sections:
- **2.2**: Append-only experiment log
- **2.3**: Crash- and Ctrl+C-safe
- **6**: History rendering: compact vs full

## Key Features

### 1. Append-Only Log

- Every iteration writes exactly one JSON line
- Earlier lines are NEVER rewritten
- All higher-level views are derived from this log

### 2. Resumability

- Lose the report? Regenerate from the log
- Every claimed improvement has single-line provenance
- Time-travel: replay state at any historical point

### 3. History Rendering

- **Full format**: Artifact text + all metrics + summary (for recent/best)
- **Compact format**: One line per entry (for older iterations)

## Log Entry Schema

```json
{
  "iter": 47,
  "batch": 10,
  "ts": "2024-01-15T14:30:00",
  "artifact_hash": "a1b2c3d4e5f67890",
  "parent": 42,
  "plan_id": "add_length_constraint",
  "rationale": "Adding length constraint to prevent verbose answers",
  "artifact": "Full prompt text here...",
  "metrics_train": {"kappa": 0.340, "f1": 0.420, "spearman": 0.290},
  "metrics_dev": {"kappa": 0.335, "f1": 0.412, "spearman": 0.287},
  "metrics_test": {"kappa": 0.274, "f1": 0.380, "spearman": 0.250},
  "stage_a_summary": "Judge penalizes long answers even when justified"
}
```

## API

### `append_entry(entry: ExperimentEntry) -> None`

Append a single entry to the log. Atomic operation.

```python
from autoresearch.history import ExperimentEntry, append_entry

entry = ExperimentEntry(
    iter=1,
    batch=1,
    ts=datetime.now().isoformat(),
    artifact_hash="abc123",
    parent=None,
    plan_id="initial",
    rationale="Initial prompt",
    artifact="My prompt...",
    metrics_train={"kappa": 0.3, ...},
    metrics_dev={"kappa": 0.25, ...},
    metrics_test={"kappa": 0.2, ...},
)
append_entry(entry)
```

### `read_log() -> list[ExperimentEntry]`

Read all entries from the log.

### `get_entry_by_iter(iter_num: int) -> ExperimentEntry | None`

Get a specific entry by iteration number.

### `get_best_entry_by_dev_kappa() -> ExperimentEntry | None`

Get the entry with the best dev kappa.

### `get_entries_by_batch(batch_num: int) -> list[ExperimentEntry]`

Get all entries for a specific batch.

### `get_last_iteration() -> int`

Get the last iteration number (0 if empty).

### `get_last_batch() -> int`

Get the last batch number (0 if empty).

## History Rendering

### `render_history_compact(entries, full_count=5) -> str`

Render history for LLM context:
- Best so far: Full text
- Last N iterations: Full text
- Everything else: One line

```python
from autoresearch.history import read_log, render_history_compact

entries = read_log()
history_text = render_history_compact(entries, full_count=5)
# Use history_text in LLM prompt
```

### `render_entry_full(entry) -> str`

Render a single entry with full artifact.

### `render_entry_compact(entry) -> str`

Render a single entry in compact format.

## Plan Statistics

### `get_plan_statistics(entries) -> dict`

Compute aggregate stats per plan_id:

```python
{
  "add_length_constraint": {
    "proposed": 3,
    "won": 1,
    "mean_delta_dev": -0.018,
  },
  "improve_clarity": {
    "proposed": 2,
    "won": 2,
    "mean_delta_dev": 0.025,
  },
}
```

## Usage in Main Loop

```python
from autoresearch.history import (
    append_entry,
    read_log,
    get_last_iteration,
    render_history_compact,
)

# At start of loop
last_iter = get_last_iteration()

# After scoring and diagnosing
entry = ExperimentEntry(
    iter=last_iter + 1,
    batch=current_batch,
    ...
)
append_entry(entry)

# For next iteration's context
entries = read_log()
history = render_history_compact(entries)
```
