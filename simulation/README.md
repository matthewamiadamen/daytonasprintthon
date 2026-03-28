# Simulation Layer

**Owner: Person 1 (Daytona infra) + Person 2 (Agent logic)**

This layer takes the full actor JSON files and scenario from the orchestration layer and runs them as real parallel simulations. Each actor file is a long, detailed JSON containing both the actor's real-world data (identity, known decisions, financial position, public stance, demographic prior) **and** their complete game theory profile (rationality level, biases, strategy tendency, decision model, known weaknesses). The simulation layer consumes these files directly — it does not generate or modify actor profiles, it executes them.

Each simulation is a full isolated Daytona sandbox. Agents read a shared decision log, take turns acting, and the completed log is streamed to the analysis layer.

---

## Input — What the Simulation Layer Receives

The orchestration layer hands off:

1. **`scenario.json`** — defines the game type, rounds, payoff structure, and context
2. **`actors/*.json`** — one file per actor, each a comprehensive JSON dossier that includes:
   - Actor identity and type
   - Real-world research data (known decisions, financial position, public stance)
   - Demographic prior (inferred behavioural tendencies for this actor type)
   - **Full game theory profile** — rationality, biases, strategy tendency, decision model, and known weaknesses

The game theory profile inside each actor JSON is what configures the agent's reasoning prompt during simulation. The simulation layer reads it as-is and uses it to drive each agent's decision-making.

---

## What This Layer Does

```
/shared/scenario.json + actors/*.json (full actor dossiers with game theory profiles)
              ↓
[ Simulation Runner ]
              ↓
   Spawns N Daytona sandboxes
   (one sandbox = one full simulation)
              ↓
   Inside each sandbox:
   Agents take turns → read actor JSON + log → decide → write to log
              ↓
   simulation_001.json
   simulation_002.json
   ... (streamed live as runs complete)
              ↓
Sent to → /analysis
```

---

## Architecture — One Sandbox Per Simulation

Each Daytona sandbox runs **one complete simulation** — all actors, all rounds, from start to finish. The parallelism is at the simulation level.

This means:
- 50 sandboxes = 50 independent parallel worlds
- Inside each sandbox, actors interact sequentially (turn-based)
- No sandbox can contaminate another — results are fully isolated

This is the correct architecture for a Daytona hackathon. It demonstrates exactly what sandboxes are for: safe, parallel, isolated execution at scale.

```
Sandbox 001  [ A→B→C→A→B→C... Round 1-5 ] → result
Sandbox 002  [ A→B→C→A→B→C... Round 1-5 ] → result   (all running simultaneously)
Sandbox 003  [ A→B→C→A→B→C... Round 1-5 ] → result
...
Sandbox 050  [ A→B→C→A→B→C... Round 1-5 ] → result
```

---

## The Decision Log — How Agents Communicate

The shared truth inside each sandbox is `decision_log.json`. It is append-only. Every agent reads the **full history** before deciding, then appends their move. This is what makes it real game theory — each actor has visibility of what every other actor has done.

### Log entry format

```json
{
  "round": 2,
  "actor_id": "B",
  "actor_name": "NovaTech Inc",
  "rationality": "semi-rational",
  "game_state_seen": {
    "round": 2,
    "previous_actions": ["A offered cooperative terms", "C made aggressive counter-bid"]
  },
  "context_source": "dossier",
  "web_search_triggered": false,
  "reasoning_summary": "Loss threshold exceeded. A's cooperative offer is a trap given C's aggression. Switching to conservative hold.",
  "action": "hold_position",
  "payoff_delta": -4,
  "timestamp": "2026-03-28T11:42:03Z"
}
```

If an agent triggers a web search mid-simulation, `web_search_triggered` is `true` and a `search_context` field is appended with what was found and how it changed the decision.

---

## Person 1 — Daytona Infrastructure

Your job is getting sandboxes to spin up programmatically, run the agent script, and return their output.

**Core tasks:**

1. **Sandbox launcher** — takes `scenario.json` + `actors/` directory, spawns N Daytona environments, injects the simulation script and actor files into each
2. **Output poller** — every few seconds, fetches the current `decision_log.json` from each running sandbox and pushes it to the analysis layer (this is what makes the frontend feel live)
3. **Result collector** — when a sandbox exits, collects the final log and marks that simulation as complete

**Key question to answer on day one:** how does Daytona's API handle file injection and output retrieval? Spike this first. Everything else can wait.

