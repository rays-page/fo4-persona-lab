# Creation Kit Worklist

This tracks the remaining in-game work that cannot be finished from Python or web code alone.

## Prerequisites

- Plugin has `F4RP_BridgeQuest` and `F4RP_BridgeQuestScript` attached. (Done in `F4RPPersonaLab.esp`.)
- One test persona actor exists in your plugin.
- Local service is reachable (`python -m fo4_persona_lab.server`).

## 1) NPC Spawning

Goal: Spawn or resolve a persona NPC reliably before conversation starts.

Creation Kit tasks:

- Create an `ActorBase` per persona.
- Place at least one persistent actor reference for smoke tests.
- Add `ReferenceAlias` entries for:
  - current speaker (`CurrentSpeakerAlias`)
  - optional spawned speaker (`SpawnedSpeakerAlias`).
- Create an activator, terminal, or topic entry that calls `StartConversation`.

Papyrus tasks:

- Add a spawn path that:
  - finds an existing placed actor first,
  - falls back to `PlaceAtMe` from a safe marker when needed,
  - stores the resulting reference in `CurrentSpeaker`.

Done check:

- Trigger entry point from a fresh save and confirm one valid speaker reference is always resolved.

## 2) Facegen Import

Goal: Persona NPC appears with expected sculpt and tint in-game.

Creation Kit tasks:

- Finalize actor head sculpt and tint in CK/LooksMenu flow.
- Export and stage facegen assets for your plugin.
- Verify head part, complexion, eyebrows, and skin tone records match final assets.

Asset sanity checks:

- Face mesh and tint paths are under plugin-scoped FaceGen folders.
- No gray-face mismatch in game.

Done check:

- Spawn actor in a test cell and validate close-up face match under indoor and outdoor lighting.

## 3) Sound Descriptors

Goal: Route generated reply audio through a stable FO4 playback path.

Creation Kit tasks:

- Create a dedicated sound category for persona dialogue.
- Add one or more sound descriptors for prototype reply playback.
- Set attenuation/ducking values so voice remains understandable during combat ambience.

Bridge tasks:

- Keep deterministic audio naming (`<session>_<request>.wav`) so CK-side lookup is predictable.
- Decide one playback strategy:
  - descriptor-backed playback from staged assets, or
  - native runtime playback with CK fallback.

Done check:

- Two back-to-back generated lines play at expected volume and do not overlap incorrectly.

## 4) Lip-Sync

Goal: Mouth movement aligns with generated voice well enough for prototype believability.

Creation Kit tasks:

- Define prototype lip-sync strategy per line type:
  - true lip data pipeline for staged lines, or
  - talk-idle fallback for fully dynamic lines.
- Hook subtitle timing to the same start/stop events used for audio.

Runtime tasks:

- Ensure response callbacks carry enough timing metadata (duration or start/stop events).
- Stop lip animation cleanly on interrupt or scene cancel.

Done check:

- During three-turn dialogue, mouth movement starts and ends with each reply without getting stuck.

## 5) Scene Control

Goal: Conversation flow can be started, advanced, and aborted safely.

Creation Kit tasks:

- Create a dedicated conversation `Scene` tied to quest aliases.
- Add phases for:
  - open,
  - player input wait,
  - NPC response playback,
  - cleanup/exit.
- Define interruption behavior for combat, distance break, or actor death.

Papyrus tasks:

- Add explicit scene state functions (start/advance/stop) in `F4RP_BridgeQuestScript`.
- Gate `SubmitPlayerText` so requests are ignored when scene state is invalid.

Done check:

- Conversation can open, complete multiple turns, and close without leaving aliases, idles, or subtitles active.

## Recommended Build Order

1. NPC spawning
2. Facegen import
3. Sound descriptors
4. Scene control
5. Lip-sync polish

## Exit Criteria

This CK work is complete when one persona NPC can be spawned, converse for at least 5 turns, play generated voice at stable levels, and cleanly recover from one forced interruption.
