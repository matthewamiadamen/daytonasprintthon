import os, json, time

from analysis.websocket_server import broadcast

RUNS_DIR = "simulation/runs"
OUTPUT_DIR = "analysis/output"
ANSWERS_DIR = "analysis/output/answers"

os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(ANSWERS_DIR, exist_ok=True)

stats = {
    "simulations_complete": 0,
    "simulations_running": 0,
    "outcome_distribution": {},
    "actor_outcome_distribution": {},
    "game_theory_stats": {
        "nash_equilibrium_reached_count": 0,
        "nash_equilibrium_reached_pct": 0,
        "pareto_optimal_count": 0,
        "pareto_optimal_pct": 0,
        "irrational_disruption_count": 0,
        "irrational_disruption_pct": 0,
        "web_search_changed_decision_count": 0,
        "web_search_changed_decision_pct": 0,
        "dominant_strategy_used_count": 0,
        "dominant_strategy_used_pct": 0
    },
    "actor_payoff_averages": {},
    "key_events_frequency": {},
    "full_logs": []
}

def watch_runs():
    seen = set()
    while True:
        for run_folder in os.listdir(RUNS_DIR):
            result_path = f"{RUNS_DIR}/{run_folder}/result.json"
            if result_path not in seen and os.path.exists(result_path):
                with open(result_path) as f:
                    sim = json.load(f)
                update_stats(stats, sim)
                seen.add(result_path)

                # Write aggregated output — matches root README contract
                # Add top-level aliases so frontend + analyst can use either name
                output = {
                    **stats,
                    "num_runs": stats["simulations_complete"],
                    "irrational_disruption_rate": round(
                        stats["game_theory_stats"]["irrational_disruption_pct"] / 100, 4
                    ),
                }
                with open(f"{OUTPUT_DIR}/aggregated_results.json", "w") as f:
                    json.dump(output, f, indent=2)

                broadcast(stats)

        time.sleep(2)

def update_stats(stats, sim):
    stats["simulations_complete"] += 1

    # Outcome distribution
    winner = sim["outcome"].get("winner_name") or "tie"
    dist = stats["outcome_distribution"]
    dist[winner] = dist.get(winner, {"count": 0, "pct": 0})
    dist[winner]["count"] += 1

    # Recalculate percentages
    total = stats["simulations_complete"]
    for k in dist:
        dist[k]["pct"] = round(dist[k]["count"] / total * 100, 1)

    # Actor payoffs and per-actor statistics
    for actor_id, payoff in sim["actor_final_payoffs"].items():
        prev = stats["actor_payoff_averages"].get(actor_id, 0)
        stats["actor_payoff_averages"][actor_id] = round(
            (prev * (total - 1) + payoff) / total, 2
        )

        outcome_stats = stats["actor_outcome_distribution"].setdefault(
            actor_id,
            {"runs": 0, "wins": 0, "win_rate": 0.0, "avg_payoff": 0.0}
        )
        outcome_stats["runs"] += 1
        if actor_id == sim["outcome"].get("winner"):
            outcome_stats["wins"] += 1
        outcome_stats["avg_payoff"] = round(
            (outcome_stats["avg_payoff"] * (outcome_stats["runs"] - 1) + payoff)
            / outcome_stats["runs"],
            2,
        )
        outcome_stats["win_rate"] = round(
            outcome_stats["wins"] / outcome_stats["runs"] * 100, 1
        )

    # Key events
    for event in sim.get("key_events", []):
        stats["key_events_frequency"][event] = \
            stats["key_events_frequency"].get(event, 0) + 1

    # Game theory flags
    gt = stats["game_theory_stats"]
    if sim["outcome"].get("nash_equilibrium_reached"):
        gt["nash_equilibrium_reached_count"] += 1
    if sim["outcome"].get("pareto_optimal"):
        gt["pareto_optimal_count"] += 1

    irrational_run = any(
        "irrational" in event.lower() for event in sim.get("key_events", [])
    ) or any(
        entry.get("rationality", "").lower().startswith("irrational")
        for entry in sim.get("decision_log", [])
    )
    if irrational_run:
        gt["irrational_disruption_count"] += 1

    web_search_run = any(
        "web search" in event.lower() for event in sim.get("key_events", [])
    ) or any(
        entry.get("web_search_triggered") for entry in sim.get("decision_log", [])
    )
    if web_search_run:
        gt["web_search_changed_decision_count"] += 1

    dominant_strategy_run = any(
        "dominant" in event.lower() for event in sim.get("key_events", [])
    ) or any(
        "dominant" in entry.get("reasoning_summary", "").lower()
        or "dominant" in entry.get("action", "").lower()
        for entry in sim.get("decision_log", [])
    )
    if dominant_strategy_run:
        gt["dominant_strategy_used_count"] += 1

    gt["nash_equilibrium_reached_pct"] = round(
        gt["nash_equilibrium_reached_count"] / total * 100, 1
    )
    gt["pareto_optimal_pct"] = round(
        gt["pareto_optimal_count"] / total * 100, 1
    )
    gt["irrational_disruption_pct"] = round(
        gt["irrational_disruption_count"] / total * 100, 1
    )
    gt["web_search_changed_decision_pct"] = round(
        gt["web_search_changed_decision_count"] / total * 100, 1
    )
    gt["dominant_strategy_used_pct"] = round(
        gt["dominant_strategy_used_count"] / total * 100, 1
    )

    # Full logs
    stats["full_logs"].append({
        "simulation_id": sim["simulation_id"],
        "decision_log": sim["decision_log"]
    })