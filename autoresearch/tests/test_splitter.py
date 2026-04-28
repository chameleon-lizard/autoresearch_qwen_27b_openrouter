"""Tests for the splitter module."""

import json
import tempfile
from pathlib import Path

import pandas as pd

from autoresearch.splitter import (
    load_ground_truth,
    stratified_split,
    save_splits,
    get_split_statistics,
)


def test_load_ground_truth():
    """Test loading ground truth from JSONL."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
        f.write('{"input": "test1", "label": "A", "domain": "math"}\n')
        f.write('{"input": "test2", "label": "B", "domain": "science"}\n')
        path = Path(f.name)
    
    try:
        df = load_ground_truth(path)
        assert len(df) == 2
        assert list(df.columns) == ["input", "label", "domain"]
    finally:
        path.unlink()


def test_stratified_split():
    """Test stratified splitting."""
    # Create test data
    data = {
        "input": [f"test{i}" for i in range(100)],
        "label": ["A"] * 50 + ["B"] * 50,
        "domain": ["math"] * 33 + ["science"] * 33 + ["history"] * 34,
    }
    df = pd.DataFrame(data)
    
    # Split
    train, dev, test = stratified_split(df)
    
    # Check sizes
    assert len(train) + len(dev) + len(test) == 100
    assert len(train) == 40
    assert len(dev) == 20
    assert len(test) == 40
    
    # Check stratification (approximately)
    train_dist = train["domain"].value_counts(normalize=True).to_dict()
    overall_dist = df["domain"].value_counts(normalize=True).to_dict()
    
    for domain in overall_dist:
        assert abs(train_dist.get(domain, 0) - overall_dist[domain]) < 0.1


def test_save_splits():
    """Test saving splits to files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        output_dir = Path(tmpdir)
        
        train = pd.DataFrame([{"input": "t1", "label": "A"}])
        dev = pd.DataFrame([{"input": "d1", "label": "B"}])
        test = pd.DataFrame([{"input": "x1", "label": "C"}])
        
        train_path, dev_path, test_path = save_splits(train, dev, test, output_dir)
        
        assert train_path.exists()
        assert dev_path.exists()
        assert test_path.exists()
        
        # Verify content
        with open(train_path) as f:
            line = f.readline()
            data = json.loads(line)
            assert data["input"] == "t1"


def test_get_split_statistics():
    """Test split statistics computation."""
    train = pd.DataFrame([{"domain": "math"}, {"domain": "math"}, {"domain": "science"}])
    dev = pd.DataFrame([{"domain": "math"}, {"domain": "science"}])
    test = pd.DataFrame([{"domain": "math"}, {"domain": "science"}])
    
    stats = get_split_statistics(train, dev, test, "domain")
    
    assert stats["total"] == 7
    assert stats["train"] == 3
    assert stats["dev"] == 2
    assert stats["test"] == 2
    assert "train_distribution" in stats
