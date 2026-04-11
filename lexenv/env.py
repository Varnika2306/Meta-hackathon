"""
LexEnv: Legal Document Analysis OpenEnv Environment
Inherits from openenv-core Environment base class for full spec compliance.
"""

from typing import Optional, Dict, Any, List

from openenv.core import Environment
from openenv.core.env_server.types import EnvironmentMetadata

from lexenv.models import LexAction, LexObservation, LexState, RiskLevel
from lexenv.data.contracts import get_task_data
from lexenv.graders import create_grader_for_task


class LexEnv(Environment[LexAction, LexObservation, LexState]):
    """
    OpenEnv-compliant Legal Document Analysis Environment.

    Episode flow
    ─────────────
    1.  env.reset(task_id=...)  → LexObservation  (step=0)
    2.  env.step(action)        → LexObservation  (step=1..max_steps, with .done and .reward)
    3.  env.state               → LexState         (inspect any time)
    """

    SUPPORTS_CONCURRENT_SESSIONS = False

    def __init__(self) -> None:
        super().__init__()
        self._state: Optional[LexState] = None
        self._grader = None
        self._episode_history: List[Dict[str, Any]] = []

    # ------------------------------------------------------------------ #
    # reset (sync — required by Environment ABC)                           #
    # ------------------------------------------------------------------ #

    def reset(
        self,
        seed: Optional[int] = None,
        episode_id: Optional[str] = None,
        task_id: str = "clause_id",
        **kwargs: Any,
    ) -> LexObservation:
        """
        Reset environment and start a new episode.

        Parameters
        ----------
        task_id : "clause_id" | "sla_review" | "ma_assessment"  (default: clause_id)
        seed    : reserved for future stochastic tasks (currently ignored)
        """
        task_data = get_task_data(task_id)
        if task_data is None:
            raise ValueError(
                f"Unknown task_id '{task_id}'. "
                "Available: clause_id, sla_review, ma_assessment"
            )

        self._state = LexState(
            episode_id=episode_id,
            task_id=task_id,
            task_name=task_data["name"],
            difficulty=task_data["difficulty"],
            contract_full_text=task_data["contract"],
            ground_truth_issues=task_data["ground_truth"],
        )
        self._grader = create_grader_for_task(task_id, task_data["ground_truth"])
        self._episode_history = []

        obs = self._build_observation(task_data, step=0)
        return obs

    async def reset_async(
        self,
        seed: Optional[int] = None,
        episode_id: Optional[str] = None,
        task_id: str = "clause_id",
        **kwargs: Any,
    ) -> LexObservation:
        return self.reset(seed=seed, episode_id=episode_id, task_id=task_id, **kwargs)

    # ------------------------------------------------------------------ #
    # step (sync — required by Environment ABC)                            #
    # ------------------------------------------------------------------ #

    def step(
        self,
        action: LexAction,
        timeout_s: Optional[float] = None,
        **kwargs: Any,
    ) -> LexObservation:
        """Execute one analysis step."""
        if self._state is None:
            raise RuntimeError("Call reset() before step().")

        self._state.step_count += 1
        step_num = self._state.step_count

        # Persist action
        self._state.actions_history.append(action.model_dump())

        task_data = get_task_data(self._state.task_id)
        max_steps: int = task_data["max_steps"]
        is_final = step_num >= max_steps

        # Calculate and strictly clamp reward (0.01 to 0.99)
        reward_breakdown = self._grader.calculate_step_reward(
            agent_analysis=action.analysis,
            agent_risk_level=action.risk_assessment.value,
            step_num=step_num,
            is_final_step=is_final,
        )
        step_reward: float = max(0.01, min(0.99, reward_breakdown["total_step_reward"]))
        self._state.step_rewards.append(step_reward)

        # Episode completion
        done = is_final
        if done:
            all_analyses = [a.get("analysis", "") for a in self._state.actions_history]
            all_risks = [a.get("risk_assessment", "medium") for a in self._state.actions_history]
            episode_grades = self._grader.grade_episode(
                all_analyses=all_analyses,
                all_risk_levels=all_risks,
                steps_taken=step_num,
            )
            # Strictly clamp episode final score (0.01 to 0.99)
            self._state.episode_score = max(0.01, min(0.99, episode_grades["final_score"]))
            self._state.episode_done = True

        self._episode_history.append({"step": step_num, "reward": step_reward, "done": done})

        obs = self._build_observation(
            task_data,
            step=step_num,
            previous_feedback=f"Step {step_num} reward: {step_reward:.3f}",
        )

        # Report the partial step reward (strictly clamped 0.01-0.99).
        # The inference.py script will calculate the final score by averaging these.
        obs.reward = step_reward
        obs.done = done
        return obs

    async def step_async(
        self,
        action: LexAction,
        timeout_s: Optional[float] = None,
        **kwargs: Any,
    ) -> LexObservation:
        return self.step(action, timeout_s=timeout_s, **kwargs)

    # ------------------------------------------------------------------ #
    # state property (required by Environment ABC)                         #
    # ------------------------------------------------------------------ #

    @property
    def state(self) -> LexState:
        if self._state is None:
            return LexState()
        return self._state

    # ------------------------------------------------------------------ #
    # metadata (optional override)                                         #
    # ------------------------------------------------------------------ #

    def get_metadata(self) -> EnvironmentMetadata:
        return EnvironmentMetadata(
            name="LexEnv",
            description=(
                "RL environment for AI legal document analysis. "
                "Agent identifies risky clauses across NDA, SLA, and M&A contracts."
            ),
            version="1.0.0",
        )

    # ------------------------------------------------------------------ #
    # internal helpers                                                     #
    # ------------------------------------------------------------------ #

    def _build_observation(
        self,
        task_data: Dict[str, Any],
        step: int = 0,
        previous_feedback: Optional[str] = None,
    ) -> LexObservation:
        contract: str = task_data["contract"]
        max_steps: int = task_data["max_steps"]

        if step == 0:
            excerpt = contract
        else:
            quarter = max(200, len(contract) // 4)
            start = quarter * min(step, 3)
            excerpt = (
                "[Continuing review — previous feedback received.]\n\n"
                + contract[start : start + quarter * 2]
            )

        rewards_so_far = sum(self._state.step_rewards) if self._state else 0.0
        actions_so_far = len(self._state.actions_history) if self._state else 0

        return LexObservation(
            task_id=self._state.task_id if self._state else task_data.get("task_id", ""),
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
                "is_gradable": True,
                "grader": True,
            },
        )


_GLOBAL_ENV = None

def make_env() -> LexEnv:
    """Factory function required by OpenEnv spec."""
    global _GLOBAL_ENV
    if _GLOBAL_ENV is None:
        _GLOBAL_ENV = LexEnv()
    return _GLOBAL_ENV
