# Analysis Layer

**Owner: Person 4**

This layer aggregates completed simulation results and makes them available to the analyst model and frontend.

---

## What This Layer Does

- Loads all `simulation/runs/*/result.json`.
- Optionally inspects the referenced `decision_log.json` files for richer patterns.
- Computes win/lose rates, payoff distributions, roles, how often irrational actors break equilibria, and how web-search events change outcomes.
- Calls the analyst LLM with scenario + aggregated stats + user question to produce natural-language answers grounded in the data.

**Input**

- `simulation/runs/{run_id}/result.json` (+ optional decision logs).

**Output**

- **Aggregated results** – `analysis/output/aggregated_results.json`
- **Analyst answers** – `analysis/output/answers/<question_name>.json`

---

## Part 1 — The Aggregator

The aggregator processes completed simulation results and updates a running statistics object.

### Source of truth

The analysis layer consumes finished simulation files from `simulation/runs/<run_id>/result.json`.
Each result is parsed and merged into the aggregated stats object.

### Aggregated stats object

The aggregated stats object includes:

- `simulations_complete`
- `outcome_distribution`
- `game_theory_stats`
- `actor_payoff_averages`
- `key_events_frequency`
- `full_logs`

This object is written to `analysis/output/aggregated_results.json` after each new simulation file is processed.

### Implementation notes

- The aggregator scans `simulation/runs/` for `result.json` files.
- New run results are loaded and merged into the shared stats object.
- The updated summary is persisted to `analysis/output/aggregated_results.json`.
- This is the primary data source for the analyst model and the frontend.

---

## Part 2 — The Analyst Model

The analyst model answers strategic questions using aggregated simulation data.

### Analyst behavior

- Load `analysis/output/aggregated_results.json`.
- Build a prompt using the latest aggregated stats.
- Send the prompt to the configured LLM client.
- Save the response as JSON in `analysis/output/answers/`.

The analyst should reason from actual simulation data, not from general knowledge alone.
It should cite percentages, name the conditions, and identify causal mechanisms where possible.

---

## Data Contract — What This Layer Expects from Simulation

Simulation results should conform to this structure:

```json
{
  "simulation_id": "string",
  "scenario": "string",
  "rounds_completed": "integer",
  "outcome": {
    "winner": "actor_id or null",
    "winner_name": "string or null",
    "nash_equilibrium_reached": "boolean",
    "pareto_optimal": "boolean"
  },
  "actor_final_payoffs": {
    "actor_id": "number"
  },
  "key_events": ["string"],
  "decision_log": [
    {
      "round": "integer",
      "actor_id": "string",
      "rationality": "string",
      "web_search_triggered": "boolean",
      "reasoning_summary": "string",
      "action": "string",
      "payoff_delta": "number"
    }
  ]
}
```

This contract is the input the analysis layer consumes.

---

## Files in This Folder

```
analysis/
├── aggregator.py
├── analyst.py
├── output/
│   ├── aggregated_results.json  # generated at runtime
│   └── answers/                # generated analyst answers
├── README.md
├── stats.py                  # optional helper / placeholder
└── websocket_server.py       # optional helper / placeholder
```

---

## Frontend integration note

The frontend app lives in `/frontend`.
The analysis layer provides aggregated JSON outputs that the frontend can consume.
A live dashboard can be built on top of these outputs using polling or a WebSocket layer.
