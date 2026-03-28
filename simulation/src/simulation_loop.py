"""
simulation_loop.py — Game-theory agent simulation engine.

Runs inside a Daytona sandbox (invoked by run_parallel.py).
Reads scenario.json + actor dossier files, instantiates N LLM-driven agents,
runs a turn-based multi-round simulation, writes the decision log live as
events unfold, and produces a final result file for the analysis layer.

Expected sandbox layout (uploaded by run_parallel.py):
    /workspace/scenario.json
    /workspace/dossiers/<actor_id>.json   (one per actor)

Outputs:
    /workspace/decision_log.json   (updated after every single action)
    /workspace/result.json         (written once when simulation completes)
"""

import json
import os
import random
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

import anthropic

# ---------------------------------------------------------------------------
# Paths — defaults match the Daytona sandbox layout from run_parallel.py.
# Override WORKSPACE_DIR for local testing.
# ---------------------------------------------------------------------------
WORKSPACE = Path(os.environ.get("WORKSPACE_DIR", "/workspace"))
SCENARIO_PATH = WORKSPACE / "scenario.json"
DOSSIERS_DIR = WORKSPACE / "dossiers"
DECISION_LOG_PATH = WORKSPACE / "decision_log.json"
RESULT_PATH = WORKSPACE / "result.json"

# ---------------------------------------------------------------------------
# LLM configuration — uses Claude via Anthropic API.
# Set ANTHROPIC_API_KEY in your environment.
# ---------------------------------------------------------------------------
MODEL = os.environ.get("SIM_MODEL", "claude-sonnet-4-20250514")
client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY from env
MAX_TOKENS = int(os.environ.get("SIM_MAX_TOKENS", "1024"))


# ---------------------------------------------------------------------------
# Rationality profile → system-prompt fragments
# ---------------------------------------------------------------------------
RATIONALITY_PROMPTS = {
    "rational": (
        "You are a fully rational game theory agent. Identify dominant strategies. "
        "Compute expected payoffs for each available action. Choose the action that "
        "maximises your expected payoff. If no dominant strategy exists, compute the "
        "mixed strategy Nash equilibrium and play accordingly. Never act on emotion."
    ),
    "semi-rational": (
        "You are a human decision-maker with real cognitive biases. You feel losses "
        "approximately twice as strongly as equivalent gains. You are susceptible to "
        "framing effects — the same outcome feels different depending on how it is "
        "presented. You anchor to your opening position and adjust insufficiently. "
        "You try to be rational but your biases shape your choices."
    ),
    "irrational": (
        "You are an impulsive decision-maker. You overvalue immediate payoffs relative "
        "to future ones. You continue investing in failing strategies because of what "
        "you have already committed. You are influenced by what others around you are "
        "doing. Your decisions are emotionally reactive and often suboptimal."
    ),
}


def _build_rationality_block(profile: dict) -> str:
    """
    Turn a game_theory_profile dict into a system-prompt paragraph that
    configures how the agent reasons.
    """
    rationality = profile.get("rationality", "semi-rational").lower().replace(" ", "-")

    if "irrational" in rationality:
        base = RATIONALITY_PROMPTS["irrational"]
    elif "semi" in rationality:
        base = RATIONALITY_PROMPTS["semi-rational"]
    elif "rational" in rationality:
        base = RATIONALITY_PROMPTS["rational"]
    else:
        base = RATIONALITY_PROMPTS["semi-rational"]

    extras = []
    if bias := profile.get("primary_bias"):
        extras.append(f"Your primary cognitive bias: {bias}.")
    if tendency := profile.get("strategy_tendency"):
        extras.append(f"Your general strategy tendency: {tendency}.")
    if model := profile.get("decision_model"):
        extras.append(f"Your decisions follow the {model} framework.")
    if weaknesses := profile.get("known_weaknesses"):
        extras.append(f"Known weaknesses: {', '.join(weaknesses)}.")

    return base + "\n" + " ".join(extras)


