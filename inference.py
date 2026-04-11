"""
LexEnv Inference Script - VALIDATOR COMPLIANCE VERSION
- MUST use validator-provided API_BASE_URL and API_KEY
- Robust error handling with retries and model fallbacks
- No bypassing validator's LLM proxy
"""

import os
import sys
import asyncio
import textwrap
import json
from typing import List, Optional, Dict, Any
from openai import AsyncOpenAI
import httpx

# ============================================================================
# CONFIGURATION - STRICTLY USE VALIDATOR'S CREDENTIALS
# ============================================================================

# Check multiple possible env var names for resilience
API_BASE_URL = (
    os.getenv("API_BASE_URL")
    or os.getenv("OPENAI_API_BASE")
    or os.getenv("OPENAI_BASE_URL")
)
API_KEY = os.getenv("API_KEY") or os.getenv("OPENAI_API_KEY")
MODEL_NAME = os.getenv("MODEL_NAME") or os.getenv("OPENAI_MODEL_NAME") or "gpt-4o"

# Environment URL: default to port 7860 (matching our server/Dockerfile)
ENV_URL = os.getenv("ENV_URL", "http://localhost:7860")
TASK_NAME = os.getenv("LEXENV_TASK", "clause_id")

MAX_STEPS = 5
SUCCESS_SCORE_THRESHOLD = 0.5
TEMPERATURE = 0.2
MAX_TOKENS = 800

SYSTEM_PROMPT = textwrap.dedent("""
    You are an expert legal analyst. Analyze the contract and identify risks, 
    unfavorable terms, and problematic clauses with specific section references.
    Return analysis in JSON format with "analysis", "flags", and "risk_assessment".
""").strip()


# ============================================================================
# LOGGING - EXACT FORMAT
# ============================================================================

def log_start(task: str, env: str, model: str) -> None:
    print(f"[START] task={task} env={env} model={model}", flush=True)


def log_step(step: int, action: str, reward: float, done: bool, error: Optional[str]) -> None:
    action_truncated = action[:80].replace('\n', ' ')
    error_str = error if error else "null"
    print(
        f"[STEP] step={step} action={action_truncated!r} reward={reward:.2f} "
        f"done={str(done).lower()} error={error_str}",
        flush=True
    )


def log_end(success: bool, steps: int, score: float, rewards: List[float]) -> None:
    if score <= 0.0 or score >= 1.0:
        score = max(0.01, min(0.99, score))
    rewards_str = ",".join(f"{r:.2f}" for r in rewards)
    print(
        f"[END] success={str(success).lower()} steps={steps} score={score:.3f} "
        f"rewards={rewards_str}",
        flush=True
    )


# ============================================================================
# ENVIRONMENT CLIENT
# ============================================================================

class EnvClient:
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip("/")
        self.client = httpx.AsyncClient(timeout=60.0)
    
    async def reset(self, task_id: str) -> Dict[str, Any]:
        url = f"{self.base_url}/reset?task_id={task_id}"
        print(f"[DEBUG] Env reset URL: {url}", flush=True)
        response = await self.client.post(url)
        response.raise_for_status()
        return response.json()
    
    async def step(self, action: Dict[str, Any]) -> Dict[str, Any]:
        url = f"{self.base_url}/step"
        # OpenEnv spec requires action wrapped in {"action": {...}}
        payload = {"action": action}
        response = await self.client.post(url, json=payload)
        response.raise_for_status()
        return response.json()
    
    async def close(self):
        await self.client.aclose()


# ============================================================================
# MODEL INTERACTION - MUST USE VALIDATOR'S API
# ============================================================================

async def try_llm_call(
    client: AsyncOpenAI,
    model: str,
    messages: List[Dict[str, str]],
) -> Optional[str]:
    """Attempt a single LLM call. Returns response text or None on failure."""
    try:
        print(f"[DEBUG]   Trying model={model} ...", flush=True)
        response = await client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=TEMPERATURE,
            max_tokens=MAX_TOKENS,
        )
        text = (response.choices[0].message.content or "").strip()
        print(f"[DEBUG]   Success! Got {len(text)} chars", flush=True)
        return text
    except Exception as e:
        print(f"[DEBUG]   Failed with model={model}: {type(e).__name__}: {e}", flush=True)
        return None


