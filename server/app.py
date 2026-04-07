"""
FastAPI application for the LexEnv Legal Document Analysis Environment.

Exposes the LexEnv environment over HTTP/WebSocket endpoints using
the OpenEnv ``create_app`` factory.

Usage:
    # Development:
    uvicorn server.app:app --reload --host 0.0.0.0 --port 8000

    # Production:
    uvicorn server.app:app --host 0.0.0.0 --port 8000
"""

from openenv.core.env_server.http_server import create_app

from lexenv.env import LexEnv
from lexenv.models import LexAction, LexObservation

# Create the FastAPI app using the OpenEnv factory.
# Passing the class (not an instance) enables per-session isolation.
app = create_app(LexEnv, LexAction, LexObservation, env_name="lexenv")


def main():
    """Entry point for direct execution.

    Run with:
        python -m server.app
        uv run --project . server
    """
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)


if __name__ == "__main__":
    main()
