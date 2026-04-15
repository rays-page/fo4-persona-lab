from __future__ import annotations

from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import json
import mimetypes
import traceback
import urllib.parse

from .config import load_settings
from .service import PersonaService


SETTINGS = load_settings()
SERVICE = PersonaService(SETTINGS)


class PersonaRequestHandler(BaseHTTPRequestHandler):
    server_version = "FO4PersonaLab/0.1"

    def do_GET(self) -> None:
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        if path == "/api/personas":
            self._send_json({"personas": SERVICE.list_personas()})
            return

        if path.startswith("/audio/"):
            self._serve_file(SETTINGS.audio_dir / path.removeprefix("/audio/"))
            return

        self._serve_web_asset(path)

    def do_POST(self) -> None:
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path != "/api/chat":
            self._send_json({"error": "Not found"}, status=HTTPStatus.NOT_FOUND)
            return

        try:
            payload = self._read_json_body()
            response = SERVICE.chat(
                persona_id=payload["persona_id"],
                message=payload["message"].strip(),
                session_id=payload.get("session_id"),
                player_name=payload.get("player_name", "Sole Survivor"),
                location=payload.get("location", "The Commonwealth"),
                speak=bool(payload.get("speak", True)),
            )
            self._send_json(
                {
                    "session_id": response.session_id,
                    "persona_id": response.persona_id,
                    "reply": response.reply,
                    "audio_url": response.audio_url,
                }
            )
        except KeyError as exc:
            self._send_json({"error": str(exc)}, status=HTTPStatus.BAD_REQUEST)
        except Exception as exc:  # noqa: BLE001
            self.log_error("%s", traceback.format_exc())
            self._send_json({"error": str(exc)}, status=HTTPStatus.INTERNAL_SERVER_ERROR)

    def _read_json_body(self) -> dict:
        content_length = int(self.headers.get("Content-Length", "0"))
        if content_length <= 0:
            raise ValueError("Expected a JSON request body.")
        raw = self.rfile.read(content_length)
        return json.loads(raw.decode("utf-8"))

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

    def _send_json(self, payload: dict, status: HTTPStatus = HTTPStatus.OK) -> None:
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
