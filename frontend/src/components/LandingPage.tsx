import { Button } from "@/components/ui/button";
import ParallaxAvatar from "./ParallaxAvatar";

interface Props {
  onLaunch: () => void;
  onUseCase: (scenario: string) => void;
}

const USE_CASES = [
  { emoji: "🏢", title: "M&A Negotiation", desc: "Three corporations negotiating an acquisition" },
  { emoji: "🌍", title: "Climate Treaty", desc: "Nations agreeing emissions targets" },
  { emoji: "💊", title: "Biotech Licensing", desc: "Startups splitting IP before Series A" },
];

const STEPS = [
  { num: "01", title: "Describe your scenario", desc: "Tell Parallax about the actors, stakes, and dynamics" },
  { num: "02", title: "AI generates actors & dossiers", desc: "Each actor gets a rationality profile and decision history" },
  { num: "03", title: "50 worlds run. Parallax answers.", desc: "Parallel simulations reveal who wins — and why" },
];

const LandingPage = ({ onLaunch, onUseCase }: Props) => (
  <div className="relative z-10 min-h-screen flex flex-col">
    {/* Hero */}
    <div className="flex-1 flex flex-col items-center justify-center text-center px-4 pt-24 pb-16 max-w-4xl mx-auto">
      {/* Pill badge */}
      <div className="glass-card px-4 py-1.5 text-xs font-medium text-muted-foreground mb-6 opacity-0 animate-fade-in" style={{ animationDelay: "0.1s", animationFillMode: "forwards" }}>
        🤖 AI-Powered Game Theory Simulation
      </div>

      {/* Avatar — flies in and floats above heading */}
      <div className="mb-6 opacity-0 animate-fly-in" style={{ animationDelay: "0.15s", animationFillMode: "forwards" }}>
        <ParallaxAvatar />
      </div>

      {/* Heading */}
      <h1 className="text-5xl md:text-7xl font-black tracking-tight mb-3 gradient-text opacity-0 animate-fade-in-up" style={{ animationDelay: "0.4s", animationFillMode: "forwards" }}>
        Hi, I'm Parallax.
      </h1>
      <p className="text-lg md:text-xl text-muted-foreground max-w-2xl mb-8 opacity-0 animate-fade-in-up" style={{ animationDelay: "0.55s", animationFillMode: "forwards" }}>
        I simulate negotiations so you don't have to guess. Tell me who's at the table, and I'll show you who walks away with what.
      </p>

      {/* Feature pills */}
      <div className="flex flex-wrap justify-center gap-3 mb-10 opacity-0 animate-fade-in-up" style={{ animationDelay: "0.7s", animationFillMode: "forwards" }}>
        {["⚡ 50 Parallel Sandboxes", "🧠 NVIDIA Nemotron", "🎯 Real Strategy Answers"].map((t) => (
          <span key={t} className="glass-card px-4 py-2 text-sm text-muted-foreground">{t}</span>
        ))}
      </div>

      {/* CTA */}
      <div className="flex flex-col sm:flex-row gap-3 mb-16 opacity-0 animate-fade-in-up" style={{ animationDelay: "0.8s", animationFillMode: "forwards" }}>
        <Button onClick={onLaunch} size="lg" className="bg-violet hover:bg-violet-dark text-white font-semibold px-8 py-6 text-base glow-violet-sm">
          Launch a Simulation →
        </Button>
        <Button variant="outline" size="lg" className="border-white/10 text-foreground hover:bg-white/5 px-8 py-6 text-base">
          <svg className="w-5 h-5 mr-2" fill="currentColor" viewBox="0 0 24 24"><path d="M12 0c-6.626 0-12 5.373-12 12 0 5.302 3.438 9.8 8.207 11.387.599.111.793-.261.793-.577v-2.234c-3.338.726-4.033-1.416-4.033-1.416-.546-1.387-1.333-1.756-1.333-1.756-1.089-.745.083-.729.083-.729 1.205.084 1.839 1.237 1.839 1.237 1.07 1.834 2.807 1.304 3.492.997.107-.775.418-1.305.762-1.604-2.665-.305-5.467-1.334-5.467-5.931 0-1.311.469-2.381 1.236-3.221-.124-.303-.535-1.524.117-3.176 0 0 1.008-.322 3.301 1.23A11.509 11.509 0 0112 5.803c1.02.005 2.047.138 3.006.404 2.291-1.552 3.297-1.23 3.297-1.23.653 1.653.242 2.874.118 3.176.77.84 1.235 1.911 1.235 3.221 0 4.609-2.807 5.624-5.479 5.921.43.372.823 1.102.823 2.222v3.293c0 .319.192.694.801.576C20.566 21.797 24 17.3 24 12c0-6.627-5.373-12-12-12z"/></svg>
          Import from GitHub
        </Button>
      </div>

      {/* Use cases */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 w-full max-w-3xl mb-20 opacity-0 animate-fade-in-up" style={{ animationDelay: "0.9s", animationFillMode: "forwards" }}>
        {USE_CASES.map((uc) => (
          <button
            key={uc.title}
            onClick={() => onUseCase(uc.desc)}
            className="glass-card-hover p-5 text-left"
          >
            <span className="text-2xl mb-2 block">{uc.emoji}</span>
            <p className="font-semibold text-sm mb-1">{uc.title}</p>
            <p className="text-xs text-muted-foreground">{uc.desc}</p>
          </button>
        ))}
      </div>
    </div>

    {/* How it works */}
    <div className="border-t border-white/5 py-16 px-4">
      <h2 className="text-center text-2xl font-bold mb-12">How it works</h2>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-8 max-w-4xl mx-auto">
        {STEPS.map((s) => (
          <div key={s.num} className="text-center">
            <div className="w-12 h-12 rounded-full bg-violet/20 text-violet flex items-center justify-center text-sm font-bold mx-auto mb-4">{s.num}</div>
            <p className="font-semibold mb-1">{s.title}</p>
            <p className="text-sm text-muted-foreground">{s.desc}</p>
          </div>
        ))}
      </div>
    </div>
  </div>
);

export default LandingPage;
