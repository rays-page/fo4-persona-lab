# FO4 Dev Install (Manual)

This is a developer workflow. Nothing in this repo writes into your Fallout folders automatically.

## 1. Prepare Local Service

From this repo:

```powershell
python -m fo4_persona_lab.server
```

Optional overlay client:

```powershell
python -m fo4_persona_lab.overlay
```

## 2. Prepare Fallout Runtime

- Install Fallout 4 on Steam or GOG.
- Install F4SE that matches your game runtime version.
- Verify game launches through F4SE before testing bridge work.

## 3. Creation Kit Setup

- Open `F4RPPersonaLab.esp` in Creation Kit.
- Verify quest `F4RP_BridgeQuest` is present.
- Verify `F4RP_BridgeQuestScript` is attached on the quest's Scripts tab.
- Create one dialogue/activator entry point that calls `StartConversation`.

## 4. Source Deployment (Manual)

Copy only what you intend to test:

- Plugin (`F4RPPersonaLab.esp`) from `game/`
- Papyrus source (`.psc`) from `game/scripts/Source/User/`
- Compiled scripts (`.pex`) from `game/scripts/` or after recompiling in your local CK/F4SE toolchain

Recommended destination pattern:

- `<Fallout4>\Data\` for `.esp`
- `<Fallout4>\Data\Scripts\Source\User\` for `.psc`
- `<Fallout4>\Data\Scripts\` for `.pex`

## 5. Validation Checklist

- Quest starts and script initializes.
- Calling `StartConversation` opens the selected typed-input route (external overlay by default).
- `SubmitTypedTextFromUI` / `SubmitPlayerText` increments request id and reaches your bridge layer.
- `ReceiveGeneratedReply` displays in notification/subtitle path.
- `CloseConversation` clears session state.

## 6. Safety Checklist

- Keep backup saves before testing quest/script changes.
- Keep private likeness/voice assets outside public git by default.
- Do not overwrite base game files; use plugin + Data folder conventions only.
