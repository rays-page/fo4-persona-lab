from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from uuid import uuid4
import json
import subprocess
import urllib.error
import urllib.request

from .models import Persona


class SpeechBackend(ABC):
    @abstractmethod
    def synthesize(self, text: str, persona: Persona, session_id: str) -> Path | None:
        raise NotImplementedError


class NullSpeechBackend(SpeechBackend):
    def synthesize(self, text: str, persona: Persona, session_id: str) -> Path | None:
        del text, persona, session_id
        return None


class SapiSpeechBackend(SpeechBackend):
    def __init__(self, audio_dir: Path, default_voice: str | None = None) -> None:
        self.audio_dir = audio_dir
        self.default_voice = default_voice

    def synthesize(self, text: str, persona: Persona, session_id: str) -> Path | None:
        output_path = self.audio_dir / f"{session_id}_{uuid4().hex}.wav"
        voice_name = persona.voice.voice_name or self.default_voice
        escaped_text = text.replace("'", "''")
        escaped_output = str(output_path).replace("'", "''")

        lines = [
            "Add-Type -AssemblyName System.Speech",
            "$synth = New-Object System.Speech.Synthesis.SpeechSynthesizer",
        ]
        if voice_name:
            escaped_voice = voice_name.replace("'", "''")
            lines.append(f"$synth.SelectVoice('{escaped_voice}')")
        lines.extend(
            [
                f"$synth.SetOutputToWaveFile('{escaped_output}')",
                f"$synth.Speak('{escaped_text}')",
                "$synth.Dispose()",
            ]
        )
        command = "; ".join(lines)
        completed = subprocess.run(
            ["powershell", "-NoProfile", "-Command", command],
            capture_output=True,
            text=True,
            check=False,
        )
        if completed.returncode != 0:
            raise RuntimeError(completed.stderr.strip() or "Windows SAPI synthesis failed.")
        return output_path


class OpenAISpeechBackend(SpeechBackend):
    def __init__(
        self,
        audio_dir: Path,
        api_key: str,
        model: str,
        voice: str,
    ) -> None:
        self.audio_dir = audio_dir
        self.api_key = api_key
        self.model = model
        self.voice = voice
        self.url = "https://api.openai.com/v1/audio/speech"

    def synthesize(self, text: str, persona: Persona, session_id: str) -> Path | None:
        output_path = self.audio_dir / f"{session_id}_{uuid4().hex}.wav"
        payload = {
            "model": self.model,
            "input": text,
            "voice": self.voice,
            "response_format": "wav",
        }
        if persona.voice.prompt and self.model == "gpt-4o-mini-tts":
            payload["instructions"] = persona.voice.prompt

        request = urllib.request.Request(
            self.url,
            data=json.dumps(payload).encode("utf-8"),
            method="POST",
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                output_path.write_bytes(response.read())
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"OpenAI speech request failed: {exc.code} {detail}") from exc
        except urllib.error.URLError as exc:
            raise RuntimeError(f"OpenAI speech request failed: {exc}") from exc
        return output_path
