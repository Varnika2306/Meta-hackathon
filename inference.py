"""
LexEnv Inference Script
- Uses OpenAI API to analyze contracts
- Exact [START]/[STEP]/[END] logging format for evaluation
- Async HTTP calls to environment
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
# CONFIGURATION
# ============================================================================

API_BASE_URL = os.getenv("API_BASE_URL", "https://api.openai.com/v1")
MODEL_NAME = os.getenv("MODEL_NAME", "gpt-4o-mini")

# Fallback Configuration
GROQ_API_KEY = os.getenv("GROQ_API_KEY") or os.getenv("HF_TOKEN")
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")

# Accept OPENAI_API_KEY (spec requirement)
API_KEY = os.getenv("OPENAI_API_KEY")
ENV_URL = os.getenv("ENV_URL", "http://localhost:7860")
TASK_NAME = os.getenv("LEXENV_TASK", "clause_id")

MAX_STEPS = 5
MAX_TOTAL_REWARD = 5.0  # Max possible cumulative reward
SUCCESS_SCORE_THRESHOLD = 0.5

TEMPERATURE = 0.2
MAX_TOKENS = 800

# System prompt for legal analysis
SYSTEM_PROMPT = textwrap.dedent("""
    You are an expert legal analyst with 15 years of experience reviewing contracts.
    
    Your task is to analyze legal documents and identify risks, unfavorable terms, and problematic clauses.
    
    For each analysis:
    1. Read the contract excerpt carefully
    2. Identify specific issues with clause references
    3. Explain the risk and suggest remediation
    4. Provide an overall risk assessment (low/medium/high/critical)
    
    Be thorough, specific, and reference exact sections. Show your reasoning.
