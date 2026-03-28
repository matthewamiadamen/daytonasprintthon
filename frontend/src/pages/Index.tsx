import { useState } from "react";
import AnimatedBackground from "@/components/AnimatedBackground";
import Navbar from "@/components/Navbar";
import LandingPage from "@/components/LandingPage";
import SetupView from "@/components/SetupView";
import RunningView from "@/components/RunningView";
import ResultsView from "@/components/ResultsView";

type View = "landing" | "setup" | "running" | "results";

const Index = () => {
  const [view, setView] = useState<View>("landing");
  const [totalRuns, setTotalRuns] = useState(50);
  const [initialScenario, setInitialScenario] = useState("");

  const handleLaunch = (_scenario: string, _actors: number, runs: number) => {
    setTotalRuns(runs);
    setView("running");
  };

  const goToSetup = (scenario?: string) => {
    if (scenario) setInitialScenario(scenario);
    setView("setup");
  };

  return (
    <div className="min-h-screen relative">
      <AnimatedBackground />
      <Navbar showAuth={view === "landing"} />
      {view === "landing" && <LandingPage onLaunch={() => goToSetup()} onUseCase={(s) => goToSetup(s)} />}
      {view === "setup" && <SetupView initialScenario={initialScenario} onLaunch={handleLaunch} />}
      {view === "running" && <RunningView totalRuns={totalRuns} onComplete={() => setView("results")} onCancel={() => setView("setup")} />}
      {view === "results" && <ResultsView totalRuns={totalRuns} onReset={() => { setInitialScenario(""); setView("landing"); }} />}
    </div>
  );
};

export default Index;
