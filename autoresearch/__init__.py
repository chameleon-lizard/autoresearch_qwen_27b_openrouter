"""
Autoresearch Loop - Autonomous LLM-driven optimization.

This package implements the autoresearch pattern as described in DesignDoc.md:
a long-running process that scores, diagnoses, proposes, and selects mutations
to an artifact (prompt, config, code patch, etc.) in an autonomous loop.

Core modules:
- paths: Centralized path management
- config: Configuration management
- splitter: Stratified train/dev/test splitting
- scorer: External scorer wrapper with caching
- metrics: Metric computation (κ, macro-F1, Spearman)
- refiner: Four-stage refinement (A/B/C/M)
- history: Append-only log management
- report: Report generation
- loop: Main autoresearch loop
- notebook: Bidirectional notebook
- cli: Command-line interface
"""

from .paths import ensure_directories

__version__ = "0.1.0"
__all__ = ["ensure_directories"]
