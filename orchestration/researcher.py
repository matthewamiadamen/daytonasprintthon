"""
researcher.py

For each actor in the scenario, uses Claude + web search to gather
real-world data and build a dossier dict.

If the actor is real (e.g. a named company), Claude searches for:
  - known strategic decisions
  - public stance / stated values
  - financial position
  - competitive behaviour

If the actor is fictional or sparse, Claude generates an ideological
prior from the actor's type and sector instead.
"""

import json
import anthropic

MODEL = "claude-opus-4-6"

DOSSIER_SCHEMA = {
    "type": "object",
    "properties": {
        "id": {"type": "string", "description": "Short snake_case identifier, e.g. actor_A"},
        "name": {"type": "string"},
        "type": {"type": "string", "description": "Entity type, e.g. Early-stage biotech, Fortune 500 corp"},
        "known_decisions": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Past strategic decisions that reveal preferences or risk tolerance"
        },
        "financial_position": {
            "type": "string",
            "description": "Brief financial snapshot relevant to the scenario"
        },
        "public_stance": {
            "type": "string",
            "description": "Official stated position or brand reputation relevant to the negotiation"
        },
        "demographic_prior": {
            "type": "string",
            "description": "What entities of this type typically do in this kind of game — used when real data is thin"
        }
    },
    "required": [
        "id", "name", "type", "known_decisions",
        "financial_position", "public_stance", "demographic_prior"
    ],
    "additionalProperties": False
}

SYSTEM_PROMPT = """\
You are a strategic intelligence analyst. Given an actor name and the scenario they are
participating in, build a comprehensive dossier on that actor.

Steps:
1. Use the web_search tool to find real information about the actor if they appear to be
   a real organisation or public figure.
2. If little real information is available, derive an ideological prior from the actor type,
   sector, and typical behaviour of similar entities.
3. Focus on information that reveals strategic preferences, risk tolerance, and likely moves
   in a negotiation or competitive game.
4. Be specific: cite actual decisions, not vague generalities.
5. Return ONLY the JSON dossier — no commentary before or after.
"""


def research_actor(
    actor_name: str,
    scenario_context: str,
    client: anthropic.Anthropic,
) -> dict:
    """
    Research one actor and return a dossier dict.

    Args:
        actor_name:        The actor's canonical name from scenario.json.
        scenario_context:  The scenario description (gives Claude context for relevance).
        client:            An initialised Anthropic client.

    Returns:
        A dict matching DOSSIER_SCHEMA.
    """
    user_message = (
        f"Actor to research: {actor_name}\n\n"
        f"Scenario context: {scenario_context}\n\n"
        "Use web search to gather real intelligence on this actor where possible, "
        "then produce the JSON dossier."
    )

    messages = [{"role": "user", "content": user_message}]

    # Agentic loop: web_search is a server-side tool so we loop until end_turn
    max_continuations = 5
    for _ in range(max_continuations):
        response = client.messages.create(
            model=MODEL,
            max_tokens=8192,
            thinking={"type": "adaptive"},
            system=SYSTEM_PROMPT,
            messages=messages,
            tools=[
                {"type": "web_search_20260209", "name": "web_search"},
            ],
            output_config={
                "format": {
                    "type": "json_schema",
                    "name": "dossier",
                    "schema": DOSSIER_SCHEMA,
                    "strict": True
                }
            }
        )

        if response.stop_reason == "end_turn":
            for block in response.content:
                if block.type == "text":
                    return json.loads(block.text)
            raise RuntimeError(f"No text block in researcher response for {actor_name}")

        if response.stop_reason == "pause_turn":
            # Server-side tool loop hit its limit; append and continue
            messages.append({"role": "assistant", "content": response.content})
            continue

        # Unexpected stop reason
        raise RuntimeError(
            f"Unexpected stop_reason '{response.stop_reason}' while researching {actor_name}"
        )

    raise RuntimeError(f"Researcher loop exceeded {max_continuations} continuations for {actor_name}")
