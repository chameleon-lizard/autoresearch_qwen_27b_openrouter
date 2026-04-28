# Autoresearch Loop

Autonomous LLM-driven optimization loop for iteratively improving artifacts
(prompts, configs, code patches, etc.).

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Set your LLM API key
export OPENAI_API_KEY="your-key-here"

# Prepare data splits
loop prepare --ground-truth data/ground_truth_sample.jsonl

# Run the loop (start small)
loop run --max-iters 5 --limit 20
```

## Documentation

- **WIKI.md**: Executive summary and architecture overview
- **DesignDoc.md**: Design patterns and lessons learned
- **OPS.md**: Operations runbook for deployment and troubleshooting
- **PROGRESS.md**: Implementation progress tracking

## Module Documentation

Each module has its own documentation file:
- `autoresearch/DOCUMENTATION_SPLITTER.md`
- `autoresearch/DOCUMENTATION_SCORER.md`
- `autoresearch/DOCUMENTATION_METRICS.md`
- `autoresearch/DOCUMENTATION_REFINER.md`
- `autoresearch/DOCUMENTATION_HISTORY.md`
- `autoresearch/DOCUMENTATION_REPORT.md`
- `autoresearch/DOCUMENTATION_LOOP.md`
- `autoresearch/DOCUMENTATION_NOTEBOOK.md`
- `autoresearch/DOCUMENTATION_CLI.md`

## Commands

```bash
loop run              # Run the main loop (infinite)
loop run --max-iters N  # Run for N iterations
loop run --limit N    # Subsample dataset for fast testing
loop report          # Regenerate experiments report
loop reset           # Reset state (preserve cache)
loop score <artifact>  # Score a single artifact
loop prepare         # Prepare data splits from ground truth
```

## Testing

```bash
# Run all tests
pytest autoresearch/tests/ -v

# Current status: 22/22 tests passing
```

## Configuration

All configuration is in `autoresearch/config.py`:

```python
LOOP = LoopConfig(
    batch_size=5,           # K siblings per batch
    parallelism=15,         # Parallel scorer processes
    max_iterations=None,    # None for infinite
)
```

## License

MIT
