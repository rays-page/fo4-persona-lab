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


class ServerSecurityTests(unittest.TestCase):
    def test_audio_path_traversal_is_rejected(self) -> None:
        with run_persona_server() as port:
            conn = HTTPConnection("127.0.0.1", port, timeout=5)
            conn.request("GET", "/audio/../../README.md")
            response = conn.getresponse()
            payload = json.loads(response.read().decode("utf-8"))
            conn.close()

        self.assertEqual(response.status, HTTPStatus.BAD_REQUEST)
        self.assertEqual(payload.get("error"), "Invalid path")


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
