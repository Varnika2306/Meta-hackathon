**LexEnv — AI Legal Document Analysis**  | OpenEnv Hackathon Implementation Guide

**LexEnv**  ·  AI Legal Document Analysis Environment

*OpenEnv Hackathon — Round 1 Implementation Guide*    |    Team: 2nd Year CS Students  |  Scalar Institute of Technology

|<p><h2>**What We're Building**</h2></p><p>LexEnv is an RL environment where an AI agent learns to analyze legal documents — identifying risky clauses, flagging issues, and assessing risk — simulating the work of a junior legal associate.</p><p></p><p>The environment wraps 3 tasks of increasing difficulty around synthetic but realistic legal contracts (NDA, SLA, M&A), all served via the OpenEnv HTTP API on a Hugging Face Space.</p>|<p><h2>**Why This Domain**</h2></p><p>- Legal document review = genuinely high-stakes real-world task</p><p>- Natural easy → medium → hard progression</p><p>- Novel: no existing OpenEnv legal environment</p><p>- Rich reward signal: partial credit per issue found</p><p>- Maps cleanly to OpenEnv step/reset/state model</p>|
| :- | :- |


# **1  Project Structure**
Everything the validator checks is in place. The openenv validate command passes on the repo root.

|lexenv/                         ← Python package|
| :- |
|`  `\_\_init\_\_.py|
|`  `env.py                        ← LexEnv(Environment) — reset / step / state|
|`  `models.py                     ← LexAction, LexObservation, LexState (Pydantic)|
|`  `graders.py                    ← Scoring logic for all 3 tasks|
|`  `data/contracts.py             ← 3 synthetic contracts + ground-truth issues|
|server/|
|`  `app.py                        ← FastAPI app via create\_fastapi\_app()|
|inference.py                    ← Agent baseline (Groq API, OpenAI-compatible)|
|openenv.yaml                    ← spec\_version: 1, app: server.app:app|
|pyproject.toml                  ← [project.scripts] server = server.app:main|
|uv.lock                         ← required by openenv validate|
|Dockerfile                      ← HF Space container|
|README.md|


# **2  The Three Tasks**

|**#**|**Task**|**Description + Grading Strategy**|
| :-: | :- | :- |
|**1**|NDA Clause Identification  (Easy)|Agent reads a Non-Disclosure Agreement and flags risky clauses: overbroad non-compete (5yr worldwide), blanket IP assignment, perpetual term, Cayman Islands jurisdiction. Grader: keyword fuzzy match across flags + analysis text. 5 weighted issues, max reward 1.0.|
|**2**|SLA Contract Review  (Medium)|Agent reviews a Service Level Agreement with 8 planted defects: no numeric uptime SLA, $500 liability cap, undefined incident timelines, 12-month vs 30-day asymmetric termination, no breach notification window. Grader: weighted checklist with partial credit.|
|**3**|M&A Due Diligence  (Hard)|Agent analyzes a merger agreement excerpt with 10 multi-layered risks: undisclosed tax audits, $2.3M hidden liability, overbroad MAE carve-outs, no reverse termination fee, asymmetric 18-month exclusivity, 5% indemnification cap. Grader: rubric scoring + reasoning quality check.|


# **3  How the Environment Works**

|<p><h2>**Episode Flow**</h2></p><p>Each episode has up to 3–5 steps depending on task difficulty. The agent receives a contract excerpt and instruction each step, submits an analysis with flags and risk level, and gets partial reward proportional to issues correctly identified.</p><p></p>||
| :- | :- |

|obs = env.reset(task\_id='clause\_id')|
| :- |
|# obs.contract\_excerpt → NDA text|
|# obs.instruction → what to do|
||
|action = LexAction(|
|`  `analysis='The non-compete is 5yr...',|
|`  `flags=['overbroad\_non\_compete'],|
|`  `risk\_level='high'|
|)|
|obs = env.step(action)|
|# obs.reward → 0.30|
|# obs.feedback → 'Issues found: ...'|
|# obs.done → False (more steps)|

