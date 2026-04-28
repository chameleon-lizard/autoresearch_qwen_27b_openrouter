# Metrics Module Documentation

## Overview

The metrics module (`metrics.py`) computes three complementary metrics for
evaluating artifacts in the autoresearch loop. Using multiple metrics prevents
the selector from exploiting single-metric pathologies.

## DesignDoc Reference

See DesignDoc.md section 10.5: "Use multiple correlated metrics, not one"

## Metrics

### 1. Cohen's Kappa (κ)

Measures agreement between predictions and labels, correcting for chance agreement.

- **Range**: -1 to 1
- **Interpretation**:
  - 1: Perfect agreement
  - 0: Agreement equal to chance
  - <0: Worse than chance

### 2. Macro F1

Macro-averaged F1 score, treating all classes equally.

- **Range**: 0 to 1
- **Interpretation**: Higher is better
- **Why macro**: Important for imbalanced class distributions

### 3. Spearman Correlation (ρ)

Rank correlation between predictions and labels. Useful for ordinal labels.

- **Range**: -1 to 1
- **Interpretation**: Higher is better (preserves ranking)
- **Requires**: Numeric labels or a label_order mapping

## API

### `compute_cohen_kappa(predictions, labels) -> float`

Compute Cohen's kappa.

### `compute_macro_f1(predictions, labels) -> float`

Compute macro-averaged F1 score.

### `compute_spearman_correlation(predictions, labels, label_order=None) -> float`

Compute Spearman correlation. Use `label_order` for non-numeric labels.

### `compute_all_metrics(predictions, labels, label_order=None) -> dict`

Compute all three metrics at once. Returns:
```python
{
    "kappa": 0.335,
    "f1": 0.412,
    "spearman": 0.287
}
```

### `compute_metric_delta(old_metrics, new_metrics) -> dict`

Compute the delta between two metric sets.

### `metrics_to_string(metrics, precision=3) -> str`

Format metrics as a human-readable string: "κ=0.335 F1=0.412 ρ=0.287"

## Usage Example

```python
from autoresearch.metrics import compute_all_metrics, metrics_to_string

predictions = ["label_a", "label_b", "label_a", "label_c"]
labels = ["label_a", "label_b", "label_c", "label_c"]

metrics = compute_all_metrics(predictions, labels)
print(metrics_to_string(metrics))
# κ=0.250 F1=0.583 ρ=0.500
```

## Label Order for Spearman

For ordinal labels (e.g., "poor", "fair", "good", "excellent"):

```python
label_order = {
    "poor": 1,
    "fair": 2,
    "good": 3,
    "excellent": 4,
}

metrics = compute_all_metrics(predictions, labels, label_order=label_order)
```

## Edge Cases

- Empty inputs return 0.0 for all metrics
- Single-class inputs return 0.0 for kappa
- Non-numeric labels without label_order return 0.0 for Spearman
- Mismatched lengths raise ValueError
