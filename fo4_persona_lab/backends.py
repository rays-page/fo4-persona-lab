from __future__ import annotations

from abc import ABC, abstractmethod
import json
import random
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

    def generate_reply(
        self,
        system_prompt: str,
        recent_history: list[Turn],
        user_message: str,
        persona: Persona,
    ) -> str:
        del system_prompt

        chosen_fact = self._pick_fact(user_message, persona.public_facts)
        chosen_style = persona.speech_style[0] if persona.speech_style else "plainspoken"
        continuity = ""
        if recent_history:
            last_user_turns = [turn for turn in recent_history if turn.role == "user"]
            if last_user_turns:
                continuity = "You keep circling back to this, and I can see why. "

        opener = self._rng.choice(
            [
                "Listen, the wasteland has a way of stripping a question down to its bones.",
                "That is a better question than most people ask in a place like this.",
                "Out here, you learn very quickly what matters and what does not.",
            ]
        )
        style_line = self._style_line(chosen_style)
        fact_line = f"One thing worth keeping in mind about me is this: {chosen_fact}" if chosen_fact else ""
        hook_line = persona.fallout_hook.strip()
        follow_up = self._rng.choice(
            [
                "What part of that are you really trying to get at?",
                "So tell me, what do you want from me here in the Commonwealth?",
                "If we are going to keep talking, what angle matters most to you?",
            ]
        )

        parts = [opener, continuity + style_line]
        if fact_line:
            parts.append(fact_line)
        if hook_line:
            parts.append(f"Now imagine that colliding with this world: {hook_line}")
        parts.append(follow_up)
        return " ".join(part.strip() for part in parts if part.strip())

    def _pick_fact(self, user_message: str, facts: list[str]) -> str:
        if not facts:
            return ""
        lowered = user_message.lower()
        for fact in facts:
            tokens = [token for token in fact.lower().split() if len(token) > 4]
            if any(token in lowered for token in tokens):
                return fact
        return self._rng.choice(facts)

    def _style_line(self, style: str) -> str:
        style_lower = style.lower()
        if "measured" in style_lower or "reflective" in style_lower:
            return "I would rather answer carefully than quickly."
        if "sharp" in style_lower or "witty" in style_lower:
            return "You will get a direct answer from me, not a polished one."
        if "warm" in style_lower or "gentle" in style_lower:
            return "I am trying to meet you honestly, not impress you."
        return "I will answer plainly."


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