||<p><h2>**Reward Design**</h2></p><p>Reward is shaped over the full trajectory — not just binary end-of-episode — to give the agent a meaningful learning signal:</p><p></p><p>- Per step: reward = Σ(weight\_i) for each issue found</p><p>- Step weights decay: early steps rewarded more</p><p>- Efficiency bonus: +10% if ≥60% issues found in ≤2 steps</p><p>- Risk level match: +0.05 bonus</p><p>- Penalty: −0.05 for analysis < 50 characters</p><p>- Episode final score: holistic grade across all steps combined</p><p></p><p>*Issue weights: NDA has 5 issues (0.15–0.25 each), SLA has 8 (0.10–0.20), M&A has 10 (0.08–0.12). All sum to 1.0.*</p>|
| :- | :- |


# **4  Implementation Steps**

|**Step**|**What to Do**|**Command / File**|
| :-: | :- | :- |
|**4.1**|Clone / init repo structure|mkdir lexenv && cd lexenv|
|**4.2**|Install openenv-core|pip install openenv-core uvicorn fastapi|
|**4.3**|Write models.py|LexAction, LexObservation, LexState extending openenv base classes|
|**4.4**|Write data/contracts.py|3 synthetic contracts + issue dicts with keywords and weights|
|**4.5**|Write graders.py|grade\_step() and grade\_episode() with fuzzy keyword matching|
|**4.6**|Write env.py|LexEnv(Environment) — reset(), step(), state property|
|**4.7**|Write server/app.py|create\_fastapi\_app(make\_env, LexAction, LexObservation)|
|**4.8**|Write openenv.yaml|spec\_version: 1 | app: server.app:app | port: 8000|
|**4.9**|Write pyproject.toml + uv lock|uv lock (generates uv.lock required by validator)|
|**4.10**|Validate locally|openenv validate .|
|**4.11**|Write inference.py|Groq API via OpenAI client compat layer, exact [START]/[STEP]/[END] logs|
|**4.12**|Write Dockerfile|FROM python:3.11-slim, EXPOSE 8000, CMD uvicorn server.app:app|
|**4.13**|Docker build test|docker build -t lexenv . && docker run -p 8000:8000 lexenv|
|**4.14**|Push to HF Space|huggingface-cli repo create lexenv --type space --sdk docker|
|**4.15**|Run validate-submission.sh|./validate-submission.sh https://your-space.hf.space|


# **5  inference.py — Using Groq Instead of OpenAI**
Groq provides an OpenAI-compatible API, so we can use the openai Python client with just a base URL swap. This is faster, free-tier available, and doesn't require an OpenAI account.

|# .env / HF Space secrets|
| :- |
|API\_BASE\_URL = https://api.groq.com/openai/v1|
|MODEL\_NAME   = llama3-8b-8192          # or mixtral-8x7b-32768|
|HF\_TOKEN     = gsk\_xxxxxxxxxxxxxxxxxxxx # your Groq API key|

|# inference.py  (key parts)|
| :- |
|import os, asyncio, textwrap|
|from openai import OpenAI          # ← same client, different base\_url|
|from openenv.core import EnvClient|
|from lexenv.models import LexAction|
||
|API\_BASE\_URL  = os.getenv('API\_BASE\_URL', 'https://api.groq.com/openai/v1')|
|MODEL\_NAME    = os.getenv('MODEL\_NAME',   'llama3-8b-8192')|
|API\_KEY       = os.getenv('HF\_TOKEN')     # Groq key stored as HF\_TOKEN|
|TASK\_NAME     = os.getenv('LEXENV\_TASK',  'clause\_id')|
|MAX\_STEPS     = 5|
||
|def log\_start(task, env, model):|
|`    `print(f'[START] task={task} env={env} model={model}', flush=True)|
||
|def log\_step(step, action, reward, done, error):|
|`    `err = error if error else 'null'|
|`    `print(f'[STEP] step={step} action={action[:80]!r} reward={reward:.2f}'|
|`          `f' done={str(done).lower()} error={err}', flush=True)|
||
|def log\_end(success, steps, score, rewards):|
|`    `rr = ','.join(f'{r:.2f}' for r in rewards)|
|`    `print(f'[END] success={str(success).lower()} steps={steps}'|
|`          `f' score={score:.3f} rewards={rr}', flush=True)|
||
|async def main():|
|`    `client = OpenAI(base\_url=API\_BASE\_URL, api\_key=API\_KEY)|
|`    `env = await LexEnvClient.from\_url('http://localhost:8000')|
|`    `rewards, done = [], False|
|`    `log\_start(TASK\_NAME, 'lexenv', MODEL\_NAME)|
|`    `try:|
|`        `obs = await env.reset(task\_id=TASK\_NAME)|
|`        `for step in range(1, MAX\_STEPS + 1):|
|`            `if done: break|
|`            `# Ask Groq model to analyze the contract|
|`            `resp = client.chat.completions.create(|
|`                `model=MODEL\_NAME,|
|`                `messages=[system\_msg, user\_msg(obs)],|
|`                `temperature=0.2, max\_tokens=600|
|`            `)|
|`            `# Parse response → LexAction|
|`            `action = parse\_action(resp.choices[0].message.content)|
|`            `obs = await env.step(action)|
|`            `rewards.append(obs.reward)|
|`            `done = obs.done|
|`            `log\_step(step, action.analysis, obs.reward, done, None)|
|`    `finally:|
|`        `score = sum(rewards) / MAX\_STEPS|
|`        `log\_end(score >= 0.5, len(rewards), score, rewards)|
|`        `await env.close()|