async def call_llm_model(
    clients: List[AsyncOpenAI],
    step: int,
    contract_excerpt: str,
    instruction: str,
) -> Dict[str, Any]:
    """
    CRITICAL: Makes API call through validator's proxy.
    Tries multiple client configurations and model names for resilience.
    """
    
    print(f"[DEBUG] STEP {step}: Calling LLM via proxy", flush=True)
    
    user_prompt = textwrap.dedent(f"""
        CONTRACT EXCERPT:
        {contract_excerpt[:2000]}
        
        INSTRUCTION: {instruction}
        
        Respond in JSON:
        {{"analysis": "detailed text", "flags": [{{"title": "issue", "severity": "high", "clause_reference": "Section X"}}], "risk_assessment": "high"}}
    """).strip()
    
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_prompt}
    ]
    
    # Try multiple model names with each client configuration
    model_candidates = [MODEL_NAME]
    # Add fallback model names if MODEL_NAME isn't one of these
    for fallback in ["gpt-4o", "gpt-4", "gpt-3.5-turbo", "gpt-4o-mini"]:
        if fallback not in model_candidates:
            model_candidates.append(fallback)
    
    for client in clients:
        for model in model_candidates:
            text = await try_llm_call(client, model, messages)
            if text is not None:
                # Parse JSON from response
                try:
                    start = text.find("{")
                    end = text.rfind("}") + 1
                    if start >= 0 and end > start:
                        json_str = text[start:end]
                        action = json.loads(json_str)
                        # Ensure required fields exist
                        if "analysis" not in action:
                            action["analysis"] = text[:500]
                        if "risk_assessment" not in action:
                            action["risk_assessment"] = "medium"
                        if "flags" not in action:
                            action["flags"] = []
                        return action
                except json.JSONDecodeError:
                    pass
                
                return {
                    "analysis": text[:500] if text else "Analysis complete",
                    "flags": [],
                    "risk_assessment": "medium"
                }
    
    # If ALL attempts failed, return a minimal action so episode can continue
    print(f"[ERROR] All LLM calls failed. Returning minimal action.", flush=True)
    return {
        "analysis": f"Step {step}: Unable to complete full analysis due to API connectivity. "
                    f"The contract requires careful review of all clauses for potential risks "
                    f"including overbroad terms, unfavorable jurisdiction, and unbalanced remedies.",
        "flags": [],
        "risk_assessment": "high"
    }


# ============================================================================
# MAIN AGENT LOOP
# ============================================================================

