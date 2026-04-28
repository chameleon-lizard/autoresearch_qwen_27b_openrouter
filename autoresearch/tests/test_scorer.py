"""Tests for the scorer module."""

import tempfile
from pathlib import Path

from autoresearch.scorer import (
    ScoringResult,
    compute_artifact_hash,
    load_cached_result,
    save_cached_result,
    serialize_artifact,
)


def test_compute_artifact_hash():
    """Test artifact hash computation."""
    artifact = "Test prompt text"
    hash1 = compute_artifact_hash(artifact)
    hash2 = compute_artifact_hash(artifact)

    # Same artifact should produce same hash
    assert hash1 == hash2
    # Hash should be 16 characters
    assert len(hash1) == 16


def test_compute_artifact_hash_different():
    """Test that different artifacts produce different hashes."""
    hash1 = compute_artifact_hash("Prompt A")
    hash2 = compute_artifact_hash("Prompt B")

    assert hash1 != hash2


def test_serialize_artifact():
    """Test artifact serialization."""
    artifact = "Test prompt"
    serialized = serialize_artifact(artifact)

    assert "artifact" in serialized
    assert "hash" in serialized
    assert serialized["artifact"] == artifact
    assert len(serialized["hash"]) == 16


def test_scoring_result():
    """Test ScoringResult dataclass."""
    result = ScoringResult(
        artifact_hash="abc123",
        split="train",
        metrics={"kappa": 0.5, "f1": 0.6, "spearman": 0.7},
        predictions=["A", "B", "C"],
        labels=["A", "B", "D"],
        success=True,
    )

    assert result.artifact_hash == "abc123"
    assert result.split == "train"
    assert result.success is True
    assert result.metrics["kappa"] == 0.5


def test_save_and_load_cached_result():
    """Test saving and loading cached results."""
    with tempfile.TemporaryDirectory() as tmpdir:
        cache_path = Path(tmpdir) / "test_hash"

        result = ScoringResult(
            artifact_hash="test123",
            split="dev",
            metrics={"kappa": 0.335},
            predictions=["A"],
            labels=["A"],
            success=True,
        )

        save_cached_result(result, cache_path, "test artifact")

        loaded = load_cached_result(cache_path)

        assert loaded is not None
        assert loaded.artifact_hash == "test123"
        assert loaded.split == "dev"


def test_load_cached_result_not_found():
    """Test loading from non-existent cache."""
    with tempfile.TemporaryDirectory() as tmpdir:
        cache_path = Path(tmpdir) / "nonexistent"

        loaded = load_cached_result(cache_path)

        assert loaded is None
