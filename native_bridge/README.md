# Native Bridge Skeleton (F4SE / CommonLibF4)

This folder now contains a **real async bridge runtime skeleton** that can be dropped into an F4SE/CommonLib-backed plugin project.

## What Is Included

- `include/f4rp/bridge_runtime.h`
  - request/result structs
  - bounded request queue
  - completed-result cache
- `src/bridge_runtime.cpp`
  - background worker threads
  - WinHTTP POST to `/api/bridge/chat`
  - non-blocking result handoff for Papyrus polling
- `src/f4se_plugin_template.cpp`
  - SDK-ready template showing where native Papyrus binding should happen
- `src/smoketest_main.cpp`
  - standalone executable to smoke test HTTP flow outside the game
- `CMakeLists.txt`
  - builds `f4rp_bridge_runtime` + `f4rp_bridge_smoketest`

## Runtime Model (Optimized For Heavy Mod Lists)

1. Papyrus calls `SubmitChat(...)` and returns immediately.
2. Native runtime enqueues request in O(1) and wakes a worker thread.
3. Worker posts to local service (`127.0.0.1:8765/api/bridge/chat`) via WinHTTP.
4. Worker stores result in completed cache.
5. Papyrus polls at fixed interval (`~0.35s` default) and processes at most N results per tick.

No network call runs on the game thread or Papyrus VM thread.

## Papyrus Contract

`game/scripts/Source/User/F4RP_NativeBridge.psc` exposes these native globals:

- `SubmitChat(...) -> Bool`
- `PopCompletedRequestId() -> Int`
- `WasRequestSuccessful(requestId) -> Bool`
- `GetReplyText/GetSessionId/GetAudioPath/GetWarning/GetError`
- `ReleaseResult(requestId)`
- `GetQueueDepth() -> Int`

`F4RP_BridgeQuestScript.psc` now polls the bridge asynchronously and routes results into existing callbacks:

- `ReceiveGeneratedReply(...)`
- `ReceiveBridgeError(...)`

## Build (Runtime + Smoke Test)

```powershell
cd C:\Users\raymo_w9whwcn\OneDrive\TT\fo4_persona_lab\native_bridge
cmake -S . -B build
cmake --build build --config Release
.\build\Release\f4rp_bridge_smoketest.exe
```

## Integrating Into A Real F4SE Plugin

1. Bring this runtime into your plugin project (or add this folder as a subdir).
2. Enable and adapt `src/f4se_plugin_template.cpp` in your SDK-backed tree.
3. Register all `F4RP_NativeBridge` functions with Papyrus VM.
4. Ship the resulting DLL in the game's F4SE plugins folder.

## Tuning Knobs

`BridgeConfig` controls runtime behavior:

- `worker_count` (default `2`)
- `max_pending_requests` (default `128`)
- `max_completed_results` (default `512`)
- connection/send/receive timeouts

For stability under load, keep Papyrus `MaxResultsPerUpdate` low (for example `1-3`) and avoid per-frame polling.
