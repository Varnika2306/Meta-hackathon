"""
LexEnv FastAPI Server
Implements OpenEnv-compliant HTTP API: /reset, /step, /state, /tasks, /health
"""

import os
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import JSONResponse
from typing import Optional

from lexenv.env import LexEnv, make_env
from lexenv.models import LexAction, RiskLevel, IssueFlag
from lexenv.data.contracts import list_tasks

# ============================================================================
# App setup
# ============================================================================

app = FastAPI(
    title="LexEnv — Legal Document Analysis Environment",
    description="OpenEnv-compliant RL environment for AI legal contract analysis",
    version="1.0.0",
)

# Single shared environment instance per server process.
# For concurrent use, swap this for a per-session store (dict keyed by session_id).
env: LexEnv = make_env()


# ============================================================================
# Routes
# ============================================================================

@app.get("/health")
async def health():
    """Health check — required by OpenEnv spec and Docker HEALTHCHECK."""
    return {"status": "ok"}


@app.get("/tasks")
async def get_tasks():
    """
    List all available tasks with metadata.
    Returns task_id → {name, difficulty, expected_issues, max_steps}.
    """
    return {"tasks": list_tasks()}


@app.post("/reset")
async def reset(
    task_id: str = Query(default="clause_id", description="Task identifier"),
    seed: Optional[int] = Query(default=None, description="Random seed (reserved)"),
):
    """
    Reset environment and begin a new episode.

    Query params
    ------------
    task_id : "clause_id" | "sla_review" | "ma_assessment"  (default: clause_id)
    seed    : integer seed for reproducibility (currently a no-op, reserved)

    Returns
    -------
    ResetResult JSON:  { observation: {...}, info: {...} }
    """
    try:
        result = await env.reset(task_id=task_id, seed=seed)
        return result.model_dump()
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Reset failed: {exc}")


@app.post("/step")
async def step(action: dict):
    """
    Submit one analysis step.

    Request body
    ------------
    {
      "analysis":        "detailed analysis text",
      "flags": [
        {
          "title":            "Issue title",
          "severity":         "low|medium|high|critical",
          "clause_reference": "Section X",   // optional
          "remediation":      "Fix suggestion"  // optional
        }
      ],
      "risk_assessment": "low|medium|high|critical"
    }

    Returns
    -------
    StepResult JSON: { observation, reward, reward_breakdown, done, info }
    """
    if env.current_state is None:
        raise HTTPException(
            status_code=400,
            detail="Environment not initialized. Call POST /reset first.",
        )

    # ---- Parse flags ----
    raw_flags = action.get("flags", [])
    parsed_flags = []
    for f in raw_flags:
        try:
            parsed_flags.append(
                IssueFlag(
                    title=f.get("title", "Untitled"),
                    severity=RiskLevel(f.get("severity", "medium").lower()),
                    clause_reference=f.get("clause_reference"),
                    remediation=f.get("remediation"),
                )
            )
        except (ValueError, KeyError):
            # Skip malformed flag entries rather than crashing
            pass

    # ---- Parse risk_assessment ----
    raw_risk = action.get("risk_assessment", "medium")
    try:
        risk = RiskLevel(raw_risk.lower())
    except ValueError:
        risk = RiskLevel.MEDIUM

    lex_action = LexAction(
        analysis=action.get("analysis", ""),
        flags=parsed_flags,
        risk_assessment=risk,
    )

    try:
        result = await env.step(lex_action)
        return result.model_dump()
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Step failed: {exc}")


@app.get("/state")
async def get_state():
    """
    Return the full current environment state.

    Returns
    -------
    State dict including step_count, episode_done, step_rewards, etc.
    If no episode is active, returns {"initialized": false}.
    """
    return env.state()


# ============================================================================
# Entry-points
# ============================================================================

def main():
    """Entry-point for `server` console script declared in pyproject.toml."""
    import uvicorn

    port = int(os.getenv("PORT", "8000"))
    uvicorn.run("server.app:app", host="0.0.0.0", port=port, reload=False)


if __name__ == "__main__":
    main()
