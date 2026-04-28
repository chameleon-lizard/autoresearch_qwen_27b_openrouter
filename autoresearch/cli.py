from __future__ import annotations

"""
Command-line interface for the autoresearch loop.

See DesignDoc.md section 12: "Minimal CLI surface"

Commands:
- loop run              # Main loop, infinite
- loop run --max-iters N  # Bounded for tests
- loop run --limit N    # Subsample dataset for fast smoke test
- loop report          # Regenerate experiments_report.md
- loop reset           # Delete iterations + log; preserve cache
- loop score <artifact>  # Score one artifact, print metrics
"""

import argparse
import shutil
import sys
from pathlib import Path

from .config import LOOP
from .history import read_log
from .paths import (
    CACHE_DIR,
    EXPERIMENTS_LOG,
    EXPERIMENTS_REPORT,
    ITERATIONS_DIR,
    BATCHES_DIR,
)
from .report import generate_report, print_report_summary
from .loop import run_loop, score_single_artifact
from .splitter import load_ground_truth, stratified_split, save_splits, get_split_statistics
from .paths import GROUND_TRUTH_FILE


def cmd_run(args: argparse.Namespace) -> None:
    """Run the main loop."""
    # Prepare data paths
    data_dir = Path(args.data) if args.data else Path("data")
    
    # Check if splits exist, create if needed
    train_path = data_dir / "train.jsonl"
    dev_path = data_dir / "dev.jsonl"
    test_path = data_dir / "test.jsonl"
    
    if not all(p.exists() for p in [train_path, dev_path, test_path]):
        print("Splits not found. Creating from ground truth...")
        
        if not GROUND_TRUTH_FILE.exists():
            print(f"Error: Ground truth file not found: {GROUND_TRUTH_FILE}")
            sys.exit(1)
        
        df = load_ground_truth(GROUND_TRUTH_FILE)
        
        if args.limit:
            # Subsample for fast testing
            df = df.sample(n=min(args.limit, len(df)), random_state=42)
            print(f"Subsampled to {len(df)} examples")
        
        train, dev, test = stratified_split(df)
        save_splits(train, dev, test, data_dir)
        
        stats = get_split_statistics(train, dev, test, "domain")
        print(f"Created splits: train={stats['train']}, dev={stats['dev']}, test={stats['test']}")
    
    # Run loop
    config = LOOP
    config.max_iterations = args.max_iters
    
    run_loop(
        train_path=train_path,
        dev_path=dev_path,
        test_path=test_path,
        max_iterations=config.max_iterations,
        config=config,
    )


def cmd_report(args: argparse.Namespace) -> None:
    """Regenerate the report."""
    print("Generating report...")
    generate_report()
    print(f"Report saved to: {EXPERIMENTS_REPORT}")
    print_report_summary()


def cmd_reset(args: argparse.Namespace) -> None:
    """Reset iterations and log, preserve cache."""
    print("Resetting experiment state...")
    
    # Remove log
    if EXPERIMENTS_LOG.exists():
        EXPERIMENTS_LOG.unlink()
        print(f"Removed: {EXPERIMENTS_LOG}")
    
    # Remove report
    if EXPERIMENTS_REPORT.exists():
        EXPERIMENTS_REPORT.unlink()
        print(f"Removed: {EXPERIMENTS_REPORT}")
    
    # Remove iterations
    if ITERATIONS_DIR.exists():
        shutil.rmtree(ITERATIONS_DIR)
        print(f"Removed: {ITERATIONS_DIR}")
    
    # Remove batches
    if BATCHES_DIR.exists():
        shutil.rmtree(BATCHES_DIR)
        print(f"Removed: {BATCHES_DIR}")
    
    # Preserve cache
    if CACHE_DIR.exists():
        print(f"Preserved: {CACHE_DIR}")
    
    print("\nReset complete. Cache preserved.")


def cmd_score(args: argparse.Namespace) -> None:
    """Score a single artifact."""
    # Prepare data paths
    data_dir = Path(args.data) if args.data else Path("data")
    
    train_path = data_dir / "train.jsonl"
    dev_path = data_dir / "dev.jsonl"
    test_path = data_dir / "test.jsonl"
    
    if not all(p.exists() for p in [train_path, dev_path, test_path]):
        print("Error: Splits not found. Run 'loop prepare' first.")
        sys.exit(1)
    
    artifact = args.artifact
    
    # If artifact is a file path, read it
    if Path(artifact).exists():
        with open(artifact) as f:
            artifact = f.read()
    
    score_single_artifact(artifact, train_path, dev_path, test_path)


def cmd_prepare(args: argparse.Namespace) -> None:
    """Prepare data splits from ground truth."""
    ground_truth = Path(args.ground_truth) if args.ground_truth else GROUND_TRUTH_FILE
    output_dir = Path(args.output) if args.output else Path("data")
    
    if not ground_truth.exists():
        print(f"Error: Ground truth file not found: {ground_truth}")
        sys.exit(1)
    
    print(f"Loading ground truth from: {ground_truth}")
    df = load_ground_truth(ground_truth)
    print(f"Loaded {len(df)} examples")
    
    if args.limit:
        df = df.sample(n=min(args.limit, len(df)), random_state=42)
        print(f"Subsampled to {len(df)} examples")
    
    print("Creating stratified splits...")
    train, dev, test = stratified_split(df)
    save_splits(train, dev, test, output_dir)
    
    stats = get_split_statistics(train, dev, test, "domain")
    
    print("\nSplit statistics:")
    print(f"  Total: {stats['total']}")
    print(f"  Train: {stats['train']} ({stats['train_distribution']})")
    print(f"  Dev:   {stats['dev']} ({stats['dev_distribution']})")
    print(f"  Test:  {stats['test']} ({stats['test_distribution']})")
    
    print(f"\nSplits saved to: {output_dir}")


def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Autoresearch loop - autonomous LLM-driven optimization"
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Commands")
    
    # loop run
    run_parser = subparsers.add_parser("run", help="Run the main loop")
    run_parser.add_argument(
        "--max-iters",
        type=int,
        default=None,
        help="Maximum iterations (default: infinite)",
    )
    run_parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Subsample dataset to N examples (for fast testing)",
    )
    run_parser.add_argument(
        "--data",
        type=str,
        default=None,
        help="Path to data directory (default: ./data)",
    )
    run_parser.set_defaults(func=cmd_run)
    
    # loop report
    report_parser = subparsers.add_parser("report", help="Regenerate report")
    report_parser.set_defaults(func=cmd_report)
    
    # loop reset
    reset_parser = subparsers.add_parser("reset", help="Reset state (preserve cache)")
    reset_parser.set_defaults(func=cmd_reset)
    
    # loop score
    score_parser = subparsers.add_parser("score", help="Score a single artifact")
    score_parser.add_argument("artifact", help="Artifact text or path to file")
    score_parser.add_argument(
        "--data",
        type=str,
        default=None,
        help="Path to data directory (default: ./data)",
    )
    score_parser.set_defaults(func=cmd_score)
    
    # loop prepare
    prepare_parser = subparsers.add_parser("prepare", help="Prepare data splits")
    prepare_parser.add_argument(
        "--ground-truth",
        type=str,
        default=None,
        help="Path to ground truth file",
    )
    prepare_parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Output directory for splits (default: ./data)",
    )
    prepare_parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Subsample to N examples",
    )
    prepare_parser.set_defaults(func=cmd_prepare)
    
    args = parser.parse_args()
    
    if args.command is None:
        parser.print_help()
        sys.exit(1)
    
    args.func(args)


if __name__ == "__main__":
    main()
