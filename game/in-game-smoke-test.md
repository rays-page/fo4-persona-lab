# In-Game Smoke Test

Use this to verify the Creation Kit quest and Papyrus script before the real F4SE native bridge DLL exists.

## Prerequisites

- `F4RPPersonaLab.esp` is enabled in your Fallout 4 load order.
- `F4RP_BridgeQuestScript.pex` and `F4RP_NativeBridge.pex` are installed under `<Fallout4>\Data\Scripts\`.
- Start from a disposable test save.

## Console Smoke Test

Open the Fallout 4 console and run:

```text
cqf F4RP_BridgeQuest StartConversation player "steve-jobs"
cqf F4RP_BridgeQuest SubmitTypedTextFromUI "Hello from the console smoke test" "Sole Survivor" "Vault 111"
```

Expected result:

- You should see `F4RP:` debug notifications when the conversation opens.
- Until the F4SE native bridge DLL is installed, the quest uses `MockBridgeWhenNativeUnavailable=True`.
- The second command should show a mock reply notification like `[mock steve-jobs] I heard: ...`.

Close the test conversation with:

```text
cqf F4RP_BridgeQuest CloseConversation
```

## What This Proves

- The plugin is enabled.
- `F4RP_BridgeQuest` can be resolved by the game.
- `F4RP_BridgeQuestScript` is attached and running.
- The typed-text handoff path reaches `SubmitPlayerText`.
- The quest can display a reply path without waiting on the native bridge DLL.

## What This Does Not Prove Yet

- Real HTTP calls through the F4SE native bridge.
- In-game NPC actor/alias resolution.
- Generated audio playback through Fallout 4 sound descriptors.
- Lip-sync or scene flow.
