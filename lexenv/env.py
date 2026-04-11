"""
LexEnv: Legal Document Analysis OpenEnv Environment
Inherits from openenv-core Environment base class for full spec compliance.
"""

from typing import Optional, Dict, Any, List
import threading

from openenv.core import Environment
from openenv.core.env_server.types import EnvironmentMetadata

from lexenv.models import LexAction, LexObservation, LexState, RiskLevel
from lexenv.data.contracts import get_task_data
from lexenv.graders import create_grader_for_task
from lexenv.llm_grader import ToneGrader

# ============================================================================
# Global Persistence Registry (Handles multi-user session survival)
# ============================================================================
_REGISTRY_LOCK = threading.Lock()
_STATE_REGISTRY: Dict[str, LexState] = {}
_GRADER_REGISTRY: Dict[str, Any] = {}

class LexEnv(Environment[LexAction, LexObservation, LexState]):
    """
    OpenEnv-compliant Legal Document Analysis Environment.
    Features state-recovery to survive session-loss in proxy environments.
    """

    SUPPORTS_CONCURRENT_SESSIONS = True

    def __init__(self) -> None:
        super().__init__()
        self._state: Optional[LexState] = None
        self._grader = None
        self._tone_grader = ToneGrader()
        self._episode_history: List[Dict[str, Any]] = []

    def _recover_session(self, session_id: Optional[str]) -> bool:
        """Attempt to recover state/grader from the global registry."""
        if not session_id:
            return False
        
        with _REGISTRY_LOCK:
            if session_id in _STATE_REGISTRY:
                self._state = _STATE_REGISTRY[session_id]
                self._grader = _GRADER_REGISTRY.get(session_id)
                return True
        return False

    def _persist_session(self, session_id: Optional[str]):
        """Save current state/grader to the global registry."""
        if not session_id:
            return
            
        with _REGISTRY_LOCK:
            _STATE_REGISTRY[session_id] = self._state
            _GRADER_REGISTRY[session_id] = self._grader

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
        # Check task_id in body
        task_id = kwargs.get("task_id", task_id)
        session_id = kwargs.get("session_id")

        task_data = get_task_data(task_id)
        if task_data is None:
            raise ValueError(f"Unknown task_id '{task_id}'")

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

        # Ensure we remember this session globally
        self._persist_session(session_id)

        return self._build_observation(task_data, step=0)

    async def reset_async(self, **kwargs) -> LexObservation:
        return self.reset(**kwargs)

    # ------------------------------------------------------------------ #
    # step (sync — required by Environment ABC)                            #
    # ------------------------------------------------------------------ #

    def step(
        self,
        action: LexAction,
        timeout_s: Optional[float] = None,
        **kwargs: Any,
    ) -> LexObservation:
        """Execute one analysis step with state-recovery."""
        
        # 1. Recovery Attempt (survive instance-loss)
        session_id = action.session_id or kwargs.get("session_id")
        if self._state is None:
            if not self._recover_session(session_id):
                raise RuntimeError("Call reset() before step(). No session found for recovery.")

        # 2. Progress counters
        self._state.step_count += 1
        step_num = self._state.step_count

        # 3. Grading logic
        self._state.actions_history.append(action.model_dump())
        task_data = get_task_data(self._state.task_id)
        max_steps: int = task_data["max_steps"]
        is_final = step_num >= max_steps

        reward_breakdown = self._grader.calculate_step_reward(
            agent_analysis=action.analysis,
            agent_risk_level=action.risk_assessment.value,
            step_num=step_num,
            is_final_step=is_final,
            tone_score=kwargs.get("tone_score", 0.0),
            tone_feedback=kwargs.get("tone_feedback", "")
        )
        step_reward: float = max(0.01, min(0.99, reward_breakdown["total_step_reward"]))
        self._state.step_rewards.append(step_reward)

        # 4. Episode completion
        done = is_final
        if done:
            self._state.episode_done = True
            # Keep records in registry for a while (don't delete yet to avoid concurrent errors)

        self._episode_history.append({"step": step_num, "reward": step_reward, "done": done})

        # 5. Build transition
        obs = self._build_observation(
            task_data,
            step=step_num,
            previous_feedback=f"Step {step_num} reward: {step_reward:.3f}",
            tone_results={
                "score": kwargs.get("tone_score", 0.0),
                "feedback": kwargs.get("tone_feedback", "")
            }
        )
        obs.reward = step_reward
        obs.done = done

        # 6. Persistent Update
        self._persist_session(session_id)

        return obs

    async def step_async(self, action: LexAction, **kwargs) -> LexObservation:
        """Asynchronous step that incorporates LLM tone grading."""
        # 1. Evaluate Tone (LLM-as-a-judge)
        task_name = self._state.task_name if self._state else "Legal contract"
        tone_results = await self._tone_grader.evaluate_tone(action.analysis, task_name)
        
        # 2. Pass results into the synchronous step logic via kwargs
        kwargs["tone_score"] = tone_results.get("tone_score", 0.0)
        kwargs["tone_feedback"] = tone_results.get("feedback", "")
        
        return self.step(action, **kwargs)

    @property
    def state(self) -> LexState:
        return self._state if self._state else LexState()

    def get_metadata(self) -> EnvironmentMetadata:
        return EnvironmentMetadata(
            name="LexEnv",
            description="Premium legal analysis environment with state-recovery.",
            version="1.2.0",
        )

    def _build_observation(
        self,
        task_data: Dict[str, Any],
        step: int = 0,
        previous_feedback: Optional[str] = None,
        tone_results: Optional[Dict[str, Any]] = None,
    ) -> LexObservation:
        contract: str = task_data["contract"]
        max_steps: int = task_data["max_steps"]

        if step == 0:
            excerpt = contract
        else:
            quarter = max(200, len(contract) // 4)
            start = quarter * min(step, 3)
            excerpt = f"[Continuing review — step {step}]\n\n" + contract[start : start + quarter * 2]

        rewards_so_far = sum(self._state.step_rewards) if self._state else 0.0
        
        return LexObservation(
            task_id=self._state.task_id if self._state else task_data.get("task_id", ""),
            task_name=task_data["name"],
            difficulty=task_data["difficulty"],
            contract_excerpt=excerpt,
            instruction=task_data["instruction"],
            step=step,
            max_steps=max_steps,
            previous_analysis=previous_feedback,
            tone_analysis=tone_results if tone_results else {},
            progress={
                "step": step,
                "max_steps": max_steps,
                "rewards_so_far": rewards_so_far,
                "grader": True,
            },
        )

def make_env() -> LexEnv:
    """Factory function for OpenEnv."""
    return LexEnv()
