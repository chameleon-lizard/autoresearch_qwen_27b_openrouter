#!/usr/bin/env python3
"""
Mock scorer for testing the autoresearch loop.

This scorer randomly predicts labels based on the artifact text hash.
It's deterministic given the same artifact and data, making it useful
for testing without needing a real LLM.

Usage:
    python mock_scorer.py --artifact prompt.txt --data data/train.jsonl
"""

import argparse
import hashlib
import json
import random
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description="Mock scorer for testing")
    parser.add_argument("--artifact", type=str, required=True, help="Path to artifact file")
    parser.add_argument("--data", type=str, required=True, help="Path to data file")
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    args = parser.parse_args()
    
    # Read artifact
    with open(args.artifact) as f:
        artifact = f.read()
    
    # Compute hash for deterministic randomness
    artifact_hash = int(hashlib.sha256(artifact.encode()).hexdigest()[:8], 16)
    random.seed(artifact_hash + args.seed)
    
    # Read data and generate predictions
    with open(args.data) as f:
        for line in f:
            if line.strip():
                record = json.loads(line)
                
                # Get possible labels
                true_label = record.get("label", record.get("ground_truth", "unknown"))
                
                # Generate prediction based on artifact hash
                # Better artifacts (higher hash) get more correct predictions
                accuracy = min(0.95, 0.3 + (artifact_hash % 100) / 200)
                
                if random.random() < accuracy:
                    prediction = true_label
                else:
                    # Wrong prediction - pick a different label
                    prediction = "wrong_" + true_label
                
                print(json.dumps({"id": record.get("id", 0), "prediction": prediction}))


if __name__ == "__main__":
    main()
