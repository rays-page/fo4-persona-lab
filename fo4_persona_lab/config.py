from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import os


@dataclass(frozen=True)
class Settings:
    project_root: Path
    personas_dir: Path
    sessions_dir: Path
    audio_dir: Path
    web_dir: Path
    host: str
    port: int
    backend: str
    tts_backend: str
    openai_api_key: str | None
    openai_chat_model: str
    openai_tts_model: str
    openai_tts_voice: str
    sapi_voice: str | None


def load_settings() -> Settings:
    project_root = Path(__file__).resolve().parent.parent
    persons_dir = project_root / "personas"
    sessions_dir = project_root / "data" / "sessions"
    audio_dir = project_root / "data" / "audio"
    web_dir = project_root / "web"

    sessions_dir.mkdir(parents=True, exist_ok=True)
    audio_dir.mkdir(parents=True, exist_ok=True)

    return Settings(
        project_root=project_root,
        personas_dir=persons_dir,
        sessions_dir=sessions_dir,
        audio_dir=audio_dir,
        web_dir=web_dir,
        host=os.getenv("FO4_PERSONA_HOST", "127.0.0.1"),
        port=int(os.getenv("FO4_PERSONA_PORT", "8765")),
        backend=os.getenv("FO4_PERSONA_BACKEND", "rules").strip().lower(),
        tts_backend=os.getenv("FO4_PERSONA_TTS_BACKEND", "sapi").strip().lower(),
        openai_api_key=os.getenv("OPENAI_API_KEY"),
        openai_chat_model=os.getenv("OPENAI_CHAT_MODEL", "gpt-5.4-mini"),
        openai_tts_model=os.getenv("OPENAI_TTS_MODEL", "gpt-4o-mini-tts"),
        openai_tts_voice=os.getenv("OPENAI_TTS_VOICE", "alloy"),
        sapi_voice=os.getenv("FO4_PERSONA_SAPI_VOICE"),
    )
