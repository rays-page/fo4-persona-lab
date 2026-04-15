from __future__ import annotations

from datetime import datetime
import threading
import tkinter as tk
from tkinter import ttk

from .bridge import BridgeChatResult, BridgeGateway
from .config import load_settings
from .service import PersonaService

try:
    import winsound
except ImportError:  # pragma: no cover - winsound is Windows-only
    winsound = None


class OverlayApp:
    def __init__(self) -> None:
        self.settings = load_settings()
        self.service = PersonaService(self.settings)
        self.bridge = BridgeGateway(self.service)
        self.root = tk.Tk()
        self.root.title("FO4 Persona Overlay")
        self.root.geometry("860x700")
        self.root.configure(bg="#10140f")
        self.root.attributes("-topmost", True)

        self.session_id: str | None = None
        self.last_request_id = 0
        self._busy = False
        self._build_ui()
        self._load_personas()
        self._append_system("Overlay ready (external bridge mode). Pick a persona and start typing.")

    def _build_ui(self) -> None:
        frame = ttk.Frame(self.root, padding=12)
        frame.pack(fill=tk.BOTH, expand=True)

        top = ttk.Frame(frame)
        top.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(top, text="Persona").grid(row=0, column=0, sticky=tk.W)
        self.persona_var = tk.StringVar()
        self.persona_box = ttk.Combobox(top, textvariable=self.persona_var, state="readonly", width=28)
        self.persona_box.grid(row=1, column=0, padx=(0, 10), sticky=tk.W)
        self.persona_box.bind("<<ComboboxSelected>>", self._on_persona_changed)

        ttk.Label(top, text="Player").grid(row=0, column=1, sticky=tk.W)
        self.player_var = tk.StringVar(value="Sole Survivor")
        self.player_entry = ttk.Entry(top, textvariable=self.player_var, width=22)
        self.player_entry.grid(row=1, column=1, padx=(0, 10), sticky=tk.W)

        ttk.Label(top, text="Location").grid(row=0, column=2, sticky=tk.W)
        self.location_var = tk.StringVar(value="Diamond City")
        self.location_entry = ttk.Entry(top, textvariable=self.location_var, width=26)
        self.location_entry.grid(row=1, column=2, padx=(0, 10), sticky=tk.W)

        self.speak_var = tk.BooleanVar(value=True)
        self.speak_check = ttk.Checkbutton(top, text="Voice reply", variable=self.speak_var)
        self.speak_check.grid(row=1, column=3, sticky=tk.W)

        controls = ttk.Frame(frame)
        controls.pack(fill=tk.X, pady=(0, 10))

        self.new_session_btn = ttk.Button(controls, text="New Session", command=self._new_session)
        self.new_session_btn.pack(side=tk.LEFT, padx=(0, 8))
        self.clear_btn = ttk.Button(controls, text="Clear Transcript", command=self._clear_transcript)
        self.clear_btn.pack(side=tk.LEFT, padx=(0, 8))

        self.session_label_var = tk.StringVar(value="Session: not started")
        ttk.Label(controls, textvariable=self.session_label_var).pack(side=tk.LEFT, padx=(8, 0))

        self.transcript = tk.Text(
            frame,
            wrap=tk.WORD,
            height=24,
            bg="#0f120e",
            fg="#d5f2c5",
            insertbackground="#d5f2c5",
            relief=tk.FLAT,
        )
        self.transcript.pack(fill=tk.BOTH, expand=True)
        self.transcript.configure(state=tk.DISABLED)

        composer = ttk.Frame(frame)
        composer.pack(fill=tk.X, pady=(10, 0))

        self.message_var = tk.StringVar()
        self.message_entry = ttk.Entry(composer, textvariable=self.message_var)
        self.message_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 8))
        self.message_entry.bind("<Return>", self._on_submit)

        self.send_btn = ttk.Button(composer, text="Send", command=self._send_message)
        self.send_btn.pack(side=tk.LEFT)

    def _load_personas(self) -> None:
        personas = self.service.list_personas()
        if not personas:
            raise RuntimeError("No persona manifests found.")
        self.persona_lookup = {item["display_name"]: item["persona_id"] for item in personas}
        names = sorted(self.persona_lookup)
        self.persona_box["values"] = names
        self.persona_var.set(names[0])

    def _on_persona_changed(self, _event: object | None = None) -> None:
        self.session_id = None
        self._refresh_session_label()
        self._append_system(f"Persona changed to {self.persona_var.get()}. Start a new session when ready.")

    def _selected_persona_id(self) -> str:
        selected = self.persona_var.get().strip()
        persona_id = self.persona_lookup.get(selected)
        if not persona_id:
            raise RuntimeError("Select a persona first.")
        return persona_id

    def _refresh_session_label(self) -> None:
        short = self.session_id[:8] if self.session_id else "not started"
        self.session_label_var.set(f"Session: {short}")

    def _new_session(self) -> None:
        try:
            persona_id = self._selected_persona_id()
            session = self.service.create_session(persona_id)
            self.session_id = session.session_id
            self._refresh_session_label()
            self._append_system(f"Started new session for {self.persona_var.get()}.")
        except Exception as exc:  # noqa: BLE001
            self._append_system(f"Session error: {exc}")

    def _clear_transcript(self) -> None:
        self.transcript.configure(state=tk.NORMAL)
        self.transcript.delete("1.0", tk.END)
        self.transcript.configure(state=tk.DISABLED)
        self._append_system("Transcript cleared.")

    def _on_submit(self, _event: object | None = None) -> str | None:
        self._send_message()
        return "break"

    def _set_busy(self, busy: bool) -> None:
        self._busy = busy
        state = tk.DISABLED if busy else tk.NORMAL
        self.send_btn.configure(state=state)
        self.new_session_btn.configure(state=state)
        self.clear_btn.configure(state=state)
        self.message_entry.configure(state=state)

    def _send_message(self) -> None:
        if self._busy:
            return

        text = self.message_var.get().strip()
        if not text:
            return

        try:
            persona_id = self._selected_persona_id()
        except Exception as exc:  # noqa: BLE001
            self._append_system(str(exc))
            return

        if not self.session_id:
            self._new_session()
            if not self.session_id:
                return

        self.message_var.set("")
        self._append_turn("You", text)
        self.last_request_id += 1
        request_id = self.last_request_id
        self._set_busy(True)
        worker = threading.Thread(
            target=self._chat_worker,
            kwargs={
                "request_id": request_id,
                "persona_id": persona_id,
                "message": text,
                "session_id": self.session_id,
                "player_name": self.player_var.get().strip() or "Sole Survivor",
                "location": self.location_var.get().strip() or "The Commonwealth",
                "speak": bool(self.speak_var.get()),
            },
            daemon=True,
        )
        worker.start()

    def _chat_worker(
        self,
        request_id: int,
        persona_id: str,
        message: str,
        session_id: str | None,
        player_name: str,
        location: str,
        speak: bool,
    ) -> None:
        response: BridgeChatResult | None = None
        error: Exception | None = None
        try:
            response = self.bridge.submit_player_text(
                request_id=request_id,
                persona_id=persona_id,
                player_text=message,
                session_id=session_id,
                player_name=player_name,
                location=location,
                speak=speak,
            )
        except Exception as exc:  # noqa: BLE001
            error = exc
        self.root.after(0, lambda: self._chat_done(response, error))

    def _chat_done(self, response: BridgeChatResult | None, error: Exception | None) -> None:
        self._set_busy(False)
        if error is not None:
            self._append_system(f"Chat error: {error}")
            return
        if response is None:
            self._append_system("Chat error: empty response.")
            return
        if not response.accepted:
            self._append_system(f"Bridge rejected request {response.request_id}: {response.error}")
            return

        self.session_id = response.session_id
        self._refresh_session_label()
        self._append_turn("Persona", response.reply)
        for warning in response.warnings:
            self._append_system(warning)
        if response.audio_url:
            self._play_audio_url(response.audio_url)

    def _play_audio_url(self, audio_url: str) -> None:
        if not audio_url.startswith("/audio/"):
            self._append_system(f"Audio generated at: {audio_url}")
            return
        path = self.settings.audio_dir / audio_url.removeprefix("/audio/")
        self._play_audio(path)

    def _play_audio(self, path) -> None:
        if winsound is None:
            self._append_system(f"Audio generated at: {path}")
            return
        try:
            winsound.PlaySound(str(path), winsound.SND_FILENAME | winsound.SND_ASYNC)
        except Exception as exc:  # noqa: BLE001
            self._append_system(f"Audio playback failed: {exc}")

    def _append_turn(self, speaker: str, text: str) -> None:
        stamp = datetime.now().strftime("%H:%M:%S")
        self._append_line(f"[{stamp}] {speaker}: {text}")

    def _append_system(self, text: str) -> None:
        stamp = datetime.now().strftime("%H:%M:%S")
        self._append_line(f"[{stamp}] SYSTEM: {text}")

    def _append_line(self, text: str) -> None:
        self.transcript.configure(state=tk.NORMAL)
        self.transcript.insert(tk.END, text + "\n\n")
        self.transcript.see(tk.END)
        self.transcript.configure(state=tk.DISABLED)

    def run(self) -> None:
        self.root.mainloop()


def main() -> None:
    app = OverlayApp()
    app.run()


if __name__ == "__main__":
    main()