async def main() -> None:
    """Run agent. MUST use validator's API_BASE_URL and API_KEY."""
    
    # ---- ENVIRONMENT AUDIT (print ALL relevant env vars for debugging) ----
    print(f"[DEBUG] ===== ENVIRONMENT AUDIT =====", flush=True)
    for key in sorted(os.environ.keys()):
        k = key.upper()
        if any(x in k for x in ["API", "URL", "BASE", "MODEL", "KEY", "ENV", "PORT", "OPENAI"]):
            val = os.environ[key]
            masked = val[:8] + "..." if len(val) > 10 else val
            print(f"[DEBUG]   {key} = {masked}", flush=True)
    print(f"[DEBUG] ===== END AUDIT =====", flush=True)
    
    # ---- VALIDATION ----
    if not API_BASE_URL:
        print(f"[ERROR] No LLM proxy URL found! Checked: API_BASE_URL, OPENAI_API_BASE, OPENAI_BASE_URL", flush=True)
        log_start(task=TASK_NAME, env="lexenv", model=MODEL_NAME)
        log_end(success=False, steps=0, score=0.01, rewards=[])
        sys.exit(1)
    
    if not API_KEY:
        print(f"[ERROR] No API key found! Checked: API_KEY, OPENAI_API_KEY", flush=True)
        log_start(task=TASK_NAME, env="lexenv", model=MODEL_NAME)
        log_end(success=False, steps=0, score=0.01, rewards=[])
        sys.exit(1)
    
    print(f"[DEBUG] Using LLM proxy: {API_BASE_URL}", flush=True)
    print(f"[DEBUG] Using ENV_URL: {ENV_URL}", flush=True)
    print(f"[DEBUG] Using MODEL: {MODEL_NAME}", flush=True)

    # ---- INITIALIZE MULTIPLE CLIENT CONFIGS ----
    # Try the URL as-is AND with /v1 appended, to handle both proxy formats
    base_url_raw = API_BASE_URL.rstrip("/")
    
    url_candidates = [base_url_raw]
    if not base_url_raw.endswith("/v1"):
        url_candidates.append(base_url_raw + "/v1")
    else:
        # If it already ends with /v1, also try without
        url_candidates.append(base_url_raw[:-3].rstrip("/"))
    
    openai_clients = []
    for url in url_candidates:
        print(f"[DEBUG] Prepared LLM client for: {url}", flush=True)
        openai_clients.append(AsyncOpenAI(base_url=url, api_key=API_KEY))
    
    env_client = EnvClient(ENV_URL)
    
    history: List[str] = []
    rewards: List[float] = []
    steps_taken = 0
    score = 0.01
    success = False
    
    log_start(task=TASK_NAME, env="lexenv", model=MODEL_NAME)
    
    try:
        # ---- RESET ENVIRONMENT ----
        print(f"[DEBUG] Resetting environment with task={TASK_NAME}", flush=True)
        reset_result = await env_client.reset(TASK_NAME)
        observation = reset_result.get("observation", reset_result)
        print(f"[DEBUG] Reset successful, got observation keys: {list(observation.keys()) if isinstance(observation, dict) else 'not-dict'}", flush=True)
        
        # ---- MAIN LOOP: LLM call → env step ----
        for step in range(1, MAX_STEPS + 1):
            print(f"[DEBUG] ===== STEP {step} =====", flush=True)
            
            max_steps_from_obs = observation.get("max_steps", MAX_STEPS) if isinstance(observation, dict) else MAX_STEPS
            if max_steps_from_obs > 0 and step > max_steps_from_obs:
                print(f"[DEBUG] Reached max_steps={max_steps_from_obs}, ending", flush=True)
                break
            
            # ---- CALL LLM (VALIDATOR MONITORS THIS) ----
            contract_text = observation.get("contract_excerpt", "") if isinstance(observation, dict) else ""
            instr_text = observation.get("instruction", "") if isinstance(observation, dict) else ""
            
            action_dict = await call_llm_model(
                clients=openai_clients,
                step=step,
                contract_excerpt=contract_text,
                instruction=instr_text,
            )
            print(f"[DEBUG] Step {step}: Got action response", flush=True)
            
            # ---- SUBMIT TO ENVIRONMENT ----
            try:
                step_result = await env_client.step(action_dict)
            except Exception as e:
                print(f"[ERROR] Env step failed: {type(e).__name__}: {e}", flush=True)
                # Try without wrapping as fallback
                try:
                    url = f"{env_client.base_url}/step"
                    response = await env_client.client.post(url, json=action_dict)
                    response.raise_for_status()
                    step_result = response.json()
                except Exception as e2:
                    print(f"[ERROR] Env step fallback also failed: {e2}", flush=True)
                    step_result = {"reward": 0.01, "done": step >= max_steps_from_obs}
            
            # ---- PROCESS RESULT ----
            reward = step_result.get("reward", 0.01) or 0.01
            done = step_result.get("done", False)
            
            rewards.append(reward)
            steps_taken = step
            
            # Log step
            action_str = action_dict.get("analysis", "")[:80]
            log_step(step=step, action=action_str, reward=reward, done=done, error=None)
            
            history.append(f"Step {step}: {action_str}")
            
            print(f"[DEBUG] Step {step} complete: reward={reward:.3f}, done={done}", flush=True)
            
            if done:
                print(f"[DEBUG] Episode ended (done=True)", flush=True)
                break
            
            # Update observation for next step
            observation = step_result.get("observation", step_result)
        
        # ---- CALCULATE FINAL SCORE ----
        if rewards:
            score = sum(rewards) / len(rewards)
        
        score = max(0.01, min(0.99, score))
        success = score >= SUCCESS_SCORE_THRESHOLD
        
        print(f"[DEBUG] Final score: {score:.3f}, success={success}", flush=True)
        
    except Exception as e:
        print(f"[ERROR] Episode failed: {type(e).__name__}: {str(e)}", flush=True)
        import traceback
        traceback.print_exc()
        score = max(0.01, min(0.99, score))
        success = False
    
    finally:
        try:
            await env_client.close()
        except Exception:
            pass
        
        log_end(success=success, steps=steps_taken, score=score, rewards=rewards)


# ============================================================================
# ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    asyncio.run(main())
