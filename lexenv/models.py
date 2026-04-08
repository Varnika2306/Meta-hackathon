"""
LexEnv Pydantic Models
Inherits from openenv-core base classes for full spec compliance.
"""

from pydantic import Field, ConfigDict
from typing import List, Optional, Dict, Any
from enum import Enum

from openenv.core import Action, Observation, State


class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class IssueFlag(Action):
    """A single flagged issue — reuses Action base for schema consistency."""
    model_config = ConfigDict(extra="allow", validate_assignment=True, arbitrary_types_allowed=True)

    title: str = Field(..., description="Issue title")
    severity: RiskLevel = Field(..., description="Severity level")
    clause_reference: Optional[str] = Field(None, description="Clause or line reference")
    remediation: Optional[str] = Field(None, description="Suggested fix")


class LexAction(Action):
    """Agent submits a legal analysis of the current contract excerpt."""
    analysis: str = Field(..., description="Detailed analysis text")
    flags: List[Dict[str, Any]] = Field(default_factory=list, description="Issues flagged")
    risk_assessment: RiskLevel = Field(default=RiskLevel.MEDIUM, description="Overall risk level")


class LexObservation(Observation):
    """Contract excerpt + context handed to the agent at each step."""
    # Inherited from Observation: done, reward, metadata
    task_id: str = Field(..., description="Task identifier")
    task_name: str = Field(..., description="Human-readable task name")
    difficulty: int = Field(..., ge=1, le=3, description="Difficulty level 1-3")
    contract_excerpt: str = Field(..., description="Contract text excerpt")
    instruction: str = Field(..., description="What to analyze")
    step: int = Field(..., description="Current step number")
    max_steps: int = Field(..., description="Maximum steps allowed")
    previous_analysis: Optional[str] = Field(None, description="Previous step feedback")
    progress: Dict[str, Any] = Field(default_factory=dict, description="Progress tracking")


class LexState(State):
    """Full environment state (extends openenv State base)."""
    # Inherited from State: episode_id, step_count
    task_id: str = Field(default="")
    task_name: str = Field(default="")
    difficulty: int = Field(default=1)
    contract_full_text: str = Field(default="")
    ground_truth_issues: List[Dict[str, Any]] = Field(default_factory=list)
    episode_done: bool = Field(default=False)
    episode_score: float = Field(default=0.0)
    step_rewards: List[float] = Field(default_factory=list)
    actions_history: List[Dict[str, Any]] = Field(default_factory=list)
