def initialise_stats():
    return {
        "simulations_complete": 0,
        "simulations_running": 0,
        "outcome_distribution": {},
        "game_theory_stats": {
            "nash_equilibrium_reached_pct": 0,
            "pareto_optimal_pct": 0,
            "irrational_actor_disrupted_eq_pct": 0,
            "web_search_changed_decision_pct": 0,
            "dominant_strategy_used_pct": 0
        },
        "actor_payoff_averages": {},
        "key_events_frequency": {},
        "full_logs": []
    }

def update_game_theory_stats(stats, sim):
    total = stats["simulations_complete"]
    gt = stats["game_theory_stats"]

    def update_pct(current, hit):
        prev_count = round(current * (total - 1) / 100)
        new_count = prev_count + (1 if hit else 0)
        return round(new_count / total * 100, 1)

    gt["nash_equilibrium_reached_pct"] = update_pct(
        gt["nash_equilibrium_reached_pct"],
        sim["outcome"].get("nash_equilibrium_reached", False)
    )
    gt["pareto_optimal_pct"] = update_pct(
        gt["pareto_optimal_pct"],
        sim["outcome"].get("pareto_optimal", False)
    )

    # Web search and irrational disruption from key events
    key_events = sim.get("key_events", [])
    has_web_search = any("web search" in e.lower() for e in key_events)
    has_irrational = any("irrational" in e.lower() for e in key_events)

    gt["web_search_changed_decision_pct"] = update_pct(
        gt["web_search_changed_decision_pct"], has_web_search
    )
    gt["irrational_actor_disrupted_eq_pct"] = update_pct(
        gt["irrational_actor_disrupted_eq_pct"], has_irrational
    )