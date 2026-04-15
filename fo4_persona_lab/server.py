from __future__ import annotations

from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import json
import mimetypes
import threading
import traceback
import urllib.parse

from .bridge import BridgeGateway
from .config import load_settings
from .service import PersonaService


SETTINGS = load_settings()
SERVICE = PersonaService(SETTINGS)
BRIDGE = BridgeGateway(SERVICE)
REQUEST_ID_LOCK = threading.Lock()
NEXT_REQUEST_ID = 1


class ValidationError(ValueError):
    pass


class PersonaRequestHandler(BaseHTTPRequestHandler):
    server_version = "FO4PersonaLab/0.1"

    def do_GET(self) -> None:
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        if path == "/api/personas":
            self._send_json({"personas": SERVICE.list_personas()})
            return

        if path.startswith("/api/personas/"):
            persona_id = urllib.parse.unquote(path.removeprefix("/api/personas/")).strip()
            if not persona_id:
                self._send_json({"error": "Missing persona_id."}, status=HTTPStatus.BAD_REQUEST)
                return
            try:
                self._send_json({"persona": SERVICE.get_persona_summary(persona_id)})
            except KeyError as exc:
                self._send_json({"error": str(exc)}, status=HTTPStatus.NOT_FOUND)
            return

        if path.startswith("/api/sessions/"):
            session_id = urllib.parse.unquote(path.removeprefix("/api/sessions/")).strip()
            if not session_id:
                self._send_json({"error": "Missing session_id."}, status=HTTPStatus.BAD_REQUEST)
                return
            try:
                self._send_json({"session": SERVICE.session_payload(session_id)})
            except KeyError as exc:
                self._send_json({"error": str(exc)}, status=HTTPStatus.NOT_FOUND)
            return

        if path.startswith("/audio/"):
            self._serve_audio_asset(path)
            return

        self._serve_web_asset(path)

    def do_POST(self) -> None:
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == "/api/sessions":
            self._handle_create_session()
            return

        if parsed.path == "/api/bridge/chat":
            self._handle_bridge_chat()
            return

        if parsed.path == "/api/chat":
            self._handle_chat()
            return

        self._send_json({"error": "Not found"}, status=HTTPStatus.NOT_FOUND)

    def _handle_create_session(self) -> None:
        try:
            payload = self._read_json_body()
            persona_id = self._required_string(payload, "persona_id", max_length=128)
            session = SERVICE.create_session(persona_id)
            self._send_json(
                {
                    "session_id": session.session_id,
                    "persona_id": session.persona_id,
                    "created_at": session.created_at,
                },
                status=HTTPStatus.CREATED,
            )
        except ValidationError as exc:
            self._send_json({"error": str(exc)}, status=HTTPStatus.BAD_REQUEST)
        except KeyError as exc:
            self._send_json({"error": str(exc)}, status=HTTPStatus.NOT_FOUND)
        except Exception as exc:  # noqa: BLE001
            self.log_error("%s", traceback.format_exc())
            self._send_json({"error": str(exc)}, status=HTTPStatus.INTERNAL_SERVER_ERROR)

    def _handle_chat(self) -> None:
        try:
            payload = self._read_json_body()
            persona_id = self._required_string(payload, "persona_id", max_length=128)
            message = self._required_string(payload, "message", max_length=4000).strip()
            session_id = self._optional_string(payload, "session_id", max_length=128)
            player_name = self._optional_string(payload, "player_name", max_length=80) or "Sole Survivor"
            location = self._optional_string(payload, "location", max_length=120) or "The Commonwealth"
            speak = self._optional_bool(payload, "speak", default=True)

            response = SERVICE.chat(
                persona_id=persona_id,
                message=message,
                session_id=session_id,
                player_name=player_name,
                location=location,
                speak=speak,
            )
            self._send_json(
                {
                    "session_id": response.session_id,
                    "persona_id": response.persona_id,
                    "reply": response.reply,
                    "audio_url": response.audio_url,
                    "warnings": response.warnings,
                }
            )
        except ValidationError as exc:
            self._send_json({"error": str(exc)}, status=HTTPStatus.BAD_REQUEST)
        except (KeyError, ValueError) as exc:
            self._send_json({"error": str(exc)}, status=HTTPStatus.BAD_REQUEST)
        except Exception as exc:  # noqa: BLE001
            self.log_error("%s", traceback.format_exc())
            self._send_json({"error": str(exc)}, status=HTTPStatus.INTERNAL_SERVER_ERROR)

    def _handle_bridge_chat(self) -> None:
        try:
            payload = self._read_json_body()
            request_id = self._optional_positive_int(payload, "request_id")
            if request_id is None:
                request_id = self._next_request_id()

            persona_id = self._required_string(payload, "persona_id", max_length=128)
            message = self._required_string(payload, "message", max_length=4000)
            session_id = self._optional_string(payload, "session_id", max_length=128)
            player_name = self._optional_string(payload, "player_name", max_length=80) or "Sole Survivor"
            location = self._optional_string(payload, "location", max_length=120) or "The Commonwealth"
            speak = self._optional_bool(payload, "speak", default=True)

            result = BRIDGE.submit_player_text(
                request_id=request_id,
                persona_id=persona_id,
                player_text=message,
                session_id=session_id,
                player_name=player_name,
                location=location,
                speak=speak,
            )
            self._send_json(
                {
                    "accepted": result.accepted,
                    "request_id": result.request_id,
                    "session_id": result.session_id,
                    "persona_id": result.persona_id,
                    "reply": result.reply,
                    "audio_file_path": result.audio_file_path,
                    "warnings": result.warnings,
                    "error": result.error,
                }
            )
        except ValidationError as exc:
            self._send_json({"error": str(exc)}, status=HTTPStatus.BAD_REQUEST)
        except Exception as exc:  # noqa: BLE001
            self.log_error("%s", traceback.format_exc())
            self._send_json({"error": str(exc)}, status=HTTPStatus.INTERNAL_SERVER_ERROR)

    def _read_json_body(self) -> dict:
        content_length = int(self.headers.get("Content-Length", "0"))
        if content_length <= 0:
            raise ValidationError("Expected a JSON request body.")
        raw = self.rfile.read(content_length)
        try:
            payload = json.loads(raw.decode("utf-8"))
        except json.JSONDecodeError as exc:
            raise ValidationError(f"Invalid JSON body: {exc.msg}") from exc
        if not isinstance(payload, dict):
            raise ValidationError("JSON body must be an object.")
        return payload

    def _required_string(self, payload: dict, key: str, max_length: int) -> str:
        value = payload.get(key)
        if not isinstance(value, str):
            raise ValidationError(f"Field '{key}' must be a string.")
        trimmed = value.strip()
        if not trimmed:
            raise ValidationError(f"Field '{key}' cannot be empty.")
        if len(trimmed) > max_length:
            raise ValidationError(f"Field '{key}' exceeds max length ({max_length}).")
        return trimmed

    def _optional_string(self, payload: dict, key: str, max_length: int) -> str | None:
        value = payload.get(key)
        if value is None:
            return None
        if not isinstance(value, str):
            raise ValidationError(f"Field '{key}' must be a string when provided.")
        trimmed = value.strip()
        if not trimmed:
            return None
        if len(trimmed) > max_length:
            raise ValidationError(f"Field '{key}' exceeds max length ({max_length}).")
        return trimmed

    def _optional_bool(self, payload: dict, key: str, default: bool) -> bool:
        value = payload.get(key, default)
        if isinstance(value, bool):
            return value
        raise ValidationError(f"Field '{key}' must be a boolean.")

    def _optional_positive_int(self, payload: dict, key: str) -> int | None:
        value = payload.get(key)
        if value is None:
            return None
        if not isinstance(value, int):
            raise ValidationError(f"Field '{key}' must be an integer when provided.")
        if value <= 0:
            raise ValidationError(f"Field '{key}' must be greater than zero.")
        return value

    def _next_request_id(self) -> int:
        global NEXT_REQUEST_ID
        with REQUEST_ID_LOCK:
            request_id = NEXT_REQUEST_ID
            NEXT_REQUEST_ID += 1
        return request_id

    def _serve_web_asset(self, raw_path: str) -> None:
        normalized = raw_path.strip("/") or "index.html"
        target = (SETTINGS.web_dir / normalized).resolve()
        if SETTINGS.web_dir.resolve() not in target.parents and target != SETTINGS.web_dir.resolve():
            self._send_json({"error": "Invalid path"}, status=HTTPStatus.BAD_REQUEST)
            return

        if target.is_dir():
            target = target / "index.html"

        if not target.exists():
            target = SETTINGS.web_dir / "index.html"

        self._serve_file(target)

    def _serve_audio_asset(self, raw_path: str) -> None:
        normalized = urllib.parse.unquote(raw_path.removeprefix("/audio/")).lstrip("/")
        if not normalized:
            self._send_json({"error": "Missing audio path"}, status=HTTPStatus.BAD_REQUEST)
            return

        audio_root = SETTINGS.audio_dir.resolve()
        target = (audio_root / normalized).resolve()
        if audio_root not in target.parents:
            self._send_json({"error": "Invalid path"}, status=HTTPStatus.BAD_REQUEST)
            return

        self._serve_file(target)

    def _serve_file(self, path: Path) -> None:
        if not path.exists() or not path.is_file():
            self.send_error(HTTPStatus.NOT_FOUND)
            return

        mime_type, _ = mimetypes.guess_type(path.name)
        data = path.read_bytes()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", mime_type or "application/octet-stream")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _send_json(self, payload: dict | list, status: HTTPStatus = HTTPStatus.OK) -> None:
        data = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


def main() -> None:
    server = ThreadingHTTPServer((SETTINGS.host, SETTINGS.port), PersonaRequestHandler)
    print(f"FO4 Persona Lab running at http://{SETTINGS.host}:{SETTINGS.port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
