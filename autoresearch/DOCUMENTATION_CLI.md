# CLI Module Documentation

## Overview

The CLI module (`cli.py`) provides the command-line interface for the
autoresearch loop. All configuration is in `config.py`, not scattered
CLI flags.

## DesignDoc Reference

See DesignDoc.md section 12: "Minimal CLI surface"

## Commands

### `loop run`

Run the main autoresearch loop (infinite by default).

```bash
# Run indefinitely
loop run

# Run for N iterations
loop run --max-iters 50

# Subsample dataset for fast testing
loop run --limit 20

# Use custom data directory
loop run --data /path/to/data
```

### `loop report`

Regenerate the experiments report from the log.

```bash
loop report
```

### `loop reset`

Reset experiment state (iterations, log, report) while preserving the cache.

```bash
loop reset
```

**Note**: Cache is preserved, so re-running will not re-score seen artifacts.

### `loop score <artifact>`

Score a single artifact on all splits (no proposal).

```bash
# Score inline text
loop score "My prompt text..."

# Score from file
loop score prompt.txt
```

### `loop prepare`

Prepare data splits from ground truth.

```bash
# Default paths
loop prepare

# Custom ground truth
loop prepare --ground-truth data/ground_truth.jsonl

# Custom output directory
loop prepare --output data/splits

# Subsample for testing
loop prepare --limit 100
```

## Usage Flow

Typical workflow:

```bash
# 1. Prepare data splits
loop prepare --ground-truth data/ground_truth.jsonl --limit 100

# 2. Run loop (start small for testing)
loop run --max-iters 10 --limit 20

# 3. Check report
loop report

# 4. Run full loop
loop run

# 5. Interrupt with Ctrl+C (state is saved)
# 6. Resume later
loop run
```

## Configuration

All configuration is in `config.py`:

```python
LOOP = LoopConfig(
    batch_size=5,
    parallelism=15,
    history_full_count=5,
    limit=None,
    max_iterations=None,
    random_seed=42,
)
```

Not CLI flags - this keeps the interface minimal.

## Exit Codes

- 0: Success
- 1: Error (missing files, invalid arguments, etc.)

## Environment Variables

See `paths.py`:

```bash
# Set custom state directory
AUTORESEARCH_STATE_DIR=/tmp/runA loop run
```

This enables running multiple instances in parallel.
