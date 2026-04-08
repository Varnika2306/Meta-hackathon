"""
Inference Script for LexEnv Custom Benchmark
===================================
MANDATORY VARIABLES:
    API_BASE_URL     The API endpoint for the LLM.
    MODEL_NAME       The model identifier to use for inference.
    HF_TOKEN         Your Hugging Face / API key.
    LOCAL_IMAGE_NAME The name of the local image to use for the environment.

STDOUT FORMAT:
    [START] task=<task_name> env=<benchmark> model=<model_name>
    [STEP] step=<n> action=<action_str> reward=<0.00> done=<true|false> error=<msg|null>
    [END] success=<true|false> steps=<n> score=<0.00> rewards=<r1,r2,...,rn>
"""

import json
import os
import re
import sys
import textwrap
import time
from typing import List, Optional

from openai import OpenAI
import requests

# ---------------------------------------------------------------------------
# Mandatory Environment Variables
# ---------------------------------------------------------------------------

API_KEY = os.getenv("HF_TOKEN")
API_BASE_URL = os.getenv("API_BASE_URL", "https://api.groq.com/openai/v1")
MODEL_NAME = os.getenv("MODEL_NAME", "llama-3.3-70b-versatile")
LOCAL_IMAGE_NAME = os.getenv("LOCAL_IMAGE_NAME")

# ---------------------------------------------------------------------------
# LexEnv Configuration
# ---------------------------------------------------------------------------

LEXENV_HOST = os.getenv("LEXENV_HOST", "http://127.0.0.1:8000")
BENCHMARK = os.getenv("BENCHMARK", "lexenv")
TASKS = os.getenv("LEXENV_TASK", "clause_id,sla_review,ma_due_diligence").split(",")

# ---------------------------------------------------------------------------
# Logging Requirements
# ---------------------------------------------------------------------------

def log_start(task: str, env: str, model: str) -> None:
    print(f"[START] task={task} env={env} model={model}", flush=True)


def log_step(step: int, action: str, reward: float, done: bool, error: Optional[str]) -> None:
    error_val = error if error else "null"
    done_val = str(done).lower()
    
    # Ensure no newlines in action string
    action_clean = action.replace("\n", " ").replace("\r", " ")
    
    print(
        f"[STEP] step={step} action={action_clean} reward={reward:.2f} done={done_val} error={error_val}",
        flush=True,
    )


def log_end(success: bool, steps: int, score: float, rewards: List[float]) -> None:
    rewards_str = ",".join(f"{r:.2f}" for r in rewards)
    print(f"[END] success={str(success).lower()} steps={steps} score={score:.3f} rewards={rewards_str}", flush=True)


# ---------------------------------------------------------------------------
# LLM Interaction
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = textwrap.dedent("""\
    You are a senior legal analyst. Your task is to carefully analyze
    legal contracts and identify ALL risky, problematic, or unusual clauses.
    For each issue you find:

    1. Explain WHY it is problematic
    2. Reference the specific contract language
    3. Assess the risk level

    You MUST respond in the following JSON format ONLY — no extra text:
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
    json_match = re.search(r"\{.*\}", content, re.DOTALL)
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

    return {
        "analysis": content,
        "flags": [],
        "risk_level": "medium",
    }


def call_openai_client(client: OpenAI, user_message: str) -> str:
    """Make a single chat completion call using OpenAI wrapper."""
    try:
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_message},
            ],
            temperature=0.2,
            max_tokens=1024,
            stream=False,
        )
        return response.choices[0].message.content or ""
    except Exception as exc:
        print(f"[DEBUG] Model request failed: {exc}", flush=True)
        return ""


# ---------------------------------------------------------------------------
# Environment client (direct HTTP)
# ---------------------------------------------------------------------------

def env_reset(base_url: str, task_id: str) -> dict:
    resp = requests.post(
        f"{base_url}/reset",
        json={"task_id": task_id},
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()


def env_step(base_url: str, action: dict, task_id: str) -> dict:
    resp = requests.post(
        f"{base_url}/step",
        json={"action": action, "task_id": task_id},
        timeout=60,
    )
    resp.raise_for_status()
    return resp.json()


# ---------------------------------------------------------------------------
# Main Routine
# ---------------------------------------------------------------------------

def run_task(client: OpenAI, base_url: str, task_id: str) -> float:
    """Run a single task with ONE LLM call and return the final score."""
    log_start(task=task_id, env=BENCHMARK, model=MODEL_NAME)

    rewards: List[float] = []
    done = False
    score = 0.0
    steps_taken = 0

    try:
        reset_resp = env_reset(base_url, task_id)
        obs_data = reset_resp.get("observation", reset_resp)

        user_msg = build_user_message(obs_data)
        llm_content = call_openai_client(client, user_msg)

        action_dict = parse_llm_response(llm_content)
        
        step_resp = env_step(base_url, action_dict, task_id)
        obs_data = step_resp.get("observation", step_resp)

        reward = float(step_resp.get("reward", obs_data.get("reward", 0.0)) or 0.0)
        done = bool(step_resp.get("done", obs_data.get("done", True)))

        rewards.append(reward)
        steps_taken = 1
        
        # We output the JSON analysis as the "action_str"
        action_repr = json.dumps(action_dict)
        
        log_step(step=1, action=action_repr, reward=reward, done=done, error=None)

    except Exception as e:
        print(f"[DEBUG] env error: {e}", flush=True)
        log_step(step=steps_taken + 1, action="ERROR", reward=0.0, done=True, error=str(e))
        done = True

    score = sum(rewards) / max(len(rewards), 1)
    # The user template requires boolean success condition
    # For lexenv, let's say >= 0.5 is success
    success = score >= 0.5
    
    log_end(success=success, steps=steps_taken, score=score, rewards=rewards)
    return score


def main():
    if not API_KEY:
        print("ERROR: No API_KEY / HF_TOKEN found in environment.", file=sys.stderr)
        sys.exit(1)

    client = OpenAI(base_url=API_BASE_URL, api_key=API_KEY)

    print(f"[DEBUG] LexEnv Inference Agent using OpenAI Client")
    print(f"[DEBUG] Base URL: {API_BASE_URL}")
    print(f"[DEBUG] Model: {MODEL_NAME}")
    
    scores = {}
    for task_id in TASKS:
        task_id = task_id.strip()
        if not task_id:
            continue
        score = run_task(client, LEXENV_HOST, task_id)
        scores[task_id] = score
        time.sleep(2)


if __name__ == "__main__":
    main()
