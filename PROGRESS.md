# Implementation Progress

## Overview

This document tracks the implementation progress of the autoresearch loop
as described in DesignDoc.md.

## Completed Modules

### Core Infrastructure ✓

- **paths.py**: Centralized path management with `AUTORESEARCH_STATE_DIR` support
- **config.py**: Configuration for scorer, refiner, loop, and split
- **requirements.txt**: Dependencies (numpy, pandas, scikit-learn, openai, etc.)

### Module 1: Data Splitting ✓

- **splitter.py**: Stratified train/dev/test split (40/20/40)
- Deterministic given same seed and input
- Supports stratification by domain or custom column
- **DOCUMENTATION_SPLITTER.md**: Complete

### Module 2: Scoring ✓

- **scorer.py**: External scorer wrapper with content-hash caching
- Cache key: `sha256(artifact)[:16]`
- Self-describing cache (includes artifact text)
- Crash-safe line-by-line output
- **DOCUMENTATION_SCORER.md**: Complete

### Module 3: Metrics ✓

- **metrics.py**: Three complementary metrics
  - Cohen's kappa (κ)
  - Macro F1
  - Spearman correlation (ρ)
- **DOCUMENTATION_METRICS.md**: Complete

### Module 4: Refiner Stages ✓

- **refiner.py**: Four-stage LLM interaction
  - Stage A: Disagreement generalisation
  - Stage B: Proposal generation (K siblings)
  - Stage C: Selection (iter=N or merge=N1,N2,...)
  - Stage M: Merge synthesis
- Retry logic with varying temperatures: [0.0, 0.4, 0.7, 0.9]
- Debug output per attempt
- **DOCUMENTATION_REFINER.md**: Complete

### Module 5: History & Logging ✓

- **history.py**: Append-only experiment log
  - Single source of truth: `experiments.jsonl`
  - Never rewrites earlier lines
  - History rendering (compact vs full)
  - Plan statistics aggregation
- **report.py**: Report generation
  - Best-so-far callout
  - Plan statistics table
  - Per-batch details
  - Dev-test gap trend
- **DOCUMENTATION_HISTORY.md**: Complete
- **DOCUMENTATION_REPORT.md**: Complete

### Module 6: Main Loop ✓

- **loop.py**: Main autoresearch loop
  - Batch mode with parallel scoring
  - Crash-safe writes
  - Notebook snapshots before/after
  - KeyboardInterrupt handling
- **DOCUMENTATION_LOOP.md**: Complete

### Module 7: CLI ✓

- **cli.py**: Command-line interface
  - `loop run`: Main loop
  - `loop report`: Regenerate report
  - `loop reset`: Reset state (preserve cache)
  - `loop score`: Score single artifact
  - `loop prepare`: Prepare data splits
- **DOCUMENTATION_CLI.md**: Complete

### Module 8: Notebook ✓

- **notebook.py**: Bidirectional notebook
  - User can edit at any time
  - Agent appends between iterations
  - Re-read fresh every iteration (never cached)
  - User constraint parsing
- **DOCUMENTATION_NOTEBOOK.md**: Complete

## Top-Level Documentation

- **WIKI.md**: Executive summary ✓
- **TODO.md**: Implementation tracking ✓
- **OPS.md**: Operations runbook (pending)

## Pending Items

### Testing

- [ ] Unit tests for each module
- [ ] Smoke test with `--limit 20`
- [ ] Integration test with mock scorer

### OPS.md

- [ ] Full deployment instructions
- [ ] Environment variable reference
- [ ] Health check procedures
- [ ] Common failure modes
- [ ] Backup/restore procedures

### Example Data

- [ ] Sample ground_truth.jsonl for testing
- [ ] Example prompt artifact
- [ ] Mock scorer script

## Git Branches

All implementation done on main branch (initial implementation).

## Next Steps

1. Create OPS.md
2. Add unit tests
3. Create example data for smoke testing
4. Test end-to-end with mock scorer
5. Document any issues or adjustments needed
