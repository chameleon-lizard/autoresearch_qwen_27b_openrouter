from __future__ import annotations

"""
Four-stage refiner for proposing artifact mutations.

See DesignDoc.md section 4: "The four refiner stages (A / B / C / M)"

This module implements the LLM prompts and parsing for:
- Stage A: Disagreement generalisation
- Stage B: Proposal generation
- Stage C: Selection
- Stage M: Merge synthesis
"""

import re
from dataclasses import dataclass
from typing import Any

from .config import REFINER, RefinerConfig
from .paths import get_batch_path


@dataclass
class StageAOutput:
    """Output from Stage A (disagreement generalisation)."""
    summary: str


@dataclass
class StageBCandidate:
    """A single candidate from Stage B (proposal)."""
    plan_id: str
    rationale: str
    artifact: str


@dataclass
class StageBOutput:
    """Output from Stage B (proposal generation)."""
    candidates: list[StageBCandidate]


@dataclass
class StageCOutput:
    """Output from Stage C (selection)."""
    action: str  # "iter=N" or "merge=N1,N2,..."
    rationale: str


@dataclass
class StageMOutput:
    """Output from Stage M (merge synthesis)."""
    artifact: str
    rationale: str


def call_llm(
    system_prompt: str,
    user_prompt: str,
    config: RefinerConfig | None = None,
    batch_id: int | None = None,
) -> tuple[str, int]:
    """
    Call the refiner LLM with retry logic.

    See DesignDoc.md section 7: "Stochasticity for retries"
    Temperature varies across attempts: [0.0, 0.4, 0.7, 0.9]

    Returns:
        Tuple of (response_text, attempt_number)
    """
    if config is None:
        config = REFINER

    from openai import OpenAI

    client = OpenAI(
        api_key=config.api_key,
        base_url=config.base_url,
    )

    for attempt, temperature in enumerate(config.retry_temperatures):
        if attempt >= config.max_retries:
            break

        try:
            response = client.chat.completions.create(
                model=config.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=temperature,
                max_tokens=config.max_tokens,
            )

            content = response.choices[0].message.content

            # Save attempt for debugging
            if batch_id is not None:
                batch_path = get_batch_path(batch_id)
                batch_path.mkdir(parents=True, exist_ok=True)

                attempt_file = batch_path / f"stage_attempt_{attempt + 1}.txt"
                with open(attempt_file, "w") as f:
                    f.write(f"Temperature: {temperature}\n")
                    f.write(f"Length: {len(content)}\n")
                    f.write(f"Has <think>: {'<think>' in content.lower()}\n")
                    f.write("=" * 50 + "\n")
                    f.write(content)

            return content, attempt + 1

        except Exception as e:
            print(f"LLM attempt {attempt + 1} failed: {e}")
            continue

    raise RuntimeError(f"LLM failed after {config.max_retries} attempts")


# ============ Stage A: Disagreement Generalisation ============

STAGE_A_SYSTEM = """You are an analyst examining where an artifact fails.

Your task is to read examples where the artifact's predictions disagree
with ground truth, and produce a GENERALISATION of the failure modes.

Do NOT simply list the errors. Instead, identify patterns and abstract
principles that explain WHY the artifact fails.

Output your generalisation as plain text (no special formatting)."""


def stage_a(
    errors: list[dict[str, Any]],
    batch_id: int | None = None,
    config: RefinerConfig | None = None,
) -> StageAOutput:
    """
    Stage A: Generalise disagreement patterns.

    Args:
        errors: List of {input, prediction, label, ...} dicts
        batch_id: For saving debug output
        config: Refiner configuration

    Returns:
        StageAOutput with generalised summary
    """
    # Build user prompt
    examples_text = []
    for i, error in enumerate(errors[:10], 1):  # Limit to 10 examples
        examples_text.append(
            f"Example {i}:\n"
            f"  Input: {error.get('input', 'N/A')[:200]}\n"
            f"  Prediction: {error.get('prediction', 'N/A')}\n"
            f"  Ground Truth: {error.get('label', 'N/A')}\n"
        )

    user_prompt = f"""Here are examples where the artifact disagrees with ground truth:

{''.join(examples_text)}

Analyse these errors and produce a concise generalisation of the failure modes.
Focus on patterns, not individual examples."""

    response, _ = call_llm(STAGE_A_SYSTEM, user_prompt, config, batch_id)

    return StageAOutput(summary=response.strip())


# ============ Stage B: Proposal Generation ============

STAGE_B_SYSTEM = """You are a proposal engine for improving an artifact.

Your task is to propose K sibling candidates, each applying ONE focused
edit to the parent artifact. Each candidate must have:
1. A plan_id (short identifier for the type of change)
2. A rationale (why this change should help)
3. The new artifact text (between <PROMPT>...</PROMPT> tags)

Rules:
- Each candidate is ONE focused edit, not multiple changes
- plan_id should be consistent for similar changes (e.g., "add_length_constraint")
- The artifact text must be complete and valid
- Do not re-propose changes that have already failed (check history)"""


