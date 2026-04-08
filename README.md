<<<<<<< HEAD
# LexEnv — AI Legal Document Analysis Environment

An [OpenEnv](https://openenv.dev)-compliant reinforcement learning environment where an AI agent learns to analyze legal contracts — identifying risky clauses, flagging issues, and assessing risk — simulating the work of a junior legal associate.

## Motivation

Legal document review is a genuinely high-stakes, real-world task. Law firms and legal-tech companies use AI tools exactly like this. LexEnv fills a gap in the OpenEnv ecosystem by providing:

- A natural easy → medium → hard difficulty progression
- Rich, shaped reward signal with partial credit per issue found
- Deterministic grading based on fuzzy keyword matching and weighted scoring
- Three realistic synthetic contracts (NDA, SLA, M&A)

---

## Environment Overview

```
POST /reset?task_id=clause_id   → initial observation
POST /step                      → (observation, reward, done, info)
GET  /state                     → current episode state
GET  /tasks                     → list all available tasks
GET  /health                    → liveness check
```

---

## Action Space

```json
{
  "analysis": "Detailed analysis text (≥50 characters)",
  "flags": [
    {
      "title": "Issue title",
      "severity": "low | medium | high | critical",
      "clause_reference": "Section X",
      "remediation": "Suggested fix"
    }
  ],
  "risk_assessment": "low | medium | high | critical"
}
```

## Observation Space

```json
{
  "task_id": "clause_id | sla_review | ma_assessment",
  "task_name": "Human-readable name",
  "difficulty": 1,
  "contract_excerpt": "Contract text for this step",
  "instruction": "What to analyze",
  "step": 1,
  "max_steps": 3,
  "previous_analysis": "Feedback from prior step (null on step 0)",
  "progress": {
    "step": 1,
    "max_steps": 3,
    "expected_issues": 5,
    "rewards_so_far": 0.0
  }
}
```

---

## Tasks

### Task 1 — NDA Clause Identification (Easy)
- **Task ID:** `clause_id`
- **Max steps:** 3
- **Issues:** 5 (weighted 0.15–0.25 each)
- **Description:** Agent reads a Mutual Non-Disclosure Agreement and must identify: overbroad 5-year worldwide non-compete, blanket perpetual IP assignment, perpetual obligations, unfavorable Cayman Islands jurisdiction, and unbalanced remedies clause.

### Task 2 — SLA Contract Review (Medium)
- **Task ID:** `sla_review`
- **Max steps:** 4
- **Issues:** 8 (weighted 0.10–0.15 each)
- **Description:** Agent reviews a Service Level Agreement with 8 planted defects: no numeric uptime SLA, $500 liability cap, undefined incident timelines, asymmetric termination (12-month vs 30-day), unilateral maintenance rights, no audit commitments, vague breach notification, and data deletion compliance issue.

### Task 3 — M&A Due Diligence (Hard)
- **Task ID:** `ma_assessment`
- **Max steps:** 5
- **Issues:** 10 (weighted 0.09–0.12 each)
- **Description:** Agent analyzes a merger agreement excerpt with 10 multi-layered risks: undisclosed $2.3M IRS tax assessment, hidden employee class action ($3.2M), three undisclosed patent infringement claims ($5M each), overbroad MAE carve-outs, 5% indemnification cap (covers fraud), asymmetric 18-month non-compete/exclusivity, no reverse termination fee, short escrow release, undisclosed DOJ antitrust inquiry, and uncapped pre-close tax indemnity.

---

## Reward Function

Reward is shaped over the full trajectory — not just binary end-of-episode:

| Component | Value |
|---|---|
| Per step | Σ(issue_weight × match_confidence) for each issue found |
| Step decay | Earlier steps yield higher multiplier |
| Efficiency bonus | +5% for early-step discovery |
| Risk level match | +0.05 if risk assessment is consistent with issues found |
| Analysis quality | +0.05 max for detailed analysis (>1000 chars) |
| Short analysis penalty | −0.05 for analysis <50 characters |
| Episode final score | Holistic 0.0–1.0 grade: 60% completeness + 25% accuracy + 15% efficiency |

All issue weights sum to 1.0 per task.

---

## Baseline Scores

Tested with `llama3-8b-8192` via Groq API:

| Task | Expected Score |
|---|---|
| NDA Clause Identification (Easy) | ~0.65 |
| SLA Contract Review (Medium) | ~0.50 |
| M&A Due Diligence (Hard) | ~0.35 |

A stronger model (Mixtral 8x7B or Llama3 70B) should reach **0.80+** on Task 1 and **0.60+** on Task 2.

---

## Setup & Usage

### Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Start server
uvicorn server.app:app --host 0.0.0.0 --port 8000

# Run baseline inference (in a separate terminal)
export OPENAI_API_KEY=gsk_...   # Groq key, or set HF_TOKEN
export API_BASE_URL=https://api.groq.com/openai/v1
export MODEL_NAME=llama3-8b-8192
export LEXENV_TASK=clause_id    # or sla_review, ma_assessment
python inference.py
```

### Docker

```bash
docker build -t lexenv .
docker run -p 8000:8000 \
  -e OPENAI_API_KEY=gsk_... \
  -e API_BASE_URL=https://api.groq.com/openai/v1 \
  lexenv
```

### OpenEnv Validate

```bash
pip install openenv-core
openenv validate .
```

---

## API Examples

**Reset:**
```bash
curl -X POST "http://localhost:8000/reset?task_id=clause_id"
```

**Step:**
```bash
curl -X POST http://localhost:8000/step \
  -H "Content-Type: application/json" \
  -d '{
    "analysis": "The non-compete clause in Section 2 is overbroad — 5 years worldwide exceeds any reasonable scope. Section 3 assigns all IP in perpetuity which is highly dangerous.",
    "flags": [
      {"title": "Overbroad non-compete", "severity": "critical", "clause_reference": "Section 2", "remediation": "Limit to 1-2 years, specific geography"}
    ],
    "risk_assessment": "high"
  }'
```

**State:**
```bash
curl http://localhost:8000/state
```

---

## Project Structure

```
lexenv/
  __init__.py
  env.py              ← LexEnv — reset() / step() / state()
  models.py           ← LexAction, LexObservation, LexState (Pydantic)
  graders.py          ← Scoring logic for all 3 tasks
  data/contracts.py   ← 3 synthetic contracts + ground-truth issues
server/
  app.py              ← FastAPI app, OpenEnv HTTP routes
inference.py          ← Agent baseline (Groq API, OpenAI-compatible)
openenv.yaml          ← spec_version: 1, app: server.app:app
pyproject.toml
requirements.txt
Dockerfile
```

---

## HF Space Deployment

```bash
# Create Space
huggingface-cli repo create lexenv --type space --sdk docker

# Add secrets in Space Settings:
#   OPENAI_API_KEY = gsk_...  (Groq key)
#   API_BASE_URL   = https://api.groq.com/openai/v1
#   MODEL_NAME     = llama3-8b-8192

# Push
git remote add space https://huggingface.co/spaces/<your-username>/lexenv
git push space main
```

The Space is tagged `openenv` for discoverability.
=======
---
title: Lexenv
emoji: 🌖
colorFrom: purple
colorTo: gray
sdk: docker
pinned: false
---

Check out the configuration reference at https://huggingface.co/docs/hub/spaces-config-reference
>>>>>>> 32a30d5df7fd7d00dae5fb608258e8edec60a4b3
