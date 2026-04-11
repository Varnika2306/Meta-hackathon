"""
LexEnv Inference Script - VALIDATOR COMPLIANCE VERSION
- MUST use validator-provided API_BASE_URL and API_KEY
- Fails LOUDLY if API calls not made
- No fallbacks, no bypassing validator's LLM proxy
"""

import os
import sys
import asyncio
import textwrap
import json
from typing import List, Optional, Dict, Any
from openai import AsyncOpenAI, APIError
import httpx

# ============================================================================
# CONFIGURATION - STRICTLY USE VALIDATOR'S CREDENTIALS
# ============================================================================

# THESE MUST BE SET BY VALIDATOR - NO DEFAULTS!
API_BASE_URL = os.getenv("API_BASE_URL")
API_KEY = os.getenv("API_KEY")
MODEL_NAME = os.getenv("MODEL_NAME", "gpt-4")  # Validator provides this

ENV_URL = os.getenv("ENV_URL", "http://localhost:8000")
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
        self.base_url = base_url
        self.client = httpx.AsyncClient(timeout=30.0)
    
    async def reset(self, task_id: str) -> Dict[str, Any]:
        url = f"{self.base_url}/reset?task_id={task_id}"
        response = await self.client.post(url)
        response.raise_for_status()
        return response.json()
    
    async def step(self, action: Dict[str, Any]) -> Dict[str, Any]:
        url = f"{self.base_url}/step"
        response = await self.client.post(url, json=action)
        response.raise_for_status()
        return response.json()
    
    async def close(self):
        await self.client.aclose()


# ============================================================================
# MODEL INTERACTION - MUST USE VALIDATOR'S API
# ============================================================================

async def call_llm_model(
    client: AsyncOpenAI,
    step: int,
    contract_excerpt: str,
    instruction: str,
) -> Dict[str, Any]:
    """
    CRITICAL: This MUST make an API call through validator's API_BASE_URL.
    No fallbacks, no local processing, no defaults.
    Raises exception if API call fails.
    """
    
    print(f"[DEBUG] STEP {step}: Calling LLM at {API_BASE_URL}", flush=True)
    
    user_prompt = textwrap.dedent(f"""
        CONTRACT EXCERPT:
        {contract_excerpt[:2000]}
        
        INSTRUCTION: {instruction}
        
        Respond in JSON:
        {{"analysis": "detailed text", "flags": [{{...}}], "risk_assessment": "high"}}
    """).strip()
    
    try:
        # VALIDATOR WILL MONITOR THIS CALL
        response = await client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt}
            ],
            temperature=TEMPERATURE,
            max_tokens=MAX_TOKENS
        )
        
        text = (response.choices[0].message.content or "").strip()
        print(f"[DEBUG] LLM response received ({len(text)} chars)", flush=True)
        
        # Parse JSON
        try:
            start = text.find("{")
            end = text.rfind("}") + 1
            if start >= 0 and end > start:
                json_str = text[start:end]
                action = json.loads(json_str)
                print(f"[DEBUG] Parsed JSON action successfully", flush=True)
                return action
        except json.JSONDecodeError:
            pass
        
        # If JSON parsing fails, create basic structure from response
        return {
            "analysis": text[:500] if text else "Analysis complete",
            "flags": [],
            "risk_assessment": "medium"
        }
        
    except Exception as e:
        # FAIL LOUDLY - don't hide API errors
        print(f"[ERROR] LLM API CALL FAILED: {type(e).__name__}: {str(e)}", flush=True)
        raise  # Re-raise to fail the whole script


# ============================================================================
# MAIN AGENT LOOP
# ============================================================================

