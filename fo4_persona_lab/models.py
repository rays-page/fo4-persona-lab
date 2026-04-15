from __future__ import annotations

from dataclasses import dataclass, field, asdict
from pathlib import Path
import json
import re


def slugify(value: str) -> str:
    value = value.strip().lower()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    return value.strip("-") or "persona"


@dataclass
class VoiceProfile:
    mode: str = "sapi"
    voice_name: str | None = None
    prompt: str | None = None


@dataclass
class Persona:
    persona_id: str
    display_name: str
    short_bio: str
    fallout_hook: str
    public_facts: list[str] = field(default_factory=list)
    speech_style: list[str] = field(default_factory=list)
    appearance_cues: list[str] = field(default_factory=list)
    relationship_seed: str = ""
    guardrails: list[str] = field(default_factory=list)
    voice: VoiceProfile = field(default_factory=VoiceProfile)

    @classmethod
    def from_json(cls, path: Path) -> "Persona":
        payload = json.loads(path.read_text(encoding="utf-8"))
        voice_payload = payload.get("voice") or {}
        return cls(
            persona_id=payload["persona_id"],
            display_name=payload["display_name"],
            short_bio=payload["short_bio"],
            fallout_hook=payload["fallout_hook"],
            public_facts=list(payload.get("public_facts", [])),
            speech_style=list(payload.get("speech_style", [])),
            appearance_cues=list(payload.get("appearance_cues", [])),
            relationship_seed=payload.get("relationship_seed", ""),
            guardrails=list(payload.get("guardrails", [])),
            voice=VoiceProfile(
                mode=voice_payload.get("mode", "sapi"),
                voice_name=voice_payload.get("voice_name"),
                prompt=voice_payload.get("prompt"),
            ),
        )

    def to_json(self) -> dict:
        data = asdict(self)
        data["voice"] = asdict(self.voice)
        return data


@dataclass
class Turn:
    role: str
    text: str
    timestamp: str


@dataclass
class SessionTranscript:
    session_id: str
    persona_id: str
    turns: list[Turn] = field(default_factory=list)
    created_at: str = ""
    updated_at: str = ""

    @classmethod
    def from_json(cls, payload: dict) -> "SessionTranscript":
        return cls(
            session_id=payload["session_id"],
            persona_id=payload["persona_id"],
            created_at=payload.get("created_at", ""),
            updated_at=payload.get("updated_at", ""),
            turns=[Turn(**turn) for turn in payload.get("turns", [])],
        )

    def to_json(self) -> dict:
        return {
            "session_id": self.session_id,
            "persona_id": self.persona_id,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "turns": [asdict(turn) for turn in self.turns],
        }


def load_personas(personas_dir: Path) -> dict[str, Persona]:
    personas: dict[str, Persona] = {}
    for path in sorted(personas_dir.glob("*.json")):
        persona = Persona.from_json(path)
        personas[persona.persona_id] = persona
    return personas
