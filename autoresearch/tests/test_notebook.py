"""Tests for the notebook module."""

import tempfile
from pathlib import Path

from autoresearch.notebook import (
    read_notebook,
    write_notebook,
    append_to_notebook,
    parse_user_constraints,
    get_notebook_summary,
)
from autoresearch.paths import NOTEBOOK


def test_read_empty_notebook():
    """Test reading non-existent notebook."""
    # Remove notebook if it exists
    if NOTEBOOK.exists():
        NOTEBOOK.unlink()
    
    content = read_notebook()
    assert content == ""


def test_write_and_read_notebook():
    """Test writing and reading notebook."""
    test_content = "# Test Notebook\n\nSome content here."
    
    write_notebook(test_content)
    
    content = read_notebook()
    assert content == test_content


def test_append_to_notebook():
    """Test appending sections to notebook."""
    # Start fresh
    write_notebook("# Initial\n")
    
    append_to_notebook("TEST_SECTION", "Test content", author="agent")
    
    content = read_notebook()
    assert "TEST_SECTION" in content
    assert "Test content" in content
    assert "Agent" in content  # author is capitalized


def test_parse_user_constraints():
    """Test parsing user constraints from notebook."""
    content = """# Notebook

## USER

Do not propose length edits.

## OBSERVATION

Some observation.

## USER

Focus on clarity.
"""
    
    constraints = parse_user_constraints(content)
    
    assert len(constraints) == 2
    assert "length" in constraints[0].lower()
    assert "clarity" in constraints[1].lower()


def test_parse_user_constraints_empty():
    """Test parsing when no user constraints exist."""
    content = """# Notebook

## OBSERVATION

Just an observation.
"""
    
    constraints = parse_user_constraints(content)
    
    assert len(constraints) == 0


def test_get_notebook_summary():
    """Test generating notebook summary."""
    content = "# Test\n\nSome content"
    
    summary = get_notebook_summary(content)
    
    assert "NOTEBOOK" in summary
    assert "Test" in summary


def test_get_notebook_summary_empty():
    """Test summary for empty content."""
    summary = get_notebook_summary("")
    
    assert "No notebook content" in summary
