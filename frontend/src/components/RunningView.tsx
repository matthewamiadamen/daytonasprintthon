import { useState, useEffect, useRef } from "react";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer } from "recharts";
import { getStatus, type PipelineStatus } from "@/lib/api";

interface TickerEntry {
  sandbox: number;
  round: number;
  actor: string;
  action: string;
  payoff: number;
  webSearch: boolean;
}

const DEMO_ENTRIES: TickerEntry[] = [
  { sandbox: 3,  round: 1, actor: "United Airlines",  action: "form_alliance_block",   payoff: 5,   webSearch: false },
  { sandbox: 7,  round: 2, actor: "Delta Air Lines",  action: "undercut_pricing",      payoff: -8,  webSearch: true  },
  { sandbox: 12, round: 1, actor: "British Airways",  action: "hold_position",         payoff: 3,   webSearch: false },
  { sandbox: 3,  round: 2, actor: "Lufthansa",        action: "escalate_slot_bid",     payoff: -4,  webSearch: false },
  { sandbox: 18, round: 3, actor: "Air France",       action: "signal_walkaway",       payoff: -12, webSearch: false },
  { sandbox: 7,  round: 3, actor: "United Airlines",  action: "counter_propose",       payoff: 8,   webSearch: true  },
  { sandbox: 22, round: 1, actor: "Delta Air Lines",  action: "accept_terms",          payoff: 11,  webSearch: false },
  { sandbox: 12, round: 4, actor: "Lufthansa",        action: "deploy_mixed_strategy", payoff: -2,  webSearch: false },
];

const EXTRA_ACTIONS = ["withdraw_bid", "raise_offer", "hold_position", "escalate_clause",
  "counter_propose", "request_extension", "accept_terms", "signal_walkaway"];
const ACTOR_NAMES = ["United Airlines", "Delta Air Lines", "British Airways", "Lufthansa", "Air France"];


const rationalityColors = ["pill-rational", "pill-semi", "pill-irrational"];

const genEntry = (totalRuns: number): TickerEntry => ({
  sandbox: Math.floor(Math.random() * totalRuns) + 1,
  round: Math.floor(Math.random() * 4) + 1,
  actor: ACTOR_NAMES[Math.floor(Math.random() * ACTOR_NAMES.length)],
  action: EXTRA_ACTIONS[Math.floor(Math.random() * EXTRA_ACTIONS.length)],
  payoff: Math.floor(Math.random() * 25) - 12,
  webSearch: Math.random() < 0.22,
});

interface Props {
  totalRuns: number;
  onComplete: () => void;
  onCancel?: () => void;
}

