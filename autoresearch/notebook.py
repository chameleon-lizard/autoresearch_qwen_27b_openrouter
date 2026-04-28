from __future__ import annotations

"""
Bidirectional notebook for human-agent communication.

See DesignDoc.md section 2.6: "Bi-directional notebook"
A shared text file that:
- The user can edit at any time during a run
- The agent can append to between iterations
- Is re-read fresh every iteration (never cached)

This gives the human an out-of-band channel to inject domain knowledge
mid-run without restarting.
"""

from datetime import datetime

from .paths import NOTEBOOK, ensure_directories


def read_notebook() -> str:
    """
    Read the current contents of the notebook.
    
    Returns empty string if notebook doesn't exist.
    """
    if not NOTEBOOK.exists():
        return ""

    with open(NOTEBOOK, "r") as f:
        return f.read()


def write_notebook(content: str) -> None:
    """
    Write content to the notebook (overwrites).
    """
    ensure_directories()

    with open(NOTEBOOK, "w") as f:
        f.write(content)


def append_to_notebook(section: str, content: str, author: str = "agent") -> None:
    """
    Append a new section to the notebook.
    
    Args:
        section: Section title
        content: Section content
        author: "user" or "agent"
    """
    ensure_directories()

    timestamp = datetime.now().isoformat()

    new_section = f"""## {section}

*{author.title()} - {timestamp}*

{content}

---

"""

    with open(NOTEBOOK, "a") as f:
        f.write(new_section)


def create_initial_notebook() -> None:
    """Create an initial notebook with instructions."""
    if NOTEBOOK.exists():
        return

    initial_content = f"""# Bidirectional Notebook

*Created: {datetime.now().isoformat()}*

This notebook is a shared communication channel between you (the human)
and the autoresearch agent.

## How to Use

### For Humans (You)

Add sections with `## USER` to inject constraints, observations, or
instructions. The agent will read these fresh every iteration.

Example:

    ## USER
    
    Do not propose any more length-related edits, that lever is exhausted.
    Focus on improving clarity instead.

### For the Agent

The agent appends observations between iterations. These are prefixed
with `## OBSERVATION` or similar.

## Rules

1. User sections (## USER) are hard constraints
2. Agent sections are observations and suggestions
3. Both can add ## IDEA sections for proposals
4. The notebook is re-read every iteration (never cached)

---

## Notes

"""

    write_notebook(initial_content)


def parse_user_constraints(content: str) -> list[str]:
    """
    Extract user constraints from the notebook.
    
    Looks for sections starting with "## USER" and returns their content.
    """
    constraints = []
    current_section = None
    current_content = []

    for line in content.split("\n"):
        if line.startswith("## USER"):
            if current_section == "USER" and current_content:
                constraints.append("\n".join(current_content).strip())
            current_section = "USER"
            current_content = []
        elif line.startswith("##"):
            if current_section == "USER" and current_content:
                constraints.append("\n".join(current_content).strip())
            current_section = line[2:].strip()
            current_content = []
        elif current_section == "USER":
            current_content.append(line)

    # Don't forget the last section
    if current_section == "USER" and current_content:
        constraints.append("\n".join(current_content).strip())

    return constraints


def get_notebook_summary(content: str) -> str:
    """
    Generate a summary of the notebook for LLM context.
    
    Includes user constraints and recent observations.
    """
    if not content.strip():
        return "No notebook content."

    lines = [
        "=== NOTEBOOK ===",
        "",
    ]

    # Extract user constraints
    constraints = parse_user_constraints(content)
    if constraints:
        lines.append("### User Constraints")
        for i, constraint in enumerate(constraints, 1):
            lines.append(f"{i}. {constraint}")
        lines.append("")

    # Include full content if not too long
    if len(content) < 2000:
        lines.append("### Full Content")
        lines.append(content)
    else:
        lines.append("### Recent Content (last 1000 chars)")
        lines.append(content[-1000:])

    return "\n".join(lines)
