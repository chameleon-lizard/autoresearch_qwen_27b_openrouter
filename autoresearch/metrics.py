"""
Metric computation for the autoresearch loop.

See DesignDoc.md section 10.5: "Use multiple correlated metrics, not one"
This module computes three metrics:
1. Cohen's kappa (κ) - agreement beyond chance
2. Macro F1 - balanced precision/recall across classes
3. Spearman correlation - rank correlation for ordinal labels

Using multiple metrics prevents the selector from finding metric pathologies.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any

import numpy as np
from scipy.stats import spearmanr
from sklearn.metrics import f1_score, cohen_kappa_score


def compute_cohen_kappa(predictions: list[str], labels: list[str]) -> float:
    """
    Compute Cohen's kappa coefficient.
    
    Kappa measures agreement between predictions and labels, correcting for
    chance agreement. Values range from -1 to 1, where:
    - 1: Perfect agreement
    - 0: Agreement equal to chance
    - <0: Agreement worse than chance
    
    Args:
        predictions: List of predicted labels
        labels: List of ground truth labels
    
    Returns:
        Cohen's kappa coefficient
    """
    if len(predictions) != len(labels):
        raise ValueError("Predictions and labels must have the same length")
    
    if len(predictions) == 0:
        return 0.0
    
    try:
        kappa = cohen_kappa_score(labels, predictions)
        return float(kappa)
    except ValueError:
        # Handle edge cases like single class
        return 0.0


def compute_macro_f1(predictions: list[str], labels: list[str]) -> float:
    """
    Compute macro-averaged F1 score.
    
    Macro F1 treats all classes equally, computing F1 for each class
    and then averaging. This is important when classes are imbalanced.
    
    Args:
        predictions: List of predicted labels
        labels: List of ground truth labels
    
    Returns:
        Macro-averaged F1 score
    """
    if len(predictions) != len(labels):
        raise ValueError("Predictions and labels must have the same length")
    
    if len(predictions) == 0:
        return 0.0
    
    try:
        f1 = f1_score(labels, predictions, average="macro", zero_division=0)
        return float(f1)
    except ValueError:
        return 0.0


def compute_spearman_correlation(
    predictions: list[str | int],
    labels: list[str | int],
    label_order: dict[str, int] | None = None,
) -> float:
    """
    Compute Spearman rank correlation.
    
    Spearman correlation measures how well predictions preserve the
    ranking of labels. This is useful for ordinal labels (e.g., 1-5 scale).
    
    Args:
        predictions: List of predicted labels
        labels: List of ground truth labels
        label_order: Optional mapping from label to numeric value.
                    If None, labels are used as-is (must be numeric).
    
    Returns:
        Spearman correlation coefficient
    """
    if len(predictions) != len(labels):
        raise ValueError("Predictions and labels must have the same length")
    
    if len(predictions) == 0:
        return 0.0
    
    # Convert labels to numeric if needed
    if label_order is not None:
        pred_numeric = [label_order.get(p, 0) for p in predictions]
        label_numeric = [label_order.get(l, 0) for l in labels]
    else:
        try:
            pred_numeric = [float(p) for p in predictions]
            label_numeric = [float(l) for l in labels]
        except (ValueError, TypeError):
            # Labels are not numeric and no mapping provided
            return 0.0
    
    try:
        corr, _ = spearmanr(pred_numeric, label_numeric)
        return float(corr) if not np.isnan(corr) else 0.0
    except (ValueError, RuntimeError):
        return 0.0


def compute_all_metrics(
    predictions: list[str],
    labels: list[str],
    label_order: dict[str, int] | None = None,
) -> dict[str, float]:
    """
    Compute all three metrics at once.
    
    Args:
        predictions: List of predicted labels
        labels: List of ground truth labels
        label_order: Optional label-to-numeric mapping for Spearman
    
    Returns:
        Dictionary with 'kappa', 'f1', and 'spearman' keys
    """
    return {
        "kappa": compute_cohen_kappa(predictions, labels),
        "f1": compute_macro_f1(predictions, labels),
        "spearman": compute_spearman_correlation(predictions, labels, label_order),
    }


def compute_metric_delta(
    old_metrics: dict[str, float],
    new_metrics: dict[str, float],
) -> dict[str, float]:
    """
    Compute the delta between two metric sets.
    
    Args:
        old_metrics: Previous metrics
        new_metrics: New metrics
    
    Returns:
        Dictionary with deltas for each metric
    """
    return {
        f"delta_{k}": new_metrics.get(k, 0.0) - old_metrics.get(k, 0.0)
        for k in set(old_metrics.keys()) | set(new_metrics.keys())
    }


def metrics_to_string(metrics: dict[str, float], precision: int = 3) -> str:
    """
    Format metrics as a human-readable string.
    
    Args:
        metrics: Dictionary of metric name to value
        precision: Number of decimal places
    
    Returns:
        Formatted string like "κ=0.335 F1=0.412 ρ=0.287"
    """
    parts = []
    for name, value in metrics.items():
        if name == "kappa":
            symbol = "κ"
        elif name == "spearman":
            symbol = "ρ"
        elif name == "f1":
            symbol = "F1"
        else:
            symbol = name
        parts.append(f"{symbol}={value:.{precision}f}")
    return " ".join(parts)
