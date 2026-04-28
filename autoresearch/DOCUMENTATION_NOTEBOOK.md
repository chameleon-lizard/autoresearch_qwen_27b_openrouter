# Notebook Module Documentation

## Overview

The notebook module (`notebook.py`) implements the bidirectional notebook
for human-agent communication. This is a critical intervention surface
that allows mid-run guidance without restarting.

## DesignDoc Reference

See DesignDoc.md sections:
- **2.6**: Bi-directional notebook
- **10.7**: The notebook is load-bearing

## Key Features

### 1. Shared Communication Channel

- Humans can edit at any time
- Agent appends between iterations
- Re-read fresh every iteration (never cached)

### 2. User Constraints

Sections starting with `## USER` are treated as hard constraints that
the agent must follow.

### 3. Agent Observations

The agent appends observations with `## OBSERVATION` sections.

## API

### `read_notebook() -> str`

Read current notebook contents.

```python
from autoresearch.notebook import read_notebook

content = read_notebook()
```

### `write_notebook(content: str) -> None`

Overwrite the notebook.

### `append_to_notebook(section, content, author="agent") -> None`

Append a new section.

```python
from autoresearch.notebook import append_to_notebook

append_to_notebook(
    "OBSERVATION",
    "The dev-test gap is increasing. Consider pausing.",
    author="agent"
)
```

### `create_initial_notebook() -> None`

Create an initial notebook with instructions.

### `parse_user_constraints(content: str) -> list[str]`

Extract user constraints from the notebook.

```python
from autoresearch.notebook import read_notebook, parse_user_constraints

content = read_notebook()
constraints = parse_user_constraints(content)
# ["Do not propose length-related edits", ...]
```

### `get_notebook_summary(content: str) -> str`

Generate a summary for LLM context.

## Usage Example

### Human Intervention

Edit `state/notes.md` directly:

```markdown
## USER

Do not propose any more length-related edits, that lever is exhausted.
Focus on improving clarity instead.

## IDEA

Consider adding examples of good responses to the prompt.
```

The next iteration will read this and respect the constraint.

### Agent Observation

```python
from autoresearch.notebook import append_to_notebook

append_to_notebook(
    "OBSERVATION",
    "Batch 10 complete. Dev κ improved by 0.015. "
    "Test κ also improved, gap remains stable at 0.08.",
    author="agent"
)
```

## Notebook Format

```markdown
# Bidirectional Notebook

*Created: 2024-01-15T10:00:00*

## How to Use

... instructions ...

---

## USER

Do not propose length-related edits.

---

## OBSERVATION

*agent - 2024-01-15T14:30:00*

Batch 5 complete. Dev κ = 0.335.

---

## IDEA

Consider adding few-shot examples.

---
```

## Best Practices

1. **Be specific**: "Do not propose X" is better than "Be careful"
2. **One constraint per section**: Easier to track
3. **Use ## IDEA for proposals**: Distinguish from constraints
4. **Agent should acknowledge**: Reference user constraints in proposals
