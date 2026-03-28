import { useState, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, Legend } from "recharts";
import NetworkGraph from "./NetworkGraph";
import { getResults, askAnalyst, type AggregatedResults } from "@/lib/api";

// ── Fallback mock data (shown when API is offline) ─────────────────────────
const MOCK_RESULTS: AggregatedResults = {
  simulations_complete: 50,
  outcome_distribution: {
    "United Airlines": { count: 22, pct: 44 },
    "Delta Air Lines":  { count: 14, pct: 28 },
    "Deadlock":         { count: 9,  pct: 18 },
    "British Airways":  { count: 5,  pct: 10 },
  },
  actor_outcome_distribution: {
    united:          { runs: 50, wins: 22, win_rate: 44,  avg_payoff:  6.2 },
    delta:           { runs: 50, wins: 14, win_rate: 28,  avg_payoff: -3.1 },
    british_airways: { runs: 50, wins:  5, win_rate: 10,  avg_payoff:  1.4 },
    lufthansa:       { runs: 50, wins:  6, win_rate: 12,  avg_payoff:  3.8 },
    air_france:      { runs: 50, wins:  3, win_rate:  6,  avg_payoff: -1.9 },
  },
  game_theory_stats: {
    nash_equilibrium_reached_pct:      18,
    pareto_optimal_pct:                72,
    irrational_disruption_pct:         42,
    web_search_changed_decision_pct:   56,
    dominant_strategy_used_pct:        34,
  },
  actor_payoff_averages: {
    united: 6.2, delta: -3.1, british_airways: 1.4, lufthansa: 3.8, air_france: -1.9,
  },
  actor_round_payoffs: {
    "United Airlines":  { R1: 3.1, R2: 1.8, R3: 2.4 },
    "Delta Air Lines":  { R1: -1.2, R2: -0.8, R3: -1.1 },
    "British Airways":  { R1: 0.5, R2: 0.9, R3: 0.3 },
    "Lufthansa":        { R1: 1.2, R2: 1.9, R3: 0.7 },
    "Air France":       { R1: -0.8, R2: -0.5, R3: -0.6 },
  },
  top_winning_conditions: {
    "United Airlines": "Secured dominant market share through aggressive slot bidding and strategic alliance formation",
  },
};

const MOCK_ANSWER = `Actor B loses in 81% of runs when Actor A adopts a mixed strategy past round 3. In 34% of those cases, Actor B triggers a web search at round 5 — temporarily resetting their loss threshold — but not enough to shift the outcome. Recommend sustained pressure after round 4.`;

const REAL_ACTORS = [
  { name: "OpenAI",        type: "AI Lab"    },
  { name: "Elon Musk",     type: "Executive" },
  { name: "EU Commission", type: "Regulator" },
  { name: "SoftBank",      type: "Investor"  },
  { name: "Apple",         type: "Big Tech"  },
];

const CHART_COLORS = ["#7c3aed", "#3b82f6", "#f97316", "#10b981", "#94a3b8", "#f43f5e"];

// ── Variance cards (Henry) ─────────────────────────────────────────────────
const VARIANCE_CARDS = [
  { title: "Payoff Variance",  desc: "Actor payoff drift over runs",    startLabel: "Start", startVal: "+15K", endLabel: "End",      endVal: "-15K",   color: "text-info"    },
  { title: "Strategy Shift",   desc: "Rate variance from baseline",     startLabel: "Base",  startVal: "50%",  endLabel: "Current",  endVal: "+60.5%", color: "text-warning" },
  { title: "Outcome Drift",    desc: "System variance tracking",        startLabel: "Peak",  startVal: "+5%",  endLabel: "Low",      endVal: "-15%",   color: "text-danger"  },
];

const OUTCOME_COLORS = ["bg-violet", "bg-warning", "bg-info", "bg-muted-foreground", "bg-success"];

interface Props {
  totalRuns: number;
  onReset: () => void;
}