**Simplification if needed:** if 50 parallel sandboxes proves painful, 8-10 will still demonstrate the concept convincingly. Prioritise reliability over scale.

---

## Person 2 — Agent Logic

Your job is the Python script that runs inside each sandbox and makes the agents actually behave according to their profiles.

**Core tasks:**

1. **Agent runner** — loads actor files, initialises decision log, runs the turn loop for N rounds
2. **Rationality engine** — translates each actor's `game_theory_profile` into a system prompt that shapes their LLM call
3. **Web search fallback** — detects when an actor hits a decision their dossier doesn't cover, triggers a search, updates their context, logs the event
4. **Game state manager** — tracks payoffs, determines round outcomes, detects win/loss conditions per scenario rules

**The turn loop (pseudocode):**

```python
for round in range(scenario["rounds"]):
    for actor in actors:
        game_state = load_decision_log()
        system_prompt = build_system_prompt(actor)  # rationality profile → prompt
        context = load_actor_dossier(actor)

        decision = call_llm(
            system=system_prompt,
            user=f"Game state: {game_state}\nYour context: {context}\nWhat do you do?"
        )

        if decision.needs_more_context:
            search_result = web_search(decision.search_query)
            context = update_dossier(context, search_result)
            decision = call_llm(system=system_prompt, user=f"Updated context: {context}\nWhat do you do?")

        append_to_log(decision)
```

### Rationality profile → system prompt

This is the core of Person 2's work. Each profile maps to a different LLM instruction:

```
Fully Rational:
"You are a fully rational game theory agent. Identify dominant strategies.
Compute expected payoffs for each available action. Choose the action that
maximises your expected payoff. If no dominant strategy exists, compute
the mixed strategy Nash equilibrium and play accordingly."

Semi-Rational (Prospect Theory):
"You are a human decision-maker with real cognitive biases. You feel losses
approximately twice as strongly as equivalent gains. You are susceptible to
framing effects — the same outcome feels different depending on how it is
presented. You anchor to your opening position and adjust insufficiently."

Irrational:
"You are an impulsive decision-maker. You overvalue immediate payoffs relative
to future ones. You continue investing in failing strategies because of what
you have already committed. You are influenced by what others around you are
doing. Your decisions are emotionally reactive."
```

---

## Simulation Output Format

When a sandbox completes, it writes a final `simulation_NNN.json`:

```json
{
  "simulation_id": "sim_014",
  "scenario": "Biotech Licensing Negotiation",
  "seed": 42,
  "rounds_completed": 5,
  "outcome": {
    "winner": "A",
    "winner_name": "BioVentures Ltd",
    "winning_condition": "Secured exclusive licence at floor price",
    "nash_equilibrium_reached": false,
    "pareto_optimal": false
  },
  "actor_final_payoffs": {
    "A": 18,
    "B": -4,
    "C": 2
  },
  "key_events": [
    "Round 2: B triggered web search, updated loss threshold",
    "Round 3: C irrational escalation destabilised Nash convergence",
    "Round 5: A mixed strategy forced B into paralysis"
  ],
  "decision_log": [ ... full log entries ... ]
}
```

This file is what gets streamed to the analysis layer.

---

## Streaming to Analysis

The simulation runner does not wait for all sandboxes to finish before sending data. It streams each completed simulation file to `/analysis/incoming/` as it arrives. The analysis layer processes them in real time, updating visualisations and probability distributions as more data comes in.

```
sim_003 completes → streamed to analysis immediately
sim_011 completes → streamed to analysis immediately
sim_029 completes → streamed to analysis immediately
...
All 50 complete → analysis layer has full dataset
```

---

## Files in This Folder

```
simulation/
├── runner.py               # Spawns and manages N Daytona sandboxes
├── agent.py                # The script that runs INSIDE each sandbox
├── rationality.py          # Rationality profile → system prompt mappings
├── game_state.py           # Payoff tracking, win/loss detection
├── web_search.py           # Search fallback for mid-simulation context gaps
├── streamer.py             # Polls sandboxes, streams logs to analysis layer
└── README.md               # This file
```

---

## Coordination Between Person 1 and Person 2

Person 1 handles everything **outside** the sandbox. Person 2 handles everything **inside** the sandbox. The interface between them is a single Python script entry point:

```
Person 1 spawns sandbox → injects agent.py + actor files → sandbox runs agent.py → Person 1 collects output
```

Agree on this interface in the first 30 minutes. Once that contract is locked, you can develop independently.