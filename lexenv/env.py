"""
LexEnv — AI Legal Document Analysis Environment.

An OpenEnv environment where an AI agent learns to analyze legal
documents: identifying risky clauses, flagging issues, and assessing
risk — simulating the work of a junior legal associate.

Three tasks of increasing difficulty:
  1. NDA Clause Identification   (Easy)   — 5 issues, 3 steps
  2. SLA Contract Review         (Medium) — 8 issues, 4 steps
  3. M&A Due Diligence           (Hard)   — 10 issues, 5 steps
"""

from typing import Any, Optional
from uuid import uuid4

from openenv.core.env_server.interfaces import Environment
from openenv.core.env_server.types import Action, Observation, State

from lexenv.data.contracts import TASK_IDS, get_contract
from lexenv.graders import grade_episode, grade_step
from lexenv.models import LexAction, LexObservation, LexState


class LexEnv(Environment):
    """OpenEnv environment for legal document analysis.

    Implements the standard Environment interface:
      - reset()  → initial observation
      - step()   → observation after grading the agent's action
      - state    → current episode state

    Example::

        env = LexEnv()
        obs = env.reset(task_id='clause_id')
        action = LexAction(
            analysis='The non-compete is overbroad...',
            flags=['overbroad_non_compete'],
            risk_level='high',
        )
        obs = env.step(action)
        print(obs.reward, obs.feedback)
    """

    def __init__(self) -> None:
        """Initialise the environment with a default empty state."""
        super().__init__()
        self._state = LexState(episode_id=str(uuid4()))
        self._contract_data: dict = {}
        self._found_issues: set = set()

    # ------------------------------------------------------------------
    # reset
    # ------------------------------------------------------------------
    def reset(
        self,
        seed: Optional[int] = None,
        episode_id: Optional[str] = None,
        **kwargs: Any,
    ) -> LexObservation:
        """Reset the environment and start a new episode.

        Args:
            seed: Optional random seed (unused — deterministic env).
            episode_id: Optional custom episode identifier.
            **kwargs: Must include ``task_id`` (str) to select the contract.
                      Defaults to ``'clause_id'`` (NDA — Easy).

        Returns:
            LexObservation with the contract text and instructions.
        """
        task_id = kwargs.get("task_id", "clause_id")
        self._contract_data = get_contract(task_id)
        self._found_issues = set()

        self._state = LexState(
            episode_id=episode_id or str(uuid4()),
            step_count=0,
            task_id=task_id,
            current_step=0,
            max_steps=self._contract_data["max_steps"],
            found_issues=[],
            total_reward=0.0,
            step_rewards=[],
        )

        return LexObservation(
            contract_excerpt=self._contract_data["text"],
            instruction=self._contract_data["instruction"],
            feedback="Episode started. Analyze the contract and flag issues.",
            task_id=task_id,
            done=False,
            reward=0.0,
            metadata={
                "task_title": self._contract_data["title"],
                "difficulty": self._contract_data["difficulty"],
                "max_steps": self._contract_data["max_steps"],
                "total_issues": len(self._contract_data["issues"]),
            },
        )

    # ------------------------------------------------------------------
    # step
    # ------------------------------------------------------------------
    def step(
        self,
        action: Action,
        timeout_s: Optional[float] = None,
        **kwargs: Any,
    ) -> LexObservation:
        """Execute one analysis step.

        The agent submits its analysis, flags, and risk level. The grader
        awards partial credit for each newly identified issue.

        Args:
            action: A LexAction (or dict with the same fields).
            timeout_s: Optional timeout (unused).

        Returns:
            LexObservation with reward, feedback, and done flag.
        """
        # Ensure contract data is loaded (for stateless HTTP calls)
        if not self._contract_data:
            task_id = kwargs.get("task_id", self._state.task_id or "clause_id")
            self._contract_data = get_contract(task_id)
            if not self._state.task_id:
                self._state.task_id = task_id
            if not self._state.max_steps:
                self._state.max_steps = self._contract_data["max_steps"]
        # Accept both LexAction objects and raw dicts
        if isinstance(action, dict):
            action = LexAction(**action)
        elif isinstance(action, Action) and not isinstance(action, LexAction):
            # Try to coerce from generic Action
            data = action.model_dump()
            data.pop("metadata", None)
            action = LexAction(**data)

        # Increment step counters
        self._state.step_count += 1
        self._state.current_step += 1

        # Grade the step
        step_reward, newly_found, feedback = grade_step(
            action_analysis=action.analysis,
            action_flags=action.flags,
            action_risk_level=action.risk_level,
            contract_data=self._contract_data,
            already_found=self._found_issues,
            step_index=self._state.current_step - 1,
        )

        # Update state
        self._found_issues.update(newly_found)
        self._state.found_issues = sorted(self._found_issues)
        self._state.total_reward += step_reward
        self._state.step_rewards.append(step_reward)

        # Check if episode is done
        all_found = len(self._found_issues) == len(self._contract_data["issues"])
        at_max_steps = self._state.current_step >= self._state.max_steps
        done = all_found or at_max_steps

        # Compute final episode score on last step
        final_score = None
        if done:
            final_score = grade_episode(
                step_rewards=self._state.step_rewards,
                found_issues=self._found_issues,
                total_issue_count=len(self._contract_data["issues"]),
                max_steps=self._state.max_steps,
            )
            feedback += (
                f" | EPISODE COMPLETE — Final score: {final_score:.3f} "
                f"({len(self._found_issues)}/{len(self._contract_data['issues'])} "
                f"issues found in {self._state.current_step} steps)."
            )

        return LexObservation(
            contract_excerpt=self._contract_data["text"] if not done else "",
            instruction=(
                self._contract_data["instruction"]
                if not done
                else "Episode complete."
            ),
            feedback=feedback,
            task_id=self._state.task_id,
            done=done,
            reward=step_reward,
            metadata={
                "step": self._state.current_step,
                "max_steps": self._state.max_steps,
                "issues_found": len(self._found_issues),
                "total_issues": len(self._contract_data["issues"]),
                "cumulative_reward": round(self._state.total_reward, 4),
                "final_score": final_score,
                "newly_found": newly_found,
            },
        )

    # ------------------------------------------------------------------
    # state property
    # ------------------------------------------------------------------
    @property
    def state(self) -> LexState:
        """Return the current environment state."""
        return self._state
