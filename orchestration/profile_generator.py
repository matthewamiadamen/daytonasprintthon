"""
profile_generator.py

Takes a completed dossier dict and derives a game_theory_profile block for it.

The profile is what the simulation layer uses to configure each agent's
reasoning prompt — it must be precise, structured, and actionable.
"""

import json
import anthropic

MODEL = "claude-opus-4-6"

PROFILE_SCHEMA = {
    "type": "object",
    "properties": {
        "rationality": {
            "type": "string",
            "enum": ["fully-rational", "semi-rational", "irrational"],
            "description": "Overall rationality level of this actor"
        },
        "decision_model": {
            "type": "string",
            "description": "The decision-making model that best fits this actor, e.g. expected utility, prospect theory, satisficing, regret minimisation"
        },
        "primary_bias": {
            "type": "string",
            "description": "The dominant cognitive or strategic bias, e.g. loss aversion, status quo bias, overconfidence"
        },
        "strategy_tendency": {
            "type": "string",
            "description": "Typical strategy stance, e.g. cooperative until cornered then unpredictable, always competitive, tit-for-tat"
        },
        "known_weaknesses": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Exploitable tendencies or blind spots"
        },
        "rationality_derived": {
            "type": "string",
            "description": "One-sentence human-readable summary used in dossier display, e.g. semi-rational — loss averse, reputation conscious"
        }
    },
    "required": [
        "rationality", "decision_model", "primary_bias",
        "strategy_tendency", "known_weaknesses", "rationality_derived"
    ],
    "additionalProperties": False
}

SYSTEM_PROMPT = """\
You are a game-theory and behavioural-economics expert. Given an actor dossier,
derive a precise game-theory profile that a simulation agent can use to make
realistic decisions.

Rules:
- Base your profile on the specific evidence in the dossier (past decisions, financial
  position, public stance).
- Choose 'fully-rational' only if there is strong evidence of consistent utility
  maximisation; default to 'semi-rational' for most real-world actors.
- The strategy_tendency must be a concrete behavioural description, not a vague label.
- known_weaknesses should be tactically useful — what a rival could exploit.
- rationality_derived is the one-liner shown in the UI: keep it under 15 words.
"""


def generate_profile(dossier: dict, client: anthropic.Anthropic) -> dict:
    """
    Derive a game_theory_profile from a dossier.

    Args:
        dossier:  A dict matching the DOSSIER_SCHEMA from researcher.py.
        client:   An initialised Anthropic client.

    Returns:
        A dict matching PROFILE_SCHEMA, to be merged into the actor file.
    """
    user_message = (
        "Actor dossier:\n"
        + json.dumps(dossier, indent=2)
        + "\n\nDerive the game-theory profile."
    )

    response = client.messages.create(
        model=MODEL,
        max_tokens=4096,
        thinking={"type": "adaptive"},
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_message}],
        output_config={
            "format": {
                "type": "json_schema",
                "name": "game_theory_profile",
                "schema": PROFILE_SCHEMA,
                "strict": True
            }
        }
    )

    for block in response.content:
        if block.type == "text":
            return json.loads(block.text)

    raise RuntimeError(f"No text block in profile generator response for {dossier.get('name')}")
