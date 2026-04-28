"""
Main autoresearch loop.

See DesignDoc.md sections 3 and 5 for the loop architecture and batch mode.

This module orchestrates:
1. Stage C: Selection of parent
2. Stage M: Merge synthesis (if needed)
3. Stage B: Proposal of K siblings
4. Parallel scoring of all candidates
5. Stage A: Diagnosis of each candidate
6. Append to experiment log
7. Regenerate report
"""

import json
from concurrent.futures import ProcessPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from typing import Any

from .config import LoopConfig, LOOP
from .history import (
    ExperimentEntry,
    append_entry,
    read_log,
    get_last_iteration,
    get_last_batch,
    get_best_entry_by_dev_kappa,
    render_history_compact,
)
from .notebook import (
    read_notebook,
    append_to_notebook,
    get_notebook_summary,
    create_initial_notebook,
)
from .paths import ensure_directories, get_batch_path, GROUND_TRUTH_FILE
from .refiner import (
    stage_a,
    stage_b,
    stage_c,
    stage_m,
    StageBOutput,
)
from .report import generate_report, print_report_summary
from .scorer import score_artifact
from .splitter import load_ground_truth, stratified_split


def diagnose_errors(
    predictions: list[str],
    labels: list[str],
    inputs: list[str],
    n_samples: int = 10,
) -> list[dict[str, Any]]:
    """
    Extract examples where predictions disagree with labels.
    
    Returns a balanced sample across error types.
    """
    errors = []
    for i, (pred, label, inp) in enumerate(zip(predictions, labels, inputs)):
        if pred != label:
            errors.append({
                "index": i,
                "input": inp[:500],  # Truncate long inputs
                "prediction": pred,
                "label": label,
            })
    
    # Simple sampling - could be improved with stratification
    return errors[:n_samples]


def run_batch(
    batch_id: int,
    train_path: Path,
    dev_path: Path,
    test_path: Path,
    config: LoopConfig | None = None,
) -> list[ExperimentEntry]:
    """
    Run a single batch of the autoresearch loop.
    
    Args:
        batch_id: Batch number
        train_path: Path to train split
        dev_path: Path to dev split
        test_path: Path to test split
        config: Loop configuration
    
    Returns:
        List of ExperimentEntry for this batch
    """
    if config is None:
        config = LOOP
    
    ensure_directories()
    create_initial_notebook()
    
    batch_path = get_batch_path(batch_id)
    batch_path.mkdir(parents=True, exist_ok=True)
    
    print(f"\n{'='*60}")
    print(f"Batch {batch_id}")
    print(f"{'='*60}")
    
    # Save notebook before batch
    notebook_before = batch_path / "notes_before.md"
    with open(notebook_before, "w") as f:
        f.write(read_notebook())
    
    # Load ground truth for diagnosis
    try:
        train_df = load_ground_truth(train_path)
        dev_df = load_ground_truth(dev_path)
        test_df = load_ground_truth(test_path)
    except Exception as e:
        print(f"Warning: Could not load ground truth for diagnosis: {e}")
        train_df = dev_df = test_df = None
    
    # ============ Stage C: Selection ============
    print("\n[Stage C] Selecting parent...")
    
    entries = read_log()
    best = get_best_entry_by_dev_kappa(entries)
    best_iter = best.iter if best else 0
    
    history_text = render_history_compact(entries, config.history_full_count)
    notebook_summary = get_notebook_summary(read_notebook())
    
    selection = stage_c(
        history_text=history_text,
        best_so_far_iter=best_iter,
        batch_id=batch_id,
    )
    
    print(f"  Selection: {selection.action}")
    print(f"  Rationale: {selection.rationale[:200]}...")
    
    # ============ Stage M: Merge (if needed) ============
    parent_artifact = ""
    parent_iter = 0
    
    if selection.action.startswith("merge="):
        print("\n[Stage M] Synthesising merge...")
        
        iter_nums = [int(x) for x in selection.action[6:].split(",")]
        parent_artifacts = []
        
        for iter_num in iter_nums:
            entry = None
            for e in entries:
                if e.iter == iter_num:
                    entry = e
                    break
            if entry:
                parent_artifacts.append((iter_num, entry.artifact))
        
        merge_output = stage_m(
            parent_artifacts=parent_artifacts,
            batch_id=batch_id,
        )
        
        parent_artifact = merge_output.artifact
        parent_iter = max(iter_nums)
        print(f"  Merge complete from iterations {iter_nums}")
        
    elif selection.action.startswith("iter="):
        parent_iter = int(selection.action[5:])
        for entry in entries:
            if entry.iter == parent_iter:
                parent_artifact = entry.artifact
                break
    
    # ============ Stage B: Proposal ============
    print(f"\n[Stage B] Proposing {config.batch_size} candidates...")
    
    # Run Stage A first for diagnosis
    if train_df is not None and entries:
        # Get errors from parent
        parent_entry = None
        for e in entries:
            if e.iter == parent_iter:
                parent_entry = e
                break
        
        if parent_entry and train_df is not None:
            errors = diagnose_errors(
                parent_entry.predictions if hasattr(parent_entry, 'predictions') else [],
                parent_entry.labels if hasattr(parent_entry, 'labels') else [],
                train_df.get('input', [''] * len(train_df)).tolist() if train_df is not None else [],
            )
            stage_a_output = stage_a(errors, batch_id=batch_id)
            stage_a_summary = stage_a_output.summary
        else:
            stage_a_summary = "No errors available for diagnosis."
    else:
        stage_a_summary = "No ground truth available for diagnosis."
    
    print(f"  Stage-A summary: {stage_a_summary[:200]}...")
    
    proposal_output = stage_b(
        parent_artifact=parent_artifact,
        stage_a_summary=stage_a_summary,
        history_text=history_text,
        notebook_summary=notebook_summary,
        k=config.batch_size,
        batch_id=batch_id,
    )
    
    print(f"  Generated {len(proposal_output.candidates)} candidates")
    
    # ============ Scoring ============
    print(f"\n[Scoring] Scoring {len(proposal_output.candidates)} candidates...")
    
    entries_this_batch = []
    
    with ProcessPoolExecutor(max_workers=config.parallelism) as executor:
        futures = {}
        
        for candidate in proposal_output.candidates:
            # Score on all three splits
            for split_name, split_path in [
                ("train", train_path),
                ("dev", dev_path),
                ("test", test_path),
            ]:
                future = executor.submit(
                    score_artifact,
                    candidate.artifact,
                    split_path,
                    split_name,
                )
                futures[future] = (candidate, split_name)
        
        # Collect results
        candidate_results: dict[str, dict[str, Any]] = {}
        
        for future in as_completed(futures):
            candidate, split_name = futures[future]
            result = future.result()
            
            if candidate.plan_id not in candidate_results:
                candidate_results[candidate.plan_id] = {
                    "candidate": candidate,
                    "results": {},
                }
            
            candidate_results[candidate.plan_id]["results"][split_name] = result
        
        # Create entries
        for plan_id, data in candidate_results.items():
            candidate = data["candidate"]
            results = data["results"]
            
            if not all(split in results for split in ["train", "dev", "test"]):
                print(f"  Warning: Incomplete results for {plan_id}")
                continue
            
            entry = ExperimentEntry(
                iter=get_last_iteration() + len(entries_this_batch) + 1,
                batch=batch_id,
                ts=datetime.now().isoformat(),
                artifact_hash=candidate.plan_id[:16],  # Use plan_id as hash proxy
                parent=parent_iter,
                plan_id=plan_id,
                rationale=candidate.rationale,
                artifact=candidate.artifact,
                metrics_train=results["train"].metrics,
                metrics_dev=results["dev"].metrics,
                metrics_test=results["test"].metrics,
                stage_a_summary=stage_a_summary,
            )
            
            # Add predictions/labels for diagnosis
            entry.predictions = results["train"].predictions
            entry.labels = results["train"].labels
            
            entries_this_batch.append(entry)
            print(
                f"  {plan_id}: train-κ={results['train'].metrics['kappa']:.3f} "
                f"dev-κ={results['dev'].metrics['kappa']:.3f} "
                f"test-κ={results['test'].metrics['kappa']:.3f}"
            )
    
    # ============ Append to log ============
    print(f"\n[Log] Appending {len(entries_this_batch)} entries...")
    
    for entry in entries_this_batch:
        append_entry(entry)
    
    # ============ Regenerate report ============
    print("[Report] Regenerating report...")
    generate_report()
    
    # ============ Save notebook after ============
    append_to_notebook(
        f"BATCH {batch_id} COMPLETE",
        f"Generated {len(entries_this_batch)} candidates. "
        f"Best dev-κ in batch: {max(e.metrics_dev['kappa'] for e in entries_this_batch):.3f}",
        author="agent",
    )
    
    notebook_after = batch_path / "notes_after.md"
    with open(notebook_after, "w") as f:
        f.write(read_notebook())
    
    print_report_summary()
    
    return entries_this_batch


