# Scorer Module Documentation

## Overview

The scorer module (`scorer.py`) wraps an external scorer (e.g., `dredd.py`) and
provides content-hash-based caching to avoid re-scoring artifacts. This is
critical for efficiency and reproducibility.

## DesignDoc Reference

See DesignDoc.md sections:
- **2.1**: Cache by content hash
- **10.6**: Wrap, don't reimplement

## Key Features

### 1. Content-Hash Caching

Every artifact is hashed using `sha256(artifact)[:16]`. Scoring results are
cached by this hash, so:
- Re-running the loop never re-scores seen artifacts
- The cache is self-describing (includes artifact text)
- Refactoring the loop reproduces identical metrics for cached artifacts

### 2. External Scorer Wrapper

The module wraps any scorer that:
- Takes an artifact file and data file as input
- Outputs predictions in JSONL format

### 3. Crash-Safe Design

- Each scoring result is saved atomically
- Partial runs can be resumed
- Cache hits are checked before every scoring attempt

## API

### `compute_artifact_hash(artifact: str) -> str`

Compute the 16-character hash of an artifact.

```python
hash = compute_artifact_hash("My prompt text...")
# "a1b2c3d4e5f67890"
```

### `score_artifact(artifact, data_path, split_name, ...) -> ScoringResult`

Score an artifact on a dataset split, with automatic caching.

**Parameters:**
- `artifact`: The artifact text to score
- `data_path`: Path to JSONL dataset
- `split_name`: "train", "dev", or "test"
- `scorer_executable`: Path to scorer script (default: "dredd.py")
- `scorer_args`: Additional arguments for the scorer

**Returns:**
```python
ScoringResult(
    artifact_hash="a1b2c3d4e5f67890",
    split="dev",
    metrics={"kappa": 0.335, "f1": 0.412, "spearman": 0.287},
    predictions=["label_a", "label_b", ...],
    labels=["label_a", "label_c", ...],
    success=True,
)
```

### `load_cached_result(cache_path) -> ScoringResult | None`

Load a cached result if it exists.

### `save_cached_result(result, cache_path, artifact) -> None`

Save a result to cache.

## Cache Structure

```
state/cache/<artifact_hash>/
├── artifact.txt      # The artifact text (for self-describing cache)
└── result.json       # Scoring result
```

## Usage Example

```python
from autoresearch.scorer import score_artifact
from autoresearch.paths import ensure_directories

ensure_directories()

# Score on train set
train_result = score_artifact(
    artifact="My prompt...",
    data_path=Path("data/train.jsonl"),
    split_name="train",
)

print(f"Train κ={train_result.metrics['kappa']:.3f}")

# Re-running with same artifact hits cache
train_result2 = score_artifact(
    artifact="My prompt...",  # Same artifact
    data_path=Path("data/train.jsonl"),
    split_name="train",
)
# [CACHE HIT] a1b2c3d4e5f67890 for train
```

## External Scorer Interface

The external scorer should:
1. Accept `--artifact <path>` and `--data <path>` arguments
2. Output one JSON object per line with a "prediction" or "label" field
3. Return exit code 0 on success, non-zero on failure

Example scorer output:
```json
{"id": 1, "prediction": "label_a"}
{"id": 2, "prediction": "label_b"}
```

## Configuration

Scorer configuration is in `config.py`:

```python
SCORER = ScorerConfig(
    executable="dredd.py",
    scorer_model="qwen/qwen-2.5-32b-instruct",
    scorer_temperature=0.0,
    scorer_max_tokens=4096,
)
```

## Parallel Scoring

For batch mode, score multiple artifacts in parallel:

```python
from concurrent.futures import ProcessPoolExecutor

artifacts = ["prompt1", "prompt2", "prompt3"]
splits = ["train", "dev", "test"]

with ProcessPoolExecutor(max_workers=15) as executor:
    futures = [
        executor.submit(score_artifact, art, split_path, split)
        for art in artifacts
        for split_path, split in split_paths
    ]
    results = [f.result() for f in futures]
```