def stage_b(
    parent_artifact: str,
    stage_a_summary: str,
    history_text: str,
    notebook_summary: str,
    k: int = 5,
    batch_id: int | None = None,
    config: RefinerConfig | None = None,
) -> StageBOutput:
    """
    Stage B: Generate K sibling candidates.

    Args:
        parent_artifact: The parent artifact text
        stage_a_summary: Generalisation from Stage A
        history_text: Rendered history for context
        notebook_summary: Summary of user constraints
        k: Number of candidates to generate
        batch_id: For saving debug output
        config: Refiner configuration

    Returns:
        StageBOutput with K candidates
    """
    user_prompt = f"""Parent artifact:
<PARENT>
{parent_artifact}
</PARENT>

Stage-A failure generalisation:
{stage_a_summary}

Recent history:
{history_text}

User constraints (from notebook):
{notebook_summary}

Propose exactly {k} sibling candidates. Each must have:
1. plan_id
2. rationale
3. Complete artifact text between <PROMPT>...</PROMPT>

Format each candidate as:
--- CANDIDATE ---
plan_id: <id>
rationale: <why this should help>
<PROMPT>
<complete artifact text>
</PROMPT>
"""

    response, _ = call_llm(STAGE_B_SYSTEM, user_prompt, config, batch_id)

    # Parse candidates
    candidates = parse_stage_b_output(response)

    return StageBOutput(candidates=candidates)


def parse_stage_b_output(text: str) -> list[StageBCandidate]:
    """Parse Stage B output into candidates."""
    candidates = []

    # Split by candidate delimiter
    parts = re.split(r'--- CANDIDATE ---', text)

    for part in parts[1:]:  # Skip first empty part
        # Extract plan_id
        plan_match = re.search(r'plan_id:\s*(\S+)', part)
        plan_id = plan_match.group(1) if plan_match else "unknown"

        # Extract rationale
        ratiole_match = re.search(r'rationale:\s*(.+?)(?:<PROMPT>|$)', part, re.DOTALL)
        rationale = ratiole_match.group(1).strip() if ratiole_match else ""

        # Extract artifact
        prompt_match = re.search(r'<PROMPT>\s*\n?(.*?)\n?\s*</PROMPT>', part, re.DOTALL)
        artifact = prompt_match.group(1).strip() if prompt_match else ""

        if artifact:
            candidates.append(StageBCandidate(
                plan_id=plan_id,
                rationale=rationale,
                artifact=artifact,
            ))

    return candidates


# ============ Stage C: Selection ============

STAGE_C_SYSTEM = """You are a selector that chooses the best parent for the next iteration.

You can either:
1. Select a single iteration: "iter=N"
2. Request a merge: "merge=N1,N2,N3"

Consider the full history, not just the latest. Sometimes an older
branch is more promising than recent plateauing iterations.

Look at:
- Dev kappa (primary metric)
- Dev-test gap (overfitting indicator)
- Trajectory (is it improving or plateauing?)
- Plan diversity (are we exploring or exploiting?)"""


def stage_c(
    history_text: str,
    best_so_far_iter: int,
    batch_id: int | None = None,
    config: RefinerConfig | None = None,
) -> StageCOutput:
    """
    Stage C: Select the next parent.

    Args:
        history_text: Rendered history with metrics
        best_so_far_iter: Iteration number of best so far
        batch_id: For saving debug output
        config: Refiner configuration

    Returns:
        StageCOutput with action and rationale
    """
    user_prompt = f"""History (compact format):
{history_text}

Best so far: iteration {best_so_far_iter}

Select either:
- "iter=N" to use iteration N as the next parent
- "merge=N1,N2,..." to synthesise a merge from these iterations

Provide your selection and a brief rationale."""

    response, _ = call_llm(STAGE_C_SYSTEM, user_prompt, config, batch_id)

    # Parse selection
    iter_match = re.search(r'"?iter=(\d+)"?', response)
    merge_match = re.search(r'"?merge=(\d+(?:,\d+)*)"?', response)

    if iter_match:
        action = f"iter={iter_match.group(1)}"
    elif merge_match:
        action = f"merge={merge_match.group(1)}"
    else:
        # Default to best so far
        action = f"iter={best_so_far_iter}"

    # Extract rationale
    rationale_match = re.search(r'(?:because|rationale|reason)[:\s]+(.+)', response, re.IGNORECASE)
    rationale = rationale_match.group(1).strip() if rationale_match else "Default selection"

    return StageCOutput(action=action, rationale=rationale)


# ============ Stage M: Merge Synthesis ============

STAGE_M_SYSTEM = """You are a merge synthesiser that combines multiple artifacts into one.

Your task is to read N parent artifacts and produce a single merged artifact
that combines their strengths.

Rules:
- Preserve coherent structure
- Don't just concatenate - integrate changes
- The output must be a complete, valid artifact
- Explain which elements came from which parent"""


def stage_m(
    parent_artifacts: list[tuple[int, str]],  # List of (iter_num, artifact)
    batch_id: int | None = None,
    config: RefinerConfig | None = None,
) -> StageMOutput:
    """
    Stage M: Synthesise a merge from multiple parents.

    Args:
        parent_artifacts: List of (iteration_number, artifact_text) tuples
        batch_id: For saving debug output
        config: Refiner configuration

    Returns:
        StageMOutput with merged artifact and rationale
    """
    parents_text = []
    for iter_num, artifact in parent_artifacts:
        parents_text.append(
            f"=== Iteration {iter_num} ===\n{artifact}"
        )

    separator = "\n\n"
    user_prompt = f"""Merge these artifacts into one:

{separator.join(parents_text)}

Produce a single merged artifact that combines their strengths.
Output format:
--- MERGE ---
rationale: <which elements from which parents>
<PROMPT>
<merged artifact text>
</PROMPT>
"""

    response, _ = call_llm(STAGE_M_SYSTEM, user_prompt, config, batch_id)

    # Parse merge
    rationale_match = re.search(r'rationale:\s*(.+?)(?:<PROMPT>|$)', response, re.DOTALL)
    rationale = rationale_match.group(1).strip() if rationale_match else ""

    prompt_match = re.search(r'<PROMPT>\s*\n?(.*?)\n?\s*</PROMPT>', response, re.DOTALL)
    artifact = prompt_match.group(1).strip() if prompt_match else ""

    return StageMOutput(artifact=artifact, rationale=rationale)
