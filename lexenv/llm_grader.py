import os
import json
import logging
from typing import Dict, Any, Optional
from openai import AsyncOpenAI

logger = logging.getLogger("lexenv.llm_grader")

class ToneGrader:
    """LLM-as-a-judge specifically for evaluating legal writing quality."""
    
    def __init__(self, model_name: Optional[str] = None):
        self.api_key = os.getenv("API_KEY") or os.getenv("OPENAI_API_KEY") or os.getenv("HF_TOKEN")
        self.base_url = os.getenv("API_BASE_URL")
        self.model_name = model_name or os.getenv("MODEL_NAME", "meta-llama/Meta-Llama-3-8B-Instruct")
        
        if self.api_key:
            self.client = AsyncOpenAI(
                api_key=self.api_key,
                base_url=self.base_url if self.base_url else None
            )
        else:
            self.client = None
            logger.warning("ToneGrader: No API key found. LLM grading will be skipped.")

    async def evaluate_tone(self, analysis: str, task_name: str) -> Dict[str, Any]:
        """
        Evaluates the analysis text for legalese fluency and professionalism.
        Returns a dict with 'tone_score' (0.0 - 1.0) and 'feedback'.
        """
        if not self.client or not analysis or len(analysis.strip()) < 10:
            return {"tone_score": 0.0, "feedback": "Analysis too short for tone evaluation."}

        prompt = f"""You are a senior legal counsel at a top-tier law firm. 
Evaluate the following analysis of a {task_name} contract for:
1. Legalese Fluency: Use of professional legal terminology.
2. Structure: Logical organization and clarity.
3. Professionalism: Formal tone vs. casual language.

ANALYSIS TO EVALUATE:
---
{analysis}
---

Provide a score between 0.0 and 1.0 and a brief feedback.
Return ONLY a JSON object:
{{
  "tone_score": 0.85,
  "feedback": "Professional and concise, uses correct terminology like 'indemnification'."
}}
"""

        try:
            response = await self.client.chat.completions.create(
                model=self.model_name,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=300,
                response_format={"type": "json_object"} if "gpt-4" in self.model_name or "llama" in self.model_name else None
            )
            
            content = response.choices[0].message.content
            # Basic JSON extraction in case response_format isn't supported
            if not content.strip().startswith("{"):
                import re
                match = re.search(r'\{.*\}', content, re.DOTALL)
                if match:
                    content = match.group(0)
            
            data = json.loads(content)
            return {
                "tone_score": float(data.get("tone_score", 0.0)),
                "feedback": data.get("feedback", "Professional review complete.")
            }
        except Exception as e:
            logger.error(f"ToneGrader Error: {str(e)}")
            return {"tone_score": 0.0, "feedback": "Grading service unavailable."}
