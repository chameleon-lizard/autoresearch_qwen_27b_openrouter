# Implementation TODO List

## Core Infrastructure
- [x] Initialize git repository
- [x] Create project structure (directories)
- [x] Create paths.py - centralized path management
- [x] Create config.py - configuration management
- [x] Create requirements.txt

## Module 1: Data Splitting
- [x] Create splitter.py - stratified train/dev/test split
- [x] Create DOCUMENTATION.md for splitter module

## Module 2: Scoring
- [x] Create scorer.py - wrapper for external scorer (dredd.py)
- [x] Implement caching by content hash
- [x] Create DOCUMENTATION.md for scorer module

## Module 3: Metrics
- [x] Create metrics.py - compute κ, macro-F1, Spearman
- [x] Create DOCUMENTATION.md for metrics module

## Module 4: Refiner Stages
- [ ] Create refiner.py with four stages (A/B/C/M)
- [ ] Stage A: Disagreement generalisation
- [ ] Stage B: Proposal generation
- [ ] Stage C: Selection
- [ ] Stage M: Merge synthesis
- [ ] Create DOCUMENTATION.md for refiner module

## Module 5: History & Logging
- [x] Create history.py - append-only log management
- [x] Create report_generator.py - experiments_report.md generation
- [x] Create DOCUMENTATION.md for history module

## Module 6: Main Loop
- [ ] Create loop.py - main autoresearch loop
- [ ] Implement batch mode with parallel scoring
- [ ] Implement crash-safe writes
- [ ] Create DOCUMENTATION.md for loop module

## Module 7: CLI
- [ ] Create cli.py - command-line interface
- [ ] Commands: run, report, reset, score
- [ ] Create DOCUMENTATION.md for CLI module

## Module 8: Notebook
- [x] Create notebook.py - bidirectional notebook management
- [x] Create DOCUMENTATION.md for notebook module

## Documentation
- [ ] Create WIKI.md - executive summary
- [ ] Create PROGRESS.md - implementation progress
- [ ] Create OPS.md - operations runbook

## Testing
- [ ] Create tests/ directory
- [ ] Add unit tests for each module
- [ ] Smoke test with --limit 20
