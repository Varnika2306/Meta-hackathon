"""
LexEnv: Legal Document Analysis OpenEnv Environment
Implements reset(), step(), and state() per OpenEnv spec.

Bug-fixes vs original upload
─────────────────────────────
1. action.dict()  →  action.model_dump()   (Pydantic v2 deprecation)
2. step termination used `len(ground_truth_issues)` as max_steps — should
   use task_data["max_steps"] (already declared; original code had an
   off-by-one and would never terminate for the hard task).
3. _create_observation() referenced self.current_state but state was
   sometimes None on the first call path; added guard.
4. progress dict now always includes max_steps (was missing from some
   paths, causing KeyError in inference.py).
5. state() now surfaces episode_history correctly.
"""

from typing import Optional, Dict, Any, List

from lexenv.models import (
    LexAction, LexObservation, LexState, ResetResult, StepResult,
    RewardBreakdown, RiskLevel,
)
from lexenv.data.contracts import TASK_DATA, get_task_data
from lexenv.graders import create_grader_for_task


class LexEnv:
    """
    OpenEnv-compliant Legal Document Analysis Environment.

    Episode flow
    ─────────────
    1.  await env.reset(task_id)   → ResetResult  (step=0)
    2.  await env.step(action)     → StepResult   (step=1..max_steps)
        … repeat until StepResult.done is True
    3.  env.state()                → Dict          (inspect any time)
    """

    def __init__(self) -> None:
        self.current_state: Optional[LexState] = None
        self.current_grader = None
        self.episode_history: List[Dict[str, Any]] = []

    # ------------------------------------------------------------------ #
    # reset                                                                #
    # ------------------------------------------------------------------ #

    async def reset(
        self,
        task_id: str = "clause_id",
        seed: Optional[int] = None,
    ) -> ResetResult:
        """
        Reset environment and start a new episode.

        Parameters
        ----------
        task_id : "clause_id" | "sla_review" | "ma_assessment"
        seed    : reserved for future stochastic tasks (currently ignored)

        Returns
        -------
        ResetResult  with the initial LexObservation and task metadata.
        """
        task_data = get_task_data(task_id)
        if task_data is None:
            raise ValueError(
                f"Unknown task_id '{task_id}'. "
                "Available: clause_id, sla_review, ma_assessment"
            )

        self.current_state = LexState(
            task_id=task_id,
            task_name=task_data["name"],
            difficulty=task_data["difficulty"],
            contract_full_text=task_data["contract"],
            ground_truth_issues=task_data["ground_truth"],
        )
        self.current_grader = create_grader_for_task(task_id, task_data["ground_truth"])
        self.episode_history = []

        observation = self._create_observation(task_data, step=0)

        return ResetResult(
            observation=observation,
            info={
                "task_id": task_id,
                "task_name": task_data["name"],
                "difficulty": task_data["difficulty"],
                "max_steps": task_data["max_steps"],
                "expected_issues": task_data["expected_issues"],
            },
        )

    # ------------------------------------------------------------------ #
    # step                                                                 #
    # ------------------------------------------------------------------ #

    async def step(self, action: LexAction) -> StepResult:
        """
        Execute one analysis step.

        Parameters
        ----------
        action : LexAction  (analysis text + issue flags + risk assessment)

        Returns
        -------
        StepResult  (next observation, step reward, done flag, info dict)

        Raises
        ------
        RuntimeError if reset() has not been called first.
        """
        if self.current_state is None:
            raise RuntimeError(
                "Environment not initialized. Call reset() before step()."
            )

        self.current_state.step_count += 1
        step_num = self.current_state.step_count

        # Record action
        self.current_state.actions_history.append(action)

        # --- Reward for this step ---
        task_data = get_task_data(self.current_state.task_id)
        max_steps: int = task_data["max_steps"]
        is_final = step_num >= max_steps

        reward_breakdown = self.current_grader.calculate_step_reward(
            agent_analysis=action.analysis,
            agent_risk_level=action.risk_assessment.value,
            step_num=step_num,
            is_final_step=is_final,
        )
        step_reward: float = reward_breakdown["total_step_reward"]
        self.current_state.step_rewards.append(step_reward)

        # --- Episode completion ---
        done = is_final
        if done:
            episode_grades = self.current_grader.grade_episode(
                all_analyses=[a.analysis for a in self.current_state.actions_history],
                all_risk_levels=[
                    a.risk_assessment.value
                    for a in self.current_state.actions_history
                ],
                steps_taken=step_num,
            )
            self.current_state.episode_score = episode_grades["final_score"]
            self.current_state.episode_done = True

        # --- Next observation ---
        next_obs = self._create_observation(
            task_data,
            step=step_num,
            previous_feedback=f"Step {step_num} reward: {step_reward:.3f}",
        )

        # --- Persist in history ---
        self.episode_history.append(
            {
                "step": step_num,
                "action": action.model_dump(),   # Pydantic v2
                "reward": step_reward,
                "done": done,
            }
        )

        return StepResult(
            observation=next_obs,
            reward=step_reward,
            reward_breakdown=RewardBreakdown(
                per_step_score=reward_breakdown["per_step_score"],
                efficiency_bonus=reward_breakdown["efficiency_bonus"],
                analysis_quality=reward_breakdown["analysis_quality"],
                risk_match_bonus=reward_breakdown["risk_match_bonus"],
                false_positive_penalty=reward_breakdown["false_positive_penalty"],
                total_step_reward=reward_breakdown["total_step_reward"],
            ),
            done=done,
            info={
                "step": step_num,
                "episode_score": (
                    self.current_state.episode_score if done else None
                ),
                "rewards_so_far": list(self.current_state.step_rewards),
            },
        )

    # ------------------------------------------------------------------ #
    # state                                                                #
    # ------------------------------------------------------------------ #

    def state(self) -> Dict[str, Any]:
        """
        Return the full current environment state as a plain dict.
        Safe to call at any point (returns {"initialized": false} before reset).
        """
        if self.current_state is None:
            return {"initialized": False}

        return {
            "task_id": self.current_state.task_id,
            "task_name": self.current_state.task_name,
            "difficulty": self.current_state.difficulty,
            "step_count": self.current_state.step_count,
            "episode_done": self.current_state.episode_done,
            "episode_score": self.current_state.episode_score,
            "step_rewards": list(self.current_state.step_rewards),
            "contract_excerpt": self.current_state.contract_full_text[:500],
            "num_ground_truth_issues": len(self.current_state.ground_truth_issues),
            "actions_count": len(self.current_state.actions_history),
            "episode_history": self.episode_history,
        }

    # ------------------------------------------------------------------ #
    # internal helpers                                                     #
    # ------------------------------------------------------------------ #

    def _create_observation(
        self,
        task_data: Dict[str, Any],
        step: int = 0,
        previous_feedback: Optional[str] = None,
    ) -> LexObservation:
        """Build the LexObservation handed to the agent at each step."""
        contract: str = task_data["contract"]
        max_steps: int = task_data["max_steps"]

        # Step 0: give the agent the full contract.
        # Later steps: show a fresh excerpt so the agent is encouraged to
        # keep reading rather than just repeating itself.
        if step == 0:
            excerpt = contract
        else:
            quarter = max(200, len(contract) // 4)
            start = quarter * min(step, 3)          # advance through contract
            excerpt = (
                "[Continuing review — previous feedback received.]\n\n"
                + contract[start : start + quarter * 2]
            )

        # Guard: current_state must exist by the time we get here
        rewards_so_far = (
            sum(self.current_state.step_rewards)
            if self.current_state and self.current_state.step_rewards
            else 0.0
        )
        actions_so_far = (
            len(self.current_state.actions_history)
            if self.current_state
            else 0
        )

        return LexObservation(
            task_id=task_data.get("task_id", self.current_state.task_id),  # type: ignore[union-attr]
            task_name=task_data["name"],
            difficulty=task_data["difficulty"],
            contract_excerpt=excerpt,
            instruction=task_data["instruction"],
            step=step,
            max_steps=max_steps,
            previous_analysis=previous_feedback,
            progress={
                "step": step,
                "max_steps": max_steps,
                "issues_found_so_far": actions_so_far,
                "expected_issues": task_data["expected_issues"],
                "rewards_so_far": rewards_so_far,
            },
        )


# ── factory ──────────────────────────────────────────────────────────────────

def make_env() -> LexEnv:
    """Factory function required by OpenEnv spec."""
    return LexEnv()
