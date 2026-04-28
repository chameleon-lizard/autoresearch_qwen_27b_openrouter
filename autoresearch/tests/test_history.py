"""Tests for the history module."""


from autoresearch.history import (
    ExperimentEntry,
    append_entry,
    get_best_entry_by_dev_kappa,
    get_entries_by_batch,
    get_entry_by_iter,
    get_last_iteration,
    get_plan_statistics,
    read_log,
    render_history_compact,
)
from autoresearch.paths import EXPERIMENTS_LOG


def test_append_and_read():
    """Test appending and reading entries."""
    # Clear log
    if EXPERIMENTS_LOG.exists():
        EXPERIMENTS_LOG.unlink()

    entry = ExperimentEntry(
        iter=1,
        batch=1,
        ts="2024-01-15T14:30:00",
        artifact_hash="abc123",
        parent=None,
        plan_id="test_plan",
        rationale="Test rationale",
        artifact="Test artifact",
        metrics_train={"kappa": 0.3, "f1": 0.4, "spearman": 0.2},
        metrics_dev={"kappa": 0.25, "f1": 0.35, "spearman": 0.15},
        metrics_test={"kappa": 0.2, "f1": 0.3, "spearman": 0.1},
    )

    append_entry(entry)

    entries = read_log()
    assert len(entries) == 1
    assert entries[0].iter == 1
    assert entries[0].plan_id == "test_plan"


def test_get_entry_by_iter():
    """Test getting entry by iteration number."""
    entry = get_entry_by_iter(1)
    assert entry is not None
    assert entry.iter == 1


def test_get_best_entry():
    """Test getting best entry by dev kappa."""
    # Add another entry with lower kappa
    entry2 = ExperimentEntry(
        iter=2,
        batch=1,
        ts="2024-01-15T14:35:00",
        artifact_hash="def456",
        parent=1,
        plan_id="worse_plan",
        rationale="Worse",
        artifact="Worse artifact",
        metrics_train={"kappa": 0.2, "f1": 0.3, "spearman": 0.1},
        metrics_dev={"kappa": 0.15, "f1": 0.25, "spearman": 0.05},
        metrics_test={"kappa": 0.1, "f1": 0.2, "spearman": 0.0},
    )
    append_entry(entry2)

    best = get_best_entry_by_dev_kappa()
    assert best.iter == 1  # First entry has higher dev kappa


def test_get_entries_by_batch():
    """Test getting entries by batch number."""
    entries = get_entries_by_batch(1)
    assert len(entries) == 2


def test_get_last_iteration():
    """Test getting last iteration number."""
    last = get_last_iteration()
    assert last == 2


def test_render_history_compact():
    """Test history rendering."""
    entries = read_log()
    rendered = render_history_compact(entries)

    assert "iter=1" in rendered
    assert "iter=2" in rendered
    assert "BEST SO FAR" in rendered


def test_get_plan_statistics():
    """Test plan statistics computation."""
    entries = read_log()
    stats = get_plan_statistics(entries)

    assert "test_plan" in stats
    assert "worse_plan" in stats
    assert stats["test_plan"]["proposed"] == 1
    assert stats["worse_plan"]["proposed"] == 1


def test_to_dict_and_from_dict():
    """Test serialization."""
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

    data = entry.to_dict()
    restored = ExperimentEntry.from_dict(data)

    assert restored.iter == entry.iter
    assert restored.plan_id == entry.plan_id
