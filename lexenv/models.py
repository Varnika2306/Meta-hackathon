"""
LexEnv Pydantic Models
- LexAction: agent action (analysis submission)
- LexObservation: environment observation (contract excerpt + context)
- LexState: full environment state
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from enum import Enum


class RiskLevel(str, Enum):
    """Risk assessment level"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class IssueFlag(BaseModel):
    """A single flagged issue"""
    title: str = Field(..., description="Issue title")
    severity: RiskLevel = Field(..., description="Severity level")
    clause_reference: Optional[str] = Field(None, description="Clause or line reference")
    remediation: Optional[str] = Field(None, description="Suggested fix")


class LexAction(BaseModel):
    """Action: agent submits analysis of contract"""
    analysis: str = Field(..., description="Detailed analysis text")
    flags: List[IssueFlag] = Field(default_factory=list, description="Issues flagged")
    risk_assessment: RiskLevel = Field(default=RiskLevel.MEDIUM, description="Overall risk level")
    
    class Config:
        json_schema_extra = {
            "example": {
                "analysis": "The NDA contains overly broad non-compete and perpetual IP assignment.",
                "flags": [
                    {
                        "title": "Overbroad non-compete",
                        "severity": "high",
                        "clause_reference": "Section 2.1",
                        "remediation": "Limit to 2 years and 50 miles"
                    }
                ],
                "risk_assessment": "high"
            }
        }


class LexObservation(BaseModel):
    """Observation: contract excerpt and context for agent"""
    task_id: str = Field(..., description="Task identifier (clause_id, sla_review, ma_assessment)")
    task_name: str = Field(..., description="Human-readable task name")
    difficulty: int = Field(..., ge=1, le=3, description="Difficulty level 1-3")
    contract_excerpt: str = Field(..., description="Contract text excerpt")
    instruction: str = Field(..., description="What to analyze")
    step: int = Field(..., description="Current step number")
    max_steps: int = Field(..., description="Maximum steps allowed")
    previous_analysis: Optional[str] = Field(None, description="Previous step feedback")
    progress: Dict[str, Any] = Field(default_factory=dict, description="Progress tracking")
    
    class Config:
        json_schema_extra = {
            "example": {
                "task_id": "clause_id",
                "task_name": "NDA Clause Identification",
                "difficulty": 1,
                "contract_excerpt": "NON-COMPETE: Employee shall not engage in any competitive activity for 5 years worldwide...",
                "instruction": "Identify risky clauses in this NDA",
                "step": 1,
                "max_steps": 3,
                "previous_analysis": None,
                "progress": {"issues_found": 0}
            }
        }


class LexState(BaseModel):
    """Full environment state"""
    task_id: str
    task_name: str
    difficulty: int
    contract_full_text: str
    ground_truth_issues: List[Dict[str, Any]]  # Ground truth for grading
    observations_history: List[LexObservation] = Field(default_factory=list)
    actions_history: List[LexAction] = Field(default_factory=list)
    step_count: int = 0
    episode_done: bool = False
    episode_score: float = 0.0
    step_rewards: List[float] = Field(default_factory=list)


class RewardBreakdown(BaseModel):
    """Detailed reward breakdown"""
    per_step_score: float = Field(..., description="Score for issues found this step")
    efficiency_bonus: float = Field(default=0.0, description="Bonus for quick identification")
    risk_match_bonus: float = Field(default=0.0, description="Bonus for correct risk level")
    analysis_quality: float = Field(default=0.0, description="Quality of analysis text")
    false_positive_penalty: float = Field(default=0.0, description="Penalty for incorrect flags")
    total_step_reward: float = Field(..., description="Total reward this step")


class StepResult(BaseModel):
    """Result of a single step"""
    observation: LexObservation
    reward: float = Field(..., description="Step reward")
    reward_breakdown: RewardBreakdown = Field(..., description="Reward details")
    done: bool = Field(..., description="Episode done?")
    info: Dict[str, Any] = Field(default_factory=dict, description="Additional info")


class ResetResult(BaseModel):
    """Result of reset"""
    observation: LexObservation
    info: Dict[str, Any] = Field(default_factory=dict)
