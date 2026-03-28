import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

const OUTCOMES = [
  { label: "Cooperative agreement reached", count: 22, color: "bg-success" },
  { label: "Actor B withdrew", count: 14, color: "bg-warning" },
  { label: "Deadlock — no deal", count: 9, color: "bg-danger" },
  { label: "Actor A dominant exit", count: 5, color: "bg-violet" },
];

const TABLE_DATA = [
  { actor: "MegaCorp Inc", avgPayoff: "+6.2", winRate: "44%", lossRate: "28%", searches: 12 },
  { actor: "NovaBio", avgPayoff: "-3.1", winRate: "18%", lossRate: "54%", searches: 31 },
  { actor: "Helix Partners", avgPayoff: "+8.7", winRate: "52%", lossRate: "16%", searches: 4 },
];

const MOCK_ANSWER = `Actor B loses in 81% of runs when Actor A adopts a mixed strategy past round 3. In 34% of those cases, Actor B triggers a web search at round 5 — temporarily resetting their loss threshold — but not enough to shift the outcome. Recommend sustained pressure after round 4.`;

const REAL_ACTORS = [
  { name: "OpenAI", type: "AI Lab" },
  { name: "Elon Musk", type: "Executive" },
  { name: "EU Commission", type: "Regulator" },
  { name: "SoftBank", type: "Investor" },
  { name: "Apple", type: "Big Tech" },
];

interface Props {
  totalRuns: number;
  onReset: () => void;
}

const ResultsView = ({ totalRuns, onReset }: Props) => {
  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState(MOCK_ANSWER);
  const maxCount = Math.max(...OUTCOMES.map((o) => o.count));

  return (
    <div className="relative z-10 max-w-[1100px] mx-auto px-4 md:px-6 pt-24 pb-12 space-y-8 opacity-0 animate-fade-in" style={{ animationFillMode: "forwards" }}>
      {/* Outcomes */}
      <section>
        <h2 className="text-2xl font-bold mb-6">Simulation Complete — {totalRuns} Runs</h2>
        <div className="glass-card p-6 space-y-4">
          {OUTCOMES.map((o) => (
            <div key={o.label} className="flex items-center gap-4">
              <span className="text-sm text-muted-foreground w-56 shrink-0 text-right">{o.label}</span>
              <div className="flex-1 bg-white/5 rounded-full h-7 overflow-hidden">
                <div className={`${o.color} h-full rounded-full flex items-center justify-end pr-3 transition-all duration-700`} style={{ width: `${(o.count / maxCount) * 100}%` }}>
                  <span className="text-xs font-bold text-foreground">{o.count}</span>
                </div>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* Table */}
      <section>
        <h2 className="text-xl font-bold mb-4">Actor Performance</h2>
        <div className="glass-card overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-white/10">
                <th className="text-left py-3 px-5 text-muted-foreground font-medium">Actor</th>
                <th className="text-right py-3 px-5 text-muted-foreground font-medium">Avg Payoff</th>
                <th className="text-right py-3 px-5 text-muted-foreground font-medium">Win Rate</th>
                <th className="text-right py-3 px-5 text-muted-foreground font-medium">Loss Rate</th>
                <th className="text-right py-3 px-5 text-muted-foreground font-medium">Web Searches</th>
              </tr>
            </thead>
            <tbody>
              {TABLE_DATA.map((row) => (
                <tr key={row.actor} className="border-b border-white/5 hover:bg-white/[0.03] transition-colors">
                  <td className="py-3 px-5 font-medium">{row.actor}</td>
                  <td className={`py-3 px-5 text-right font-mono-ticker font-medium ${row.avgPayoff.startsWith("+") ? "text-success" : "text-danger"}`}>{row.avgPayoff}</td>
                  <td className="py-3 px-5 text-right">{row.winRate}</td>
                  <td className="py-3 px-5 text-right">{row.lossRate}</td>
                  <td className="py-3 px-5 text-right">{row.searches}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      {/* Analyst Q&A */}
      <section>
        <h2 className="text-xl font-bold mb-1">Ask Parallax</h2>
        <p className="text-sm text-muted-foreground mb-4">Grounded in {totalRuns} parallel simulation runs</p>
        <div className="flex gap-3 mb-5">
          <Input
            placeholder="e.g. How do I make Actor B lose?"
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && setAnswer(MOCK_ANSWER)}
            className="bg-white/5 border-white/10 text-foreground placeholder:text-muted-foreground"
          />
          <Button onClick={() => setAnswer(MOCK_ANSWER)} className="shrink-0 px-6 font-semibold bg-violet hover:bg-violet-dark text-white">
            Ask Parallax →
          </Button>
        </div>
        {answer && (
          <div className="glass-card p-5 border-l-2 border-l-violet opacity-0 animate-fade-in-up" style={{ animationFillMode: "forwards" }}>
            <p className="text-sm text-muted-foreground leading-relaxed">{answer}</p>
            <p className="text-xs text-muted-foreground mt-3 opacity-60">Based on {totalRuns} simulation runs · NVIDIA Nemotron</p>
          </div>
        )}
      </section>

      {/* Real-world actors */}
      <section>
        <h2 className="text-xl font-bold mb-1">Use a real-world actor profile</h2>
        <p className="text-sm text-muted-foreground mb-4">Parallax can load a real company, figure, or institution as an actor — drawing from public decision history.</p>
        <div className="flex gap-4 overflow-x-auto pb-2 scrollbar-thin">
          {REAL_ACTORS.map((a) => (
            <div key={a.name} className="glass-card-hover p-4 min-w-[160px] text-center shrink-0">
              <div className="w-14 h-14 rounded-full bg-violet/20 mx-auto mb-3 flex items-center justify-center text-lg">
                {a.name[0]}
              </div>
              <p className="font-semibold text-sm">{a.name}</p>
              <p className="text-xs text-muted-foreground mb-3">{a.type}</p>
              <Button variant="ghost" size="sm" className="text-xs text-violet hover:text-violet-light">Load as Actor →</Button>
            </div>
          ))}
        </div>
      </section>

      <div className="flex justify-end pt-4 pb-8">
        <Button onClick={onReset} className="bg-violet hover:bg-violet-dark text-white font-semibold">
          New Simulation →
        </Button>
      </div>
    </div>
  );
};

export default ResultsView;
