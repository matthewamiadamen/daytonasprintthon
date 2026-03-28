# Parallax — AI-Powered Game Theory Simulation

Parallax is an interactive web application that simulates complex negotiations using AI-driven game theory. Describe a scenario with multiple actors, and Parallax runs parallel sandbox simulations to reveal likely outcomes, dominant strategies, and hidden dynamics.

## Features

- **Scenario Builder** — Define negotiation scenarios with custom actors, stakes, and dynamics
- **Multi-Model Support** — Choose from NVIDIA Nemotron, Claude 3.5 Sonnet, GPT-4o, or Llama 3
- **50 Parallel Sandboxes** — Simultaneous simulation runs for statistically meaningful results
- **Live Decision Ticker** — Real-time feed of actor decisions, payoffs, and web-search-augmented moves
- **Actor Rationality Profiles** — Rational, semi-rational, and irrational behavioral modeling
- **Results Dashboard** — Outcome distributions, Nash equilibrium analysis, and strategic recommendations
- **Ask Parallax (Analyst Q&A)** — Ask strategic questions grounded in simulation data; answers are sourced from `analysis/output/answers/`

## Tech Stack

- **Framework:** React 18 + TypeScript
- **Build Tool:** Vite
- **Styling:** Tailwind CSS + shadcn/ui
- **Charts:** Recharts
- **Routing:** React Router
- **State Management:** TanStack React Query

## Getting Started

```bash
# Install dependencies
npm install

# Start development server
npm run dev

# Build for production
npm run build
```

## Project Structure

```
src/
├── assets/          # Static assets (dragon avatar, images)
├── components/      # React components
│   ├── ui/          # shadcn/ui primitives
│   ├── LandingPage  # Hero, use cases, how-it-works
│   ├── SetupView    # Scenario configuration
│   ├── RunningView  # Live simulation dashboard
│   └── ResultsView  # Outcome analysis + analyst Q&A
├── hooks/           # Custom React hooks
├── lib/             # Utility functions
└── pages/           # Route-level page components
```

## Data Integration

The frontend consumes outputs produced by the analysis layer:

| Source | Path | Used by |
|---|---|---|
| Aggregated stats | `analysis/output/aggregated_results.json` | Results Dashboard, charts |
| Analyst answers | `analysis/output/answers/*.json` | Ask Parallax Q&A |
| Live decision updates | WebSocket on `ws://127.0.0.1:8765` | Live Decision Ticker |

The frontend expects `aggregated_results.json` to contain at minimum:
- `num_runs` — total completed simulation runs
- `actor_outcome_distribution` — per-actor win rate and avg payoff
- `irrational_disruption_rate` — fraction of runs where an irrational actor disrupted equilibrium
- `game_theory_stats` — Nash equilibrium, Pareto optimality, web-search trigger rates

## License

MIT
