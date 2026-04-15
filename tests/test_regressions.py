from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from contextlib import contextmanager
from dataclasses import replace
from http import HTTPStatus
from http.client import HTTPConnection
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import json
import shutil
import subprocess
import sys
import threading
import unittest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fo4_persona_lab.config import load_settings
from fo4_persona_lab.bridge import BridgeChatResult
from fo4_persona_lab.server import PersonaRequestHandler
from fo4_persona_lab.service import PersonaService


class _QuietPersonaRequestHandler(PersonaRequestHandler):
    def log_message(self, _format: str, *args: object) -> None:  # noqa: A003
        del args


@contextmanager
def run_persona_server():
    server = ThreadingHTTPServer(("127.0.0.1", 0), _QuietPersonaRequestHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield server.server_address[1]
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


@contextmanager
def run_fake_bridge_server(payload: dict):
    body = json.dumps(payload).encode("utf-8")

    class FakeBridgeHandler(BaseHTTPRequestHandler):
        def do_POST(self) -> None:  # noqa: N802
            content_length = int(self.headers.get("Content-Length", "0"))
            self.rfile.read(content_length)
            if self.path != "/api/bridge/chat":
                self.send_error(HTTPStatus.NOT_FOUND)
                return
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, _format: str, *args: object) -> None:  # noqa: A003
            del args

    server = ThreadingHTTPServer(("127.0.0.1", 0), FakeBridgeHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield server.server_address[1]
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


@contextmanager
def patch_server_bridge(fake_bridge: object):
    import fo4_persona_lab.server as server_module

    original = server_module.BRIDGE
    server_module.BRIDGE = fake_bridge
    try:
        yield
    finally:
        server_module.BRIDGE = original


class ServerSecurityTests(unittest.TestCase):
    def test_health_endpoint_reports_ready_status(self) -> None:
        with run_persona_server() as port:
            conn = HTTPConnection("127.0.0.1", port, timeout=5)
            conn.request("GET", "/api/health")
            response = conn.getresponse()
            payload = json.loads(response.read().decode("utf-8"))
            conn.close()

        self.assertEqual(response.status, HTTPStatus.OK)
        self.assertEqual(payload.get("status"), "ok")
        self.assertGreaterEqual(int(payload.get("persona_count", 0)), 1)

    def test_audio_path_traversal_is_rejected(self) -> None:
        with run_persona_server() as port:
            conn = HTTPConnection("127.0.0.1", port, timeout=5)
            conn.request("GET", "/audio/../../README.md")
            response = conn.getresponse()
            payload = json.loads(response.read().decode("utf-8"))
            conn.close()

        self.assertEqual(response.status, HTTPStatus.BAD_REQUEST)
        self.assertEqual(payload.get("error"), "Invalid path")

    def test_audio_backslash_traversal_is_rejected(self) -> None:
        with run_persona_server() as port:
            conn = HTTPConnection("127.0.0.1", port, timeout=5)
            conn.request("GET", "/audio/..%5C..%5CREADME.md")
            response = conn.getresponse()
            payload = json.loads(response.read().decode("utf-8"))
            conn.close()

        self.assertEqual(response.status, HTTPStatus.BAD_REQUEST)
        self.assertEqual(payload.get("error"), "Invalid path")

    def test_bridge_chat_includes_audio_url_when_audio_file_path_present(self) -> None:
        class FakeBridge:
            def submit_player_text(self, request_id: int, persona_id: str, player_text: str, **kwargs):
                del player_text, kwargs
                return BridgeChatResult(
                    request_id=request_id,
                    accepted=True,
                    session_id="session-123",
                    persona_id=persona_id,
                    reply="Voice line ready.",
                    audio_file_path=r"C:\tmp\voice test.wav",
                    warnings=[],
                )

        body = json.dumps(
            {
                "request_id": 77,
                "persona_id": "steve-jobs",
                "message": "test",
            }
        ).encode("utf-8")

        with patch_server_bridge(FakeBridge()):
            with run_persona_server() as port:
                conn = HTTPConnection("127.0.0.1", port, timeout=5)
                conn.request(
                    "POST",
                    "/api/bridge/chat",
                    body=body,
                    headers={"Content-Type": "application/json"},
                )
                response = conn.getresponse()
                payload = json.loads(response.read().decode("utf-8"))
                conn.close()

        self.assertEqual(response.status, HTTPStatus.OK)
        self.assertEqual(payload.get("audio_file_path"), r"C:\tmp\voice test.wav")
        self.assertEqual(payload.get("audio_url"), "/audio/voice%20test.wav")

    def test_invalid_content_length_header_is_rejected(self) -> None:
        with run_persona_server() as port:
            conn = HTTPConnection("127.0.0.1", port, timeout=5)
            conn.putrequest("POST", "/api/chat")
            conn.putheader("Content-Type", "application/json")
            conn.putheader("Content-Length", "abc")
            conn.endheaders()
            conn.send(b"{}")
            response = conn.getresponse()
            payload = json.loads(response.read().decode("utf-8"))
            conn.close()

        self.assertEqual(response.status, HTTPStatus.BAD_REQUEST)
        self.assertEqual(payload.get("error"), "Invalid Content-Length header.")


class ConcurrencyRegressionTests(unittest.TestCase):
    def test_parallel_chat_on_single_session_keeps_valid_json(self) -> None:
        settings = replace(load_settings(), tts_backend="none")
        service = PersonaService(settings)
        persona_id = service.list_personas()[0]["persona_id"]
        session = service.create_session(persona_id)
        session_path = settings.sessions_dir / f"{session.session_id}.json"

        try:
            call_count = 40

            def run_chat(index: int) -> None:
                service.chat(
                    persona_id=persona_id,
                    message=f"concurrent message {index}",
                    session_id=session.session_id,
                    speak=False,
                )

            with ThreadPoolExecutor(max_workers=16) as executor:
                futures = [executor.submit(run_chat, i) for i in range(call_count)]
                for future in as_completed(futures):
                    future.result()

            loaded = service.get_session(session.session_id)
            self.assertEqual(len(loaded.turns), call_count * 2)

            payload = json.loads(session_path.read_text(encoding="utf-8"))
            self.assertEqual(len(payload.get("turns", [])), call_count * 2)
        finally:
            session_path.unlink(missing_ok=True)


@unittest.skipUnless(
    shutil.which("g++") is not None and shutil.which("powershell") is not None,
    "Native bridge regression tests require g++ and PowerShell.",
)
class NativeBridgeRegressionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.repo_root = ROOT
        cls.exe_path = cls.repo_root / "native_bridge" / "build" / "f4rp_bridge_smoketest.exe"
        build_script = cls.repo_root / "native_bridge" / "build_smoketest.ps1"
        subprocess.run(
            [
                "powershell",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                str(build_script),
            ],
            cwd=cls.repo_root,
            check=True,
            capture_output=True,
            text=True,
        )
        if not cls.exe_path.exists():
            raise RuntimeError(f"Missing native bridge smoketest executable: {cls.exe_path}")

    def run_smoketest(self, port: int) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [str(self.exe_path), "127.0.0.1", str(port)],
            cwd=self.repo_root,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=30,
        )

    def test_unicode_escaped_reply_roundtrips_from_json(self) -> None:
        with run_fake_bridge_server(
            {
                "accepted": True,
                "request_id": 1,
                "session_id": "abc123",
                "reply": "Caf\u00e9 level check",
                "warnings": [],
            }
        ) as port:
            completed = self.run_smoketest(port)

        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertIn("Reply:", completed.stdout)
        self.assertIn("level check", completed.stdout)
        self.assertNotIn("Caf? level check", completed.stdout)

    def test_audio_file_path_is_used_when_present(self) -> None:
        with run_fake_bridge_server(
            {
                "accepted": True,
                "request_id": 1,
                "session_id": "abc123",
                "reply": "ok",
                "audio_file_path": "C:/tmp/voice.wav",
                "warnings": [],
            }
        ) as port:
            completed = self.run_smoketest(port)

        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertIn("Audio file path: C:/tmp/voice.wav", completed.stdout)

    def test_audio_url_is_used_as_fallback_when_audio_file_path_is_missing(self) -> None:
        with run_fake_bridge_server(
            {
                "accepted": True,
                "request_id": 1,
                "session_id": "abc123",
                "reply": "ok",
                "audio_url": "/audio/fallback.wav",
                "warnings": [],
            }
        ) as port:
            completed = self.run_smoketest(port)

        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertIn("Audio file path: /audio/fallback.wav", completed.stdout)


if __name__ == "__main__":
    unittest.main()
