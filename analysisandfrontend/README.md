# Analysis & Frontend Layer

**Owner: Person 4**

This layer receives simulation logs as they stream in from the simulation layer, builds a live picture of outcomes across all runs, and serves two things: a visual dashboard that updates in real time, and an analyst model that answers strategic questions grounded in the actual simulation data. One person owns this entire layer — aggregation, analysis, frontend, and demo narrative.

---

## What This Layer Does

```
simulation_001.json  ──┐
simulation_002.json  ──┤
simulation_003.json  ──┼──→ [ Aggregator ] ──→ [ Visual Dashboard ]
...                  ──┤                   ──→ [ Analyst Model ]
simulation_050.json  ──┘
```

Data flows in continuously. The dashboard updates as each simulation completes. The analyst model becomes available once enough runs have finished to give statistically meaningful answers — in practice, after around 10-15 runs.

---

## Part 1 — The Aggregator

The aggregator is a lightweight process that watches `/analysis/incoming/` for new simulation files, parses each one, and updates a running statistics object.

### Running stats object

```json
{
  "simulations_complete": 23,
  "simulations_running": 27,
  "outcome_distribution": {
    "A wins": { "count": 9, "pct": 39.1 },
    "B wins": { "count": 4, "pct": 17.4 },
    "C wins": { "count": 2, "pct":  8.7 },
    "tie":    { "count": 8, "pct": 34.8 }
  },
  "game_theory_stats": {
    "nash_equilibrium_reached_pct": 31,
    "pareto_optimal_pct": 24,
    "irrational_actor_disrupted_eq_pct": 58,
    "web_search_changed_decision_pct": 34,
    "dominant_strategy_used_pct": 67
  },
  "key_events_frequency": {
    "B triggered web search": 12,
    "C irrational escalation": 18,
    "A mixed strategy": 9
  },
  "actor_payoff_averages": {
    "A": 14.2,
    "B": -2.1,
    "C": 3.8
  },
  "full_logs": [ ... all decision logs from completed simulations ... ]
}
```

This object is the single source of truth for both the dashboard and the analyst model. It lives in memory and is updated every time a new simulation file arrives.

### Aggregator pseudocode

```python
import os, json, time

stats = initialise_stats()

def watch_incoming():
    seen = set()
    while True:
        for file in os.listdir("incoming/"):
            if file not in seen:
                sim = json.load(open(f"incoming/{file}"))
                update_stats(stats, sim)
                seen.add(file)
                push_to_dashboard(stats)   # WebSocket push to frontend
        time.sleep(2)
```

---

## Part 2 — The Analyst Model

The analyst model is the same orchestrator model that generated the scenario. After simulations complete, it re-activates with the full stats object as context and answers user queries.

### What makes this different from a normal chatbot

The analyst is not reasoning from general knowledge. It is reasoning from actual data — 50 real simulation runs, structured logs, outcome distributions, event frequencies. Its answers are grounded in what actually happened across those runs.

### Analyst prompt structure

```
System:
You are the analyst for a game theory simulation. You designed the scenario
and generated the actors. You now have access to the complete results of
[N] parallel simulation runs. Answer the user's strategic question using
the data. Be specific — cite percentages, name the conditions, identify
the causal mechanisms. Flag uncertainty where the data is thin.

Context:
[Full stats object as JSON]
[Full decision logs from all completed simulations]

User query:
"How do I make Actor B lose?"
```

### Example analyst response

```
Actor B loses in 81% of runs when two conditions align:

1. Actor A adopts a mixed strategy (observed in 9 runs). When A randomises
   between cooperative and aggressive moves, B cannot predict and defaults
   to their conservative loss-averse baseline — which underperforms in this
   scenario's payoff structure.

2. The negotiation extends past round 3 (observed in 31 runs). B's prospect
   theory profile compounds over time — each round of uncertainty increases
   their perceived loss exposure and pushes them toward paralysis.

Watch out for round 2. In 12 of 50 runs, B triggered a web search that
updated their loss threshold upward. In 34% of those cases, B became
significantly more competitive for the remainder of the game. Keeping
information pressure high in round 2 suppresses this.

Weakest result: in 4 runs where C overcommitted early and collapsed, B
recovered and won despite A's mixed strategy. C's irrational behaviour
can accidentally benefit B.
```

