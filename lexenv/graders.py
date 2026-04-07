"""
Grading logic for LexEnv legal document analysis tasks.

Provides step-level and episode-level scoring with:
  - Fuzzy keyword matching against ground-truth issues
  - Weighted partial credit per issue found
  - Step decay (earlier steps rewarded more)
  - Risk level bonus / analysis length penalty
  - Episode-level efficiency bonus
"""

from typing import Any, Dict, List, Set, Tuple


def _normalize(text: str) -> str:
    """Lowercase and strip a string for fuzzy comparison."""
    return text.lower().strip()


def _fuzzy_match(text: str, keywords: List[str]) -> bool:
    """Check if any keyword appears in the text (case-insensitive).

    Args:
        text: The text to search within.
        keywords: List of keywords to look for.

    Returns:
        True if at least one keyword is found in the text.
    """
    text_lower = _normalize(text)
    for kw in keywords:
        if _normalize(kw) in text_lower:
            return True
    return False


def grade_step(
    action_analysis: str,
    action_flags: List[str],
    action_risk_level: str,
    contract_data: Dict[str, Any],
    already_found: Set[str],
    step_index: int,
) -> Tuple[float, List[str], str]:
    """Grade a single step of the agent's legal analysis.

    Checks the agent's flags and analysis text against the ground-truth
    issues for the current contract.  Awards weighted partial credit for
    each newly identified issue.

    Args:
        action_analysis: Free-text analysis submitted by the agent.
        action_flags: List of issue ID strings the agent flagged.
        action_risk_level: Agent's overall risk assessment.
        contract_data: The contract dict from contracts.py.
        already_found: Set of issue IDs already found in prior steps.
        step_index: Zero-based index of the current step.

    Returns:
        Tuple of (step_reward, newly_found_ids, feedback_text).
    """
    issues = contract_data["issues"]
    expected_risk = contract_data["expected_risk_level"]

    newly_found: List[str] = []
    step_reward = 0.0

    # --- Score each ground-truth issue ---------------------------------
    for issue in issues:
        issue_id = issue["id"]

        # Skip issues already credited
        if issue_id in already_found:
            continue

        matched = False

        # Check 1: Does any agent flag fuzzy-match this issue?
        for flag in action_flags:
            if _fuzzy_match(flag, issue["keywords"]):
                matched = True
                break
            # Also allow exact match on issue id
            if _normalize(flag) == _normalize(issue_id):
                matched = True
                break

        # Check 2: Does the analysis text mention any keyword?
        if not matched and _fuzzy_match(action_analysis, issue["keywords"]):
            matched = True

        if matched:
            newly_found.append(issue_id)
            step_reward += issue["weight"]

    # --- Step decay: earlier steps rewarded more -----------------------
    decay_factor = max(0.5, 1.0 - step_index * 0.05)
    step_reward *= decay_factor

    # --- Risk level bonus ----------------------------------------------
    if _normalize(action_risk_level) == _normalize(expected_risk):
        step_reward += 0.05

    # --- Short analysis penalty ----------------------------------------
    if len(action_analysis.strip()) < 50:
        step_reward -= 0.05

    # Clamp to non-negative
    step_reward = max(0.0, step_reward)

    # --- Build feedback string -----------------------------------------
    total_issues = len(issues)
    total_found = len(already_found) + len(newly_found)

    feedback_parts: List[str] = []
    if newly_found:
        feedback_parts.append(
            f"Issues found this step: {', '.join(newly_found)} "
            f"({len(newly_found)} new)."
        )
    else:
        feedback_parts.append("No new issues identified this step.")

    feedback_parts.append(
        f"Total issues identified: {total_found}/{total_issues}."
    )

    if _normalize(action_risk_level) == _normalize(expected_risk):
        feedback_parts.append("Risk level assessment: CORRECT.")
    else:
        feedback_parts.append(
            f"Risk level assessment: '{action_risk_level}' "
            f"(expected: '{expected_risk}')."
        )

    # Hint about remaining issues (without revealing them)
    remaining = total_issues - total_found
    if remaining > 0:
        feedback_parts.append(
            f"There are {remaining} issue(s) still unidentified."
        )
    else:
        feedback_parts.append("All issues have been identified!")

    feedback = " ".join(feedback_parts)
    return step_reward, newly_found, feedback


def grade_episode(
    step_rewards: List[float],
    found_issues: Set[str],
    total_issue_count: int,
    max_steps: int,
) -> float:
    """Compute the final episode score with efficiency bonus.

    Args:
        step_rewards: List of rewards from each step.
        found_issues: Set of all issue IDs found during the episode.
        total_issue_count: Total number of ground-truth issues.
        max_steps: Maximum steps allowed for this task.

    Returns:
        Final episode score in [0.0, 1.0].
    """
    if not step_rewards:
        return 0.0

    base_score = sum(step_rewards)

    # --- Efficiency bonus: +10% if ≥60% issues found in ≤2 steps ------
    coverage = len(found_issues) / total_issue_count if total_issue_count else 0
    if coverage >= 0.6 and len(step_rewards) <= 2:
        base_score *= 1.10

    # Cap at 1.0
    return min(1.0, round(base_score, 4))
