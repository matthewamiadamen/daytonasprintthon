import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Input } from "@/components/ui/input";

interface Props {
  initialScenario?: string;
  onLaunch: (scenario: string, actors: number, runs: number) => void;
}

const MODELS = ["NVIDIA Nemotron (Recommended) ✦", "Claude 3.5 Sonnet", "GPT-4o", "Llama 3 (Groq)"];

const SetupView = ({ initialScenario = "", onLaunch }: Props) => {
  const [scenario, setScenario] = useState(initialScenario);
  const [actors, setActors] = useState(3);
  const [runs, setRuns] = useState(50);
  const [model, setModel] = useState(MODELS[0]);
  const [showGithub, setShowGithub] = useState(false);

  return (
    <div className="relative z-10 pt-24 pb-12 px-4 max-w-7xl mx-auto opacity-0 animate-fade-in" style={{ animationFillMode: "forwards" }}>
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        {/* Left — Input */}
        <div className="space-y-5">
          <h2 className="text-2xl font-bold">Configure Your Simulation</h2>

          <Textarea
            placeholder="Describe the scenario, actors, and stakes. Be as specific as you like..."
            value={scenario}
            onChange={(e) => setScenario(e.target.value)}
            className="min-h-[140px] bg-white/5 border-white/10 text-foreground placeholder:text-muted-foreground resize-none backdrop-blur"
            rows={5}
          />

          {/* Image upload */}
          <div className="glass-card border-dashed border-white/15 p-6 text-center cursor-pointer hover:border-white/25 transition-colors">
            <p className="text-sm text-muted-foreground">📎 Drop a scenario image or context screenshot</p>
          </div>

          {/* Model */}
          <div>
            <label className="text-sm text-muted-foreground mb-1.5 block">Select Model</label>
            <select
              value={model}
              onChange={(e) => setModel(e.target.value)}
              className="w-full rounded-lg bg-white/5 border border-white/10 px-3 py-2.5 text-sm text-foreground backdrop-blur outline-none focus:ring-2 focus:ring-violet/50"
            >
              {MODELS.map((m) => <option key={m} value={m} className="bg-[#0a0d14]">{m}</option>)}
            </select>
          </div>

          {/* Number inputs */}
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="text-sm text-muted-foreground mb-1.5 block">Number of Actors</label>
              <Input
                type="number" min={2} max={6} value={actors}
                onChange={(e) => setActors(Math.min(6, Math.max(2, Number(e.target.value))))}
                className="bg-white/5 border-white/10 text-foreground"
              />
            </div>
            <div>
              <label className="text-sm text-muted-foreground mb-1.5 block">Simulation Runs</label>
              <Input
                type="number" min={1} max={50} value={runs}
                onChange={(e) => setRuns(Math.min(50, Math.max(1, Number(e.target.value))))}
                className="bg-white/5 border-white/10 text-foreground"
              />
            </div>
          </div>

          {/* GitHub import */}
          <Button variant="outline" className="border-white/10 text-foreground hover:bg-white/5 w-full" onClick={() => setShowGithub(!showGithub)}>
            <svg className="w-4 h-4 mr-2" fill="currentColor" viewBox="0 0 24 24"><path d="M12 0c-6.626 0-12 5.373-12 12 0 5.302 3.438 9.8 8.207 11.387.599.111.793-.261.793-.577v-2.234c-3.338.726-4.033-1.416-4.033-1.416-.546-1.387-1.333-1.756-1.333-1.756-1.089-.745.083-.729.083-.729 1.205.084 1.839 1.237 1.839 1.237 1.07 1.834 2.807 1.304 3.492.997.107-.775.418-1.305.762-1.604-2.665-.305-5.467-1.334-5.467-5.931 0-1.311.469-2.381 1.236-3.221-.124-.303-.535-1.524.117-3.176 0 0 1.008-.322 3.301 1.23A11.509 11.509 0 0112 5.803c1.02.005 2.047.138 3.006.404 2.291-1.552 3.297-1.23 3.297-1.23.653 1.653.242 2.874.118 3.176.77.84 1.235 1.911 1.235 3.221 0 4.609-2.807 5.624-5.479 5.921.43.372.823 1.102.823 2.222v3.293c0 .319.192.694.801.576C20.566 21.797 24 17.3 24 12c0-6.627-5.373-12-12-12z"/></svg>
            Import from GitHub
          </Button>

          {showGithub && (
            <div className="glass-card p-4 space-y-3 opacity-0 animate-fade-in" style={{ animationFillMode: "forwards" }}>
              <p className="text-xs text-muted-foreground">Load scenario config or actor dossiers from a GitHub repository.</p>
              <Input placeholder="https://github.com/user/repo" className="bg-white/5 border-white/10 text-foreground" />
              <Button size="sm" className="bg-violet hover:bg-violet-dark text-white">Load</Button>
            </div>
          )}

          {/* Suggestion */}
          <div className="glass-card p-4">
            <p className="text-xs font-semibold text-muted-foreground mb-1">💡 Parallax Suggests:</p>
            <p className="text-sm text-muted-foreground leading-relaxed">
              A biotech licensing standoff between two well-funded startups and one cash-strapped pioneer makes for asymmetric tension — ideal for game theory. Try 3 actors, 50 runs.
            </p>
          </div>

          <Button
            onClick={() => onLaunch(scenario, actors, runs)}
            className="w-full bg-violet hover:bg-violet-dark text-white font-semibold py-6 text-base glow-violet-sm"
            size="lg"
          >
            ⚡ Predict Now
          </Button>
        </div>

        {/* Right — Preview */}
        <div className="space-y-5">
          <h2 className="text-2xl font-bold">Scenario Preview</h2>
          <div className="glass-card aspect-[4/3] flex items-center justify-center overflow-hidden">
            <div className="text-center p-8">
              <div className="w-20 h-20 rounded-full bg-violet/20 flex items-center justify-center mx-auto mb-4">
                <span className="text-3xl">🎬</span>
              </div>
              <p className="text-sm text-muted-foreground">AI-Generated Scene</p>
              <p className="text-xs text-muted-foreground mt-1">Preview renders after input</p>
            </div>
          </div>
          {/* Actor preview pills */}
          <div className="flex flex-wrap gap-2">
            <span className="pill-rational">Actor A · Rational</span>
            <span className="pill-semi">Actor B · Semi-Rational</span>
            <span className="pill-irrational">Actor C · Irrational</span>
          </div>
        </div>
      </div>
    </div>
  );
};

export default SetupView;
