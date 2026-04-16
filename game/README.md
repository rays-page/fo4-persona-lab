# Fallout 4 Integration Notes

The files in `scripts/` include Papyrus source plus compiled local-test outputs for the in-game bridge.

This folder now includes:

- `F4RPPersonaLab.esp`: Creation Kit scaffold plugin with `F4RP_BridgeQuest`
- `scripts/Source/User/F4RP_BridgeQuestScript.psc`: quest-level bridge contract
- `scripts/Source/User/F4RP_NativeBridge.psc`: native Papyrus function contract for F4SE bridge DLLs
- `scripts/F4RP_BridgeQuestScript.pex` and `scripts/F4RP_NativeBridge.pex`: compiled Papyrus outputs for local testing
- `plugin-design.md`: Creation Kit record design and runtime flow
- `install-dev.md`: manual developer install path (no automatic writes to Fallout folders)
- `in-game-smoke-test.md`: console-driven test path before the F4SE DLL exists
- `creation-kit-worklist.md`: actionable checklist for remaining CK-only tasks

Still intentionally missing:

- a compiled F4SE native plugin,
- a SWF typed input menu,
- or in-game sound descriptor setup.
