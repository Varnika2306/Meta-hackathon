"""
Inference agent for LexEnv using Google Gemini API.

Runs a baseline legal-analysis agent against the LexEnv environment.
Uses Gemini 1.5 Flash to analyze contracts and report structured
[START]/[STEP]/[END] logs.

Configuration via environment variables:
    GOOGLE_API_KEY — your Gemini API key (required)
    MODEL_NAME     — default: gemini-1.5-flash
    LEXENV_TASK    — task to run: clause_id | sla_review | ma_due_diligence
    LEXENV_HOST    — server URL, default: http://127.0.0.1:8000

Usage:
    export GOOGLE_API_KEY=AIzaSy...
    python inference.py
"""

import json
import os
import re
import sys
import textwrap
import time
from typing import List, Optional

import google.generativeai as genai
import requests

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

# Look for various env var names common in different setups
_google_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
_hf_token = os.getenv("HF_TOKEN")

# Avoid using a Groq key (starts with gsk_) for Gemini calls
if _hf_token and _hf_token.startswith("gsk_"):
    _hf_token = None

API_KEY = _google_key or _hf_token
MODEL_NAME = os.getenv("MODEL_NAME", "gemini-3.1-flash")
LEXENV_HOST = os.getenv("LEXENV_HOST", "http://127.0.0.1:8000")
MAX_STEPS = 5

TASKS = os.getenv("LEXENV_TASK", "clause_id,sla_review,ma_due_diligence").split(",")

# ---------------------------------------------------------------------------
# Logging helpers (OpenEnv convention)
# ---------------------------------------------------------------------------


def log_start(task: str, env: str, model: str) -> None:
    print(f"[START] task={task} env={env} model={model}", flush=True)


def log_step(
    step: int, action: str, reward: float, done: bool, error: Optional[str]
) -> None:
    err = error if error else "null"
    # Truncate action for clean logs
    action_preview = action[:80].replace("\n", " ")
    print(
        f"[STEP] step={step} action={action_preview!r} "
        f"reward={reward:.2f} done={str(done).lower()} error={err}",
        flush=True,
    )


def log_end(
    success: bool, steps: int, score: float, rewards: List[float]
) -> None:
    rr = ",".join(f"{r:.2f}" for r in rewards)
    print(
        f"[END] success={str(success).lower()} steps={steps} "
        f"score={score:.3f} rewards={rr}",
        flush=True,
    )


# ---------------------------------------------------------------------------
# LLM interaction
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = textwrap.dedent("""\
    You are a senior legal analyst. Your task is to carefully analyze
    legal contracts and identify ALL risky, problematic, or unusual
    clauses. For each issue you find:

    1. Explain WHY it is problematic
    2. Reference the specific contract language
    3. Assess the risk level

    You MUST respond in the following JSON format:
    {
        "analysis": "Your detailed analysis text here...",
        "flags": ["issue_id_1", "issue_id_2"],
        "risk_level": "low|medium|high|critical"
    }

    Use descriptive snake_case flag names like:
    overbroad_non_compete, blanket_ip_assignment, perpetual_term,
    no_uptime_sla, low_liability_cap, asymmetric_termination, etc.

    Be thorough — identify as many issues as possible in each response.
""")


def build_user_message(obs_data: dict) -> str:
    """Build the user prompt from an observation."""
    parts = []
    if obs_data.get("instruction"):
        parts.append(f"**Instruction**: {obs_data['instruction']}")
    if obs_data.get("feedback") and obs_data["feedback"] != "Episode started. Analyze the contract and flag issues.":
        parts.append(f"**Previous Feedback**: {obs_data['feedback']}")
    if obs_data.get("contract_excerpt"):
        parts.append(f"**Contract**:\n```\n{obs_data['contract_excerpt']}\n```")
    return "\n\n".join(parts)