# ---------------------------------------------------------------------------
# Agent
# ---------------------------------------------------------------------------
class Agent:
    """
    Wraps a single actor dossier and exposes a decide() method that calls
    the LLM with the actor's profile and the current game state.
    """

    def __init__(self, dossier: dict, scenario: dict, all_dossiers: list):
        self.id = dossier["id"]
        self.name = dossier["name"]
        self.dossier = dossier
        self.profile = dossier.get("game_theory_profile", {})
        self.scenario = scenario
        # Build a compact summary of every OTHER actor so this agent knows
        # who it is dealing with — without stuffing full dossiers into context.
        self._other_actors_summary = self._summarise_others(all_dossiers)
        self.system_prompt = self._build_system_prompt()

    @staticmethod
    def _summarise_others(all_dossiers: list) -> str:
        """
        Build a concise (token-cheap) summary of every actor so each agent
        understands who the other players are.  We include name, type,
        financial stance, key bias, and strategy tendency — enough for the
        agent to reason about opponents without duplicating full dossiers.
        """
        lines = []
        for d in all_dossiers:
            gtp = d.get("game_theory_profile", {})
            line = (
                f"- {d.get('name', '?')} ({d.get('id', '?')}): "
                f"{d.get('type', 'unknown type')}. "
                f"Finance: {d.get('financial_position', 'unknown')}. "
                f"Bias: {gtp.get('primary_bias', 'none noted')}. "
                f"Tendency: {gtp.get('strategy_tendency', 'unknown')}."
            )
            lines.append(line)
        return "\n".join(lines)

    def _build_system_prompt(self) -> str:
        rationality_block = _build_rationality_block(self.profile)

        # Build a context block from the dossier (excluding the profile itself)
        dossier_parts = []
        for key in ("type", "known_decisions", "financial_position",
                     "public_stance", "demographic_prior"):
            if val := self.dossier.get(key):
                label = key.replace("_", " ").title()
                if isinstance(val, list):
                    val = "; ".join(str(v) for v in val)
                dossier_parts.append(f"- {label}: {val}")
        dossier_block = "\n".join(dossier_parts)

        payoff = self.scenario.get("payoff_structure", {})
        scenario_block = (
            f"Scenario: {self.scenario.get('title', 'Unknown')}\n"
            f"Type: {self.scenario.get('type', 'negotiation')}\n"
            f"Total rounds: {self.scenario.get('rounds', 5)}\n"
            f"Context: {self.scenario.get('context', '')}\n"
            f"Win condition: {payoff.get('win_condition', 'Maximise your payoff')}\n"
            f"Zero-sum: {payoff.get('zero_sum', False)}\n"
            f"Cooperation possible: {payoff.get('cooperation_possible', True)}"
        )

        return (
            f"You are {self.name}, participating in a game theory simulation.\n\n"
            f"=== SCENARIO ===\n{scenario_block}\n\n"
            f"=== YOUR DOSSIER ===\n{dossier_block}\n\n"
            f"=== THE OTHER ACTORS ===\n{self._other_actors_summary}\n\n"
            f"=== YOUR DECISION PROFILE ===\n{rationality_block}\n\n"
            "=== RULES ===\n"
            "Each round you see everything every actor has done so far. "
            "You must choose ONE action and explain your reasoning briefly. "
            "Stay in character. Your goal is to advance your strategic position "
            "according to your profile and the scenario's win condition.\n\n"
            "You MUST respond with a valid JSON object with exactly these keys:\n"
            '  "action": a short description of what you do this round,\n'
            '  "reasoning_summary": 1-3 sentences explaining your logic,\n'
            '  "payoff_delta": integer estimating how this action changes your '
            "position (positive = good for you, negative = bad),\n"
            '  "dominant_strategy_used": boolean — true if you believe this is '
            "a dominant strategy,\n"
            '  "wants_more_context": boolean — true if you feel your dossier '
            "lacks information needed for this decision\n"
            "Respond ONLY with the JSON object, no other text."
        )

    def decide(self, decision_log: list, round_num: int, total_rounds: int) -> dict:
        """
        Call the LLM with the current game state and return a decision log entry.
        """
        # Format the decision history
        if decision_log:
            history_lines = []
            for entry in decision_log:
                history_lines.append(
                    f"  Round {entry['round']} | {entry['actor_name']}: "
                    f"{entry['action']} (payoff delta: {entry['payoff_delta']:+d})"
                )
            history_block = "\n".join(history_lines)
        else:
            history_block = "  (No actions yet — you are the first to act.)"

        user_msg = (
            f"Round {round_num} of {total_rounds}. It is your turn.\n\n"
            f"=== DECISION HISTORY ===\n{history_block}\n\n"
            "What do you do? Respond with the JSON object only."
        )

        # Slightly higher temperature for irrational agents
        temp = 0.7
        if "irrational" in self.profile.get("rationality", "").lower():
            temp = 0.9

        response = client.messages.create(
            model=MODEL,
            max_tokens=MAX_TOKENS,
            system=self.system_prompt,
            messages=[
                {"role": "user", "content": user_msg},
            ],
            temperature=temp,
        )

        raw = response.content[0].text
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            parsed = {
                "action": raw[:200] if raw else "no action",
                "reasoning_summary": "LLM did not return valid JSON.",
                "payoff_delta": 0,
                "dominant_strategy_used": False,
                "wants_more_context": False,
            }

        # Build recent-actions summary for game_state_seen
        recent = [
            f"{e['actor_name']}: {e['action']}"
            for e in decision_log
            if e["round"] >= round_num - 1
        ][-6:]

        web_search_triggered = bool(parsed.get("wants_more_context", False))

        return {
            "round": round_num,
            "actor_id": self.id,
            "actor_name": self.name,
            "rationality": self.profile.get("rationality", "unknown"),
            "game_state_seen": {
                "round": round_num,
                "previous_actions": recent,
            },
            "context_source": "dossier",
            "web_search_triggered": web_search_triggered,
            "reasoning_summary": parsed.get("reasoning_summary", ""),
            "action": parsed.get("action", "no action"),
            "payoff_delta": int(parsed.get("payoff_delta", 0)),
            "dominant_strategy_used": bool(parsed.get("dominant_strategy_used", False)),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }


