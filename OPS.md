# Operations Runbook

This document serves as a runbook for operating the autoresearch loop system.
It is written for an AI agent (Codex, Claude Code, etc.) acting as a DevOps
engineer for the deployed system.

## Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Set API key
export OPENAI_API_KEY="your-key-here"

# 3. Prepare data
loop prepare --ground-truth data/ground_truth.jsonl

# 4. Run loop
loop run --max-iters 10  # Start small
```

## Full Deployment Instructions

### Prerequisites

- Python 3.10+
- pip
- Ground truth data file (JSONL format)
- LLM API key (OpenAI-compatible)

### Step 1: Clone and Install

```bash
cd /path/to/autoresearch_exps/qwen-27b-openrouter
pip install -r requirements.txt
```

### Step 2: Configure

Edit `autoresearch/config.py` or set environment variables:

```bash
export OPENAI_API_KEY="your-key-here"
export AUTORESEARCH_STATE_DIR="/path/to/state"
```

### Step 3: Prepare Data

```bash
# Create data directory
mkdir -p data

# Place ground truth file
cp /path/to/ground_truth.jsonl data/

# Create splits
loop prepare --ground-truth data/ground_truth.jsonl
```

### Step 4: Run

```bash
# Smoke test
loop run --limit 20 --max-iters 5

# Full run
loop run
```

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `OPENAI_API_KEY` | Yes | None | LLM API key |
| `AUTORESEARCH_STATE_DIR` | No | `./state` | State directory path |
| `AUTORESEARCH_DATA_DIR` | No | `./data` | Data directory path |

### Configuration in config.py

```python
# autoresearch/config.py

SCORER = ScorerConfig(
    executable="dredd.py",           # External scorer path
    scorer_model="qwen/qwen-2.5-32b-instruct",
    scorer_api_key=None,             # Or set via env var
    scorer_base_url=None,            # For custom endpoints
    scorer_temperature=0.0,
    scorer_max_tokens=4096,
)

REFINER = RefinerConfig(
    model="qwen/qwen-2.5-32b-instruct",
    api_key=None,                    # Falls back to OPENAI_API_KEY
    base_url=None,
    max_tokens=8192,
    retry_temperatures=(0.0, 0.4, 0.7, 0.9),
    max_retries=4,
)

LOOP = LoopConfig(
    batch_size=5,                    # K siblings per batch
    parallelism=15,                  # Parallel scorer processes
    history_full_count=5,            # Recent iterations in full
    limit=None,                      # Dataset subsample
    max_iterations=None,             # None for infinite
    random_seed=42,
)
```

## Health Check

### Verify System is Running

```bash
# Check if loop process exists
ps aux | grep "loop run"

# Check recent log entries
tail -n 5 state/experiments.jsonl

# Check report was generated
ls -la state/experiments_report.md

