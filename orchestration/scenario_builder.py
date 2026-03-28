"""
scenario_builder.py

Takes a raw user prompt and produces a structured scenario.json.
Uses Claude with structured output to guarantee the exact shape the
simulation layer expects.
"""

import json
import anthropic

MODEL = "claude-opus-4-6"

SCENARIO_SCHEMA = {
    "type": "object",
    "properties": {
        "scenario_id": {
            "type": "string",
            "description": "Snake-case identifier derived from the scenario title, e.g. biotech_licensing_v1"
        },
        "title": {"type": "string"},
        "description": {"type": "string"},
        "type": {
            "type": "string",
            "description": "The game-theory interaction type, e.g. multi-round negotiation, auction, coalition formation"
        },
        "rounds": {"type": "integer", "description": "Number of decision rounds"},
        "actors": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Canonical names of each actor in the scenario"
        },
        "payoff_structure": {
            "type": "object",
            "properties": {
                "win_condition": {"type": "string"},
                "zero_sum": {"type": "boolean"},
                "cooperation_possible": {"type": "boolean"}
            },
            "required": ["win_condition", "zero_sum", "cooperation_possible"],
            "additionalProperties": False
        },
        "information_asymmetry": {
            "type": "string",
            "description": "Brief description of what each actor knows vs. doesn't know at start"
        },
        "environment_params": {
            "type": "object",
            "description": "Any extra numeric or categorical params the simulation may use (can be empty)",
            "additionalProperties": False
        }
    },
    "required": [
        "scenario_id", "title", "description", "type", "rounds",
        "actors", "payoff_structure", "information_asymmetry", "environment_params"
    ],
    "additionalProperties": False
}

SYSTEM_PROMPT = """\
You are a game-theory scenario architect. Given a natural-language description of a
multi-actor strategic situation, produce a structured scenario definition.

Rules:
- Choose the number of rounds that best fits the scenario (typically 4–8).
- Actor names must be distinct strings that clearly identify each party.
- The scenario_id must be unique, snake_case, and end with _v1.
- Keep descriptions concise but specific enough for simulation agents to act on.
- environment_params may be empty ({}) if nothing extra is needed.
"""


def build_scenario(prompt: str, client: anthropic.Anthropic, rounds: int | None = None) -> dict:
    """
    Call Claude to turn a free-text scenario prompt into a validated scenario dict.

    Args:
        prompt:  The raw user scenario description.
        client:  An initialised Anthropic client.
        rounds:  If provided, override Claude's choice of round count.

    Returns:
        A dict matching SCENARIO_SCHEMA, ready to be written to scenario.json.
    """
    user_message = prompt
    if rounds:
        user_message += f"\n\n(Run exactly {rounds} rounds.)"

    response = client.messages.create(
        model=MODEL,
        max_tokens=4096,
        thinking={"type": "adaptive"},
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_message}],
        output_config={
            "format": {
                "type": "json_schema",
                "name": "scenario",
                "schema": SCENARIO_SCHEMA,
                "strict": True
            }
        }
    )

    for block in response.content:
        if block.type == "text":
            return json.loads(block.text)

    raise RuntimeError("No text block in scenario builder response")
