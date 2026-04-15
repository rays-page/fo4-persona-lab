# Native Bridge Plan (F4SE)

This folder is a research and design stub only.

No F4SE SDK, binary, or compiled plugin is vendored here yet.

## Purpose

Papyrus cannot directly run arbitrary HTTP workflows for this project shape, so a native bridge is the clean long-term path.

The bridge should expose native functions callable from `F4RP_BridgeQuestScript` and asynchronously return results back into Papyrus/UI.

## Responsibilities

1. Register Papyrus native functions for chat submission and callback routing.
2. Receive `persona_id`, `session_id`, `player_name`, `location`, and typed message.
3. Send HTTP requests to local FO4 Persona Lab service.
4. Parse response (`reply`, optional `audio_url`, `warnings`, `session_id`).
5. Call back into Papyrus:
   - `ReceiveGeneratedReply` on success
   - `ReceiveBridgeError` on failure/timeout
6. Keep one non-blocking worker queue to avoid stalling game thread.

## Suggested Internal Contract

- Input key: `request_id` integer from Papyrus.
- Timeout: configurable (for example, 10-20 seconds).
- Retry: none by default; return explicit error.
- Logging: write concise bridge logs with request id correlation.

## Incremental Delivery Plan

1. Loopback plugin: returns canned reply string.
2. HTTP plugin: real call to `http://127.0.0.1:8765/api/chat`.
3. Audio path handling: surface local path/URL and test playback.
4. UI integration: connect callbacks to custom menu subtitles.
