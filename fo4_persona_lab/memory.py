from __future__ import annotations

from datetime import datetime, UTC
from pathlib import Path
from uuid import uuid4
import json

from .models import SessionTranscript, Turn


def utc_now() -> str:
    return datetime.now(UTC).isoformat()


class ConversationStore:
    def __init__(self, sessions_dir: Path) -> None:
        self.sessions_dir = sessions_dir
        self.sessions_dir.mkdir(parents=True, exist_ok=True)

    def _path_for(self, session_id: str) -> Path:
        return self.sessions_dir / f"{session_id}.json"

    def create(self, persona_id: str) -> SessionTranscript:
        stamp = utc_now()
        session = SessionTranscript(
            session_id=str(uuid4()),
            persona_id=persona_id,
            created_at=stamp,
            updated_at=stamp,
        )
        self.save(session)
        return session

    def load(self, session_id: str) -> SessionTranscript | None:
        path = self._path_for(session_id)
        if not path.exists():
            return None
        payload = json.loads(path.read_text(encoding="utf-8"))
        return SessionTranscript.from_json(payload)

    def save(self, session: SessionTranscript) -> None:
        session.updated_at = utc_now()
        self._path_for(session.session_id).write_text(
            json.dumps(session.to_json(), indent=2),
            encoding="utf-8",
        )

    def ensure(self, persona_id: str, session_id: str | None) -> SessionTranscript:
        if session_id:
            existing = self.load(session_id)
            if existing is not None:
                if existing.persona_id != persona_id:
                    raise ValueError(
                        f"Session {session_id} belongs to persona "
                        f"{existing.persona_id}, not {persona_id}."
                    )
                return existing
        return self.create(persona_id)

    def append_turn(self, session: SessionTranscript, role: str, text: str) -> None:
        session.turns.append(Turn(role=role, text=text, timestamp=utc_now()))
        self.save(session)

    def recent_turns(self, session: SessionTranscript, limit: int = 10) -> list[Turn]:
        return session.turns[-limit:]

    def update_memory_summary(self, session: SessionTranscript, summary: str) -> None:
        session.memory_summary = summary.strip()
        self.save(session)
