import { useState, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Input } from "@/components/ui/input";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { getPresets, usePreset, generateScenario, runSimulation, type Preset } from "@/lib/api";

interface Props {
  initialScenario?: string;
  onLaunch: (scenario: string, actors: number, runs: number) => void;
}

const MODELS = ["Claude Haiku (Fast)", "Claude Sonnet", "Claude Opus"];

// Built-in base cases shown even when API is offline
const FALLBACK_PRESETS: Preset[] = [
  {
    id: "airlines",
    label: "Transatlantic Route Competition",
    description: "Five major airlines — United, Delta, British Airways, Lufthansa, and Air France — compete to secure the most profitable transatlantic routes. Alliance formation, slot bidding, and yield-management pricing.",
    actors: ["United Airlines", "Delta Air Lines", "British Airways", "Lufthansa", "Air France"],
    rounds: 6,
  },
  {
    id: "biotech",
    label: "Biotech IP Standoff",
    description: "Two well-funded startups and one cash-strapped pioneer negotiate licensing terms before a critical FDA deadline.",
    actors: ["MegaCorp Inc", "NovaBio", "Helix Partners"],
    rounds: 5,
  },
];

const ACTOR_COLORS = ["bg-success", "bg-warning", "bg-violet", "bg-info", "bg-danger"];

