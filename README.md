# FO4 Persona Lab

Prototype scaffold for a Fallout 4 mod that lets you drop a real person into the Commonwealth, chat with them in a typed interface, and hear voiced replies.

This project is split on purpose:

- `fo4_persona_lab/` is the local AI service and browser-based typed dialogue prototype.
- `personas/` stores per-person manifests with facts, style notes, appearance cues, and voice hints.
- `game/` holds Fallout-side source stubs and notes for the later Creation Kit and F4SE bridge.
- `docs/` explains the architecture and the hard engine limitations.

## What Works In This Scaffold

- Load persona manifests from JSON.
- Keep per-session conversation memory on disk.
- Generate fallback dialogue locally with a rule-based backend.
- Optionally call an OpenAI chat model if `OPENAI_API_KEY` is present.
- Optionally synthesize speech with:
  - built-in Windows SAPI voices, or
  - OpenAI text-to-speech if `OPENAI_API_KEY` is present.
- Serve a Fallout-style local web UI for typed conversations.

## What Still Needs Fallout 4 Mod Work

- In-game typed text entry needs either a custom Scaleform menu or an external overlay bridge.
- NPC spawning, facegen import, sound descriptors, lip-sync, and scene control still need Creation Kit work.
- Direct Papyrus-to-HTTP calls are not available in vanilla Fallout 4, so a native bridge or overlay flow is still required.

## Quick Start

```powershell
cd C:\Users\raymo_w9whwcn\OneDrive\TT\fo4_persona_lab
python -m fo4_persona_lab.server
```

Then open `http://127.0.0.1:8765`.

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

## Distribution Note

This scaffold is best treated as a private prototype. Real-person likenesses, cloned voices, and celebrity personas can raise consent, publicity-right, and distribution issues. The code is set up so you can start with a normal TTS voice and swap in licensed assets later.
