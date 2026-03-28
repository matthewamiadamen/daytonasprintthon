"""
master_assembler.py

Merges and deduplicates sources from all four research agents into a
single ranked MASTER_DATASET.json.

Accepts either:
  - a dict of {agent_name: [source, ...]} (from research_agents.py in-process), or
  - a directory of per-agent JSON files on disk (standalone CLI mode).

Output: MASTER_DATASET.json + MASTER_DATASET_SUMMARY.txt
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any


# Grade order: lower index = higher reliability
GRADE_ORDER: dict[str, int] = {
    "A": 0, "A-": 1, "B+": 2, "B": 3, "B-": 4, "C": 5, "D": 6, "F": 7
}


def assemble(
    agent_results: dict[str, list[dict[str, Any]]],
    output_dir: Path,
    scenario_id: str = "unknown_scenario",
) -> dict[str, Any]:
    """
    Merge, deduplicate, rank, and write the master dataset.

    Args:
        agent_results:  {agent_name: [source_dict, ...]}
        output_dir:     Directory to write MASTER_DATASET.json and summary.
        scenario_id:    Identifier carried into the dataset metadata.

    Returns:
        The master dataset dict.
    """
    # ── 1. Flatten all sources ─────────────────────────────────────────────
    all_sources: list[dict[str, Any]] = []
    for agent_name, sources in agent_results.items():
        for s in sources:
            s.setdefault("agent", agent_name)
            all_sources.append(s)

    print(f"  [assembler] raw sources total: {len(all_sources)}")

    # ── 2. Deduplicate by URL (fall back to title) ─────────────────────────
    seen: set[str] = set()
    deduped: list[dict[str, Any]] = []
    for s in all_sources:
        key = s.get("url") or s.get("title", "")
        if key and key not in seen:
            seen.add(key)
            deduped.append(s)

    print(f"  [assembler] after dedup: {len(deduped)} unique sources")

    # ── 3. Sort by reliability grade ──────────────────────────────────────
    deduped.sort(key=lambda x: GRADE_ORDER.get(x.get("reliability_grade", "C"), 5))

    # ── 4. Build statistics ────────────────────────────────────────────────
    by_agent: dict[str, int] = {}
    by_category: dict[str, int] = {}
    by_reliability: dict[str, int] = {}

    for s in deduped:
        by_agent[s.get("agent", "unknown")]                       = by_agent.get(s.get("agent", "unknown"), 0) + 1
        by_category[str(s.get("category", "unknown"))]           = by_category.get(str(s.get("category", "unknown")), 0) + 1
        by_reliability[s.get("reliability_grade", "unknown")]    = by_reliability.get(s.get("reliability_grade", "unknown"), 0) + 1

    # ── 5. Assemble master dataset ─────────────────────────────────────────
    master: dict[str, Any] = {
        "metadata": {
            "title":         f"{scenario_id} — Master Research Dataset",
            "created":        datetime.utcnow().isoformat() + "Z",
            "total_sources":  len(deduped),
            "agents":         list(agent_results.keys()),
            "scenario_id":    scenario_id,
            "purpose":        "Full-text content for Daytona simulation processing"
        },
        "statistics": {
            "by_agent":       by_agent,
            "by_category":    by_category,
            "by_reliability": by_reliability
        },
        "sources": deduped
    }

    # ── 6. Write outputs ───────────────────────────────────────────────────
    output_dir.mkdir(parents=True, exist_ok=True)

    json_path = output_dir / "MASTER_DATASET.json"
    json_path.write_text(json.dumps(master, indent=2))
    print(f"  [assembler] MASTER_DATASET.json → {json_path}")

    _write_summary(master, output_dir / "MASTER_DATASET_SUMMARY.txt")

    return master


def _write_summary(master: dict[str, Any], path: Path) -> None:
    """Write a human-readable text summary of the master dataset."""
    with path.open("w", encoding="utf-8") as f:
        sep = "=" * 80
        f.write(f"{sep}\n")
        f.write(f"{master['metadata']['title'].upper()}\n")
        f.write(f"Generated : {master['metadata']['created']}\n")
        f.write(f"Sources   : {master['metadata']['total_sources']}\n")
        f.write(f"{sep}\n\n")

        f.write("STATISTICS\n")
        f.write("-" * 40 + "\n")
        f.write(f"By agent      : {json.dumps(master['statistics']['by_agent'], indent=2)}\n")
        f.write(f"By category   : {json.dumps(master['statistics']['by_category'], indent=2)}\n")
        f.write(f"By reliability: {json.dumps(master['statistics']['by_reliability'], indent=2)}\n\n")

        f.write("SOURCES\n")
        f.write(f"{sep}\n\n")

        for i, source in enumerate(master["sources"], 1):
            f.write(f"[{i:03d}] {source.get('title', 'Unknown Title')}\n")
            f.write(f"      URL      : {source.get('url', 'N/A')}\n")
            f.write(f"      Agent    : {source.get('agent', 'N/A')}\n")
            f.write(f"      Category : {source.get('category', 'N/A')}\n")
            f.write(f"      Grade    : {source.get('reliability_grade', 'N/A')}\n")
            f.write(f"      Year     : {source.get('year', 'N/A')}\n")

            content = source.get("full_content", source.get("content", ""))
            if content:
                f.write("\n      FULL CONTENT:\n")
                f.write("      " + "-" * 36 + "\n")
                excerpt = content[:5000]
                for line in excerpt.splitlines():
                    f.write(f"      {line}\n")
                if len(content) > 5000:
                    f.write(f"      ... [truncated — {len(content)} total chars]\n")

            insights = source.get("key_insights", [])
            if insights:
                f.write("\n      KEY INSIGHTS:\n")
                for insight in insights:
                    f.write(f"      • {insight}\n")

            f.write(f"\n{sep}\n\n")

    print(f"  [assembler] MASTER_DATASET_SUMMARY.txt → {path}")


# ── Standalone CLI ─────────────────────────────────────────────────────────────

def _load_agent_file(filepath: Path, agent_name: str) -> list[dict[str, Any]]:
    """Load a single agent output file (handles several output formats)."""
    try:
        data = json.loads(filepath.read_text())
    except Exception as exc:
        print(f"  [assembler] could not load {filepath}: {exc}")
        return []

    if isinstance(data, list):
        return data

    for key in ("sources", "results", "collected_sources"):
        if key in data:
            return data[key]

    return []


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Assemble master dataset from agent JSON files")
    parser.add_argument("--input-dir",   required=True, help="Directory containing agent_*.json output files")
    parser.add_argument("--output-dir",  required=True, help="Directory to write MASTER_DATASET files")
    parser.add_argument("--scenario-id", default="scenario", help="Scenario identifier for metadata")
    args = parser.parse_args()

    input_dir  = Path(args.input_dir)
    output_dir = Path(args.output_dir)

    agent_results: dict[str, list[dict]] = {}
    for file in sorted(input_dir.glob("*.json")):
        agent_name = file.stem.replace("_sources", "").replace("research_results_", "")
        sources = _load_agent_file(file, agent_name)
        print(f"  loaded {len(sources)} sources from {file.name}")
        agent_results[agent_name] = sources

    assemble(agent_results, output_dir, scenario_id=args.scenario_id)