def parse_llm_response(content: str) -> dict:
    """Parse the LLM response into action fields."""
    # Try to extract JSON from the response
    json_match = re.search(r"\{[^{}]*\}", content, re.DOTALL)
    if json_match:
        try:
            data = json.loads(json_match.group())
            return {
                "analysis": data.get("analysis", content),
                "flags": data.get("flags", []),
                "risk_level": data.get("risk_level", "medium"),
            }
        except json.JSONDecodeError:
            pass

    # Fallback: treat entire response as analysis
    return {
        "analysis": content,
        "flags": [],
        "risk_level": "medium",
    }


# ---------------------------------------------------------------------------
# Environment client (direct HTTP)
# ---------------------------------------------------------------------------


def env_reset(base_url: str, task_id: str) -> dict:
    """Reset the environment via HTTP POST."""
    resp = requests.post(
        f"{base_url}/reset",
        json={"task_id": task_id},
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()


def env_step(base_url: str, action: dict, task_id: str) -> dict:
    """Step the environment via HTTP POST.
    
    Includes task_id to support the stateless fix for REST calls.
    """
    resp = requests.post(
        f"{base_url}/step",
        json={"action": action, "task_id": task_id},
        timeout=60,
    )
    resp.raise_for_status()
    return resp.json()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def run_task(model: genai.GenerativeModel, base_url: str, task_id: str) -> float:
    """Run a single task and return the final score."""
    log_start(task_id, "lexenv", MODEL_NAME)

    rewards: List[float] = []
    done = False
    obs_data = {}

    try:
        # Reset environment
        reset_resp = env_reset(base_url, task_id)
        obs_data = reset_resp.get("observation", reset_resp)

        for step in range(1, MAX_STEPS + 1):
            if done:
                break

            # Ask LLM to analyze the contract
            user_msg = build_user_message(obs_data)
            
            # Gemini generation
            prompt = f"{SYSTEM_PROMPT}\n\n{user_msg}"
            response = model.generate_content(prompt)
            llm_content = response.text or ""
            
            # Parse response → action
            action = parse_llm_response(llm_content)

            # Step environment
            step_resp = env_step(base_url, action, task_id)
            obs_data = step_resp.get("observation", step_resp)

            reward = step_resp.get("reward", obs_data.get("reward", 0.0)) or 0.0
            done = step_resp.get("done", obs_data.get("done", False))

            rewards.append(reward)
            log_step(step, action["analysis"], reward, done, None)
            
            # Small delay for rate limiting if needed
            time.sleep(1)

    except Exception as e:
        log_step(len(rewards) + 1, "ERROR", 0.0, True, str(e))
        done = True

    score = sum(rewards) / max(len(rewards), 1)
    log_end(score >= 0.5, len(rewards), score, rewards)
    return score


def main():
    """Run inference across all configured tasks."""
    if not API_KEY:
        print(
            "ERROR: No API key found. Set the GOOGLE_API_KEY environment variable.",
            file=sys.stderr,
        )
        sys.exit(1)

    genai.configure(api_key=API_KEY)
    # Using the flash model as requested
    model = genai.GenerativeModel(MODEL_NAME)

    print(f"{'='*60}")
    print(f"LexEnv Inference Agent (Gemini)")
    print(f"Model: {MODEL_NAME}")
    print(f"Host:  {LEXENV_HOST}")
    print(f"Tasks: {TASKS}")
    print(f"{'='*60}\n")

    scores = {}
    for task_id in TASKS:
        task_id = task_id.strip()
        if not task_id:
            continue
        print(f"\n--- Running task: {task_id} ---\n")
        score = run_task(model, LEXENV_HOST, task_id)
        scores[task_id] = score
        print(f"\n  Score for {task_id}: {score:.3f}\n")

    print(f"\n{'='*60}")
    print("FINAL RESULTS")
    print(f"{'='*60}")
    for task_id, score in scores.items():
        print(f"  {task_id:25s}  ->  {score:.3f}")
    avg = sum(scores.values()) / max(len(scores), 1)
    print(f"  {'AVERAGE':25s}  ->  {avg:.3f}")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
