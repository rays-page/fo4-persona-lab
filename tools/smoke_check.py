from __future__ import annotations

from dataclasses import replace
from pathlib import Path
import argparse
import json
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from fo4_persona_lab.config import load_settings
from fo4_persona_lab.service import PersonaService


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a local FO4 Persona Lab smoke check.")
    parser.add_argument(
        "--persona-id",
        default="steve-jobs",
        help="Persona id to test (defaults to steve-jobs, falls back to first available).",
    )
    parser.add_argument(
        "--test-tts",
        action="store_true",
        help="Run one additional request with voice synthesis enabled.",
    )
    args = parser.parse_args()

    settings = load_settings()
    base_service = PersonaService(replace(settings, tts_backend="none"))
    personas = base_service.list_personas()
    if not personas:
        raise SystemExit("Smoke failed: no personas were loaded.")

    requested_id = args.persona_id
    persona_ids = {item["persona_id"] for item in personas}
    persona_id = requested_id if requested_id in persona_ids else personas[0]["persona_id"]
    print(f"Using persona: {persona_id}")

    response = base_service.chat(
        persona_id=persona_id,
        message="Give me one practical design principle for surviving the Commonwealth.",
        player_name="Sole Survivor",
        location="Diamond City",
        speak=False,
    )
    if not response.reply.strip():
        raise SystemExit("Smoke failed: chat response was empty.")
    print("Chat response OK.")
    if response.warnings:
        print("Warnings:")
        for warning in response.warnings:
            print(f"  - {warning}")

    session_path = Path(settings.sessions_dir) / f"{response.session_id}.json"
    if not session_path.exists():
        raise SystemExit(f"Smoke failed: expected session file missing at {session_path}")

    payload = json.loads(session_path.read_text(encoding="utf-8"))
    if "memory_summary" not in payload:
        raise SystemExit("Smoke failed: memory_summary missing from session payload.")
    print(f"Session persistence OK: {session_path}")

    if args.test_tts:
        tts_service = PersonaService(settings)
        tts_response = tts_service.chat(
            persona_id=persona_id,
            message="Say one short line for a radio greeting.",
            player_name="Sole Survivor",
            location="The Castle",
            speak=True,
        )
        if tts_response.audio_url:
            print(f"TTS OK: {tts_response.audio_url}")
        else:
            print("TTS completed without audio output (check warnings/config).")
        if tts_response.warnings:
            print("TTS warnings:")
            for warning in tts_response.warnings:
                print(f"  - {warning}")

    print("Smoke check passed.")


if __name__ == "__main__":
    main()
