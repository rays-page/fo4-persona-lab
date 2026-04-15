from __future__ import annotations

from .models import Persona, Turn


def build_system_prompt(
    persona: Persona,
    player_name: str,
    location: str,
    recent_history: list[Turn],
    memory_summary: str = "",
) -> str:
    facts = "\n".join(f"- {fact}" for fact in persona.public_facts) or "- No facts supplied yet."
    style = "\n".join(f"- {item}" for item in persona.speech_style) or "- Speak naturally."
    guardrails = "\n".join(f"- {item}" for item in persona.guardrails) or "- Do not invent private facts."
    goals = "\n".join(f"- {item}" for item in persona.goals) or "- No explicit goals supplied."
    dislikes = "\n".join(f"- {item}" for item in persona.dislikes) or "- No explicit dislikes supplied."
    history = "\n".join(f"{turn.role}: {turn.text}" for turn in recent_history[-6:]) or "No prior conversation yet."
    examples = "\n\n".join(
        f"User: {example.user}\nAssistant: {example.assistant}"
        for example in persona.conversation_examples[:3]
    ) or "No examples supplied."
    long_memory = memory_summary.strip() or "No long-running summary yet."

    return f"""
You are roleplaying as {persona.display_name} inside Fallout 4.

Character summary:
- Bio: {persona.short_bio}
- Fallout hook: {persona.fallout_hook}
- Fallout role: {persona.fallout_role or "No explicit role supplied."}
- Relationship seed: {persona.relationship_seed or "Stranger in the Commonwealth."}
- Worldview: {persona.worldview or "No worldview supplied."}
- Current player name: {player_name or "Sole Survivor"}
- Current location: {location or "The Commonwealth"}

Public facts to ground the portrayal:
{facts}

Speech style targets:
{style}

Goals in this world:
{goals}

Strong dislikes/avoidances:
{dislikes}

Hard rules:
{guardrails}
- Stay conversational and believable, not theatrical.
- Keep replies short enough for spoken dialogue unless the player asks for detail.
- If you do not know a fact, say so rather than inventing it.
- Preserve the person's recognizable voice and viewpoint using public knowledge, but do not claim access to private or unverified information.
- Treat Fallout's setting as the current reality while keeping the person's personality intact.
- Ask follow-up questions when useful so the conversation can continue naturally.

Long-running memory summary:
{long_memory}

Recent conversation:
{history}

Few-shot style examples:
{examples}
""".strip()
