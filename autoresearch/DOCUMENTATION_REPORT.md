# Report Module Documentation

## Overview

The report module (`report.py`) generates human-readable reports from the
experiment log. The report is auto-regenerated after every batch.

## DesignDoc Reference

See DesignDoc.md section 8: "Observability"

## Key Features

### 1. Best-So-Far Callout

Highlights the iteration with the best dev kappa, including:
- Full artifact text
- All metrics (train/dev/test)
- Dev-test gap (overfitting indicator)

### 2. Plan Statistics

Aggregate statistics for each proposal type:
- How many times proposed
- How many times won
- Mean delta in dev kappa

### 3. Per-Batch Tables

Detailed tables showing all iterations in each batch.

### 4. Dev-Test Gap Trend

Tracks the gap between dev and test kappa over time to detect overfitting.

## API

### `generate_report() -> str`

Generate the full report and save to `experiments_report.md`.

```python
from autoresearch.report import generate_report

report = generate_report()
print(report)
```

### `print_report_summary() -> None`

Print a brief summary to stdout.

```python
from autoresearch.report import print_report_summary

print_report_summary()
# ============================================================
# Experiments Summary: 47 iterations, 10 batches
# ============================================================
#
# Best (iter 27):
#   Dev κ: 0.335
#   Test κ: 0.231
#   Gap: +0.104
#
# Latest (iter 47):
#   Dev κ: 0.340
#   Test κ: 0.240
#   Gap: +0.100
```

## Report Format

The generated report includes:

1. **Header**: Number of iterations and batches
2. **Best So Far**: Full artifact and metrics
3. **Plan Statistics**: Table of proposal performance
4. **Batch Details**: Per-batch iteration tables
5. **Dev-Test Gap Trend**: Last 20 iterations

## Usage

```bash
# Generate report from CLI
loop report
```

Or programmatically:

```python
from autoresearch.report import generate_report

# After each batch
generate_report()
```

## Dev-Test Gap

The dev-test gap is a critical indicator of overfitting:

- **Gap < 0.05**: Healthy, generalizing well
- **Gap 0.05-0.10**: Caution, some overfitting
- **Gap > 0.10**: Warning, significant overfitting

See DesignDoc.md section 10.4: "Selector overfit is real"
