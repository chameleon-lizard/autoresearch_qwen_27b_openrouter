# Refiner Module Documentation

## Overview

The refiner module (`refiner.py`) implements the four-stage LLM interaction
for proposing artifact mutations. Each stage has its own meta-prompt and
output format.

## DesignDoc Reference

See DesignDoc.md sections:
- **4**: The four refiner stages (A / B / C / M)
- **7**: Stochasticity for retries

## The Four Stages

### Stage A: Disagreement Generalisation

**Input**: Examples where artifact disagrees with ground truth
**Output**: Free-text generalisation of failure modes

Purpose: Force an abstraction step to prevent overfitting to specific examples.

```python
from autoresearch.refiner import stage_a

errors = [
    {"input": "...", "prediction": "A", "label": "B"},
    ...
]

output = stage_a(errors, batch_id=1)
print(output.summary)
# "The artifact tends to over-predict category A when..."
```

### Stage B: Proposal Generation

**Input**: Parent artifact, Stage-A summary, history, notebook
**Output**: K sibling candidates with plan_id, rationale, artifact

Purpose: Generate diverse, focused mutations for parallel scoring.

```python
from autoresearch.refiner import stage_b

output = stage_b(
    parent_artifact="My prompt...",
    stage_a_summary="Tends to over-predict A...",
    history_text="iter=1... iter=2...",
    notebook_summary="Do not propose length edits",
    k=5,
    batch_id=1,
)

for candidate in output.candidates:
    print(f"{candidate.plan_id}: {candidate.rationale}")
```

### Stage C: Selection

**Input**: History with metrics, best-so-far callout
**Output**: Either `iter=N` or `merge=N1,N2,...`

Purpose: Choose the best parent for the next iteration, considering
trajectory and overfitting, not just argmax.

```python
from autoresearch.refiner import stage_c

output = stage_c(
    history_text="iter=1 κ=0.3... iter=2 κ=0.35...",
    best_so_far_iter=27,
    batch_id=1,
)

print(output.action)  # "iter=27" or "merge=25,27"
print(output.rationale)
```

### Stage M: Merge Synthesis

**Input**: Multiple parent artifacts
**Output**: Single merged artifact

Purpose: Combine strengths of multiple branches (different cognitive task
than proposing a delta).

```python
from autoresearch.refiner import stage_m

output = stage_m(
    parent_artifacts=[
        (25, "Prompt from iter 25..."),
        (27, "Prompt from iter 27..."),
    ],
    batch_id=1,
)

print(output.artifact)
```

## LLM Call Configuration

The `call_llm` function handles:
- Retry logic with varying temperatures: `[0.0, 0.4, 0.7, 0.9]`
- Debug output saving per attempt
- OpenAI API integration

Configuration in `config.py`:

```python
REFINER = RefinerConfig(
    model="qwen/qwen-2.5-32b-instruct",
    api_key="...",
    max_tokens=8192,
    retry_temperatures=(0.0, 0.4, 0.7, 0.9),
    max_retries=4,
)
```

## Output Parsing

Each stage has a dedicated parser:
- `parse_stage_b_output`: Extracts candidates from delimited format
- Stage C/M parsing is inline (simpler formats)

## Debug Output

For each batch, attempt files are saved:

```
state/batches/batch_0001/
├── stage_attempt_1.txt
├── stage_attempt_2.txt
└── ...
```

Each contains:
- Temperature used
- Response length
- Parse metadata
- Full response text

## Meta-Prompts

The system prompts are defined as constants:
- `STAGE_A_SYSTEM`
- `STAGE_B_SYSTEM`
- `STAGE_C_SYSTEM`
- `STAGE_M_SYSTEM`

These can be modified to tune the refiner's behaviour without changing code.
