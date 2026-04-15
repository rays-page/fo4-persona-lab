from __future__ import annotations

from abc import ABC, abstractmethod
import json
import random
import re
import urllib.error
import urllib.request

from .models import Persona, Turn


class DialogueBackend(ABC):
    @abstractmethod
    def generate_reply(
        self,
        system_prompt: str,
        recent_history: list[Turn],
        user_message: str,
        persona: Persona,
    ) -> str:
        raise NotImplementedError


class RuleBasedBackend(DialogueBackend):
    def __init__(self) -> None:
        self._rng = random.Random()
        self._topic_keywords: dict[str, tuple[str, ...]] = {
            "design": ("design", "simple", "simplicity", "clean", "interface", "ux", "ui"),
            "build": ("build", "ship", "prototype", "system", "product", "tool", "hardware"),
            "leadership": ("team", "lead", "hire", "culture", "management", "execute", "execution"),
            "survival": ("raider", "gun", "fight", "survive", "wasteland", "settlement", "danger"),
            "ethics": ("ethic", "moral", "right", "wrong", "consent", "private", "truth"),
            "science": ("science", "space", "cosmos", "experiment", "evidence", "research"),
        }

    def generate_reply(
        self,
        system_prompt: str,
        recent_history: list[Turn],
        user_message: str,
        persona: Persona,
    ) -> str:
        del system_prompt

        chosen_fact = self._pick_fact(user_message, persona.public_facts)
        chosen_style = self._pick_style(persona)
        continuity = self._continuity_line(recent_history)
        topic = self._infer_topic(user_message)
        persona_focus = self._infer_persona_focus(persona)
        opener = self._build_opener(persona_focus, topic)
        style_line = self._style_line(chosen_style, persona_focus)
        strategy_line = self._strategy_line(persona, topic, persona_focus)
        fact_line = self._fact_line(chosen_fact)
        goal_line = self._goal_line(persona, topic)
        dislike_line = self._dislike_line(persona, user_message)
        follow_up = self._follow_up_line(topic)

        parts = [opener, continuity, style_line, strategy_line, fact_line, goal_line, dislike_line, follow_up]
        return " ".join(part.strip() for part in parts if part.strip())

    def _pick_style(self, persona: Persona) -> str:
        if persona.speech_style:
            return self._rng.choice(persona.speech_style)
        return "plainspoken"

    def _continuity_line(self, recent_history: list[Turn]) -> str:
        last_user_turns = [turn for turn in recent_history if turn.role == "user"]
        if not last_user_turns:
            return ""
        last = last_user_turns[-1].text.strip()
        if not last:
            return ""
        snippet = last[:72].rstrip()
        return f"Last time you said \"{snippet}\" and that context matters."

    def _infer_topic(self, user_message: str) -> str:
        lowered = user_message.lower()
        for topic, keywords in self._topic_keywords.items():
            if any(re.search(rf"\b{re.escape(word)}\b", lowered) for word in keywords):
                return topic
        return "general"

    def _infer_persona_focus(self, persona: Persona) -> str:
        corpus = " ".join(
            [
                persona.display_name,
                persona.short_bio,
                persona.fallout_hook,
                persona.worldview,
                *persona.public_facts,
                *persona.goals,
            ]
        ).lower()
        if any(word in corpus for word in ("apple", "product", "design", "interface", "startup", "execution")):
            return "product"
        if any(word in corpus for word in ("astronomy", "cosmic", "universe", "science", "research")):
            return "science"
        return "general"

    def _build_opener(self, persona_focus: str, topic: str) -> str:
        if persona_focus == "product":
            options = [
                "The wasteland doesn't care about ideas, only what ships.",
                "If this is worth doing, we should make it simple enough to survive contact with reality.",
                "People confuse complexity with progress. They are not the same thing.",
            ]
        elif persona_focus == "science":
            options = [
                "In a broken world, careful thinking is still one of the few reliable tools we have.",
                "Even out here, a good question can be a compass.",
                "Catastrophe changes the setting, not the value of evidence.",
            ]
        else:
            options = [
                "The Commonwealth has a way of clarifying what matters.",
                "Good question. It gets to the center of the problem.",
                "Out here, vague thinking gets people hurt.",
            ]

        if topic in {"survival", "build"}:
            options.append("Let's keep this practical and choose what works under pressure.")
        return self._rng.choice(options)

    def _style_line(self, style: str, persona_focus: str) -> str:
        style_lower = style.lower()
        if "measured" in style_lower or "reflective" in style_lower:
            return "I'd rather be precise than loud."
        if "sharp" in style_lower or "witty" in style_lower or "direct" in style_lower:
            return "I'll give you the direct version."
        if "warm" in style_lower or "gentle" in style_lower:
            return "I'll answer honestly, not theatrically."
        if persona_focus == "product":
            return "Let's strip this down to first principles."
        if persona_focus == "science":
            return "Let's separate what we know from what we merely hope."
        return "I'll answer plainly."

    def _strategy_line(self, persona: Persona, topic: str, persona_focus: str) -> str:
        if topic == "design":
            return "Start by removing friction: fewer steps, clearer feedback, no decorative complexity."
        if topic == "build":
            return "Build the smallest thing that proves the core behavior, then iterate with discipline."
        if topic == "leadership":
            return "Pick a clear bar, protect focus, and align the team around one outcome at a time."
        if topic == "survival":
            return "In this world, reliability beats elegance; choose systems you can repair under stress."
        if topic == "ethics":
            return "If we use a real person's voice or likeness, consent and transparency are non-negotiable."
        if topic == "science":
            return "Test assumptions, keep uncertainty visible, and update beliefs when evidence changes."
        if persona_focus == "product":
            return "What matters is product clarity: who it's for, what pain it removes, and why now."
        if persona_focus == "science":
            return "Frame the problem carefully, then follow evidence even when it is inconvenient."
        if persona.fallout_hook:
            return f"Context matters here: {persona.fallout_hook}"
        return ""

    def _fact_line(self, chosen_fact: str) -> str:
        if not chosen_fact:
            return ""
        return f"Grounding detail: {chosen_fact}"

    def _goal_line(self, persona: Persona, topic: str) -> str:
        if not persona.goals:
            return ""
        if topic in {"build", "leadership", "survival"}:
            return f"My priority is simple: {self._rng.choice(persona.goals)}"
        if self._rng.random() < 0.4:
            return f"Longer-term, I care about this: {self._rng.choice(persona.goals)}"
        return ""

    def _dislike_line(self, persona: Persona, user_message: str) -> str:
        if not persona.dislikes:
            return ""
        lowered = user_message.lower()
        for dislike in persona.dislikes:
            tokens = [token for token in re.split(r"[^a-z0-9]+", dislike.lower()) if len(token) > 4]
            if tokens and any(token in lowered for token in tokens):
                return f"I want to avoid this trap: {dislike}"
        return ""

    def _follow_up_line(self, topic: str) -> str:
        if topic == "design":
            return "What single interaction feels most broken right now?"
        if topic == "build":
            return "What's the smallest milestone we can ship this week?"
        if topic == "survival":
            return "What threat are we optimizing against first?"
        if topic == "ethics":
            return "Where do you want to draw the line so this stays responsible?"
        return self._rng.choice(
            [
                "What part do you want to tackle first?",
                "What constraint is hurting you most right now?",
                "If we continue, where should we focus next?",
            ]
        )

    def _pick_fact(self, user_message: str, facts: list[str]) -> str:
        if not facts:
            return ""
        lowered = user_message.lower()
        for fact in facts:
            tokens = [token for token in fact.lower().split() if len(token) > 4]
            if any(token in lowered for token in tokens):
                return fact
        return self._rng.choice(facts)


