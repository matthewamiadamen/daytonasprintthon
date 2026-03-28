# Orchestration Layer

**Owner: Person 3**

This is the entry point of the entire system. It takes a raw user prompt and turns it into everything the simulation layer needs to run — a structured scenario, a set of fully fleshed-out actor files, and a game theory profile for each actor.

---

## What This Layer Does

```
User Prompt (natural language)
        ↓
[ Orchestrator Model ]
        ↓
  ┌─────────────────────────────────┐
  │  scenario.json                  │
  │  actors/actor_A.json            │
  │  actors/actor_B.json            │
  │  actors/actor_C.json            │
  │  ... (n actors)                 │
  └─────────────────────────────────┘
        ↓
Sent to → /simulation
```

The orchestrator is also the analyst model at the end of the pipeline. The same model that understands the setup is the one that answers strategic questions after all simulations complete.

---

## Input

A plain text prompt from the user describing the scenario. Examples:

```
"Three biotech startups negotiating a licensing deal with a major pharma company"
"Five nations at a climate summit with conflicting economic interests"
"A startup acquisition negotiation between a cash-rich acquirer and a desperate founder"
```

No structure required from the user. The orchestrator figures out everything else.

---

## Step 1 — Scenario Generation

The orchestrator model reads the prompt and produces a `scenario.json` file. This defines the game: what type of interaction it is, how many rounds it runs, what the payoff structure looks like, and what winning/losing means.

```json
// scenario.json
{
  "title": "Biotech Licensing Negotiation",
  "type": "multi-round negotiation",
  "rounds": 5,
  "actors": ["BioVentures Ltd", "NovaTech Inc", "PharmaGiant Corp"],
  "payoff_structure": {
    "win_condition": "Secure licensing deal with best terms",
    "zero_sum": false,
    "cooperation_possible": true
  },
  "context": "Three early-stage biotechs competing and occasionally cooperating to land an exclusive licensing deal. Resource constraints are asymmetric."
}
```

---

## Step 2 — Actor Research & File Generation

For each actor in the scenario, the orchestrator runs a research pass. It uses web search to find real information about the actor (if they are based on a real company or entity). It then generates a dossier file.

**If the actor has rich real-world data:**
The dossier is built from real decisions, public statements, financial position, and known strategic behaviour.

**If the actor is sparse or fictional:**
The orchestrator generates an ideological prior based on the actor's demographic category — what entities of this type typically do in this type of game. This is not a guess. It is a principled inference from the actor's type, size, sector, and position.

```json
// actors/actor_BioVentures.json
{
  "id": "A",
  "name": "BioVentures Ltd",
  "type": "Early-stage biotech, Series A",
  "known_decisions": [
    "Rejected acquisition offer in 2023 to pursue independence",
    "Co-developed IP with a competitor rather than litigating"
  ],
  "financial_position": "18 months runway, needs deal to survive",
  "public_stance": "Founder publicly committed to keeping IP in-house",
  "demographic_prior": "Early stage biotech typically prioritises runway preservation over optimal deal terms. Founder-led means faster but emotionally driven decisions. Cooperative strategies dominate when existential pressure is high.",
  "game_theory_profile": {
    "rationality": "semi-rational",
    "primary_bias": "loss aversion — existential threat amplifies risk sensitivity",
    "strategy_tendency": "cooperative until cornered, then unpredictable",
    "decision_model": "prospect theory",
    "known_weaknesses": ["sunk cost on IP position", "overweights short-term survival vs long-term value"]
  }
}
```

The `game_theory_profile` block is what the simulation layer uses to configure each agent's reasoning prompt.

---

## Step 3 — Output to Simulation Layer

Once all actor files and the scenario file are generated, this layer writes them to a shared directory that the simulation layer reads from.

```
/shared/
  scenario.json
  actors/
    actor_A.json
    actor_B.json
    actor_C.json
```

The simulation layer polls this directory and spins up sandboxes as soon as files are ready.

---

## Step 4 — Analyst Mode (Post-Simulation)

After all simulation runs complete, the orchestrator model re-activates as the analyst. It receives the full set of simulation logs from the analysis layer and answers user queries.

Because it generated the scenario and actors, it has full context on why actors behaved the way they did — it can give grounded, specific answers rather than generic observations.

Example query → response:

```
Query:  "How do I make Actor B lose?"

Response: "Actor B loses in 81% of runs when two conditions align:
(1) Actor A adopts a mixed strategy, removing B's ability to predict moves,
and (2) the negotiation extends beyond round 3, which triggers B's
loss aversion to compound into paralysis. Watch out for runs where B
triggers a web search — in 34% of those cases, new information resets
their threshold and they become competitive again."
```

---

## Files in This Folder

```
orchestration/
├── orchestrator.py         # Main entry point — takes user prompt, runs research, generates files
├── researcher.py           # Web search module for actor data gathering
├── profile_generator.py    # Derives game theory profile from dossier data
├── scenario_builder.py     # Builds scenario.json from prompt
└── README.md               # This file
```

---

## Key Decisions Made Here

- How many actors are generated (n)
- What rationality profile each actor receives
- What the payoff structure of the game is
- What counts as winning and losing
- What each actor knows at the start (information asymmetry setup)

Everything downstream depends on the quality of this layer. Garbage in, garbage out — the simulation is only as interesting as the actors are differentiated.