import { useState, useEffect, useRef } from "react";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";

interface Actor {
  name: string;
  type: string;
  rationality: "rational" | "semi" | "irrational";
  decisions: string[];
  sparseData?: boolean;
}

interface TickerEntry {
  sandbox: number;
  round: number;
  actor: string;
  action: string;
  payoff: number;
  webSearch: boolean;
}

const ACTORS: Actor[] = [
  { name: "MegaCorp Inc", type: "Fortune 500 Corporation", rationality: "semi", decisions: ["Delayed Series A term sheet by 3 weeks", "Acquired competing patent portfolio", "Lobbied for regulatory change in Q2"] },
  { name: "NovaBio", type: "Early-stage Biotech Startup", rationality: "irrational", decisions: ["Rejected $40M licensing offer", "Pivoted platform mid-negotiation"], sparseData: true },
  { name: "Helix Partners", type: "Mid-size PE-backed Firm", rationality: "rational", decisions: ["Structured earn-out deal at 2.1x", "Leveraged data room access strategically", "Maintained BATNA throughout process"] },
];

const ACTIONS = ["withdraw_bid", "raise_offer", "hold_position", "escalate_clause", "counter_propose", "request_extension", "accept_terms", "file_dispute", "signal_walkaway", "deploy_mixed_strategy"];

const rationalityLabel = { rational: "Fully Rational", semi: "Semi-Rational", irrational: "Irrational" };
const rationalityClass = { rational: "pill-rational", semi: "pill-semi", irrational: "pill-irrational" };

const generateEntry = (): TickerEntry => ({
  sandbox: Math.floor(Math.random() * 50) + 1,
  round: Math.floor(Math.random() * 6) + 1,
  actor: ACTORS[Math.floor(Math.random() * ACTORS.length)].name,
  action: ACTIONS[Math.floor(Math.random() * ACTIONS.length)],
  payoff: Math.floor(Math.random() * 25) - 12,
  webSearch: Math.random() < 0.22,
});

const INITIAL_ENTRIES: TickerEntry[] = [
  { sandbox: 3, round: 1, actor: "MegaCorp Inc", action: "raise_offer", payoff: 5, webSearch: false },
  { sandbox: 7, round: 2, actor: "NovaBio", action: "withdraw_bid", payoff: -8, webSearch: true },
  { sandbox: 12, round: 1, actor: "Helix Partners", action: "hold_position", payoff: 3, webSearch: false },
  { sandbox: 3, round: 2, actor: "MegaCorp Inc", action: "escalate_clause", payoff: -4, webSearch: false },
  { sandbox: 18, round: 3, actor: "NovaBio", action: "signal_walkaway", payoff: -12, webSearch: false },
  { sandbox: 7, round: 3, actor: "Helix Partners", action: "counter_propose", payoff: 8, webSearch: true },
  { sandbox: 22, round: 1, actor: "MegaCorp Inc", action: "accept_terms", payoff: 11, webSearch: false },
  { sandbox: 12, round: 4, actor: "NovaBio", action: "deploy_mixed_strategy", payoff: -2, webSearch: false },
  { sandbox: 31, round: 2, actor: "Helix Partners", action: "raise_offer", payoff: 6, webSearch: false },
  { sandbox: 18, round: 4, actor: "MegaCorp Inc", action: "request_extension", payoff: 0, webSearch: true },
  { sandbox: 41, round: 1, actor: "NovaBio", action: "file_dispute", payoff: -6, webSearch: true },
];

const OUTCOMES = [
  { label: "Cooperative", count: 0, max: 22 },
  { label: "Actor B withdrew", count: 0, max: 14 },
  { label: "Deadlock", count: 0, max: 9 },
  { label: "Actor A dominant", count: 0, max: 5 },
];

interface Props {
  totalRuns: number;
  onComplete: () => void;
}

const RunningView = ({ totalRuns, onComplete }: Props) => {
  const [entries, setEntries] = useState<TickerEntry[]>(INITIAL_ENTRIES);
  const [completed, setCompleted] = useState(18);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const tickerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    intervalRef.current = setInterval(() => {
      setEntries((prev) => [...prev, generateEntry()].slice(-40));
      setCompleted((prev) => (prev >= totalRuns ? totalRuns : prev + 1));
    }, 1200);
    return () => { if (intervalRef.current) clearInterval(intervalRef.current); };
  }, [totalRuns]);

  useEffect(() => {
    if (tickerRef.current) tickerRef.current.scrollTop = tickerRef.current.scrollHeight;
  }, [entries.length]);

  const remaining = Math.max(0, Math.round((totalRuns - completed) * 2.2));

  return (
    <div className="relative z-10 pt-24 pb-8 px-4 max-w-[1400px] mx-auto opacity-0 animate-fade-in" style={{ animationFillMode: "forwards" }}>
      {/* Top status */}
      <div className="flex items-center gap-3 mb-2">
        <span className="w-2 h-2 rounded-full bg-violet animate-pulse-dot" />
        <span className="text-sm font-medium">⚡ Parallax is running your simulation...</span>
      </div>
      <div className="glass-card p-4 mb-6 space-y-2">
        <div className="flex justify-between text-sm">
          <span>Sandboxes complete: {completed} / {totalRuns}</span>
          <span className="text-muted-foreground">~{remaining}s remaining</span>
        </div>
        <Progress value={(completed / totalRuns) * 100} className="h-2 bg-white/5 [&>div]:bg-violet" />
        {completed >= totalRuns && (
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
          {ACTORS.map((actor, i) => (
            <div key={actor.name} className="glass-card p-4 opacity-0 animate-fade-in-up" style={{ animationDelay: `${i * 200}ms`, animationFillMode: "forwards" }}>
              {/* Avatar placeholder */}
              <div className="w-16 h-16 rounded-full bg-violet/20 mx-auto mb-3 flex items-center justify-center text-xs text-muted-foreground">AI</div>
              <h3 className="font-bold text-sm text-center">{actor.name}</h3>
              <p className="text-xs text-muted-foreground text-center mb-2">{actor.type}</p>
              <div className="flex justify-center mb-3">
                <span className={rationalityClass[actor.rationality]}>{rationalityLabel[actor.rationality]}</span>
              </div>
              <ul className="space-y-1 mb-2">
                {actor.decisions.map((d, j) => (
                  <li key={j} className="text-xs text-muted-foreground">• {d}</li>
                ))}
              </ul>
              <p className="text-[10px] text-muted-foreground italic">Rationality derived from dossier</p>
              {actor.sparseData && <p className="text-[10px] text-muted-foreground italic opacity-60">Ideology inferred from demographic prior</p>}
            </div>
          ))}
        </div>

        {/* Ticker */}
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

        {/* Right — Early Signals */}
        <div className="space-y-4">
          <h2 className="text-lg font-bold">Early Signals</h2>
          <div className="glass-card p-4 space-y-3">
            {OUTCOMES.map((o) => {
              const frac = Math.min(completed / totalRuns, 1);
              const current = Math.round(o.max * frac);
              return (
                <div key={o.label}>
                  <div className="flex justify-between text-xs mb-1">
                    <span className="text-muted-foreground">{o.label}</span>
                    <span>{current}</span>
                  </div>
                  <div className="h-1.5 bg-white/5 rounded-full overflow-hidden">
                    <div className="h-full bg-violet rounded-full transition-all duration-700" style={{ width: `${(current / (o.max || 1)) * 100}%` }} />
                  </div>
                </div>
              );
            })}
          </div>
          <div className="glass-card p-4">
            <p className="text-xs text-muted-foreground italic">Analyst warming up...</p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default RunningView;
