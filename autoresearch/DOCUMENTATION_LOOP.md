# Loop Module Documentation

## Overview

The loop module (`loop.py`) implements the main autoresearch loop that
orchestrates all other modules. It runs in batch mode with parallel scoring.

## DesignDoc Reference

See DesignDoc.md sections:
- **3**: Reference architecture
- **5**: Batch mode and parallel scoring
- **8**: Observability

## Loop Flow

Each batch executes:

```
1. Stage C: Select parent (or merge)
   ↓
2. Stage M: Synthesise merge (if needed)
   ↓
3. Stage A: Diagnose parent's errors
   ↓
4. Stage B: Propose K siblings
   ↓
5. Score K candidates × 3 splits (parallel)
   ↓
6. Stage A: Diagnose each candidate
   ↓
7. Append K entries to log
   ↓
8. Regenerate report
```

## API

### `run_loop(train_path, dev_path, test_path, max_iterations=None) -> None`

Run the loop indefinitely (or until max_iterations).

```python
from pathlib import Path
from autoresearch.loop import run_loop

run_loop(
    train_path=Path("data/train.jsonl"),
    dev_path=Path("data/dev.jsonl"),
    test_path=Path("data/test.jsonl"),
    max_iterations=100,  # Or None for infinite
)
```

### `run_batch(batch_id, train_path, dev_path, test_path) -> list[ExperimentEntry]`

Run a single batch.

```python
from autoresearch.loop import run_batch

entries = run_batch(
    batch_id=1,
    train_path=Path("data/train.jsonl"),
    dev_path=Path("data/dev.jsonl"),
    test_path=Path("data/test.jsonl"),
)
```

### `score_single_artifact(artifact, train_path, dev_path, test_path) -> None`

Score a single artifact without proposing mutations.

```python
from autoresearch.loop import score_single_artifact

score_single_artifact(
    artifact="My prompt...",
    train_path=Path("data/train.jsonl"),
    dev_path=Path("data/dev.jsonl"),
    test_path=Path("data/test.jsonl"),
)
```

## Configuration

Loop configuration in `config.py`:

```python
LOOP = LoopConfig(
    batch_size=5,           # K siblings per batch
    parallelism=15,         # Parallel scorer processes
    history_full_count=5,   # Recent iterations in full
    limit=None,             # Dataset subsample (for smoke tests)
    max_iterations=None,    # None for infinite
    random_seed=42,
)
```

## Parallel Scoring

Scoring uses `ProcessPoolExecutor` with configurable parallelism:

- K candidates × 3 splits = 3K scoring jobs
- Default: 5 × 3 = 15 parallel processes
- Cache hits short-circuit scoring

## Crash Safety

The loop is designed to be interruptible:

- Each entry is appended atomically
- Notebook is saved before/after each batch
- Report is regenerated on interrupt
- State can be resumed from any point

## Observability

Each batch prints:
- Stage C selection and rationale
- Stage A summary
- Candidate generation count
- Per-candidate metrics
- Summary after completion

Files saved per batch:
- `state/batches/batch_NNNN/notes_before.md`
- `state/batches/batch_NNNN/notes_after.md`
- `state/batches/batch_NNNN/stage_attempt_*.txt` (on LLM failures)

## Usage

```bash
# Run loop (infinite)
loop run

# Run for N iterations
loop run --max-iters 50

# Subsample dataset for fast testing
loop run --limit 20

# Score single artifact
loop score "My prompt..."
```
