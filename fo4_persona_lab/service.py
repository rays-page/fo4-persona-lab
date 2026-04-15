from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .backends import DialogueBackend, OpenAIChatBackend, RuleBasedBackend
from .config import Settings
from .memory import ConversationStore
from .models import Persona, load_personas
from .prompting import build_system_prompt
from .tts import NullSpeechBackend, OpenAISpeechBackend, SapiSpeechBackend, SpeechBackend


@dataclass
class ChatResponse:
    session_id: str
    persona_id: str
    reply: str
    audio_url: str | None


class PersonaService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.personas = load_personas(settings.personas_dir)
        self.store = ConversationStore(settings.sessions_dir)
        self.dialogue_backend = self._build_dialogue_backend()
        self.speech_backend = self._build_speech_backend()

    def list_personas(self) -> list[dict]:
        return [
            {
                "persona_id": persona.persona_id,
                "display_name": persona.display_name,
                "short_bio": persona.short_bio,
                "fallout_hook": persona.fallout_hook,
                "appearance_cues": persona.appearance_cues,
            }
            for persona in self.personas.values()
        ]

    def get_persona(self, persona_id: str) -> Persona:
        try:
            return self.personas[persona_id]
        except KeyError as exc:
            raise KeyError(f"Unknown persona_id: {persona_id}") from exc

    def chat(
        self,
        persona_id: str,
        message: str,
        session_id: str | None = None,
        player_name: str = "Sole Survivor",
        location: str = "The Commonwealth",
        speak: bool = True,
    ) -> ChatResponse:
        persona = self.get_persona(persona_id)
        session = self.store.ensure(persona_id, session_id)
        history = self.store.recent_turns(session, limit=12)
        system_prompt = build_system_prompt(persona, player_name, location, history)

        self.store.append_turn(session, "user", message)
        reply = self.dialogue_backend.generate_reply(system_prompt, history, message, persona)
        self.store.append_turn(session, "assistant", reply)

        audio_url: str | None = None
        if speak:
            audio_path = self.speech_backend.synthesize(reply, persona, session.session_id)
            if audio_path is not None:
                audio_url = self._audio_url(audio_path)

        return ChatResponse(
            session_id=session.session_id,
            persona_id=persona.persona_id,
            reply=reply,
            audio_url=audio_url,
        )

    def _audio_url(self, path: Path) -> str:
        return f"/audio/{path.name}"

    def _build_dialogue_backend(self) -> DialogueBackend:
        if self.settings.backend == "openai":
            if not self.settings.openai_api_key:
                raise RuntimeError("FO4_PERSONA_BACKEND=openai requires OPENAI_API_KEY.")
            return OpenAIChatBackend(
                api_key=self.settings.openai_api_key,
                model=self.settings.openai_chat_model,
            )
        return RuleBasedBackend()

    def _build_speech_backend(self) -> SpeechBackend:
        if self.settings.tts_backend == "none":
            return NullSpeechBackend()
        if self.settings.tts_backend == "openai":
            if not self.settings.openai_api_key:
                raise RuntimeError("FO4_PERSONA_TTS_BACKEND=openai requires OPENAI_API_KEY.")
            return OpenAISpeechBackend(
                audio_dir=self.settings.audio_dir,
                api_key=self.settings.openai_api_key,
                model=self.settings.openai_tts_model,
                voice=self.settings.openai_tts_voice,
            )
        return SapiSpeechBackend(
            audio_dir=self.settings.audio_dir,
            default_voice=self.settings.sapi_voice,
        )
