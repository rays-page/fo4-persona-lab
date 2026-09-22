# FO4 Persona Lab
Experiments with LLM-driven NPCs in Fallout 4: giving companions and settlers generated personalities and dialogue instead of fixed scripted lines.

Exploratory, far from a finished mod.

Working prototype for a Fallout 4 real-person NPC mod pipeline:

- local dialogue service,
- typed web client,
- desktop overlay client,
- persona pack tooling,
- and a source-level Fallout bridge contract.

This project is split on purpose:

- `fo4_persona_lab/` is the local AI service and browser-based typed dialogue prototype.
- `personas/` stores per-person manifests with facts, style notes, appearance cues, and voice hints.
- `game/` holds Fallout-side source stubs and notes for the later Creation Kit and F4SE bridge.
- `docs/` explains the architecture and the hard engine limitations.

## What Works Right Now

- Load persona manifests from JSON.
- Keep per-session conversation memory and rolling summaries on disk.
- Generate fallback dialogue locally with a persona-aware rule-based backend.
- Optionally call an OpenAI chat model if `OPENAI_API_KEY` is present.
- Optionally synthesize speech with:
  - built-in Windows SAPI voices, or
  - OpenAI text-to-speech if `OPENAI_API_KEY` is present.
- Serve a Fallout-style local web UI for typed conversations.
- Run a desktop always-on-top overlay client beside the game.
- Surface warnings when backend/TTS fail without dropping text replies.

## API Endpoints

- `GET /api/health`
- `GET /api/personas`
- `GET /api/personas/{persona_id}`
- `POST /api/sessions`
- `GET /api/sessions/{session_id}`
- `POST /api/chat`
- `POST /api/bridge/chat` (bridge-style handoff with `request_id`)

## What Still Needs Fallout 4 Mod Work

- Decision for current prototype: use external overlay text entry now; keep Scaleform as a future immersion upgrade.
- NPC spawning, facegen import, sound descriptors, lip-sync, and scene control still need Creation Kit work.
- Direct Papyrus-to-HTTP calls are not available in vanilla Fallout 4, so a native bridge or overlay flow is still required.

## Quick Start

```powershell
cd C:\Users\raymo_w9whwcn\OneDrive\TT\fo4_persona_lab
python -m fo4_persona_lab.server
```

Then open `http://127.0.0.1:8765`.

Optional overlay:

```powershell
python -m fo4_persona_lab.overlay
```

## Smoke Check

```powershell
python .\tools\smoke_check.py
```

Optional TTS path test:

```powershell
python .\tools\smoke_check.py --test-tts
```

Bridge endpoint soak test (short multithreaded load):

```powershell
python .\tools\bridge_soak_test.py
```

Run regression tests:

```powershell
python -m unittest -v
```

## Optional Environment Variables

```powershell
$env:OPENAI_API_KEY="..."
$env:FO4_PERSONA_BACKEND="openai"
$env:FO4_PERSONA_TTS_BACKEND="sapi"
```

Other supported variables:

- `FO4_PERSONA_HOST`
- `FO4_PERSONA_PORT`
- `OPENAI_CHAT_MODEL`
- `OPENAI_TTS_MODEL`
- `OPENAI_TTS_VOICE`
- `FO4_PERSONA_SAPI_VOICE`

## Persona Creation

Create a manifest skeleton:

```powershell
python .\tools\create_persona_manifest.py "Carl Sagan"
```

Then edit the new JSON file in `personas/`.

Create a full persona pack scaffold:

```powershell
python .\tools\create_persona_pack.py "Carl Sagan"
```

This creates `persona_packs/<persona_id>/` with manifest + notes + private-reference placeholders.

## Fallout Integration Docs

- `game/plugin-design.md` for CK record design and bridge flow
- `game/install-dev.md` for safe manual dev install
- `game/creation-kit-worklist.md` for the remaining CK implementation checklist
- `native_bridge/README.md` for F4SE bridge responsibilities

## Distribution Note

This scaffold is best treated as a private prototype. Real-person likenesses, cloned voices, and celebrity personas can raise consent, publicity-right, and distribution issues. The code is set up so you can start with a normal TTS voice and swap in licensed assets later.