class OpenAIChatBackend(DialogueBackend):
    def __init__(self, api_key: str, model: str) -> None:
        self.api_key = api_key
        self.model = model
        self.url = "https://api.openai.com/v1/chat/completions"

    def generate_reply(
        self,
        system_prompt: str,
        recent_history: list[Turn],
        user_message: str,
        persona: Persona,
    ) -> str:
        del persona

        messages: list[dict[str, str]] = [{"role": "system", "content": system_prompt}]
        for turn in recent_history[-12:]:
            messages.append({"role": turn.role, "content": turn.text})
        messages.append({"role": "user", "content": user_message})

        payload = json.dumps(
            {
                "model": self.model,
                "messages": messages,
                "temperature": 0.9,
            }
        ).encode("utf-8")
        request = urllib.request.Request(
            self.url,
            data=payload,
            method="POST",
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                body = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"OpenAI chat request failed: {exc.code} {detail}") from exc
        except urllib.error.URLError as exc:
            raise RuntimeError(f"OpenAI chat request failed: {exc}") from exc

        content = body["choices"][0]["message"]["content"]
        if isinstance(content, str):
            return content.strip()

        if isinstance(content, list):
            text_parts: list[str] = []
            for item in content:
                if isinstance(item, dict) and item.get("type") == "text":
                    text_parts.append(item.get("text", ""))
            return "\n".join(part for part in text_parts if part).strip()

        raise RuntimeError("OpenAI chat response did not include text content.")
