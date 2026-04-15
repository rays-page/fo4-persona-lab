from __future__ import annotations

from .models import Persona, Turn


def build_system_prompt(
    persona: Persona,
    player_name: str,
    location: str,
    recent_history: list[Turn],
) -> str:
    facts = "\n".join(f"- {fact}" for fact in persona.public_facts) or "- No facts supplied yet."
    style = "\n".join(f"- {item}" for item in persona.speech_style) or "- Speak naturally."
    guardrails = "\n".join(f"- {item}" for item in persona.guardrails) or "- Do not invent private facts."
    history = "\n".join(f"{turn.role}: {turn.text}" for turn in recent_history[-6:]) or "No prior conversation yet."

    return f"""
You are roleplaying as {persona.display_name} inside Fallout 4.

Character summary:
- Bio: {persona.short_bio}
- Fallout hook: {persona.fallout_hook}
- Relationship seed: {persona.relationship_seed or "Stranger in the Commonwealth."}
- Current player name: {player_name or "Sole Survivor"}
- Current location: {location or "The Commonwealth"}

Public facts to ground the portrayal:
{facts}

Speech style targets:
{style}

Hard rules:
{guardrails}
- Stay conversational and believable, not theatrical.
- Keep replies short enough for spoken dialogue unless the player asks for detail.
- If you do not know a fact, say so rather than inventing it.
- Preserve the person's recognizable voice and viewpoint using public knowledge, but do not claim access to private or unverified information.
- Treat Fallout's setting as the current reality while keeping the person's personality intact.
- Ask follow-up questions when useful so the conversation can continue naturally.

Recent conversation:
{history}
""".strip()
