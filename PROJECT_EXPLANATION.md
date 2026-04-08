# LexEnv: Legal Document Analysis Project Overview

LexEnv is a simulated AI testing environment built on top of the **OpenEnv framework**. It is designed to act as a benchmark and training ground for AI Agents to read legal documents and extract problematic, risky, or unusual clauses—simulating the work of a junior legal associate.

The project operates as an **API-driven loop**: an AI agent requests an environment state (with a contract to review) and interacts with the environment sequentially by making observations, flagging items, and receiving partial reward grades. 

Below is a breakdown of how the key components of the project work together.

## 1. Project Architecture

The codebase cleanly splits into the "Environment Engine" (backend simulation) and the "Agent Inference" (the AI model testing the environment).

- **`lexenv/` (The Environment Module):** 
  - `models.py`: Defines the strictly-typed inputs and outputs using Pydantic. It defines what an Action (what the AI returns), Observation (what the AI sees), and State (internal tracker) look like.
  - `env.py`: The `LexEnv` class. This is the core engine inheriting from `openenv.core.env_server.interfaces.Environment`. It handles initialization (`reset`) and the transition dynamics between turns (`step`).
  - `graders.py`: The automatic grading logic that calculates how well the AI analyzed the contract.
  - `data/contracts.py`: Contains the actual Ground Truth legal documents (NDA, SLA, M&A Diligence), instructions, and the true hidden "issues" each one holds.

- **`server/` (Backend Server):**
  - `app.py`: Wraps the `LexEnv` module into a fully-fledged FastAPI application using OpenEnv's `create_app` factory. It provides HTTP endpoints (like `/reset` and `/step`) that agents can connect to in a stateless manner.

- **`inference.py` (The AI Agent):**
  - The script that acts as the "Player" in the environment. It queries the FastAPI server for the current contract, wraps the text in an aggressive system prompt, sends it to an LLM provider (like Groq), and pushes the LLM's structured JSON analysis back into the environment as a `LexAction` to receive a grade.

---

## 2. OpenEnv Integration & The Loop

Like reinforcement learning environments (e.g., OpenAI Gym), LexEnv operates in episodes. An episode represents a full analysis task of a single document.

1. **Reset Phase:** 
   The agent calls `/reset`. The environment randomly generates an `episode_id`, selects the legal document, resets step counters, and returns a `LexObservation` containing the `contract_excerpt` and the `instruction`.
2. **Analysis Phase (The LLM Call):**
   The agent processes the observation. It prompts the LLM (e.g., `llama-3.3-70b-versatile`) with the contract and instructs it to output a JSON containing its `analysis`, identified `flags`, and a `risk_level`. 
3. **Step Phase:**
   The agent calls `/step` and provides its JSON extraction as a `LexAction`. 
   The environment processes this action, grades it using the `graders.py` engine, updates its internal state (increasing the step count and cumulating rewards), and returns a new `LexObservation`. This observation tells the agent its reward, what feedback it got, and if the episode is `done` (all issues found or max steps reached).

---

## 3. Automatic Grading Mechanics

LexEnv doesn't require a human to grade the agent. It leverages a rigorous programmatic grader in `lexenv/graders.py`.

### Fuzzy Issue Matching
Each contract (e.g., the M&A contract) has predefined hidden issues equipped with fuzzy-match `keywords` (e.g., "overbroad_non_compete").
When the agent submits its flags or analysis text, the grader does a case-insensitive string check to see if the agent successfully referenced any of the keywords associated with a ground-truth issue. 

### Weighted Partial Credit & Step Decay
Instead of a simple "pass/fail", the environment rewards agents granularly:
* **Weighted Issues:** Not all issues are equal. Deeper, more complex issues might grant a higher `weight` than obvious syntax errors.
* **Step Decay:** Agents are encouraged to find issues as quickly as possible. Every step the agent takes slowly decreases the reward multiplier (`decay_factor = max(0.5, 1.0 - step_index * 0.05)`). If an agent needs 5 turns with the AI to find the problem, it earns fewer points than finding it immediately.
* **Risk Bonus & Short Penalty:** A flat bonus is awarded if the agent's chosen `risk_level` matches the ground-truth level. A flat penalty is subtracted if the agent's textual analysis is under 50 characters (preventing "guessing" just the flags).

---

## 4. Why This Configuration Works
By encapsulating the legal contract simulation inside a standalone HTTP server and interacting with it purely via typed Pydantic models, **LexEnv creates a completely reproducible, stateless AI benchmark.** You can hot-swap `inference.py` to use *any* AI provider (Groq, Gemini, OpenAI) and independently verify which model performs better at deep legal reasoning without ever leaking the "ground truth" answers directly to the agent.
