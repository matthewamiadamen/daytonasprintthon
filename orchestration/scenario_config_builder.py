"""
scenario_config_builder.py

Takes our high-level scenario.json (from scenario_builder.py) and produces
the richer scenario_config.json that generate_profiles.py consumes.

The key job here is mapping each actor to one of the five archetypes:
  incumbent | challenger | specialist | disruptor | follower

Claude also derives:
  - decision_variables  (what moves each actor can make)
  - objectives          (what each actor is trying to optimise)
  - constraints         (hard / soft limits on the game)
  - information_asymmetry (what each actor privately knows)
  - market structure

The output schema is locked to what AgentProfileGenerator expects.
"""

import json
import anthropic

MODEL = "claude-opus-4-6"

# ── JSON schema for structured output ─────────────────────────────────────────

SCENARIO_CONFIG_SCHEMA = {
    "type": "object",
    "properties": {
        "scenario": {
            "type": "object",
            "properties": {
                "name":        {"type": "string"},
                "domain":      {"type": "string", "description": "e.g. biotech, airlines, geopolitics"},
                "description": {"type": "string"}
            },
            "required": ["name", "domain", "description"],
            "additionalProperties": False
        },
        "market": {
            "type": "object",
            "properties": {
                "structure": {
                    "type": "string",
                    "description": "e.g. oligopoly, duopoly, fragmented, monopolistic competition"
                },
                "size_description": {"type": "string"},
                "key_dynamics":     {"type": "array", "items": {"type": "string"}}
            },
            "required": ["structure", "size_description", "key_dynamics"],
            "additionalProperties": False
        },
        "agents": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "id":                    {"type": "string", "description": "snake_case, e.g. actor_A"},
                    "name":                  {"type": "string"},
                    "archetype": {
                        "type": "string",
                        "enum": ["incumbent", "challenger", "specialist", "disruptor", "follower"]
                    },
                    "role_description":      {"type": "string"},
                    "market_position":       {"type": "string"},
                    "resource_constraints":  {"type": "array", "items": {"type": "string"}},
                    "competitive_advantages":{"type": "array", "items": {"type": "string"}},
                    "behavioral_traits":     {"type": "array", "items": {"type": "string"}}
                },
                "required": [
                    "id", "name", "archetype", "role_description", "market_position",
                    "resource_constraints", "competitive_advantages", "behavioral_traits"
                ],
                "additionalProperties": False
            }
        },
        "decision_variables": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "name":        {"type": "string"},
                    "type":        {"type": "string", "enum": ["continuous", "discrete", "binary", "categorical"]},
                    "range":       {"type": "string", "description": "e.g. [0, 100], {low, medium, high}"},
                    "description": {"type": "string"}
                },
                "required": ["name", "type", "range", "description"],
                "additionalProperties": False
            }
        },
        "objectives": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "name":         {"type": "string"},
                    "optimization": {"type": "string", "enum": ["maximize", "minimize"]},
                    "weight":       {"type": "number", "description": "Base weight 0–1 before archetype modifier"},
                    "description":  {"type": "string"}
                },
                "required": ["name", "optimization", "weight", "description"],
                "additionalProperties": False
            }
        },
        "constraints": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "type":        {"type": "string", "enum": ["hard", "soft"]},
                    "description": {"type": "string"}
                },
                "required": ["type", "description"],
                "additionalProperties": False
            }
        },
        "information_asymmetry": {
            "type": "array",
            "description": "One entry per agent that has non-default private info",
            "items": {
                "type": "object",
                "properties": {
                    "agent_id":            {"type": "string"},
                    "private_information": {"type": "array", "items": {"type": "string"}},
                    "public_information":  {"type": "array", "items": {"type": "string"}}
                },
                "required": ["agent_id", "private_information", "public_information"],
                "additionalProperties": False
            }
        }
    },
    "required": [
        "scenario", "market", "agents", "decision_variables",
        "objectives", "constraints", "information_asymmetry"
    ],
    "additionalProperties": False
}

SYSTEM_PROMPT = """\
You are a game-theory scenario architect specialising in multi-agent competitive systems.

Your task is to take a high-level scenario description and expand it into a rich
structured configuration that will drive agent-based simulation.

Guidelines:
- Assign each actor a single archetype from: incumbent, challenger, specialist, disruptor, follower.
  An actor can only have one archetype; choose the most dominant.
- Decision variables should be the actual levers each actor can pull each round
  (pricing, capacity, alliance choice, bid level, etc.).
- Objectives must have weights that sum roughly to 1.0 across all objectives (not per agent).
- information_asymmetry: list only agents whose private info is meaningfully different from the
  default ["own_costs", "own_capacity", "own_strategy", "private_forecasts"].
- Be concrete — use numbers where possible in range descriptions.
"""


def build_scenario_config(scenario: dict, client: anthropic.Anthropic) -> dict:
    """
    Derive a full scenario_config dict from a high-level scenario dict.

    Args:
        scenario:  The dict produced by scenario_builder.build_scenario().
        client:    An initialised Anthropic client.

    Returns:
        A dict matching SCENARIO_CONFIG_SCHEMA, ready for AgentProfileGenerator.
    """
    user_message = (
        "High-level scenario:\n"
        + json.dumps(scenario, indent=2)
        + "\n\nExpand this into the full scenario_config."
    )

    response = client.messages.create(
        model=MODEL,
        max_tokens=8192,
        thinking={"type": "adaptive"},
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_message}],
        output_config={
            "format": {
                "type": "json_schema",
                "name": "scenario_config",
                "schema": SCENARIO_CONFIG_SCHEMA,
                "strict": True
            }
        }
    )

    for block in response.content:
        if block.type == "text":
            return json.loads(block.text)

    raise RuntimeError("No text block in scenario_config_builder response")
