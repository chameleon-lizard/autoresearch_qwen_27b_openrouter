"""Tests for the metrics module."""

from autoresearch.metrics import (
    compute_all_metrics,
    compute_cohen_kappa,
    compute_macro_f1,
    compute_metric_delta,
    compute_spearman_correlation,
    metrics_to_string,
)


def test_cohen_kappa_perfect():
    """Test kappa with perfect agreement."""
    predictions = ["A", "B", "A", "B"]
    labels = ["A", "B", "A", "B"]

    kappa = compute_cohen_kappa(predictions, labels)
    assert kappa == 1.0


def test_cohen_kappa_random():
    """Test kappa with random agreement."""
    predictions = ["A", "A", "A", "A"]
    labels = ["A", "B", "C", "D"]

    kappa = compute_cohen_kappa(predictions, labels)
    assert kappa < 0.5  # Should be low


def test_macro_f1():
    """Test macro F1 computation."""
    predictions = ["A", "B", "A", "B"]
    labels = ["A", "B", "A", "B"]

    f1 = compute_macro_f1(predictions, labels)
    assert f1 == 1.0


def test_spearman_correlation():
    """Test Spearman correlation."""
    predictions = [1, 2, 3, 4, 5]
    labels = [1, 2, 3, 4, 5]

    spearman = compute_spearman_correlation(predictions, labels)
    assert abs(spearman - 1.0) < 0.0001


def test_spearman_with_label_order():
    """Test Spearman with label order mapping."""
    predictions = ["poor", "fair", "good", "excellent"]
    labels = ["poor", "fair", "good", "excellent"]
    label_order = {"poor": 1, "fair": 2, "good": 3, "excellent": 4}

    spearman = compute_spearman_correlation(predictions, labels, label_order)
    assert spearman == 1.0


def test_compute_all_metrics():
    """Test computing all metrics at once."""
    predictions = ["A", "B", "A", "B"]
    labels = ["A", "B", "A", "B"]

    metrics = compute_all_metrics(predictions, labels)

    assert "kappa" in metrics
    assert "f1" in metrics
    assert "spearman" in metrics
    assert metrics["kappa"] == 1.0
    assert metrics["f1"] == 1.0


def test_compute_metric_delta():
    """Test computing metric delta."""
    old = {"kappa": 0.3, "f1": 0.4}
    new = {"kappa": 0.35, "f1": 0.38}

    delta = compute_metric_delta(old, new)

    assert abs(delta["delta_kappa"] - 0.05) < 0.0001
    assert abs(delta["delta_f1"] - (-0.02)) < 0.0001


def test_metrics_to_string():
    """Test metrics string formatting."""
    metrics = {"kappa": 0.335, "f1": 0.412, "spearman": 0.287}

    s = metrics_to_string(metrics)

    assert "κ=0.335" in s
    assert "F1=0.412" in s
    assert "ρ=0.287" in s


def test_empty_input():
    """Test handling of empty input."""
    assert compute_cohen_kappa([], []) == 0.0
    assert compute_macro_f1([], []) == 0.0
    assert compute_spearman_correlation([], []) == 0.0


def test_mismatched_length():
    """Test error handling for mismatched lengths."""
    try:
        compute_cohen_kappa(["A", "B"], ["A"])
        assert False, "Should have raised ValueError"
    except ValueError:
        pass
