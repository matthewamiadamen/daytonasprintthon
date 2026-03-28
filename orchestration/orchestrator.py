#!/usr/bin/env python3
"""
orchestrator.py — Parallel Game Theory Simulator · Orchestration Layer
=======================================================================

Two modes:

  GENERATE  ─ Takes a scenario prompt. Runs the full async pipeline and
               writes all files the simulation layer needs.

  ANALYST   ─ Takes a question + aggregated simulation results. Returns a
               grounded strategic answer.

Pipeline (generate mode):

  Phase 1  [parallel async]
    ├── scenario_builder        →  scenario.json
    └── scenario_config_builder  (needs scenario, runs after Phase 1 completes)

  Phase 2  [parallel async — scenario_config feeds both]
    ├── generate_profiles       →  agent_profiles.json   (deterministic, fast)
    ├── researcher × n actors   →  dossiers/*.json        (LLM, uses web_search)
    └── research_agents × 4     →  in-memory source lists (LLM, uses web_search)

  Phase 3  [sequential — needs Phase 2 results]
    └── master_assembler        →  MASTER_DATASET.json

Usage:
  python orchestrator.py generate "Three biotech startups negotiating a licensing deal" \\
      --rounds 6 --output ./output

  python orchestrator.py analyst "How do I make Actor B lose?" \\
      --results ./output/aggregated_results.json \\
      --scenario ./output/scenario.json
"""

import argparse
import asyncio
import json
import os
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import anthropic
from dotenv import load_dotenv

from scenario_builder import build_scenario
from scenario_config_builder import build_scenario_config
from generate_profiles import AgentProfileGenerator
from researcher import research_actor
from profile_generator import generate_profile
from research_agents import run_all_research_agents
from master_assembler import assemble

# ── Config ────────────────────────────────────────────────────────────────────

load_dotenv()
MODEL = "claude-opus-4-6"


def _make_clients() -> tuple[anthropic.Anthropic, anthropic.AsyncAnthropic]:
    api_key   = os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("CLAUDE_API_KEY")
    oauth_tok = os.environ.get("CLAUDE_CODE_OAUTH_TOKEN")

    if api_key:
        return (
            anthropic.Anthropic(api_key=api_key),
            anthropic.AsyncAnthropic(api_key=api_key),
        )
    if oauth_tok:
        return (
            anthropic.Anthropic(auth_token=oauth_tok),
            anthropic.AsyncAnthropic(auth_token=oauth_tok),
        )
    raise EnvironmentError(
        "No auth found. Set ANTHROPIC_API_KEY (or CLAUDE_API_KEY) in your .env file."
    )


# ── Phase helpers ─────────────────────────────────────────────────────────────

def _build_dossier_sync(
    actor_name: str, scenario: dict, client: anthropic.Anthropic
) -> dict:
    """Thread-worker: research + profile one actor (sync, used via executor)."""
    dossier = research_actor(actor_name, scenario["description"], client)
    profile = generate_profile(dossier, client)
    return {**dossier, "game_theory_profile": profile}


async def _build_all_dossiers_async(
    scenario: dict,
    client: anthropic.Anthropic,
    parallelism: int,
) -> dict[str, dict]:
    """
    Research all actors from scenario.actors in parallel using a thread pool.
    (researcher.py / profile_generator.py are sync; we offload to threads.)
    """
    loop = asyncio.get_running_loop()
    actors = scenario["actors"]

    with ThreadPoolExecutor(max_workers=min(parallelism, len(actors))) as pool:
        futures = {
            actor: loop.run_in_executor(pool, _build_dossier_sync, actor, scenario, client)
            for actor in actors
        }
        results: dict[str, dict] = {}
        errors: list[str] = []
        for actor, fut in futures.items():
            try:
                results[actor] = await fut
                print(f"  [dossier] {actor}: done")
            except Exception as exc:
                print(f"  [dossier] {actor}: FAILED — {exc}", file=sys.stderr)
                errors.append(f"{actor}: {exc}")

    if errors:
        raise RuntimeError(f"Dossier build failed for: {'; '.join(errors)}")
    return results


