# Autoresearch Loop - Wiki

## Executive Summary

The autoresearch loop is an autonomous LLM-driven optimization system that
iteratively improves an artifact (prompt, config, code patch, etc.) by:

1. **Scoring** the current artifact on a labelled dataset
2. **Diagnosing** where it fails relative to ground truth
3. **Proposing** mutations that target those failure modes
4. **Selecting** which proposal to keep based on held-out signal
5. **Repeating** indefinitely with full audit trail

## Key Design Principles

### 1. Cache by Content Hash (DesignDoc 2.1)

Every artifact has a deterministic ID: `sha256(artifact)[:16]`. All expensive
work is cached by this ID. Re-running never re-does completed work.

### 2. Append-Only Log (DesignDoc 2.2)

Single source of truth: `experiments.jsonl`. Every iteration writes one JSON
line. Earlier lines are NEVER rewritten. Enables resumability and audit.

### 3. Crash-Safe (DesignDoc 2.3)

Line-buffered writes. Ctrl+C mid-batch is safe. Restart skips cached work.

### 4. Held-Out Test Set (DesignDoc 2.4)

Train/dev/test split (40/20/40). Loop sees train+dev. Test is logged but
NEVER surfaced to proposer/selector. Detects overfitting.

### 5. Single-Edit Attribution (DesignDoc 2.5)

Each candidate applies ONE focused change. Multi-change candidates forbidden
because you cannot attribute which sub-change caused the Δ-metric.

### 6. Bidirectional Notebook (DesignDoc 2.6)

Shared text file (`notes.md`) that humans can edit mid-run and agents can
append to. Re-read fresh every iteration (never cached).

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  iter loop (batch mode):                                    │
│                                                             │
│   1. Stage C  selector → pick parent (or merge)             │
│   2. Stage M  if merge: synthesise base artifact            │
│   3. Stage B  proposer → K sibling candidates               │
│   4. score K candidates in parallel (cache hits!)           │
│   5. Stage A  diagnose each candidate's errors              │
│   6. append K lines to experiments.jsonl                    │
│   7. regenerate experiments_report.md                       │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

## Modules

| Module | File | Description |
|--------|------|-------------|
| paths | `autoresearch/paths.py` | Centralized path management |
| config | `autoresearch/config.py` | Configuration management |
| splitter | `autoresearch/splitter.py` | Stratified train/dev/test split |
| scorer | `autoresearch/scorer.py` | External scorer wrapper with caching |
| metrics | `autoresearch/metrics.py` | κ, macro-F1, Spearman computation |
| refiner | `autoresearch/refiner.py` | Four-stage LLM interaction (A/B/C/M) |
| history | `autoresearch/history.py` | Append-only log management |
| report | `autoresearch/report.py` | Report generation |
| loop | `autoresearch/loop.py` | Main autoresearch loop |
| notebook | `autoresearch/notebook.py` | Bidirectional notebook |
| cli | `autoresearch/cli.py` | Command-line interface |

## The Four Refiner Stages

### Stage A: Disagreement Generalisation

Input: Examples where artifact disagrees with ground truth
Output: Free-text generalisation of failure modes

Purpose: Force abstraction to prevent overfitting to specific examples.

### Stage B: Proposal

Input: Parent artifact, Stage-A summary, history, notebook
Output: K sibling candidates with plan_id, rationale, artifact

Purpose: Generate diverse, focused mutations for parallel scoring.

### Stage C: Selection

Input: History with metrics, best-so-far callout
Output: Either `iter=N` or `merge=N1,N2,...`

Purpose: Choose best parent considering trajectory, not just argmax.

### Stage M: Merge Synthesis

Input: Multiple parent artifacts
Output: Single merged artifact

Purpose: Combine strengths of multiple branches.

## CLI Commands

```bash
loop run              # Main loop, infinite
loop run --max-iters N  # Bounded for tests
loop run --limit N    # Subsample dataset for fast smoke test
loop report          # Regenerate experiments_report.md
loop reset           # Delete iterations + log; preserve cache
loop score <artifact>  # Score one artifact, print metrics
loop prepare         # Prepare data splits from ground truth
```

## File Structure

```
autoresearch_exps/qwen-27b-openrouter/
├── loop                    # Entry point script
├── autoresearch/
│   ├── __init__.py
│   ├── paths.py            # Path management
│   ├── config.py           # Configuration
│   ├── splitter.py         # Data splitting
│   ├── scorer.py           # Scorer wrapper
│   ├── metrics.py          # Metric computation
│   ├── refiner.py          # LLM interaction
│   ├── history.py          # Log management
│   ├── report.py           # Report generation
│   ├── loop.py             # Main loop
│   ├── notebook.py         # Notebook management
│   ├── cli.py              # CLI
│   ├── DOCUMENTATION_*.md  # Per-module docs
├── state/
│   ├── cache/              # Artifact scoring cache
│   ├── iterations/         # Iteration snapshots
│   ├── batches/            # Batch-specific data
│   ├── experiments.jsonl   # Append-only log
│   ├── experiments_report.md  # Generated report
│   └── notes.md            # Bidirectional notebook
├── data/
│   ├── ground_truth.jsonl  # Input data
│   ├── train.jsonl
│   ├── dev.jsonl
│   └── test.jsonl
├── requirements.txt
├── WIKI.md                 # This file
├── PROGRESS.md             # Implementation progress
├── OPS.md                  # Operations runbook
└── DesignDoc.md            # Design specification
```

## Configuration

All configuration is in `autoresearch/config.py`:

```python
SCORER = ScorerConfig(
    executable="dredd.py",
    scorer_model="qwen/qwen-2.5-32b-instruct",
    scorer_temperature=0.0,
)

REFINER = RefinerConfig(
    model="qwen/qwen-2.5-32b-instruct",
    api_key="...",
    max_tokens=8192,
    retry_temperatures=(0.0, 0.4, 0.7, 0.9),
)

LOOP = LoopConfig(
    batch_size=5,
    parallelism=15,
    history_full_count=5,
    max_iterations=None,
)

SPLIT = SplitConfig(
    train_ratio=0.4,
    dev_ratio=0.2,
    test_ratio=0.4,
    stratify_column="domain",
    random_seed=42,
)
```

## Multi-Instance Support

Set `AUTORESEARCH_STATE_DIR` to run multiple instances in parallel:

```bash
AUTORESEARCH_STATE_DIR=/tmp/runA loop run
AUTORESEARCH_STATE_DIR=/tmp/runB loop run
```

## Metrics

Three complementary metrics prevent single-metric pathologies:

1. **Cohen's kappa (κ)**: Agreement beyond chance
2. **Macro F1**: Balanced precision/recall across classes
3. **Spearman (ρ)**: Rank correlation for ordinal labels

## Overfitting Detection

The dev-test gap is tracked in the report:

- Gap < 0.05: Healthy
- Gap 0.05-0.10: Caution
- Gap > 0.10: Warning - significant overfitting

## Lessons Learned

See DesignDoc.md section 10 for detailed lessons:

- Aggregating winners ≠ improvement
- First edit dominates
- ~⅓ of proposals win
- Selector overfit is real
- Use multiple correlated metrics
- Wrap, don't reimplement
- The notebook is load-bearing
- Greedy retries are useless
- Server token budgets bite
- Document while building
