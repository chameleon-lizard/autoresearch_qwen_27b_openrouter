# Splitter Module Documentation

## Overview

The splitter module (`splitter.py`) provides deterministic, stratified train/dev/test
splitting for the autoresearch loop. This is a critical component because:

1. **Reproducibility**: The same input data always produces the same splits
2. **Stratification**: Each split maintains similar distribution of key attributes (e.g., domain)
3. **Held-out test set**: The test set is never exposed to the loop, preventing overfitting

## DesignDoc Reference

See DesignDoc.md sections:
- **2.4**: Held-out evaluation set
- **3**: Reference architecture (splitting is the first step)

## API

### `load_ground_truth(filepath: Path) -> pd.DataFrame`

Load ground truth data from a JSONL file. Each line should be a valid JSON object.

### `stratified_split(df: pd.DataFrame, config: SplitConfig | None = None) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]`

Perform stratified train/dev/test split.

**Parameters:**
- `df`: Ground truth dataframe with at least a `domain` column (or custom stratify_column)
- `config`: Optional SplitConfig; uses defaults from `config.SPLIT` if None

**Returns:**
- Tuple of (train, dev, test) dataframes

**Default ratios:** 40% train, 20% dev, 40% test

### `save_splits(train, dev, test, output_dir) -> tuple[Path, Path, Path]`

Save the three splits to JSONL files in the specified directory.

### `get_split_statistics(train, dev, test, stratify_column) -> dict`

Compute statistics about the splits for verification. Returns counts and
distributions for each split.

## Usage Example

```python
from autoresearch.splitter import load_ground_truth, stratified_split, get_split_statistics
from autoresearch.paths import GROUND_TRUTH_FILE

# Load data
df = load_ground_truth(GROUND_TRUTH_FILE)

# Split
train, dev, test = stratified_split(df)

# Verify
stats = get_split_statistics(train, dev, test, "domain")
print(stats)
# {
#   "total": 1000,
#   "train": 400,
#   "dev": 200,
#   "test": 400,
#   "train_distribution": {"domain_a": 0.3, "domain_b": 0.7},
#   ...
# }
```

## Configuration

Split configuration is in `config.py`:

```python
SPLIT = SplitConfig(
    train_ratio=0.4,
    dev_ratio=0.2,
    test_ratio=0.4,
    stratify_column="domain",
    random_seed=42,
)
```

## Important Notes

1. **Determinism**: The split is fully deterministic given the same seed and input
2. **Stratification column**: Must exist in the input dataframe and have categorical values
3. **Minimum samples**: Each stratum needs enough samples to be split across all three sets
4. **Test set secrecy**: The test set is logged but NEVER surfaced to the proposer or selector

## Testing

```bash
pytest tests/test_splitter.py
```
