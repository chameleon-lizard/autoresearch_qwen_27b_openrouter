"""Tests for the report module."""


from autoresearch.history import ExperimentEntry, append_entry
from autoresearch.paths import EXPERIMENTS_LOG, EXPERIMENTS_REPORT
from autoresearch.report import generate_report, print_report_summary


def setup_clean_log():
    """Clean up log and report for tests."""
    if EXPERIMENTS_LOG.exists():
        EXPERIMENTS_LOG.unlink()
    if EXPERIMENTS_REPORT.exists():
        EXPERIMENTS_REPORT.unlink()


def test_generate_empty_report():
    """Test generating report with no entries."""
    setup_clean_log()

    report = generate_report()

    assert "No experiments recorded yet" in report


def test_generate_report_with_entries():
    """Test generating report with entries."""
    setup_clean_log()

    # Add test entries
    entry1 = ExperimentEntry(
        iter=1,
        batch=1,
        ts="2024-01-15T14:30:00",
        artifact_hash="abc123",
        parent=None,
        plan_id="test_plan",
        rationale="Test rationale",
        artifact="Test artifact content",
        metrics_train={"kappa": 0.3, "f1": 0.4, "spearman": 0.2},
        metrics_dev={"kappa": 0.25, "f1": 0.35, "spearman": 0.15},
        metrics_test={"kappa": 0.2, "f1": 0.3, "spearman": 0.1},
    )
    append_entry(entry1)

    entry2 = ExperimentEntry(
        iter=2,
        batch=1,
        ts="2024-01-15T14:35:00",
        artifact_hash="def456",
        parent=1,
        plan_id="better_plan",
        rationale="Better rationale",
        artifact="Better artifact",
        metrics_train={"kappa": 0.35, "f1": 0.45, "spearman": 0.25},
        metrics_dev={"kappa": 0.3, "f1": 0.4, "spearman": 0.2},
        metrics_test={"kappa": 0.25, "f1": 0.35, "spearman": 0.15},
    )
    append_entry(entry2)

    report = generate_report()

    # Check report contains expected content
    assert "Best So Far" in report
    assert "Iteration 2" in report
    assert "Plan Statistics" in report
    assert "test_plan" in report
    assert "better_plan" in report
    assert "Batch Details" in report
    assert "Dev-Test Gap Trend" in report


def test_report_file_created():
    """Test that report file is created."""
    setup_clean_log()

    entry = ExperimentEntry(
        iter=1,
        batch=1,
        ts="2024-01-15T14:30:00",
        artifact_hash="abc123",
        parent=None,
        plan_id="test",
        rationale="Test",
        artifact="Test",
        metrics_train={"kappa": 0.3},
        metrics_dev={"kappa": 0.25},
        metrics_test={"kappa": 0.2},
    )
    append_entry(entry)

    generate_report()

    assert EXPERIMENTS_REPORT.exists()


def test_print_report_summary():
    """Test that print_report_summary doesn't crash."""
    setup_clean_log()

    # This should not raise an exception
    try:
        print_report_summary()
    except Exception as e:
        assert False, f"print_report_summary raised: {e}"