""").strip()


# ============================================================================
# LOGGING (Exact format for evaluation)
# ============================================================================

def log_start(task: str, env: str, model: str) -> None:
    """Log episode start with exact [START] format"""
    print(f"[START] task={task} env={env} model={model}", flush=True)


def log_step(step: int, action: str, reward: float, done: bool, error: Optional[str]) -> None:
    """Log step with exact [STEP] format"""
    action_truncated = action[:80].replace('\n', ' ')
    error_str = error if error else "null"
    print(
        f"[STEP] step={step} action={action_truncated!r} reward={reward:.2f} "
        f"done={str(done).lower()} error={error_str}",
        flush=True
    )


def log_end(success: bool, steps: int, score: float, rewards: List[float]) -> None:
    """Log episode end with exact [END] format"""
    rewards_str = ",".join(f"{r:.2f}" for r in rewards)
    print(
        f"[END] success={str(success).lower()} steps={steps} score={score:.3f} "
        f"rewards={rewards_str}",
        flush=True
    )


# ============================================================================
# API CLIENTS
# ============================================================================

class EnvClient:
    """Async client for LexEnv HTTP API"""
    
    def __init__(self, base_url: str):
        self.base_url = base_url
        self.client = httpx.AsyncClient(timeout=30.0)
    
    async def reset(self, task_id: str) -> Dict[str, Any]:
        """Reset environment"""
        url = f"{self.base_url}/reset?task_id={task_id}"
        response = await self.client.post(url)
        response.raise_for_status()
        return response.json()
    
    async def step(self, action: Dict[str, Any]) -> Dict[str, Any]:
        """Submit action and get result"""
        url = f"{self.base_url}/step"
        response = await self.client.post(url, json=action)
        response.raise_for_status()
        return response.json()
    
    async def get_state(self) -> Dict[str, Any]:
        """Get current state"""
        url = f"{self.base_url}/state"
        response = await self.client.get(url)
        response.raise_for_status()
        return response.json()
    
    async def close(self):
        """Close client"""
        await self.client.aclose()


# ============================================================================
# AGENT LOGIC
# ============================================================================

def build_user_prompt(
    step: int,
    contract_excerpt: str,
    instruction: str,
    previous_analysis: Optional[str] = None,
    history: Optional[List[str]] = None
) -> str:
    """Build user prompt for model"""
    history_block = ""
    if history:
        history_block = "\n\nPrevious analyses:\n" + "\n".join(history[-2:])
    
    previous_block = ""
    if previous_analysis:
        previous_block = f"\n\nFeedback on your previous analysis: {previous_analysis}"
    
    return textwrap.dedent(f"""
        STEP {step}
        
        INSTRUCTION: {instruction}
        
        CONTRACT EXCERPT:
        {contract_excerpt[:2000]}
        
        {previous_block}
        {history_block}
        
        Provide your analysis in the following JSON format:
        {{
            "analysis": "detailed analysis text",
            "flags": [
                {{"title": "issue title", "severity": "high", "clause_reference": "Section X", "remediation": "fix"}}
            ],
            "risk_assessment": "high"
        }}
    """).strip()


async def get_model_response(
    primary_client: AsyncOpenAI,
    fallback_client: Optional[AsyncOpenAI],
    step: int,
    observation: Dict[str, Any],
    history: List[str]
) -> Optional[Dict[str, Any]]:
    """Get response from OpenAI model, fallback to Groq"""
    try:
        user_prompt = build_user_prompt(
            step=step,
            contract_excerpt=observation["observation"]["contract_excerpt"],
            instruction=observation["observation"]["instruction"],
            previous_analysis=observation["observation"]["previous_analysis"],
            history=history
        )
        
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt}
        ]
        
        try:
            response = await primary_client.chat.completions.create(
                model=MODEL_NAME,
                messages=messages,
                temperature=TEMPERATURE,
                max_tokens=MAX_TOKENS
            )
            text = (response.choices[0].message.content or "").strip()
        except APIError as e:
            print(f"[DEBUG] OpenAI API error: {e}", flush=True)
            if fallback_client:
                print(f"[DEBUG] Falling back to Groq ({GROQ_MODEL})...", flush=True)
                response = await fallback_client.chat.completions.create(
                    model=GROQ_MODEL,
                    messages=messages,
                    temperature=TEMPERATURE,
                    max_tokens=MAX_TOKENS
                )
                text = (response.choices[0].message.content or "").strip()
            else:
                print("[DEBUG] No fallback configured, failing...", flush=True)
                return None
        
        # Try to parse JSON response
        try:
            # Find JSON in response
            start = text.find("{")
            end = text.rfind("}") + 1
            if start >= 0 and end > start:
                json_str = text[start:end]
                action = json.loads(json_str)
                return action
        except json.JSONDecodeError:
            pass
        
        # Fallback: construct minimal action
        return {
            "analysis": text[:500] if text else "Unable to analyze",
            "flags": [],
            "risk_assessment": "medium"
        }
        
    except APIError as e:
        print(f"[DEBUG] Groq Fallback API error: {e}", flush=True)
        return None
    except Exception as e:
        print(f"[DEBUG] Error getting model response: {e}", flush=True)
        return None


# ============================================================================
# MAIN AGENT LOOP
# ============================================================================

async def main() -> None:
    """Run agent against environment"""
    
    if not API_KEY:
        print("[ERROR] API key not set. Provide OPENAI_API_KEY or HF_TOKEN.", flush=True)
        sys.exit(1)
    
    # Initialize clients
    openai_client = AsyncOpenAI(base_url=API_BASE_URL, api_key=API_KEY)
    groq_client = AsyncOpenAI(base_url="https://api.groq.com/openai/v1", api_key=GROQ_API_KEY) if GROQ_API_KEY else None
    env_client = EnvClient(ENV_URL)
    
    history: List[str] = []
    rewards: List[float] = []
    steps_taken = 0
    score = 0.0
    success = False
    error_msg: Optional[str] = None
    
    log_start(task=TASK_NAME, env="lexenv", model=MODEL_NAME)
    
    try:
        # Reset environment
        print(f"[DEBUG] Resetting environment with task={TASK_NAME}", flush=True)
        reset_result = await env_client.reset(TASK_NAME)
        observation = reset_result
        
        # Main episode loop
        for step in range(1, MAX_STEPS + 1):
            obs_data = observation.get("observation", {})
            
            if obs_data.get("max_steps", MAX_STEPS) > 0 and step > obs_data.get("max_steps"):
                break
            
            # Get model response
            action_dict = await get_model_response(
                primary_client=openai_client,
                fallback_client=groq_client,
                step=step,
                observation=observation,
                history=history
            )
            
            if not action_dict:
                action_dict = {
                    "analysis": "Unable to generate analysis",
                    "flags": [],
                    "risk_assessment": "medium"
                }
            
            # Submit action to environment
            step_result = await env_client.step(action_dict)
            
            # Extract results
            reward = step_result.get("reward", 0.0) or 0.0
            done = step_result.get("done", False)
            
            rewards.append(reward)
            steps_taken = step
            
            # Log step
            action_str = action_dict.get("analysis", "")[:80]
            log_step(
                step=step,
                action=action_str,
                reward=reward,
                done=done,
                error=None
            )
            
            # Add to history
            history.append(f"Step {step}: {action_str}")
            
            if done:
                break
            
            observation = step_result
        
        # Calculate final score
        if rewards:
            score = sum(rewards) / len(rewards)
        
        score = min(max(score, 0.0), 1.0)  # Clamp to [0, 1]
        success = score >= SUCCESS_SCORE_THRESHOLD
        
    except Exception as e:
        print(f"[DEBUG] Episode error: {e}", flush=True)
        error_msg = str(e)
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