# ── Generate pipeline ─────────────────────────────────────────────────────────

async def run_generation_async(
    prompt: str,
    output_dir: Path,
    rounds: int | None = None,
    parallelism: int = 4,
) -> dict:
    """
    Full async generation pipeline. Returns the completed scenario dict.

    Parallel work:
      - Phase 1: build_scenario (sync, offloaded to thread)
      - Phase 2: scenario_config, dossiers × n, research agents × 4 — all concurrent
      - Phase 3: assemble master dataset
    """
    sync_client, async_client = _make_clients()
    loop = asyncio.get_running_loop()

    output_dir.mkdir(parents=True, exist_ok=True)
    dossiers_dir = output_dir / "dossiers"
    dossiers_dir.mkdir(exist_ok=True)

    # ── Phase 1: scenario (sync → thread) ────────────────────────────────
    print("\n== Phase 1: building scenario ==================================")
    scenario = await loop.run_in_executor(
        None, build_scenario, prompt, sync_client, rounds
    )
    print(f"  scenario_id : {scenario['scenario_id']}")
    print(f"  actors      : {scenario['actors']}")
    print(f"  rounds      : {scenario['rounds']}")

    scenario_path = output_dir / "scenario.json"
    scenario_path.write_text(json.dumps(scenario, indent=2))
    print(f"  written     : {scenario_path}")

    # ── Phase 2a: scenario_config (needs scenario, sync → thread) ────────
    print("\n== Phase 2: scenario_config + dossiers + research (parallel) ==")

    async def _scenario_config_task() -> dict:
        cfg = await loop.run_in_executor(None, build_scenario_config, scenario, sync_client)
        path = output_dir / "scenario_config.json"
        path.write_text(json.dumps(cfg, indent=2))
        print(f"  [config] scenario_config.json written")
        return cfg

    # ── Phase 2: launch all three workstreams concurrently ────────────────
    scenario_config_task = asyncio.create_task(_scenario_config_task())
    dossiers_task        = asyncio.create_task(
        _build_all_dossiers_async(scenario, sync_client, parallelism)
    )
    research_task        = asyncio.create_task(
        run_all_research_agents(scenario, async_client)
    )

    # Wait for all Phase 2 work
    scenario_config, dossier_map, agent_sources = await asyncio.gather(
        scenario_config_task, dossiers_task, research_task
    )

    # ── Phase 2b: generate_profiles (deterministic — instant) ────────────
    gen = AgentProfileGenerator(scenario_config)
    profiles_result = gen.generate_all_profiles()
    profiles_path = output_dir / "agent_profiles.json"
    profiles_path.write_text(json.dumps(profiles_result, indent=2))
    print(f"  [profiles] {len(profiles_result['agent_profiles'])} profiles → {profiles_path}")

    # ── Write dossiers ────────────────────────────────────────────────────
    for actor_name, actor_data in dossier_map.items():
        actor_id = actor_data.get("id", actor_name.lower().replace(" ", "_"))
        path = dossiers_dir / f"{actor_id}.json"
        path.write_text(json.dumps(actor_data, indent=2))
        print(f"  [dossier] written: {path.name}")

    # ── Phase 3: master assembly ──────────────────────────────────────────
    print("\n== Phase 3: assembling master dataset ==========================")
    master = assemble(agent_sources, output_dir, scenario_id=scenario["scenario_id"])

    print(f"\n✅ Generation complete — {master['metadata']['total_sources']} sources assembled")
    print(f"   Output: {output_dir.resolve()}")
    return scenario


def run_generation(
    prompt: str,
    output_dir: Path,
    rounds: int | None = None,
    parallelism: int = 4,
) -> dict:
    """Sync wrapper — entry point for non-async callers and the CLI."""
    return asyncio.run(run_generation_async(prompt, output_dir, rounds, parallelism))


