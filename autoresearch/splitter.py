"""
Stratified dataset splitting for train/dev/test.

See DesignDoc.md section 2.4 and 3 for the importance of held-out evaluation sets.
This module provides deterministic, stratified splitting that can be reproduced
across runs.
"""

import json
from pathlib import Path
from typing import Any

import pandas as pd
from sklearn.model_selection import train_test_split

from .config import SplitConfig, SPLIT


def load_ground_truth(filepath: Path) -> pd.DataFrame:
    """Load ground truth data from a JSONL file."""
    records = []
    with open(filepath, "r") as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return pd.DataFrame(records)


def stratified_split(
    df: pd.DataFrame,
    config: SplitConfig | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """
    Perform stratified train/dev/test split.
    
    Args:
        df: Ground truth dataframe
        config: Split configuration (uses SPLIT defaults if None)
    
    Returns:
        Tuple of (train, dev, test) dataframes
    
    The split is deterministic given the same seed and input data.
    Stratification ensures each split has similar distribution of the
    stratify_column (e.g., domain).
    """
    if config is None:
        config = SPLIT
    
    # First split: separate test set
    train_dev, test = train_test_split(
        df,
        test_size=config.test_ratio,
        stratify=df[config.stratify_column],
        random_state=config.random_seed,
    )
    
    # Second split: separate dev from train
    # Adjust ratios since we're splitting train_dev, not the full dataset
    dev_ratio_from_train_dev = config.dev_ratio / (config.train_ratio + config.dev_ratio)
    
    train, dev = train_test_split(
        train_dev,
        test_size=dev_ratio_from_train_dev,
        stratify=train_dev[config.stratify_column],
        random_state=config.random_seed,
    )
    
    return train, dev, test


def save_splits(
    train: pd.DataFrame,
    dev: pd.DataFrame,
    test: pd.DataFrame,
    output_dir: Path,
) -> tuple[Path, Path, Path]:
    """Save splits to JSONL files."""
    output_dir.mkdir(parents=True, exist_ok=True)
    
    train_path = output_dir / "train.jsonl"
    dev_path = output_dir / "dev.jsonl"
    test_path = output_dir / "test.jsonl"
    
    for df, path in [(train, train_path), (dev, dev_path), (test, test_path)]:
        with open(path, "w") as f:
            for _, row in df.iterrows():
                f.write(json.dumps(row.to_dict()) + "\n")
    
    return train_path, dev_path, test_path


def get_split_statistics(
    train: pd.DataFrame,
    dev: pd.DataFrame,
    test: pd.DataFrame,
    stratify_column: str,
) -> dict[str, Any]:
    """Compute and return split statistics for verification."""
    all_data = pd.concat([train, dev, test])
    
    def distribution(df: pd.DataFrame) -> dict[str, float]:
        return df[stratify_column].value_counts(normalize=True).to_dict()
    
    return {
        "total": len(all_data),
        "train": len(train),
        "dev": len(dev),
        "test": len(test),
        "train_distribution": distribution(train),
        "dev_distribution": distribution(dev),
        "test_distribution": distribution(test),
        "overall_distribution": distribution(all_data),
    }
