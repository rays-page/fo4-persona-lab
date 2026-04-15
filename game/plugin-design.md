# FO4 Plugin Design

This document describes the target Fallout 4 mod/plugin structure for FO4 Persona Lab.

For the current remaining manual tasks (NPC spawning, facegen, sound descriptor routing, lip-sync, and scene flow), use `creation-kit-worklist.md` as the execution checklist.

## Scope

- Build one quest-driven bridge that can open typed conversation flow.
- Keep Persona/AI generation external (local service running on the same PC).
- Keep this repo source-only for game integration until native bridge code is ready.

## Core Creation Kit Records

Create these records in your `.esp/.esm`:

- `Quest`: `F4RP_BridgeQuest`
  - Start Game Enabled.
  - Holds `F4RP_BridgeQuestScript`.
- `ReferenceAlias`: `CurrentSpeakerAlias`
  - Bound to the actor currently talking with player.
- `ActorBase` + placed `Actor` for each persona NPC you want in-game.
- `Topic` / `TopicInfo` entry point to trigger `StartConversation`.
- Optional activator or terminal to open typed dialogue without vanilla dialogue wheel.
- `Sound Category` + `Sound Descriptor` placeholders for generated reply playback routing.

## Quest Script Contract

`F4RP_BridgeQuestScript` now defines:

- persona state (`ActivePersonaId`),
- session state (`ActiveSessionId`),
- request correlation (`LastRequestId`),
- submission function (`SubmitPlayerText`),
- callback functions (`ReceiveGeneratedReply`, `ReceiveBridgeError`),
- update-loop polling knobs (`PollIntervalSeconds`, `MaxResultsPerUpdate`).

`F4RP_NativeBridge` defines the native F4SE-facing API surface used by the quest script.

Native bridge target behavior:

1. Papyrus calls `SubmitPlayerText`.
2. Native bridge sends `/api/bridge/chat` request to local service (including `request_id`).
3. Papyrus polls for completed `request_id` values on a fixed update interval.
4. Papyrus reads result fields from native and routes into `ReceiveGeneratedReply` or `ReceiveBridgeError`.
5. Papyrus pushes subtitle/UI updates and optionally triggers voice playback logic.

Game-facing audio contract: consume `audio_file_path` (filesystem path), not URL fields.

## UI Options

Two practical approaches:

- Custom Scaleform menu:
  - In-game text input and subtitle panel.
  - Best immersion, most implementation effort.
- External overlay window:
  - Faster to ship for testing.
  - Can coexist with Fallout window and call service directly.

Current prototype decision: default to external overlay (`TextInputMode = 1`) and keep Scaleform as a future implementation track.

This repo ships an overlay prototype at `python -m fo4_persona_lab.overlay`.

## Audio Strategy

- Use generated WAV for prototype playback.
- For native dialogue-style integration, plan an asset pipeline for engine-friendly voice assets:
  - subtitle text,
  - lip data,
  - packaged voice assets.
- Keep a deterministic naming convention keyed by session + request id.

## State and Reliability

- Treat each conversation turn as request/response with an integer request id.
- Never block Papyrus on long network calls; native layer must complete asynchronously.
- Add timeout and error callback paths (`ReceiveBridgeError`) for every request.
- Keep session id persistent during one conversation and reset when new conversation starts.

## Testing Ladder

1. Script-only: call `StartConversation`, `SubmitPlayerText`, and callback methods with test data.
2. Overlay-assisted: run overlay + script debug notifications.
3. Native bridge loopback: return canned response, then real HTTP call.
4. Full loop: real response + sound routing + idle animation.