# **6  Dockerfile + HF Space Deployment**

|<h2>**Dockerfile**</h2>||
| :- | :- |

|FROM python:3.11-slim|
| :- |
|WORKDIR /app|
|COPY requirements.txt .|
|RUN pip install --no-cache-dir -r requirements.txt|
|COPY . .|
|EXPOSE 8000|
|ENV LEXENV\_TASK=clause\_id|
|CMD ["uvicorn", "server.app:app",|
|`     `"--host", "0.0.0.0",|
|`     `"--port", "8000"]|

|<p></p><p><h2>**requirements.txt**</h2></p>||
| :- | :- |

|openenv-core>=0.2.0|
| :- |
|fastapi>=0.100.0|
|uvicorn>=0.20.0|
|pydantic>=2.0.0|
|openai>=1.0.0|

||<p><h2>**HF Space Setup**</h2></p><p>- Create a new Space: type = Docker</p><p>- Tag the Space with openenv for discoverability</p><p>- Add secrets in Space Settings:</p>|
| :- | :- |

|HF\_TOKEN   = gsk\_...   # Groq key|
| :- |
|API\_BASE\_URL = https://api.groq.com/openai/v1|
|MODEL\_NAME   = llama3-8b-8192|

||<p>- Push repo: git push to HF Space remote</p><p>- Space auto-builds Docker image on push</p><p></p><p><h2>**Validate Submission**</h2></p>|
| :- | :- |

|# After Space is live:|
| :- |
|./validate-submission.sh \|
|`  `https://your-team.hf.space \|
|  ./lexenv|
||
|# Checks: /reset returns 200|
|# docker build succeeds|
|# openenv validate passes|

|||
| :- | :- |


# **7  Scoring Checklist & Expected Scores**

|**Criterion**|**Weight**|**Why LexEnv Scores Well**|
| :- | :-: | :- |
|**Real-world utility**|**30%**|Legal document review is genuinely high-stakes. Law firms use AI tools exactly like this. Fills a real gap in the RL/agent community.|
|**Task & grader quality**|**25%**|3 tasks with clear difficulty progression. All graders produce deterministic 0.0–1.0 scores. Hard task (M&A) has 10 layered issues that challenge frontier models.|
|**Environment design**|**20%**|Clean state machine. reset() always produces fresh state. Reward shaped across trajectory (not sparse). Episode boundaries are sensible.|
|**Code quality & spec**|**15%**|openenv validate passes. Dockerfile works. Typed Pydantic models throughout. README with baseline scores.|
|**Creativity & novelty**|**10%**|Legal domain is novel for OpenEnv. Multi-issue weighted grading with fuzzy matching is an interesting reward design.|


**Baseline Expected Scores (llama3-8b via Groq)  →**  Task 1: ~0.65   Task 2: ~0.50   Task 3: ~0.35

*A stronger model (Mixtral 8x7B or Llama3 70B) should reach 0.80+ on Task 1 and 0.60+ on Task 2, demonstrating meaningful difficulty progression.*
Scalar Institute × MetaxScaler Hackathon 2025  	Page 