const ResultsView = ({ totalRuns, onReset }: Props) => {
  const [results, setResults]     = useState<AggregatedResults | null>(null);
  const [question, setQuestion]   = useState("");
  const [answer, setAnswer]       = useState<string | null>(null);
  const [askLoading, setAskLoading] = useState(false);
  const [apiOnline, setApiOnline] = useState(true);

  useEffect(() => {
    getResults()
      .then((r) => { setResults(r); setApiOnline(true); })
      .catch(() => { setResults(MOCK_RESULTS); setApiOnline(false); });
  }, []);

  const data = results ?? MOCK_RESULTS;

  const outcomeRows = Object.entries(data.outcome_distribution)
    .sort((a, b) => b[1].count - a[1].count);
  const maxCount = Math.max(...outcomeRows.map(([, v]) => v.count), 1);

  const actorRows = Object.entries(data.actor_outcome_distribution ?? {}).map(([id, v]) => ({
    id,
    avgPayoff: data.actor_payoff_averages?.[id] ?? v.avg_payoff,
    winRate:   v.win_rate,
    searches:  Math.round((data.game_theory_stats.web_search_changed_decision_pct / 100) * v.runs),
  }));

  const gt = data.game_theory_stats;

  // Build chart data from real actor_round_payoffs
  const actorNames = Object.keys(data.actor_round_payoffs ?? {});
  const allRounds = actorNames.length > 0
    ? Object.keys(data.actor_round_payoffs[actorNames[0]])
    : ["R1", "R2", "R3"];
  const activityData = allRounds.map((r) => {
    const row: Record<string, string | number> = { round: r };
    actorNames.forEach((name) => { row[name] = data.actor_round_payoffs[name]?.[r] ?? 0; });
    return row;
  });

  // Top winner and their reason
  const topWinner = outcomeRows[0]?.[0] ?? null;
  const topWinnerCondition = topWinner ? data.top_winning_conditions?.[topWinner] : null;

  const handleAsk = async () => {
    if (!question.trim()) return;
    setAskLoading(true);
    try {
      const resp = await askAnalyst(question);
      setAnswer(resp.answer);
    } catch {
      setAnswer(MOCK_ANSWER);
    } finally {
      setAskLoading(false);
    }
  };

  return (
    <div className="relative z-10 max-w-[1100px] mx-auto px-4 md:px-6 pt-24 pb-12 space-y-8 opacity-0 animate-fade-in" style={{ animationFillMode: "forwards" }}>
      {!apiOnline && (
        <div className="glass-card p-3 border border-warning/40">
          <p className="text-xs text-warning">API offline — showing demo data.</p>
        </div>
      )}

      {/* ── Outcome distribution ── */}
      <section>
        <h2 className="text-2xl font-bold mb-2">Simulation Complete — {data.simulations_complete || totalRuns} Runs</h2>
        {topWinner && (
          <div className="glass-card p-4 mb-6 border-l-2 border-l-violet">
            <p className="text-sm font-semibold text-violet mb-1">
              Most likely outcome: <span className="text-foreground">{topWinner}</span> wins ({outcomeRows[0]?.[1].pct}% of runs)
            </p>
            {topWinnerCondition && (
              <p className="text-xs text-muted-foreground leading-relaxed">{topWinnerCondition}</p>
            )}
          </div>
        )}
        <div className="glass-card p-6 space-y-4">
          {outcomeRows.map(([label, val], i) => (
            <div key={label} className="flex items-center gap-4">
              <span className="text-sm text-muted-foreground w-56 shrink-0 text-right">{label}</span>
              <div className="flex-1 bg-white/5 rounded-full h-7 overflow-hidden">
                <div
                  className={`${OUTCOME_COLORS[i % OUTCOME_COLORS.length]} h-full rounded-full flex items-center justify-end pr-3 transition-all duration-700`}
                  style={{ width: `${(val.count / maxCount) * 100}%` }}
                >
                  <span className="text-xs font-bold text-foreground">{val.count}</span>
                </div>
              </div>
              <span className="text-xs text-muted-foreground w-10 shrink-0">{val.pct}%</span>
            </div>
          ))}
        </div>
      </section>

      {/* ── Game-theory stats ── */}
      <section>
        <h2 className="text-xl font-bold mb-4">Game Theory Stats</h2>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {[
            { label: "Nash Equilibrium",       value: `${gt.nash_equilibrium_reached_pct}%`    },
            { label: "Pareto Optimal",          value: `${gt.pareto_optimal_pct}%`              },
            { label: "Irrational Disruptions",  value: `${gt.irrational_disruption_pct}%`       },
            { label: "Web Search Swings",       value: `${gt.web_search_changed_decision_pct}%` },
          ].map((s) => (
            <div key={s.label} className="glass-card p-4 text-center">
              <p className="text-2xl font-bold text-violet">{s.value}</p>
              <p className="text-xs text-muted-foreground mt-1">{s.label}</p>
            </div>
          ))}
        </div>
      </section>

      {/* ── Actor activity line chart (Henry) ── */}
      <section>
        <h2 className="text-xl font-bold mb-4">Actor Activity Over Rounds</h2>
        <div className="glass-card p-6">
          <ResponsiveContainer width="100%" height={300}>
            <LineChart data={activityData}>
              <XAxis dataKey="round" tick={{ fontSize: 11, fill: "hsl(215 20% 65%)" }} axisLine={{ stroke: "rgba(255,255,255,0.1)" }} tickLine={false} />
              <YAxis tick={{ fontSize: 11, fill: "hsl(215 20% 65%)" }} axisLine={false} tickLine={false} />
              <Tooltip contentStyle={{ background: "rgba(10,13,20,0.95)", border: "1px solid rgba(255,255,255,0.1)", borderRadius: 8, fontSize: 12 }} labelStyle={{ color: "white" }} />
              <Legend wrapperStyle={{ fontSize: 12 }} />
              {actorNames.map((name, i) => (
                <Line key={name} type="monotone" dataKey={name} stroke={CHART_COLORS[i % CHART_COLORS.length]} strokeWidth={2.5} dot={{ r: 0 }} activeDot={{ r: 4 }} />
              ))}
            </LineChart>
          </ResponsiveContainer>
        </div>
      </section>

      {/* ── Actor relationship network (Henry) ── */}
      <section>
        <h2 className="text-xl font-bold mb-4">Actor Relationship Network</h2>
        <div className="glass-card p-6">
          <NetworkGraph />
        </div>
      </section>

      {/* ── Variance analysis cards (Henry) ── */}
      <section>
        <h2 className="text-xl font-bold mb-4">Variance Analysis</h2>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          {VARIANCE_CARDS.map((card) => (
            <div key={card.title} className="glass-card p-5">
              <h3 className="font-semibold text-sm mb-0.5">{card.title}</h3>
              <p className="text-xs text-muted-foreground mb-4">{card.desc}</p>
              <div className="flex items-end justify-between">
                <div className="text-center">
                  <p className={`text-lg font-bold font-mono-ticker ${card.color}`}>{card.startVal}</p>
                  <p className="text-[10px] text-muted-foreground">{card.startLabel}</p>
                </div>
                <svg viewBox="0 0 60 24" className={`w-16 h-8 ${card.color}`} fill="none" stroke="currentColor" strokeWidth={1.5}>
                  <path d="M2 18 C10 14, 15 8, 22 12 S35 4, 42 10 S52 6, 58 8" />
                </svg>
                <div className="text-center">
                  <p className={`text-lg font-bold font-mono-ticker ${card.color}`}>{card.endVal}</p>
                  <p className="text-[10px] text-muted-foreground">{card.endLabel}</p>
                </div>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* ── Actor performance table ── */}
      {actorRows.length > 0 && (
        <section>
          <h2 className="text-xl font-bold mb-4">Actor Performance</h2>
          <div className="glass-card overflow-hidden">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-white/10">
                  <th className="text-left  py-3 px-5 text-muted-foreground font-medium">Actor</th>
                  <th className="text-right py-3 px-5 text-muted-foreground font-medium">Avg Payoff</th>
                  <th className="text-right py-3 px-5 text-muted-foreground font-medium">Win Rate</th>
                  <th className="text-right py-3 px-5 text-muted-foreground font-medium">Web Searches</th>
                </tr>
              </thead>
              <tbody>
                {actorRows.map((row) => (
                  <tr key={row.id} className="border-b border-white/5 hover:bg-white/[0.03] transition-colors">
                    <td className="py-3 px-5 font-medium capitalize">{row.id.replace(/_/g, " ")}</td>
                    <td className={`py-3 px-5 text-right font-mono-ticker font-medium ${row.avgPayoff >= 0 ? "text-success" : "text-danger"}`}>
                      {row.avgPayoff >= 0 ? "+" : ""}{row.avgPayoff.toFixed(1)}
                    </td>
                    <td className="py-3 px-5 text-right">{row.winRate.toFixed(1)}%</td>
                    <td className="py-3 px-5 text-right">{row.searches}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}

      {/* ── Analyst Q&A ── */}
      <section>
        <h2 className="text-xl font-bold mb-1">Ask Parallax</h2>
        <p className="text-sm text-muted-foreground mb-4">Grounded in {data.simulations_complete || totalRuns} parallel simulation runs</p>
        <div className="flex gap-3 mb-5">
          <Input
            placeholder="e.g. How do I make Actor B lose?"
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && handleAsk()}
            className="bg-white/5 border-white/10 text-foreground placeholder:text-muted-foreground"
          />
          <Button onClick={handleAsk} disabled={askLoading} className="shrink-0 px-6 font-semibold bg-violet hover:bg-violet-dark text-white">
            {askLoading ? "Thinking…" : "Ask Parallax →"}
          </Button>
        </div>
        {answer && (
          <div className="glass-card p-5 border-l-2 border-l-violet opacity-0 animate-fade-in-up" style={{ animationFillMode: "forwards" }}>
            <p className="text-sm text-muted-foreground leading-relaxed">{answer}</p>
            <p className="text-xs text-muted-foreground mt-3 opacity-60">Based on {data.simulations_complete || totalRuns} runs · Claude Haiku</p>
          </div>
        )}
      </section>

      {/* ── Real-world actor suggestions ── */}
      <section>
        <h2 className="text-xl font-bold mb-1">Use a real-world actor profile</h2>
        <p className="text-sm text-muted-foreground mb-4">Parallax can load a real company, figure, or institution as an actor — drawing from public decision history.</p>
        <div className="flex gap-4 overflow-x-auto pb-2 scrollbar-thin">
          {REAL_ACTORS.map((a) => (
            <div key={a.name} className="glass-card-hover p-4 min-w-[160px] text-center shrink-0">
              <div className="w-14 h-14 rounded-full bg-violet/20 mx-auto mb-3 flex items-center justify-center text-lg">{a.name[0]}</div>
              <p className="font-semibold text-sm">{a.name}</p>
              <p className="text-xs text-muted-foreground mb-3">{a.type}</p>
              <Button variant="ghost" size="sm" className="text-xs text-violet hover:text-violet-light">Load as Actor →</Button>
            </div>
          ))}
        </div>
      </section>

      <div className="flex justify-end pt-4 pb-8">
        <Button onClick={onReset} className="bg-violet hover:bg-violet-dark text-white font-semibold">New Simulation →</Button>
      </div>
    </div>
  );
};

export default ResultsView;
