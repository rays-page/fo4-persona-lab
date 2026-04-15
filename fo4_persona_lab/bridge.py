from __future__ import annotations

from dataclasses import dataclass, field

from .service import PersonaService


@dataclass
class BridgeChatResult:
    request_id: int
    accepted: bool
    session_id: str | None = None
    persona_id: str | None = None
    reply: str = ""
    audio_file_path: str | None = None
    warnings: list[str] = field(default_factory=list)
    error: str = ""


class BridgeGateway:
    def __init__(self, service: PersonaService) -> None:
        self.service = service

    def submit_player_text(
        self,
        request_id: int,
        persona_id: str,
        player_text: str,
        session_id: str | None = None,
        player_name: str = "Sole Survivor",
        location: str = "The Commonwealth",
        speak: bool = True,
    ) -> BridgeChatResult:
        if request_id <= 0:
            return BridgeChatResult(
                request_id=request_id,
                accepted=False,
                error="request_id must be a positive integer.",
            )

        message = player_text.strip()
        if not message:
            return BridgeChatResult(
                request_id=request_id,
                accepted=False,
                error="Typed input was empty.",
            )

        try:
            response = self.service.chat(
                persona_id=persona_id,
                message=message,
                session_id=session_id,
                player_name=player_name,
                location=location,
                speak=speak,
            )
        except Exception as exc:  # noqa: BLE001
            return BridgeChatResult(
                request_id=request_id,
                accepted=False,
                error=str(exc),
            )

        return BridgeChatResult(
            request_id=request_id,
            accepted=True,
            session_id=response.session_id,
            persona_id=response.persona_id,
            reply=response.reply,
            audio_file_path=str(response.audio_file_path) if response.audio_file_path is not None else None,
            warnings=response.warnings,
        )
