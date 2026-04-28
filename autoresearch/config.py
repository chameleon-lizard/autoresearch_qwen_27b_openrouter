"""
Configuration management for the autoresearch loop.

All configuration is centralized here to avoid scattered CLI flags.
See DesignDoc.md section 12.
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class ScorerConfig:
    """Configuration for the external scorer (e.g., dredd.py)."""
    # Path to the scorer executable or script
    executable: str = "dredd.py"
    
    # Scorer LLM API configuration
    scorer_model: str = "qwen/qwen-2.5-32b-instruct"
    scorer_api_key: Optional[str] = None
    scorer_base_url: Optional[str] = None
    
    # Scoring parameters
    scorer_temperature: float = 0.0
    scorer_max_tokens: int = 4096


@dataclass
class RefinerConfig:
    """Configuration for the refiner LLM (proposes mutations)."""
    # Refiner LLM API configuration
    model: str = "qwen/qwen-2.5-32b-instruct"
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    
    # Generation parameters
    max_tokens: int = 8192
    
    # Retry temperatures for parse failures (see DesignDoc section 7)
    retry_temperatures: tuple = (0.0, 0.4, 0.7, 0.9)
    
    # Maximum retry attempts
    max_retries: int = 4


@dataclass
class LoopConfig:
    """Configuration for the main autoresearch loop."""
    # Number of sibling candidates per batch
    batch_size: int = 5
    
    # Number of parallel scorer processes
    parallelism: int = 15
    
    # History rendering: how many recent iterations to show in full
    history_full_count: int = 5
    
    # Dataset subsampling limit (for smoke tests)
    limit: Optional[int] = None
    
    # Maximum iterations (None for infinite)
    max_iterations: Optional[int] = None
    
    # Random seed for deterministic splits
    random_seed: int = 42


@dataclass
class SplitConfig:
    """Configuration for dataset splitting."""
    # Train/dev/test proportions
    train_ratio: float = 0.4
    dev_ratio: float = 0.2
    test_ratio: float = 0.4
    
    # Stratification column in ground truth
    stratify_column: str = "domain"
    
    # Random seed for reproducibility
    random_seed: int = 42


# Default configurations
SCORER = ScorerConfig()
REFINER = RefinerConfig()
LOOP = LoopConfig()
SPLIT = SplitConfig()