---

## Part 3 — Visual Dashboard (Person 4)

The dashboard has four views. They update live as simulations stream in.

### View 1 — Live Run Monitor

Shows all N sandboxes. Each is a tile with a status indicator — running, complete, or errored. Inside running tiles, the last decision log entry scrolls in real time.

**Key element:** the decision ticker. A live feed of the most recent agent decisions across all running simulations. This is the most visually compelling part of the demo.

```
00:14  [Sim 003 / Actor B]  Web search triggered: "NovaTech acquisition 2025" → context updated
00:15  [Sim 011 / Actor A]  Mixed strategy computed. Randomising between options.
00:17  [Sim 029 / Actor C]  Sunk cost detected. Continuing failed strategy. (Bias flagged)
00:19  [Sim 003 / Actor A]  Nash equilibrium identified. Dominant strategy: hold.
```

Colour-code by rationality: green for rational decisions, amber for semi-rational, red for irrational/biased moves.

### View 2 — Outcome Distribution

Horizontal bar chart updating in real time as simulations complete. Shows win percentages per actor plus ties. Should visually shift and stabilise as more data comes in — this movement is what shows the system is running.

### View 3 — Game Theory Stats Panel

Shows the metrics that give the project intellectual credibility:

- Nash equilibrium reached: X%
- Pareto optimal outcomes: X%
- Irrational actor disrupted equilibrium: X%
- Web search changed a decision: X%
- Dominant strategy deployed: X%

### View 4 — Analyst Query Interface

Clean text input. User types a strategic question. The analyst model responds. Display the answer with the key conditions highlighted — this is the money shot of the demo.

Show suggested queries to guide the demo:
- "How do I make Actor B lose?"
- "What is the most stable coalition?"
- "When was Nash equilibrium closest?"
- "Which actor was most irrational?"

---

## Data Contract — What This Layer Expects from Simulation

Every simulation file that arrives must conform to this structure. Person 1 and Person 2 must produce this exact format:

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

**Lock this contract with the simulation team in hour 1.** This layer cannot be built without it.

---

## WebSocket Push to Frontend

The aggregator pushes updated stats to the frontend via WebSocket every time a new simulation completes. Person 4's frontend subscribes on load and re-renders on each push.

```python
# aggregator pushes
websocket.send(json.dumps(stats))

# frontend receives
socket.onmessage = (event) => {
  const stats = JSON.parse(event.data)
  updateDashboard(stats)
}
```

This is what makes the dashboard feel live rather than requiring page refreshes.

---

## Files in This Folder

```
analysis/
├── aggregator.py           # Watches incoming/, updates running stats, pushes to frontend
├── analyst.py              # Analyst model query interface — takes question, returns grounded answer
├── stats.py                # Stats object definition and update logic
├── incoming/               # Simulation files land here as they complete
├── frontend/
│   ├── index.html          # Dashboard entry point
│   ├── dashboard.js        # Live views — monitor, outcomes, stats, analyst
│   └── styles.css          # Styling
└── README.md               # This file
```

---

## Demo Ownership

Person 4 owns the demo. The flow should be:

1. Show the user entering a scenario prompt — keep it dramatic
2. Show actor dossiers being generated — call out the sparse actor getting an ideological prior
3. Launch sandboxes — show the monitor view light up
4. Let the decision ticker run for 30 seconds — point out a web search event and a bias flag
5. Show outcome distribution stabilising as more runs complete
6. Ask the analyst a question live — let the answer do the work

The demo is the pitch. Everything else is infrastructure.