const BASE = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

export interface Preset {
  id: string;
  label: string;
  description: string;
  actors: string[];
  rounds: number;
}

export interface PipelineStatus {
  scenario_ready: boolean;
  orchestration_running: boolean;
  simulation_running: boolean;
  runs_complete: number;
  runs_total: number;
  current_scenario_id: string | null;
  error: string | null;
  runs_in_disk: number;
}

export interface AggregatedResults {
  simulations_complete: number;
  outcome_distribution: Record<string, { count: number; pct: number }>;
  actor_outcome_distribution: Record<string, { runs: number; wins: number; win_rate: number; avg_payoff: number }>;
  game_theory_stats: {
    nash_equilibrium_reached_pct: number;
    pareto_optimal_pct: number;
    irrational_disruption_pct: number;
    web_search_changed_decision_pct: number;
    dominant_strategy_used_pct: number;
  };
  actor_payoff_averages: Record<string, number>;
  actor_round_payoffs: Record<string, Record<string, number>>;
  top_winning_conditions: Record<string, string>;
}

export async function getPresets(): Promise<Preset[]> {
  const r = await fetch(`${BASE}/api/presets`);
  return r.json();
}

export async function usePreset(presetId: string) {
  const r = await fetch(`${BASE}/api/use-preset`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ preset_id: presetId }),
  });
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}

export async function generateScenario(prompt: string, rounds = 6) {
  const r = await fetch(`${BASE}/api/generate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ prompt, rounds }),
  });
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}

export async function runSimulation(numRuns = 1) {
  const r = await fetch(`${BASE}/api/simulate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ num_runs: numRuns }),
  });
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}

export async function getStatus(): Promise<PipelineStatus> {
  const r = await fetch(`${BASE}/api/status`);
  return r.json();
}

export async function getResults(): Promise<AggregatedResults> {
  const r = await fetch(`${BASE}/api/results`);
  return r.json();
}

export async function getScenario() {
  const r = await fetch(`${BASE}/api/scenario`);
  if (!r.ok) return null;
  return r.json();
}

export async function getDossiers() {
  const r = await fetch(`${BASE}/api/dossiers`);
  return r.json();
}

export async function askAnalyst(question: string): Promise<{ question: string; answer: string }> {
  const r = await fetch(`${BASE}/api/ask`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question }),
  });
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}
