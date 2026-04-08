---
title: LexEnv
emoji: ⚖️
colorFrom: indigo
colorTo: blue
sdk: docker
pinned: false
---

# LexEnv — AI Legal Document Analysis Environment

An [OpenEnv](https://github.com/meta-pytorch/OpenEnv) reinforcement learning environment where an AI agent learns to analyze legal documents — identifying risky clauses, flagging issues, and assessing risk — simulating the work of a junior legal associate.

## 🎯 Overview

LexEnv wraps 3 tasks of increasing difficulty around synthetic but realistic legal contracts, all served via the OpenEnv HTTP API.

| # | Task | Difficulty | Issues | Steps | Baseline Score |
|:-:|------|:----------:|:------:|:-----:|:--------------:|
| 1 | NDA Clause Identification | Easy | 5 | 3 | ~0.65 |
| 2 | SLA Contract Review | Medium | 8 | 4 | ~0.50 |
| 3 | M&A Due Diligence | Hard | 10 | 5 | ~0.35 |

*Baseline scores measured with `llama3-8b-8192` via Groq.*

## 🚀 Quick Start

### Install
```bash
pip install -e .
```

### Run the Server
```bash
uvicorn server.app:app --host 0.0.0.0 --port 8000
```

### Use the Environment
```python
from lexenv.env import LexEnv
from lexenv.models import LexAction

env = LexEnv()
obs = env.reset(task_id='clause_id')
print(obs.contract_excerpt[:200])

action = LexAction(
    analysis='The non-compete clause is overbroad with 5-year worldwide scope...',
    flags=['overbroad_non_compete', 'perpetual_term'],
    risk_level='high',
)
obs = env.step(action)
print(f"Reward: {obs.reward:.2f}, Feedback: {obs.feedback}")
```

### Run the Inference Agent
```bash
# Set your Groq API key
export HF_TOKEN=gsk_your_groq_api_key_here

# Run the agent
python inference.py
```

## 🏗️ Project Structure
```
lexenv/
├── lexenv/                  # Core package
│   ├── models.py            # LexAction, LexObservation, LexState
│   ├── graders.py           # Scoring logic (fuzzy match + reward shaping)
│   ├── env.py               # LexEnv — reset/step/state
│   └── data/contracts.py    # 3 synthetic contracts + ground-truth
├── server/app.py            # FastAPI server
├── inference.py             # Groq-powered baseline agent
├── openenv.yaml             # OpenEnv manifest
├── pyproject.toml           # Package config
├── Dockerfile               # HF Space container
└── README.md
```

## 📊 Reward Design

- **Per step**: reward = Σ(weight_i) for each newly-found issue
- **Step decay**: earlier steps rewarded more (−5% per step)
- **Efficiency bonus**: +10% if ≥60% issues found in ≤2 steps
- **Risk level match**: +0.05 bonus for correct assessment
- **Penalty**: −0.05 for analysis < 50 characters
- **Final score**: holistic combination, capped at 1.0

## 🐳 Docker Deployment

```bash
docker build -t lexenv .
docker run -p 8000:8000 lexenv
```

## ☁️ Hugging Face Space

```bash
huggingface-cli repo create lexenv --type space --sdk docker
git push
```

## 📝 License

BSD 3-Clause License
