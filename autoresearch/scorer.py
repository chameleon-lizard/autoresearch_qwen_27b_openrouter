from __future__ import annotations

"""
External scorer wrapper with caching.

See DesignDoc.md sections:
- 2.1: Cache by content hash
- 10.6: Wrap, don't reimplement

This module wraps an external scorer (e.g., dredd.py) and provides:
1. Content-hash-based caching to avoid re-scoring
2. Parallel scoring support
3. Crash-safe line-by-line output
"""

import hashlib
import json
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .paths import ensure_directories, get_cache_path


def compute_artifact_hash(artifact: str) -> str:
    """
    Compute deterministic hash of an artifact.
    
    See DesignDoc.md section 2.1: "Every artifact has a deterministic id
    sha256(serialise(artifact))[:16]".
    
    Args:
        artifact: The artifact text (prompt, config, etc.)
    
    Returns:
        16-character hex hash
    """
    # Use UTF-8 encoding for consistency
    artifact_bytes = artifact.encode("utf-8")
    full_hash = hashlib.sha256(artifact_bytes).hexdigest()
    return full_hash[:16]


def serialize_artifact(artifact: str) -> dict[str, Any]:
    """Serialize artifact for cache storage."""
    return {
        "artifact": artifact,
        "hash": compute_artifact_hash(artifact),
    }


@dataclass
class ScoringResult:
    """Result of scoring an artifact on a dataset split."""
    artifact_hash: str
    split: str  # "train", "dev", or "test"
    metrics: dict[str, float]
    predictions: list[str]
    labels: list[str]
    success: bool
    error: str | None = None


def load_cached_result(cache_path: Path) -> ScoringResult | None:
    """Load a cached scoring result if it exists."""
    result_file = cache_path / "result.json"
    if not result_file.exists():
        return None

    try:
        with open(result_file, "r") as f:
            data = json.load(f)
        return ScoringResult(**data)
    except (json.JSONDecodeError, KeyError) as e:
        print(f"Warning: Failed to load cached result from {result_file}: {e}")
        return None


def save_cached_result(result: ScoringResult, cache_path: Path, artifact: str) -> None:
    """Save a scoring result to cache."""
    cache_path.mkdir(parents=True, exist_ok=True)

    # Save the result
    result_file = cache_path / "result.json"
    with open(result_file, "w") as f:
        json.dump({
            "artifact_hash": result.artifact_hash,
            "split": result.split,
            "metrics": result.metrics,
            "predictions": result.predictions,
            "labels": result.labels,
            "success": result.success,
            "error": result.error,
        }, f, indent=2)

    # Save the artifact text for self-describing cache
    artifact_file = cache_path / "artifact.txt"
    with open(artifact_file, "w") as f:
        f.write(artifact)


def score_with_external_scorer(
    artifact: str,
    data_path: Path,
    scorer_executable: str,
    scorer_args: list[str] | None = None,
) -> tuple[list[str], str | None]:
    """
    Score an artifact using an external scorer.
    
    Args:
        artifact: The artifact to score
        data_path: Path to the dataset split (JSONL)
        scorer_executable: Path to the scorer script
        scorer_args: Additional arguments to pass to the scorer
    
    Returns:
        Tuple of (predictions, error_message)
        error_message is None on success
    """
    if scorer_args is None:
        scorer_args = []

    # Write artifact to a temp file
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        f.write(artifact)
        artifact_path = Path(f.name)

    try:
        # Build command
        cmd = [
            "python", scorer_executable,
            "--artifact", str(artifact_path),
            "--data", str(data_path),
            *scorer_args,
        ]

        # Run scorer
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300,  # 5 minute timeout per split
        )

        if result.returncode != 0:
            return [], f"Scorer failed with code {result.returncode}: {result.stderr}"

        # Parse output (expecting JSONL with predictions)
        predictions = []
        for line in result.stdout.strip().split("\n"):
            if line:
                try:
                    pred = json.loads(line)
                    predictions.append(pred.get("prediction", pred.get("label", "")))
                except json.JSONDecodeError:
                    predictions.append(line)

        return predictions, None

    except subprocess.TimeoutExpired:
        return [], "Scorer timed out after 300 seconds"
    except FileNotFoundError:
        return [], f"Scorer executable not found: {scorer_executable}"
    finally:
        # Clean up temp file
        artifact_path.unlink(missing_ok=True)


def score_artifact(
    artifact: str,
    data_path: Path,
    split_name: str,
    scorer_executable: str = "dredd.py",
    scorer_args: list[str] | None = None,
) -> ScoringResult:
    """
    Score an artifact on a dataset split, with caching.
    
    Args:
        artifact: The artifact to score
        data_path: Path to the dataset split (JSONL)
        split_name: Name of the split ("train", "dev", "test")
        scorer_executable: Path to the scorer script
        scorer_args: Additional arguments for the scorer
    
    Returns:
        ScoringResult with metrics and predictions
    """
    ensure_directories()

    # Compute hash and check cache
    artifact_hash = compute_artifact_hash(artifact)
    cache_path = get_cache_path(artifact_hash)

    # Check if we have a cached result for this split
    cached = load_cached_result(cache_path)
    if cached is not None and cached.split == split_name:
        print(f"[CACHE HIT] {artifact_hash} for {split_name}")
        return cached

    print(f"[SCORING] {artifact_hash} on {split_name}")

    # Score the artifact
    predictions, error = score_with_external_scorer(
        artifact, data_path, scorer_executable, scorer_args
    )

    # Load ground truth labels
    labels = []
    with open(data_path, "r") as f:
        for line in f:
            if line.strip():
                record = json.loads(line)
                labels.append(record.get("label", record.get("ground_truth", "")))

    # Ensure predictions and labels match
    if len(predictions) != len(labels):
        # Pad or truncate predictions to match
        if len(predictions) < len(labels):
            predictions = predictions + [""] * (len(labels) - len(predictions))
        else:
            predictions = predictions[:len(labels)]

    # Compute metrics
    from .metrics import compute_all_metrics

    if error:
        result = ScoringResult(
            artifact_hash=artifact_hash,
            split=split_name,
            metrics={"kappa": 0.0, "f1": 0.0, "spearman": 0.0},
            predictions=predictions,
            labels=labels,
            success=False,
            error=error,
        )
    else:
        metrics = compute_all_metrics(predictions, labels)
        result = ScoringResult(
            artifact_hash=artifact_hash,
            split=split_name,
            metrics=metrics,
            predictions=predictions,
            labels=labels,
            success=True,
        )

    # Cache the result
    save_cached_result(result, cache_path, artifact)

    return result
