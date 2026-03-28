# Live Website: https://daytonasprintthon.vercel.app

# Parallel Game Theory Simulator

AI agents with distinct rationality profiles run in isolated Daytona sandboxes to play out game‑theory scenarios in parallel, and a neutral analyst model answers strategic questions grounded in the simulation data.[conversation_history:1]

---

## High‑Level Architecture

There are three main layers:

1. **Orchestrator** – builds the game (scenario + actors) and later acts as analyst.
2. **Simulation** – runs many full simulations in parallel (one per Daytona sandbox).
3. **Analysis** – aggregates all run results and answers questions over the data.[conversation_history:1]

---

## Repository Structure

```text
.
├─ orchestration/      # Scenario + actors + dossiers + rationality profiles
├─ simulation/         # In‑sandbox game loop + decision logs + per‑run results
├─ analysis/           # Aggregations + analyst model
├─ daytona_infra/      # Spinning up sandboxes + polling outputs
├─ frontend/           # UI + demo flow
└─ docs/               # Diagrams, notes, etc.
```

---

## Orchestration Layer (`/orchestration`)

The orchestrator is an LLM that sets up the world and later explains it.

**What it does**

- Takes a natural‑language scenario (e.g. “three biotech startups negotiating a licensing deal”).  
- Generates a set of actors and their dossiers (background, known decisions, demographics).  
- Derives a rationality profile per actor (fully rational, semi‑rational, irrational).  
- Emits all artifacts the simulation layer needs (no LLMs inside simulation).  
- After runs complete, re‑uses the same model as the analyst over aggregated results.[conversation_history:1]

**Input**

- Scenario text (CLI, API, or UI).
- Optional config (rounds, number of simulations, randomness settings).

**Output**

- **Scenario config** – `orchestration/output/scenario.json`  
  Minimal shape:

  ```json
  {
    "scenario_id": "biotech_licensing_v1",
    "description": "Three biotech startups negotiating a licensing deal.",
    "actors": ["startup_A", "startup_B", "incumbent_C"],
    "rounds": 6,
    "environment_params": {}
  }
  ```

- **Actor dossiers** – one per actor, e.g. `orchestration/output/dossiers/{actor_id}.json`:

  ```json
  {
    "actor": "MegaCorp Inc",
    "type": "Fortune 500 corporation",
    "known_decisions": [
      "Acquired three competitors rather than building internally",
      "Pulled out of Chinese market citing regulatory risk",
      "Chose stock buybacks over R&D investment Q3 2024"
    ],
    "rationality_derived": "semi-rational — loss averse, reputation conscious"
  }
  ```

These files are the **contract** the simulation layer consumes.[conversation_history:1]

---

## Simulation Layer (`/simulation`)

Each Daytona sandbox runs one full simulation: all actors, all rounds, one shared decision log.[conversation_history:1]

**What it does**

- For each run:
  - Boot a sandbox with `scenario.json`, all dossiers, and the game loop.  
  - Inside the sandbox:
    - Initialize a shared JSON `decision_log.json`.  
    - For each round, each actor:
      - reads the full log (knows what others did),  
      - applies its rationality profile to choose an action,  
      - appends its move + reasoning to the log.  
    - Optionally triggers web searches when the dossier is insufficient and logs that explicitly.[conversation_history:1]

**Input**

- `orchestration/output/scenario.json`.  
- `orchestration/output/dossiers/*.json`.  
- Optional per‑run config (seed, initial conditions).

**Internal file**

- **Decision log** – `decision_log.json` (in the sandbox):

  ```json
  {
    "round": 2,
    "actor": "B",
    "rationality": "semi-rational",
    "reasoning": "Loss threshold exceeded, switching conservative",
    "action": "withdraw_bid",
    "payoff_delta": -12
  }
  ```

**Output**

- **Per‑run result** – `simulation/runs/{run_id}/result.json`:

  ```json
  {
    "run_id": "run_0007",
    "scenario_id": "biotech_licensing_v1",
    "rounds_played": 6,
    "actors": ["startup_A", "startup_B", "incumbent_C"],
    "outcomes": {
      "startup_A": {"payoff": 42, "status": "licensor"},
      "startup_B": {"payoff": -15, "status": "acqui-hired"},
      "incumbent_C": {"payoff": 60, "status": "dominant_licensor"}
    },
    "decision_log_path": "decision_log.json",
    "statistics": {
      "irrational_disruptions": 2,
      "web_search_triggers": 1
    }
  }
  ```