async def main() -> None:
    """Run agent. MUST use validator's API_BASE_URL and API_KEY."""
    
    # ---- VALIDATION ----
    if not API_BASE_URL:
        print(f"[ERROR] API_BASE_URL not set by validator!", flush=True)
        log_start(task=TASK_NAME, env="lexenv", model=MODEL_NAME)
        log_end(success=False, steps=0, score=0.01, rewards=[])
        sys.exit(1)
    
    if not API_KEY:
        print(f"[ERROR] API_KEY not set by validator!", flush=True)
        log_start(task=TASK_NAME, env="lexenv", model=MODEL_NAME)
        log_end(success=False, steps=0, score=0.01, rewards=[])
        sys.exit(1)
    
    print(f"[DEBUG] Using validator's API:", flush=True)
    print(f"[DEBUG]   API_BASE_URL = {API_BASE_URL}", flush=True)
    print(f"[DEBUG]   MODEL_NAME = {MODEL_NAME}", flush=True)
    
    # ---- INITIALIZE ----
    try:
        # MUST use validator's credentials
        # FINAL HARDENING: Ensure the base URL ends in /v1. 
        # Many proxies (like LiteLLM) require this to route correctly.
        sanitized_base_url = API_BASE_URL.rstrip("/")
        if not sanitized_base_url.endswith("/v1"):
            sanitized_base_url += "/v1"
            print(f"[DEBUG] Sanitized API_BASE_URL: {sanitized_base_url}", flush=True)

        openai_client = AsyncOpenAI(base_url=sanitized_base_url, api_key=API_KEY)
        env_client = EnvClient(ENV_URL)
        
        history: List[str] = []
        rewards: List[float] = []
        steps_taken = 0
        score = 0.01
        
        log_start(task=TASK_NAME, env="lexenv", model=MODEL_NAME)
        
        # ---- RESET ENVIRONMENT ----
        print(f"[DEBUG] Resetting environment with task={TASK_NAME}", flush=True)
        reset_result = await env_client.reset(TASK_NAME)
        observation = reset_result.get("observation", {})
        
        # ---- MAIN LOOP ----
        for step in range(1, MAX_STEPS + 1):
            print(f"[DEBUG] ===== STEP {step} =====", flush=True)
            
            if observation.get("max_steps", MAX_STEPS) > 0 and step > observation.get("max_steps"):
                print(f"[DEBUG] Reached max_steps, ending episode", flush=True)
                break
            
            # ---- CALL LLM (VALIDATOR MONITORS THIS) ----
            try:
                action_dict = await call_llm_model(
                    client=openai_client,
                    step=step,
                    contract_excerpt=observation.get("contract_excerpt", ""),
                    instruction=observation.get("instruction", ""),
                )
                print(f"[DEBUG] Step {step}: Got LLM response", flush=True)
            except Exception as e:
                print(f"[ERROR] Step {step}: LLM call failed, cannot continue", flush=True)
                print(f"[ERROR] {type(e).__name__}: {str(e)}", flush=True)
                raise  # Fail loudly - don't fallback
            
            # ---- SUBMIT TO ENVIRONMENT ----
            try:
                step_result = await env_client.step(action_dict)
            except Exception as e:
                print(f"[ERROR] Step {step}: Environment step failed: {e}", flush=True)
                raise
            
            # ---- PROCESS RESULT ----
            reward = step_result.get("reward", 0.01) or 0.01
            done = step_result.get("done", False)
            
            rewards.append(reward)
            steps_taken = step
            
            # Log step
            action_str = action_dict.get("analysis", "")[:80]
            log_step(step=step, action=action_str, reward=reward, done=done, error=None)
            
            history.append(f"Step {step}: {action_str}")
            
            print(f"[DEBUG] Step {step} complete: reward={reward:.2f}, done={done}", flush=True)
            
            if done:
                print(f"[DEBUG] Episode ended (done=True)", flush=True)
                break
            
            observation = step_result.get("observation", observation)
        
        # ---- CALCULATE FINAL SCORE ----
        print(f"[DEBUG] Episode complete: {steps_taken} steps, {len(rewards)} rewards", flush=True)
        
        if rewards:
            score = sum(rewards) / len(rewards)
        
        score = max(0.01, min(0.99, score))
        success = score >= SUCCESS_SCORE_THRESHOLD
        
        print(f"[DEBUG] Final score: {score:.3f}, success={success}", flush=True)
        
    except Exception as e:
        print(f"[ERROR] Episode failed: {type(e).__name__}: {str(e)}", flush=True)
        import traceback
        traceback.print_exc()
        score = 0.01
        success = False
    
    finally:
        try:
            await env_client.close()
        except:
            pass
        
        log_end(success=success, steps=steps_taken, score=score, rewards=rewards)


# ============================================================================
# ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    asyncio.run(main())