const RunningView = ({ totalRuns, onComplete, onCancel }: Props) => {
  const [entries, setEntries] = useState<TickerEntry[]>(DEMO_ENTRIES);
  const [completed, setCompleted] = useState(0);
  const [signalHistory, setSignalHistory] = useState<Array<Record<string, number>>>([]);
  const tickCount = useRef(0);
  const [status, setStatus] = useState<PipelineStatus | null>(null);
  const [apiOnline, setApiOnline] = useState(true);
  const tickerRef = useRef<HTMLDivElement>(null);

  // Poll /api/status every 2 s
  useEffect(() => {
    let alive = true;
    const poll = async () => {
      try {
        const s = await getStatus();
        if (!alive) return;
        setStatus(s);
        setApiOnline(true);
        setCompleted(s.runs_complete);
      } catch {
        setApiOnline(false);
      }
    };
    poll();
    const id = setInterval(poll, 2000);
    return () => { alive = false; clearInterval(id); };
  }, []);

  // Ticker + signal chart updater
  useEffect(() => {
    const id = setInterval(() => {
      if (!apiOnline) setCompleted((p) => Math.min(p + 1, totalRuns));

      setEntries((prev) => [...prev, genEntry(totalRuns)].slice(-40));

      tickCount.current += 1;
      const tick = tickCount.current;
      setSignalHistory((h) => {
        const last = h[h.length - 1] ?? { t: 0, Cooperative: 1, "B withdrew": 0.5, Deadlock: 0.3, "A dominant": 0.2 };
        return [...h, {
          t: tick,
          Cooperative:  Math.max(0, +(last.Cooperative  + Math.random() * 0.9 + 0.1).toFixed(1)),
          "B withdrew": Math.max(0, +(last["B withdrew"] + Math.random() * 0.6 + 0.05).toFixed(1)),
          Deadlock:     Math.max(0, +(last.Deadlock      + Math.random() * 0.5 + 0.03).toFixed(1)),
          "A dominant": Math.max(0, +(last["A dominant"] + Math.random() * 0.35 + 0.02).toFixed(1)),
        }].slice(-30);
      });
    }, 1200);
    return () => clearInterval(id);
  }, [apiOnline, totalRuns]);

  useEffect(() => {
    if (tickerRef.current) tickerRef.current.scrollTop = tickerRef.current.scrollHeight;
  }, [entries.length]);

  const displayCompleted = apiOnline ? (status?.runs_complete ?? completed) : completed;
  const isComplete = apiOnline
    ? (status ? !status.simulation_running && status.runs_in_disk >= totalRuns : false)
    : displayCompleted >= totalRuns;
  const remaining = Math.max(0, Math.round((totalRuns - displayCompleted) * 2.2));

  return (
    <div className="relative z-10 pt-24 pb-8 px-4 max-w-[1400px] mx-auto opacity-0 animate-fade-in" style={{ animationFillMode: "forwards" }}>
      {/* Status bar */}
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-3">
          <span className={`w-2 h-2 rounded-full ${apiOnline ? "bg-violet animate-pulse-dot" : "bg-warning"}`} />
          <span className="text-sm font-medium">
            {apiOnline ? "⚡ Parallax is running your simulation…" : "⚡ Demo mode (API offline)"}
          </span>
        </div>
        {onCancel && (
          <Button
            onClick={onCancel}
            variant="outline"
            size="sm"
            className="border-destructive/30 text-destructive hover:bg-destructive/10 hover:text-destructive"
          >
            Cancel Prediction
          </Button>
        )}
      </div>

      <div className="glass-card p-4 mb-6 space-y-2">
        <div className="flex justify-between text-sm">
          <span>Sandboxes complete: {displayCompleted} / {totalRuns}</span>
          <span className="text-muted-foreground">
            {isComplete ? "Done" : `~${remaining}s remaining`}
          </span>
        </div>
        <Progress value={(displayCompleted / Math.max(totalRuns, 1)) * 100} className="h-2 bg-white/5 [&>div]:bg-violet" />
        {status?.error && <p className="text-xs text-danger pt-1">{status.error}</p>}
        {isComplete && (
          <div className="flex justify-end pt-1">
            <Button onClick={onComplete} className="bg-violet hover:bg-violet-dark text-white font-semibold">
              View Results →
            </Button>
          </div>
        )}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-[280px_1fr_280px] gap-6">
        {/* Actors */}
        <div className="space-y-4">
          <h2 className="text-lg font-bold">Actors</h2>
          {ACTOR_NAMES.map((name, i) => (
            <div key={name} className="glass-card p-4 opacity-0 animate-fade-in-up" style={{ animationDelay: `${i * 200}ms`, animationFillMode: "forwards" }}>
              <div className="w-16 h-16 rounded-full bg-violet/20 mx-auto mb-3 flex items-center justify-center text-lg font-bold text-violet/70">
                {name.split(" ").map((w) => w[0]).join("").slice(0, 2)}
              </div>
              <h3 className="font-bold text-sm text-center">{name}</h3>
              <div className="flex justify-center mt-2">
                <span className={rationalityColors[i % 3]}>
                  {["Fully Rational", "Semi-Rational", "Irrational"][i % 3]}
                </span>
              </div>
              <p className="text-[10px] text-muted-foreground italic text-center mt-2">Rationality derived from dossier</p>
            </div>
          ))}
        </div>

        {/* Live ticker */}
        <div className="glass-card p-5 flex flex-col" style={{ height: "calc(100vh - 260px)", minHeight: "500px" }}>
          <div className="flex items-center gap-2 mb-4">
            <h2 className="text-lg font-bold">Live Decisions</h2>
            <span className="w-2 h-2 rounded-full bg-success animate-pulse-dot" />
          </div>
          <div ref={tickerRef} className="flex-1 overflow-y-auto scrollbar-thin space-y-1.5">
            {entries.map((entry, i) => (
              <div key={i} className="font-mono-ticker text-xs py-2 px-3 rounded-md bg-white/[0.03] flex items-center gap-2 flex-wrap opacity-0 animate-slide-up" style={{ animationDelay: `${Math.min(i * 30, 200)}ms`, animationFillMode: "forwards" }}>
                <span className="pill-info text-[10px] shrink-0">Sandbox #{entry.sandbox}</span>
                <span className="text-muted-foreground shrink-0">Round {entry.round}</span>
                <span className="font-semibold shrink-0">{entry.actor}</span>
                <span className="text-muted-foreground">→</span>
                <span className="text-muted-foreground">{entry.action}</span>
                <span className={`font-semibold shrink-0 ml-auto ${entry.payoff >= 0 ? "text-success" : "text-danger"}`}>
                  {entry.payoff >= 0 ? "+" : ""}{entry.payoff}
                </span>
                {entry.webSearch && <span className="pill-semi text-[10px] shrink-0">🔍 Web Search</span>}
              </div>
            ))}
          </div>
        </div>

        {/* Early signals — live line chart (Henry's feature) */}
        <div className="space-y-4">
          <h2 className="text-lg font-bold">Early Signals</h2>
          <div className="glass-card p-4">
            {signalHistory.length > 2 ? (
              <ResponsiveContainer width="100%" height={220}>
                <LineChart data={signalHistory}>
                  <XAxis dataKey="t" hide />
                  <YAxis tick={{ fontSize: 10, fill: "hsl(215 20% 65%)" }} axisLine={false} tickLine={false} width={24} />
                  <Tooltip
                    contentStyle={{ background: "rgba(10,13,20,0.95)", border: "1px solid rgba(255,255,255,0.1)", borderRadius: 8, fontSize: 12 }}
                    labelStyle={{ color: "white" }}
                  />
                  <Line type="monotone" dataKey="Cooperative" stroke="#7c3aed" strokeWidth={2} dot={false} />
                  <Line type="monotone" dataKey="B withdrew"  stroke="#f97316" strokeWidth={2} dot={false} />
                  <Line type="monotone" dataKey="Deadlock"    stroke="#3b82f6" strokeWidth={2} dot={false} />
                  <Line type="monotone" dataKey="A dominant"  stroke="#94a3b8" strokeWidth={2} dot={false} />
                </LineChart>
              </ResponsiveContainer>
            ) : (
              <div className="h-[220px] flex items-center justify-center">
                <p className="text-xs text-muted-foreground italic">Collecting data…</p>
              </div>
            )}
          </div>
          <div className="glass-card p-4">
            <p className="text-xs text-muted-foreground italic">
              {apiOnline ? "Analyst warming up…" : "Results ready when runs complete."}
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default RunningView;
