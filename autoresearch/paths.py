"""
Centralized path management for the autoresearch loop.

All paths are derived from a single STATE_DIR environment variable to enable
multi-instance support. See DesignDoc.md section 9.
"""

import os
from pathlib import Path

# State directory from environment variable, with sensible default
_STATE_DIR = Path(os.environ.get("AUTORESEARCH_STATE_DIR", Path(__file__).parent / "state"))

# Cache directory for artifact scoring results
CACHE_DIR = _STATE_DIR / "cache"

# Iteration snapshots
ITERATIONS_DIR = _STATE_DIR / "iterations"

# Batch-specific data
BATCHES_DIR = _STATE_DIR / "batches"

# Append-only experiment log
EXPERIMENTS_LOG = _STATE_DIR / "experiments.jsonl"

# Generated report
EXPERIMENTS_REPORT = _STATE_DIR / "experiments_report.md"

# Bidirectional notebook
NOTEBOOK = _STATE_DIR / "notes.md"

# Ground truth data file (expected to be provided externally)
GROUND_TRUTH_FILE = Path(__file__).parent / "data" / "ground_truth.jsonl"


def ensure_directories():
    """Create all required directories if they don't exist."""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    ITERATIONS_DIR.mkdir(parents=True, exist_ok=True)
    BATCHES_DIR.mkdir(parents=True, exist_ok=True)
    _STATE_DIR.mkdir(parents=True, exist_ok=True)


def get_cache_path(artifact_hash: str) -> Path:
    """Get the cache directory path for a specific artifact hash."""
    return CACHE_DIR / artifact_hash


def get_batch_path(batch_id: int) -> Path:
    """Get the batch-specific directory path."""
    return BATCHES_DIR / f"batch_{batch_id:04d}"