This JSON is the **only thing the analysis layer depends on**.

---

## Analysis Layer (`/analysis`)

The analysis layer aggregates many runs and lets us ask strategic questions.[conversation_history:1]

**What it does**

- Loads all `simulation/runs/*/result.json`.  
- Optionally inspects the referenced `decision_log.json` files for richer patterns.  
- Computes:
  - win/lose rates, payoff distributions, roles;  
  - how often irrational actors break equilibria;  
  - how web‑search events change outcomes.  
- Calls the analyst LLM with scenario + aggregated stats + user question to produce natural‑language answers grounded in the data.[conversation_history:1]

**Input**

- `simulation/runs/{run_id}/result.json` (+ optional decision logs).

**Output**

- **Aggregated results** – `analysis/output/aggregated_results.json`:

  ```json
  {
    "scenario_id": "biotech_licensing_v1",
    "num_runs": 50,
    "actor_outcome_distribution": {
      "Actor_A": {"win_rate": 0.81, "avg_payoff": 37.2},
      "Actor_B": {"lose_rate": 0.81, "web_search_round_5_reset_prob": 0.34}
    },
    "irrational_disruption_rate": 0.58
  }
  ```

- **Analyst answers** – e.g. `analysis/output/answers/how_to_make_actor_B_lose.json`:

  ```json
  {
    "question": "How do I make Actor B lose?",
    "answer": "Actor B loses in 81% of runs when Actor A adopts a mixed strategy and the game goes beyond 3 rounds — but watch out for round 5 when B triggers a web search, which resets their loss threshold in 34% of cases.",
    "supporting_stats_path": "aggregated_results.json",
    "confidence": 0.87
  }
  ```

The frontend only needs these JSONs.

---

## Daytona Infra (`/daytona_infra`)

This folder owns the “parallel worlds” part.[conversation_history:1]

**What it does**

- Launches N Daytona sandboxes in parallel (one simulation per sandbox).  
- Mounts into each sandbox:
  - scenario config,  
  - actor dossiers,  
  - simulation code.  
- Polls each sandbox:
  - streams `decision_log.json` tails for the live ticker;  
  - detects completion and copies out `result.json` into `simulation/runs/{run_id}/`.[conversation_history:1]

**Output**

- Populated `simulation/runs/*` directories.  
- Optional `simulation/runs_manifest.json` listing all completed runs.

---

## Frontend (`/frontend`)

The frontend is a thin UI over the JSON contracts.[conversation_history:1]

**What it does**

- Lets a user:
  - enter a scenario,  
  - launch simulations,  
  - ask analyst questions.  
- Shows:
  - actor dossiers + rationality profiles,  
  - live decision ticker across parallel runs,  
  - distributions and key stats,  
  - analyst answers linked back to the scenario and metrics.[conversation_history:1]

**Input**

- `analysis/output/aggregated_results.json`.  
- `analysis/output/answers/*.json`.  
- Live decision‑log updates from `/daytona_infra`.

---

## Data Contracts (For Team Integration)

Lock these early so everyone can work independently.[conversation_history:1]

1. **Orchestration → Simulation**  
   - Orchestration **outputs**:
     - `scenario.json` (scenario_id, actors, rounds, env params).  
     - `dossiers/{actor_id}.json` (actor metadata + `rationality_derived`).  
   - Simulation **assumes** those files exist and does not call LLMs.

2. **Simulation → Analysis**  
   - Simulation **outputs**:
     - `runs/{run_id}/result.json` (run metadata, outcomes, optional stats + decision_log_path).  
   - Analysis **assumes** all runs share a scenario_id and that payoff/status fields are comparable.

3. **Analysis → Frontend**  
   - Analysis **outputs**:
     - `aggregated_results.json` (metrics for charts).  
     - `answers/*.json` (Q&A responses).  
   - Frontend **assumes** these shapes are stable.[conversation_history:1]

---

## Team Ownership

- **Daytona Infra** – `/daytona_infra`: sandbox orchestration, parallel launches, polling.  
- **Agent Logic** – `/simulation`: rationality profiles, decision loop, game‑state I/O, result.json schema.  
- **Orchestrator + Analyst** – `/orchestration`, `/analysis`: scenario + actors + dossiers + analyst answers.  
- **Frontend + Demo** – `/frontend`, `/docs`: UI, wiring, and 2‑minute pitch narrative.[conversation_history:1]