const SetupView = ({ initialScenario = "", onLaunch }: Props) => {
  const [scenario, setScenario] = useState(initialScenario);
  const [actors, setActors] = useState(3);
  const [runs, setRuns] = useState(1);
  const [model, setModel] = useState(MODELS[0]);
  const [presets, setPresets] = useState<Preset[]>(FALLBACK_PRESETS);
  const [selectedPreset, setSelectedPreset] = useState<Preset | null>(FALLBACK_PRESETS[0]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showGithub, setShowGithub] = useState(false);

  useEffect(() => {
    getPresets()
      .then((ps) => { if (ps.length > 0) setPresets(ps); })
      .catch(() => { /* stay with fallback */ });
  }, [initialScenario]);

  const handleLaunch = async (mode: "preset" | "custom") => {
    setError(null);
    setLoading(true);
    try {
      if (mode === "preset" && selectedPreset) {
        await usePreset(selectedPreset.id);
        await runSimulation(runs);
        onLaunch(selectedPreset.label, selectedPreset.actors.length, runs);
      } else {
        if (!scenario.trim()) { setError("Please describe a scenario first."); setLoading(false); return; }
        await generateScenario(scenario, 6);
        await runSimulation(runs);
        onLaunch(scenario, actors, runs);
      }
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : String(e);
      if (msg.includes("Failed to fetch") || msg.includes("NetworkError")) {
        // API offline — proceed to demo mode
        onLaunch(mode === "preset" ? (selectedPreset?.label ?? "Simulation") : scenario, actors, runs);
      } else {
        setError(msg);
        setLoading(false);
      }
    }
  };

  return (
    <div className="relative z-10 pt-24 pb-12 px-4 max-w-3xl mx-auto opacity-0 animate-fade-in" style={{ animationFillMode: "forwards" }}>
      <h2 className="text-2xl font-bold mb-6">Configure Your Simulation</h2>

      <Tabs defaultValue={initialScenario ? "custom" : "base"} className="w-full">
        <TabsList className="w-full mb-6 bg-white/5 border border-white/10">
          <TabsTrigger value="base"   className="flex-1 data-[state=active]:bg-violet data-[state=active]:text-white">Use Base Case</TabsTrigger>
          <TabsTrigger value="custom" className="flex-1 data-[state=active]:bg-violet data-[state=active]:text-white">Custom Scenario</TabsTrigger>
        </TabsList>

        {/* ── Base case tab ── */}
        <TabsContent value="base" className="space-y-5">
          {presets.map((p, i) => (
            <button
              key={p.id}
              onClick={() => setSelectedPreset(p)}
              className={`glass-card w-full text-left p-5 transition-all ${selectedPreset?.id === p.id ? "border border-violet/50 bg-violet/10" : "border border-transparent hover:bg-white/[0.03]"}`}
            >
              <h3 className="font-semibold text-sm mb-1">{p.label}</h3>
              <p className="text-xs text-muted-foreground mb-3">{p.description}</p>
              <div className="flex flex-wrap gap-2">
                {p.actors.map((a, j) => (
                  <span key={a} className="flex items-center gap-1.5 glass-card px-2.5 py-1 text-xs text-muted-foreground">
                    <span className={`w-1.5 h-1.5 rounded-full ${ACTOR_COLORS[(i * p.actors.length + j) % ACTOR_COLORS.length]}`} />
                    {a}
                  </span>
                ))}
              </div>
            </button>
          ))}

          {selectedPreset && (
            <div className="glass-card p-5 opacity-0 animate-fade-in" style={{ animationFillMode: "forwards" }}>
              <h3 className="font-semibold text-sm mb-2">{selectedPreset.label}</h3>
              <div className="space-y-1.5 mb-3">
                {selectedPreset.actors.map((a, i) => (
                  <div key={a} className="flex items-center gap-2">
                    <span className={`w-2 h-2 rounded-full ${ACTOR_COLORS[i % ACTOR_COLORS.length]}`} />
                    <span className="text-sm">{a}</span>
                  </div>
                ))}
              </div>
              <p className="text-xs text-muted-foreground">{selectedPreset.rounds} rounds · Real-world dossiers loaded</p>
            </div>
          )}

          <div>
            <label className="text-sm text-muted-foreground mb-1.5 block">Select Model</label>
            <select value={model} onChange={(e) => setModel(e.target.value)} className="w-full rounded-lg bg-white/5 border border-white/10 px-3 py-2.5 text-sm text-foreground backdrop-blur outline-none focus:ring-2 focus:ring-violet/50">
              {MODELS.map((m) => <option key={m} value={m} className="bg-[#0a0d14]">{m}</option>)}
            </select>
          </div>

          <div>
            <label className="text-sm text-muted-foreground mb-1.5 block">Simulation Runs</label>
            <Input type="number" min={1} max={50} value={runs} onChange={(e) => setRuns(Math.min(50, Math.max(1, Number(e.target.value))))} className="bg-white/5 border-white/10 text-foreground" />
          </div>

          {error && <div className="glass-card p-3 border border-danger/40"><p className="text-xs text-danger">{error}</p></div>}

          <Button onClick={() => handleLaunch("preset")} disabled={loading || !selectedPreset} className="w-full bg-violet hover:bg-violet-dark text-white font-semibold py-6 text-base glow-violet-sm" size="lg">
            {loading ? "Starting…" : "⚡ Predict Now"}
          </Button>
        </TabsContent>

        {/* ── Custom scenario tab ── */}
        <TabsContent value="custom" className="space-y-5">
          <Textarea
            placeholder="Describe the scenario, actors, and stakes. Be as specific as you like — e.g. 'Three biotech startups negotiating a licensing deal with a large pharma company.'"
            value={scenario}
            onChange={(e) => setScenario(e.target.value)}
            className="min-h-[140px] bg-white/5 border-white/10 text-foreground placeholder:text-muted-foreground resize-none backdrop-blur"
            rows={5}
          />

          <div className="glass-card border-dashed border-white/15 p-6 text-center cursor-pointer hover:border-white/25 transition-colors">
            <p className="text-sm text-muted-foreground">📎 Drop a scenario image or context screenshot</p>
          </div>

          <div>
            <label className="text-sm text-muted-foreground mb-1.5 block">Select Model</label>
            <select value={model} onChange={(e) => setModel(e.target.value)} className="w-full rounded-lg bg-white/5 border border-white/10 px-3 py-2.5 text-sm text-foreground backdrop-blur outline-none focus:ring-2 focus:ring-violet/50">
              {MODELS.map((m) => <option key={m} value={m} className="bg-[#0a0d14]">{m}</option>)}
            </select>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="text-sm text-muted-foreground mb-1.5 block">Number of Actors</label>
              <Input type="number" min={2} max={6} value={actors} onChange={(e) => setActors(Math.min(6, Math.max(2, Number(e.target.value))))} className="bg-white/5 border-white/10 text-foreground" />
            </div>
            <div>
              <label className="text-sm text-muted-foreground mb-1.5 block">Simulation Runs</label>
              <Input type="number" min={1} max={50} value={runs} onChange={(e) => setRuns(Math.min(50, Math.max(1, Number(e.target.value))))} className="bg-white/5 border-white/10 text-foreground" />
            </div>
          </div>

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

          <div className="glass-card p-4">
            <p className="text-xs font-semibold text-muted-foreground mb-1">💡 Parallax Suggests:</p>
            <p className="text-sm text-muted-foreground leading-relaxed">A biotech licensing standoff between two well-funded startups and one cash-strapped pioneer makes for asymmetric tension — ideal for game theory. Try 3 actors, 50 runs.</p>
          </div>

          {error && <div className="glass-card p-3 border border-danger/40"><p className="text-xs text-danger">{error}</p></div>}

          <Button onClick={() => handleLaunch("custom")} disabled={loading} className="w-full bg-violet hover:bg-violet-dark text-white font-semibold py-6 text-base glow-violet-sm" size="lg">
            {loading ? "Starting…" : "⚡ Predict Now"}
          </Button>
        </TabsContent>
      </Tabs>
    </div>
  );
};

export default SetupView;
