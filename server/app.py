"""
LexEnv FastAPI Server
Uses openenv-core's create_fastapi_app for full spec compliance.
Provides /health, /metadata, /schema, /mcp, /reset, /step, /state automatically.
"""

import os
from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

from openenv.core import create_fastapi_app

from lexenv.env import make_env
from lexenv.models import LexAction, LexObservation
from lexenv.data.contracts import list_tasks

# ============================================================================
# App — all OpenEnv-required endpoints generated automatically
# ============================================================================

app: FastAPI = create_fastapi_app(make_env, LexAction, LexObservation)

# Mount the frontend UI
app.mount("/ui", StaticFiles(directory="frontend", html=True), name="frontend")

# Override the auto-generated title/version with our project info
app.title = "LexEnv — Legal Document Analysis Environment"
app.version = "1.0.0"
app.description = (
    "OpenEnv-compliant RL environment for AI legal contract analysis. "
    "Three tasks of increasing difficulty: NDA (easy), SLA (medium), M&A (hard)."
)


# ============================================================================
# Extra route: list available tasks
# ============================================================================

@app.get("/tasks", tags=["Environment Info"])
async def get_tasks():
    """List all available tasks with metadata."""
    return {"tasks": list_tasks()}


@app.get("/", include_in_schema=False)
async def root():
    """Redirect root to /ui/."""
    return RedirectResponse(url="/ui/")


# ============================================================================
# Entry-point
# ============================================================================

def main():
    """Entry-point for `server` console script declared in pyproject.toml."""
    import uvicorn
    port = int(os.getenv("PORT", "7860"))
    uvicorn.run("server.app:app", host="0.0.0.0", port=port, reload=False)


if __name__ == "__main__":
    main()