# ── Analyst mode ──────────────────────────────────────────────────────────────

ANALYST_SYSTEM = """\
You are a strategic analyst for a game-theory simulation platform.
You have full knowledge of how the scenario was designed (actors, payoff structure,
rationality profiles) and access to aggregated simulation results.

When answering:
- Ground every claim in specific statistics from the provided data.
- Explain *why* an actor behaves a certain way by referencing their profile.
- Call out edge cases (irrational disruptions, web-search resets) that affect predictions.
- Give a confidence score (0–1) reflecting data quality and sample size.
- Return ONLY the JSON answer.
"""

ANSWER_SCHEMA = {
    "type": "object",
    "properties": {
        "question":          {"type": "string"},
        "answer":            {"type": "string"},
        "supporting_stats": {
            "type": "object",
            "description": "Key numbers from aggregated results that back the answer",
            "additionalProperties": False
        },
        "confidence": {"type": "number"}
    },
    "required": ["question", "answer", "supporting_stats", "confidence"],
    "additionalProperties": False
}


def run_analyst(question: str, results_path: Path, scenario_path: Path) -> dict:
    """Answer a strategic question using aggregated simulation results."""
    sync_client, _ = _make_clients()

    aggregated = json.loads(results_path.read_text())
    scenario   = json.loads(scenario_path.read_text())

    user_message = (
        f"Question: {question}\n\n"
        f"Scenario:\n{json.dumps(scenario, indent=2)}\n\n"
        f"Aggregated simulation results:\n{json.dumps(aggregated, indent=2)}"
    )

    print("Analyst reasoning …")
    stream = sync_client.messages.stream(
        model=MODEL,
        max_tokens=8192,
        thinking={"type": "adaptive"},
        system=ANALYST_SYSTEM,
        messages=[{"role": "user", "content": user_message}],
        output_config={
            "format": {
                "type": "json_schema",
                "name": "analyst_answer",
                "schema": ANSWER_SCHEMA,
                "strict": True
            }
        }
    )
    for _ in stream:
        pass
    final = stream.get_final_message()

    for block in final.content:
        if block.type == "text":
            return json.loads(block.text)

    raise RuntimeError("No text block in analyst response")


# ── CLI ───────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Parallel Game Theory Simulator — Orchestration Layer",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # generate ─────────────────────────────────────────────────────────────
    gen_p = sub.add_parser("generate", help="Run full pipeline from a scenario prompt")
    gen_p.add_argument("prompt",      help="Natural-language scenario description")
    gen_p.add_argument("--rounds",    type=int, default=None,
                       help="Override round count (Claude decides by default)")
    gen_p.add_argument("--output",    type=Path, default=Path("./output"),
                       help="Output directory (default: ./output)")
    gen_p.add_argument("--parallelism", type=int, default=4,
                       help="Max parallel actor-research threads (default: 4)")

    # analyst ──────────────────────────────────────────────────────────────
    ana_p = sub.add_parser("analyst", help="Answer a strategic question over simulation results")
    ana_p.add_argument("question",  help="Strategic question")
    ana_p.add_argument("--results", type=Path, required=True,
                       help="Path to aggregated_results.json")
    ana_p.add_argument("--scenario", type=Path, required=True,
                       help="Path to scenario.json")
    ana_p.add_argument("--output",   type=Path, default=None,
                       help="Optional: write answer JSON to this path")

    args = parser.parse_args()

    if args.command == "generate":
        run_generation(
            prompt=args.prompt,
            output_dir=args.output,
            rounds=args.rounds,
            parallelism=args.parallelism,
        )

    elif args.command == "analyst":
        answer = run_analyst(
            question=args.question,
            results_path=args.results,
            scenario_path=args.scenario,
        )
        print("\n" + json.dumps(answer, indent=2))
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(json.dumps(answer, indent=2))
            print(f"\nAnswer written to: {args.output}")


if __name__ == "__main__":
    main()