# ---------------------------------------------------------------------------
# Simulation Engine
# ---------------------------------------------------------------------------
class SimulationEngine:
    """
    Runs a complete multi-round simulation for a set of agents.
    Writes the decision log to disk after every single action so that the
    Daytona output poller can stream partial results to the analysis layer.
    """

    def __init__(self, scenario: dict, agents: list):
        self.scenario = scenario
        self.agents = agents
        self.decision_log: list[dict] = []
        self.seed = random.randint(0, 999_999)
        self.sim_id = f"sim_{uuid.uuid4().hex[:6]}"
        random.seed(self.seed)

    def run(self):
        total_rounds = self.scenario.get("rounds", 5)
        print(
            f"[{self.sim_id}] Starting simulation — {total_rounds} rounds, "
            f"{len(self.agents)} agents, seed={self.seed}",
            flush=True,
        )

        for round_num in range(1, total_rounds + 1):
            print(
                f"\n[{self.sim_id}] === Round {round_num}/{total_rounds} ===",
                flush=True,
            )
            for agent in self.agents:
                entry = agent.decide(self.decision_log, round_num, total_rounds)
                self.decision_log.append(entry)
                self._flush_log()  # live update after every action
                print(
                    f"  {agent.name} ({agent.id}): {entry['action']} "
                    f"[delta {entry['payoff_delta']:+d}]",
                    flush=True,
                )

        print(f"\n[{self.sim_id}] Simulation complete.", flush=True)

    def _flush_log(self):
        """Write the current decision log to disk (overwrites each time)."""
        DECISION_LOG_PATH.write_text(
            json.dumps(self.decision_log, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    def compile_result(self) -> dict:
        """
        Analyse the completed decision log and produce a structured result
        file that the analysis layer can aggregate across all simulation runs.
        """
        # Compute per-actor cumulative payoffs
        payoffs: dict[str, int] = {}
        for entry in self.decision_log:
            aid = entry["actor_id"]
            payoffs[aid] = payoffs.get(aid, 0) + entry["payoff_delta"]

        # Extract key events (large swings, web searches, irrational escalations)
        key_events = []
        for entry in self.decision_log:
            if abs(entry["payoff_delta"]) >= 5:
                key_events.append(
                    f"Round {entry['round']}: {entry['actor_name']} — "
                    f"{entry['action']} (delta {entry['payoff_delta']:+d})"
                )
            if entry.get("web_search_triggered"):
                key_events.append(
                    f"Round {entry['round']}: {entry['actor_name']} triggered web search"
                )

        # Aggregate stats for the analysis layer
        total_decisions = len(self.decision_log)
        web_search_count = sum(
            1 for e in self.decision_log if e.get("web_search_triggered")
        )
        dominant_count = sum(
            1 for e in self.decision_log if e.get("dominant_strategy_used")
        )
        irrational_present = any(
            "irrational" in a.profile.get("rationality", "").lower()
            for a in self.agents
        )

        # LLM judge evaluates the outcome
        outcome = self._judge_outcome(payoffs, key_events)

        return {
            "simulation_id": self.sim_id,
            "scenario": self.scenario.get("title", "Unknown"),
            "seed": self.seed,
            "rounds_completed": self.scenario.get("rounds", 5),
            "outcome": outcome,
            "actor_final_payoffs": payoffs,
            "key_events": key_events,
            "stats": {
                "total_decisions": total_decisions,
                "web_search_triggered_count": web_search_count,
                "dominant_strategy_used_count": dominant_count,
                "irrational_actor_present": irrational_present,
                "irrational_actor_disrupted_equilibrium": outcome.get(
                    "irrational_disrupted_eq", False
                ),
            },
            "decision_log": self.decision_log,
        }

    def _judge_outcome(self, payoffs: dict, key_events: list) -> dict:
        """
        Use the LLM to evaluate the completed simulation — who won, whether
        Nash equilibrium or Pareto optimality was reached, and whether
        irrational actors disrupted convergence.
        """
        actors_summary = "\n".join(
            f"  {a.id} ({a.name}): cumulative payoff = {payoffs.get(a.id, 0)}, "
            f"rationality = {a.profile.get('rationality', 'unknown')}"
            for a in self.agents
        )

        log_summary = "\n".join(
            f"  R{e['round']} {e['actor_name']}: {e['action']} "
            f"(delta {e['payoff_delta']:+d})"
            for e in self.decision_log
        )

        events_block = "\n".join(key_events) if key_events else "None"

        prompt = (
            "You are a game theory analyst. A simulation just completed. "
            "Analyse the results and produce a JSON verdict.\n\n"
            f"=== SCENARIO ===\n{json.dumps(self.scenario, indent=2)}\n\n"
            f"=== ACTORS & FINAL PAYOFFS ===\n{actors_summary}\n\n"
            f"=== KEY EVENTS ===\n{events_block}\n\n"
            f"=== FULL DECISION LOG ===\n{log_summary}\n\n"
            "Respond with a JSON object containing exactly these keys:\n"
            '  "winner": actor ID of the winner (or "tie"),\n'
            '  "winner_name": full name of the winner (or "Tie"),\n'
            '  "winning_condition": short description of how they won,\n'
            '  "nash_equilibrium_reached": boolean,\n'
            '  "pareto_optimal": boolean,\n'
            '  "irrational_disrupted_eq": boolean — did any irrational actor '
            "prevent convergence to equilibrium,\n"
            '  "summary": 2-3 sentence narrative of the simulation\n'
            "Respond ONLY with the JSON object."
        )

        response = client.messages.create(
            model=MODEL,
            max_tokens=MAX_TOKENS,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
        )

        try:
            return json.loads(response.content[0].text)
        except json.JSONDecodeError:
            # Fallback: determine winner by highest payoff
            winner_id = max(payoffs, key=payoffs.get) if payoffs else "tie"
            winner_agent = next(
                (a for a in self.agents if a.id == winner_id), None
            )
            return {
                "winner": winner_id,
                "winner_name": winner_agent.name if winner_agent else "Unknown",
                "winning_condition": "Highest cumulative payoff",
                "nash_equilibrium_reached": False,
                "pareto_optimal": False,
                "irrational_disrupted_eq": False,
                "summary": "Outcome determined by payoff totals (judge parse failure).",
            }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def load_agents(dossiers_dir: Path, scenario: dict) -> list:
    """Load all actor dossier JSON files and create Agent instances.
    Each agent receives the full list of dossiers so it can build a
    compact awareness of who the other actors are."""
    all_dossiers = []
    for dossier_file in sorted(dossiers_dir.glob("*.json")):
        all_dossiers.append(load_json(dossier_file))

    agents = []
    for dossier in all_dossiers:
        agents.append(Agent(dossier, scenario, all_dossiers))
    return agents


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    if not SCENARIO_PATH.exists():
        print(f"ERROR: scenario.json not found at {SCENARIO_PATH}", file=sys.stderr)
        sys.exit(1)

    if not DOSSIERS_DIR.exists() or not any(DOSSIERS_DIR.glob("*.json")):
        print(f"ERROR: no actor dossiers found in {DOSSIERS_DIR}", file=sys.stderr)
        sys.exit(1)

    scenario = load_json(SCENARIO_PATH)
    agents = load_agents(DOSSIERS_DIR, scenario)

    print(f"Loaded scenario: {scenario.get('title')}")
    print(f"Actors: {', '.join(a.name for a in agents)}")

    engine = SimulationEngine(scenario, agents)
    engine.run()

    result = engine.compile_result()
    RESULT_PATH.write_text(
        json.dumps(result, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    print(f"\nResult written to {RESULT_PATH}")


if __name__ == "__main__":
    main()
