"""
Pydantic models for the LexEnv environment.

Defines the Action, Observation, and State types used by
the LexEnv OpenEnv environment for legal document analysis.
"""

from typing import Any, Dict, List, Optional

from pydantic import Field

from openenv.core.env_server.types import Action, Observation, State


class LexAction(Action):
    """Action submitted by the agent for legal document analysis.

    The agent provides an analysis of the contract, flags any risky
    clauses it identifies, and assigns an overall risk level.
    """

    analysis: str = Field(
        default="",
        description="Free-text analysis of the contract excerpt. "
        "Should explain identified risks and their implications.",
    )
    flags: List[str] = Field(
        default_factory=list,
        description="List of issue identifiers flagged by the agent. "
        "E.g. ['overbroad_non_compete', 'perpetual_term'].",
    )
    risk_level: str = Field(
        default="medium",
        description="Overall risk assessment: 'low', 'medium', 'high', or 'critical'.",
    )


class LexObservation(Observation):
    """Observation returned by the LexEnv environment.

    Extends the base Observation (which provides done, reward, metadata)
    with legal-domain-specific fields.
    """

    contract_excerpt: str = Field(
        default="",
        description="The legal contract text for the agent to analyze.",
    )
    instruction: str = Field(
        default="",
        description="Task-specific instruction telling the agent what to do.",
    )
    feedback: str = Field(
        default="",
        description="Feedback from the grader about the agent's last action.",
    )
    task_id: str = Field(
        default="",
        description="Identifier for the current task: "
        "'clause_id', 'sla_review', or 'ma_due_diligence'.",
    )


class LexState(State):
    """Internal state of the LexEnv environment.

    Extends the base State (which provides episode_id, step_count)
    with episode-specific tracking for legal analysis.
    """

    task_id: str = Field(
        default="clause_id",
        description="Current task being evaluated.",
    )
    current_step: int = Field(
        default=0,
        ge=0,
        description="Current step number within the episode.",
    )
    max_steps: int = Field(
        default=3,
        ge=1,
        description="Maximum number of steps allowed for this task.",
    )
    found_issues: List[str] = Field(
        default_factory=list,
        description="Issue IDs that the agent has correctly identified so far.",
    )
    total_reward: float = Field(
        default=0.0,
        description="Cumulative reward earned during this episode.",
    )
    step_rewards: List[float] = Field(
        default_factory=list,
        description="Reward earned at each step.",
    )