def run_loop(
    train_path: Path,
    dev_path: Path,
    test_path: Path,
    max_iterations: int | None = None,
    config: LoopConfig | None = None,
) -> None:
    """
    Run the autoresearch loop indefinitely (or until max_iterations).
    
    Args:
        train_path: Path to train split
        dev_path: Path to dev split
        test_path: Path to test split
        max_iterations: Maximum iterations (None for infinite)
        config: Loop configuration
    """
    if config is None:
        config = LOOP
    
    ensure_directories()
    create_initial_notebook()
    
    current_batch = get_last_batch() + 1
    total_iterations = get_last_iteration()
    
    print(f"Starting autoresearch loop from batch {current_batch}, iteration {total_iterations + 1}")
    
    try:
        while True:
            if max_iterations is not None and total_iterations >= max_iterations:
                print(f"\nReached max_iterations ({max_iterations}). Stopping.")
                break
            
            run_batch(current_batch, train_path, dev_path, test_path, config)
            
            current_batch += 1
            total_iterations = get_last_iteration()
            
    except KeyboardInterrupt:
        print("\n\nInterrupted by user. Saving state...")
        generate_report()
        print_report_summary()
        print("State saved. Can resume with 'loop run'.")


def score_single_artifact(
    artifact: str,
    train_path: Path,
    dev_path: Path,
    test_path: Path,
) -> None:
    """
    Score a single artifact on all splits (no proposal).
    
    Used for the 'loop score' CLI command.
    """
    print("Scoring artifact on all splits...")
    
    for split_name, split_path in [
        ("train", train_path),
        ("dev", dev_path),
        ("test", test_path),
    ]:
        result = score_artifact(artifact, split_path, split_name)
        print(f"\n{split_name.upper()}:")
        print(f"  κ={result.metrics['kappa']:.3f}")
        print(f"  F1={result.metrics['f1']:.3f}")
        print(f"  ρ={result.metrics['spearman']:.3f}")