# Check cache is being used
ls state/cache/ | wc -l
```

### Verify Data Integrity

```bash
# Check splits exist
ls -la data/*.jsonl

# Verify log is valid JSONL
python -c "import json; [json.loads(l) for l in open('state/experiments.jsonl')]"

# Check cache entries are valid
python -c "import json; print(json.load(open('state/cache/abc123/result.json')))"
```

## Log Locations

| File | Description |
|------|-------------|
| `state/experiments.jsonl` | Append-only experiment log |
| `state/experiments_report.md` | Human-readable report |
| `state/notes.md` | Bidirectional notebook |
| `state/batches/batch_NNNN/` | Batch-specific data |
| `state/cache/<hash>/` | Cached scoring results |

### Log Format

Each line in `experiments.jsonl`:

```json
{
  "iter": 47,
  "batch": 10,
  "ts": "2024-01-15T14:30:00",
  "artifact_hash": "a1b2c3d4e5f67890",
  "parent": 42,
  "plan_id": "add_length_constraint",
  "rationale": "...",
  "artifact": "...",
  "metrics_train": {"kappa": 0.34, "f1": 0.42, "spearman": 0.29},
  "metrics_dev": {"kappa": 0.335, "f1": 0.412, "spearman": 0.287},
  "metrics_test": {"kappa": 0.274, "f1": 0.38, "spearman": 0.25},
  "stage_a_summary": "..."
}
```

### Query Logs

```bash
# Get latest iteration
tail -n 1 state/experiments.jsonl | python -m json.tool

# Get all entries from batch 5
grep '"batch": 5' state/experiments.jsonl

# Get best dev kappa
python -c "
import json
entries = [json.loads(l) for l in open('state/experiments.jsonl')]
best = max(entries, key=lambda e: e['metrics_dev']['kappa'])
print(f'Iter {best[\"iter\"]}: dev-κ={best[\"metrics_dev\"][\"kappa\"]:.3f}')
"

# Get dev-test gap trend
python -c "
import json
entries = [json.loads(l) for l in open('state/experiments.jsonl')]
for e in entries[-10:]:
    gap = e['metrics_dev']['kappa'] - e['metrics_test']['kappa']
    print(f'Iter {e[\"iter\"]}: gap={gap:+.3f}')
"
```

## Common Failure Modes

### 1. Container OOM (Out of Memory)

**Symptoms**: Process killed, no error message

**Resolution**:
```bash
# Check memory usage
free -h

# Reduce parallelism
# Edit config.py: LOOP.parallelism = 5

# Or reduce batch size
# Edit config.py: LOOP.batch_size = 3
```

### 2. Agent Timeout

**Symptoms**: `subprocess.TimeoutExpired` in logs

**Resolution**:
```bash
# Check scorer is responding
python dredd.py --help

# Increase timeout in scorer.py (currently 300s)
# Or reduce dataset size with --limit
```

### 3. Git Push Failure

**Symptoms**: `remote: Repository not found`

**Resolution**:
```bash
# Check git remote
git remote -v

# Re-add remote if needed
git remote set-url origin <url>

# Push again
git push
```

### 4. Database Connection Loss

**Symptoms**: Connection errors (if using external DB)

**Resolution**:
```bash
# This system uses file-based storage, no DB
# Check disk space
df -h

# Check file permissions
ls -la state/
```

### 5. LLM API Errors

**Symptoms**: `APIError`, `RateLimitError`

**Resolution**:
```bash
# Check API key
echo $OPENAI_API_KEY

# Check rate limits
# Wait and retry (built-in retry logic)

# Reduce parallelism to stay under rate limits
# Edit config.py: LOOP.parallelism = 5
```

### 6. Truncated LLM Output

**Symptoms**: Missing closing tags, incomplete JSON

**Resolution**:
```bash
# Check attempt files
cat state/batches/batch_NNNN/stage_attempt_*.txt

# Reduce input size (compress history)
# Edit config.py: LOOP.history_full_count = 3

# Or reduce expected output
# Edit meta-prompts in refiner.py
```

## Backup and Restore

### Backup

```bash
# Full backup
tar czf autoresearch_backup_$(date +%Y%m%d).tar.gz \
    state/ data/ autoresearch/ config.py

# Backup just the log (critical)
cp state/experiments.jsonl experiments_backup.jsonl

# Backup cache (large but valuable)
tar czf cache_backup.tar.gz state/cache/
```

### Restore

```bash
# Restore from full backup
tar xzf autoresearch_backup_YYYYMMDD.tar.gz

# Restore just the log
cp experiments_backup.jsonl state/experiments.jsonl

# Restore cache
tar xzf cache_backup.tar.gz
```

### What to Backup

| Priority | File/Directory | Reason |
|----------|---------------|--------|
| Critical | `state/experiments.jsonl` | All iteration history |
| Critical | `state/cache/` | Avoid re-scoring |
| High | `state/notes.md` | Human interventions |
| Medium | `data/` | Can be regenerated |
| Low | `state/batches/` | Debug info only |

## Scaling

### Scale Up (More Parallelism)

```python
# Edit config.py
LOOP.parallelism = 30  # From 15
LOOP.batch_size = 10   # From 5
```

### Scale Down (Less Resources)

```python
# Edit config.py
LOOP.parallelism = 5
LOOP.batch_size = 3
```

### Multiple Instances

```bash
# Run multiple loops in parallel
AUTORESEARCH_STATE_DIR=/tmp/runA loop run
AUTORESEARCH_STATE_DIR=/tmp/runB loop run
```

## Update and Rollback

### Update

```bash
# 1. Backup current state
tar czf backup_$(date +%Y%m%d_%H%M%S).tar.gz state/

# 2. Pull updates
git pull

# 3. Install new dependencies
pip install -r requirements.txt

# 4. Resume loop
loop run
```

### Rollback

```bash
# 1. Stop current loop
# (Ctrl+C or kill process)

# 2. Restore code
git checkout <previous-commit>

# 3. Restore dependencies
pip install -r requirements.txt

# 4. State is preserved, just resume
loop run
```

## Troubleshooting Checklist

1. **Check logs**: `tail -f state/experiments.jsonl`
2. **Check report**: `cat state/experiments_report.md`
3. **Check notebook**: `cat state/notes.md`
4. **Check disk space**: `df -h`
5. **Check memory**: `free -h`
6. **Check API key**: `echo $OPENAI_API_KEY`
7. **Check data files**: `ls -la data/`
8. **Check cache**: `ls state/cache/ | wc -l`

## Emergency Procedures

### Loop Stuck

```bash
# Check what it's doing
tail -f state/experiments.jsonl

# If truly stuck, kill and restart
pkill -f "loop run"
loop run
```

### Corrupted Log

```bash
# Backup corrupted log
cp state/experiments.jsonl state/experiments.jsonl.corrupted

# Try to repair (remove last incomplete line)
head -n -1 state/experiments.jsonl.corrupted > state/experiments.jsonl

# Verify
python -c "import json; [json.loads(l) for l in open('state/experiments.jsonl')]"
```

### Full Reset

```bash
# Keep cache, reset everything else
loop reset

# Or full reset including cache
rm -rf state/
mkdir -p state/{cache,iterations,batches}
```
