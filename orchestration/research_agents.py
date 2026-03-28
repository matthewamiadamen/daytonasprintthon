"""
research_agents.py

Four specialised async research agents that run in parallel via asyncio.
Each uses the Claude AsyncAnthropic client with the web_search server-side tool.

Agent roster:
  alpha  — academic:     game theory papers, academic research, citations
  beta   — industry:     analyst reports, company filings, market data
  gamma  — news/policy:  press coverage, regulatory filings, policy documents
  delta  — technical:    patents, technical specs, engineering reports

All four return a list of source dicts compatible with master_assembler.py.
"""

import asyncio
import json
from typing import Any
import anthropic

MODEL = "claude-opus-4-6"

# ── Source schema Claude must produce ─────────────────────────────────────────

SOURCE_LIST_SCHEMA = {
    "type": "object",
    "properties": {
        "sources": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "title":             {"type": "string"},
                    "url":               {"type": "string"},
                    "year":              {"type": "string"},
                    "category":          {"type": "string"},
                    "reliability_grade": {
                        "type": "string",
                        "enum": ["A", "A-", "B+", "B", "B-", "C", "D", "F"]
                    },
                    "full_content":  {"type": "string", "description": "Full extracted text, up to ~3000 chars"},
                    "key_insights":  {"type": "array", "items": {"type": "string"}}
                },
                "required": ["title", "url", "year", "category", "reliability_grade", "full_content", "key_insights"],
                "additionalProperties": False
            }
        }
    },
    "required": ["sources"],
    "additionalProperties": False
}

# ── Per-agent system prompts ───────────────────────────────────────────────────

_ALPHA_SYSTEM = """\
You are an academic research agent. Your job is to find peer-reviewed papers,
academic studies, and game theory literature relevant to the scenario.

Steps:
1. Use web_search to find academic papers and citations.
2. Prioritise journals, university working papers, NBER/SSRN preprints.
3. For each source: extract the full abstract/introduction, list 3–5 key insights.
4. Grade reliability: A for peer-reviewed journals, B for working papers, C for blog/commentary.
5. Return at least 10 sources as a JSON list.
"""

_BETA_SYSTEM = """\
You are an industry intelligence agent. Your job is to find analyst reports,
company filings, earnings calls, and market data relevant to the scenario.

Steps:
1. Use web_search to find industry reports (McKinsey, Bain, IBISWorld, etc.),
   10-K filings, investor presentations, and trade association data.
2. For each source: extract key market figures, strategic moves, financial metrics.
3. Grade reliability: A for official filings, B for tier-1 analyst reports, C for trade press.
4. Return at least 10 sources as a JSON list.
"""

_GAMMA_SYSTEM = """\
You are a news and policy research agent. Your job is to find press coverage,
regulatory filings, policy documents, and government reports relevant to the scenario.

Steps:
1. Use web_search to find news articles, regulatory announcements, policy papers.
2. Prioritise FT, Reuters, WSJ, official government/regulator sources.
3. For each source: extract key facts, dates, and strategic implications.
4. Grade reliability: A for official regulatory docs, B for tier-1 press, C for other media.
5. Return at least 10 sources as a JSON list.
"""

_DELTA_SYSTEM = """\
You are a technical research agent. Your job is to find patents, technical
specifications, engineering reports, and R&D documents relevant to the scenario.

Steps:
1. Use web_search to find patent filings (Google Patents, USPTO), technical white papers,
   engineering blogs, and R&D disclosures.
2. For each source: extract technical claims, dates, and competitive implications.
3. Grade reliability: A for granted patents, B for technical white papers, C for blog posts.
4. Return at least 10 sources as a JSON list.
"""

AGENTS: dict[str, dict[str, str]] = {
    "alpha-academic":   {"system": _ALPHA_SYSTEM,  "focus": "academic research and game theory literature"},
    "beta-industry":    {"system": _BETA_SYSTEM,   "focus": "industry reports and company intelligence"},
    "gamma-news-policy":{"system": _GAMMA_SYSTEM,  "focus": "news coverage and regulatory/policy documents"},
    "delta-technical":  {"system": _DELTA_SYSTEM,  "focus": "patents and technical specifications"},
}


# ── Core async agent runner ────────────────────────────────────────────────────

async def _run_agent(
    agent_name: str,
    system_prompt: str,
    query: str,
    async_client: anthropic.AsyncAnthropic,
    max_continuations: int = 8,
) -> list[dict[str, Any]]:
    """
    Run a single research agent to completion and return its source list.

    Handles the pause_turn loop that server-side web_search may produce.
    """
    messages: list[dict] = [{"role": "user", "content": query}]

    for attempt in range(max_continuations):
        response = await async_client.messages.create(
            model=MODEL,
            max_tokens=16000,
            thinking={"type": "adaptive"},
            system=system_prompt,
            messages=messages,
            tools=[{"type": "web_search_20260209", "name": "web_search"}],
            output_config={
                "format": {
                    "type": "json_schema",
                    "name": "source_list",
                    "schema": SOURCE_LIST_SCHEMA,
                    "strict": True
                }
            }
        )

        if response.stop_reason == "end_turn":
            for block in response.content:
                if block.type == "text":
                    data = json.loads(block.text)
                    sources = data.get("sources", [])
                    # Tag each source with the agent name
                    for s in sources:
                        s["agent"] = agent_name
                    return sources
            raise RuntimeError(f"[{agent_name}] end_turn but no text block found")

        if response.stop_reason == "pause_turn":
            # Server-side search loop hit its iteration cap; append and continue
            messages.append({"role": "assistant", "content": response.content})
            continue

        raise RuntimeError(f"[{agent_name}] unexpected stop_reason: {response.stop_reason}")

    raise RuntimeError(f"[{agent_name}] exceeded {max_continuations} continuations without end_turn")


# ── Public API: run all four agents concurrently ───────────────────────────────

async def run_all_research_agents(
    scenario: dict,
    async_client: anthropic.AsyncAnthropic,
) -> dict[str, list[dict[str, Any]]]:
    """
    Launch all four research agents in parallel and return their results.

    Args:
        scenario:     The scenario dict (from scenario_builder or scenario_config).
        async_client: An initialised AsyncAnthropic client.

    Returns:
        A dict keyed by agent name, each value a list of source dicts.
    """
    scenario_summary = (
        f"Scenario: {scenario.get('title') or scenario.get('scenario', {}).get('name', 'Unknown')}\n"
        f"Description: {scenario.get('description') or scenario.get('scenario', {}).get('description', '')}\n"
        f"Actors: {', '.join(scenario.get('actors', []))}"
    )

    tasks = {
        name: asyncio.create_task(
            _run_agent(
                agent_name=name,
                system_prompt=cfg["system"],
                query=(
                    f"Research the following scenario from the perspective of {cfg['focus']}:\n\n"
                    f"{scenario_summary}\n\n"
                    "Find and return at least 10 highly relevant sources."
                ),
                async_client=async_client,
            ),
            name=name
        )
        for name, cfg in AGENTS.items()
    }

    results: dict[str, list[dict[str, Any]]] = {}
    errors: list[str] = []

    for name, task in tasks.items():
        try:
            results[name] = await task
            print(f"  [research] {name}: {len(results[name])} sources collected")
        except Exception as exc:
            print(f"  [research] {name}: FAILED — {exc}")
            errors.append(f"{name}: {exc}")
            results[name] = []

    if errors:
        print(f"  [research] {len(errors)} agent(s) failed: {'; '.join(errors)}")

    return results
