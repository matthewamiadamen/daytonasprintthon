import json, os
from anthropic import Anthropic  # or swap for NVIDIA Nemotron client

OUTPUT_DIR = "analysis/output"
ANSWERS_DIR = "analysis/output/answers"
client = Anthropic()

def ask_analyst(question: str) -> str:
    # Load latest aggregated results
    with open(f"{OUTPUT_DIR}/aggregated_results.json") as f:
        stats = json.load(f)

    prompt = f"""You are the analyst for a game theory simulation.
You have access to the complete results of {stats['simulations_complete']} parallel simulation runs.
Answer the user's strategic question using this data. Be specific — cite percentages,
name the conditions, identify the causal mechanisms. Flag uncertainty where data is thin.

Simulation Data:
{json.dumps(stats, indent=2)}

User question: {question}"""

    response = client.messages.create(
        model="claude-haiku-4-5-20251001",  # fast + cheap for agents
        max_tokens=1000,
        messages=[{"role": "user", "content": prompt}]
    )

    answer = response.content[0].text

    # Save answer to output/answers/ — matches root README contract
    safe_name = question[:40].replace(" ", "_").replace("?", "")
    with open(f"{ANSWERS_DIR}/{safe_name}.json", "w") as f:
        json.dump({
            "question": question,
            "answer": answer,
            "supporting_stats_path": "aggregated_results.json",
            "based_on_runs": stats["simulations_complete"],
            "confidence": None
        }, f, indent=2)

    return answer