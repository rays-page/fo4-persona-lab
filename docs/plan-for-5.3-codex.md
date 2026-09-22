# Plan For 5.3-Codex

## Mission

Build FO4 Persona Lab into a usable end-to-end prototype for AI-driven real-person NPCs in Fallout 4, starting with the Steve Jobs persona.

The goal is not to silently edit the user's live Fallout 4 setup. The goal is to make the repo production-shaped: clear service layer, persona pipeline, local overlay/chat client, generated voice playback, and a safe Fallout integration path that can later be installed intentionally.

## Hard Boundaries

- Work only inside the `fo4-persona-lab` repo checkout.
- Do not edit `Fallout4Custom.ini`, Vortex state, Steam game files, or any other folder outside this repo.
- Do not delete generated user data unless explicitly asked.
- Do not add API keys, tokens, generated voice samples, reference photos, or private data to git.
- Keep `data/audio/` and `data/sessions/` ignored.
- Use commits for meaningful milestones and push to `origin/main` after validated changes.

## Current Repo State

- Python package: `fo4_persona_lab/`
- Browser prototype UI: `web/`
- Persona manifests: `personas/`
- Fallout-side source stub: `game/scripts/Source/User/F4RP_BridgeQuestScript.psc`
- Architecture docs: `docs/architecture.md`
- GitHub remote: `https://github.com/rays-page/fo4-persona-lab.git`
- Current target persona: `personas/steve-jobs.json`

## Phase 1: Stabilize The Service

Tasks:

- Add structured request and response validation for `/api/chat`.
- Add `GET /api/personas/{persona_id}`.
- Add `GET /api/sessions/{session_id}` for debugging transcripts.
- Add `POST /api/sessions` so the UI can intentionally start a fresh conversation.
- Make backend and TTS errors visible but non-fatal in the UI.
- Add a small test/smoke script under `tools/` that checks persona loading, a chat turn, and optional TTS.

Acceptance criteria:

- `python -m compileall .` passes.
- Smoke script can run without an OpenAI key using the rules backend.
- UI still works at `http://127.0.0.1:8765`.
- Steve Jobs appears in the persona list.

## Phase 2: Improve Dialogue Quality

Tasks:

- Strengthen `prompting.py` with a better celebrity portrayal structure:
  - public facts,
  - speech style,
  - Fallout situation,
  - conversational memory,
  - refusal to invent private claims.
- Improve `RuleBasedBackend` so local fallback feels less generic and uses persona style more directly.
- Add optional long-running memory summaries to session JSON.
- Add persona fields if needed:
  - `goals`,
  - `dislikes`,
  - `conversation_examples`,
  - `worldview`,
  - `fallout_role`.
- Update `personas/persona-template.json`, `personas/carl-sagan.json`, and `personas/steve-jobs.json` if the schema changes.

Acceptance criteria:

- A Steve Jobs local fallback answer should mention design, focus, product simplicity, or execution when relevant.
- OpenAI backend should receive enough prompt context to stay believable without becoming a caricature.
- Existing persona JSON remains loadable or is migrated cleanly.

## Phase 3: Build The Local Overlay Client

Tasks:

- Add a desktop overlay client under `fo4_persona_lab/overlay.py` or `tools/run_overlay.py`.
- Use standard-library `tkinter` first to avoid dependency setup.
- Features:
  - always-on-top window,
  - persona selector,
  - player/location fields,
  - typed input,
  - transcript view,
  - play voiced replies,
  - clear/new session button.
- Keep it independent from Fallout files. It should run beside Fallout, not modify Fallout.

Acceptance criteria:

- `python -m fo4_persona_lab.overlay` launches a usable window.
- User can chat with Steve Jobs through the local service logic.
- Voice playback works when TTS returns a WAV.
- If TTS fails, text still appears.

## Phase 4: Persona Pack Pipeline

Tasks:

- Create `persona_packs/` structure documentation but keep actual private photos out of git.
- Add `tools/create_persona_pack.py` that creates:
  - manifest JSON,
  - `references/README.md`,
  - `appearance-notes.md`,
  - `voice-notes.md`,
  - `creation-kit-notes.md`.
- Add docs for how to gather reference images safely and how to translate appearance cues into LooksMenu/Creation Kit work.
- Add a Steve Jobs pack README without copyrighted images.

Acceptance criteria:

- Running `python tools/create_persona_pack.py "Example Person"` creates a clean pack scaffold.
- `.gitignore` prevents accidental commit of large/reference/private media unless explicitly whitelisted.
- Docs explain that likeness assets require user-provided or licensed references.

## Phase 5: Fallout Integration Scaffold

Tasks:

- Expand the Papyrus source stub into a clearer bridge contract:
  - start conversation,
  - receive generated reply,
  - close conversation,
  - set current persona,
  - debug notification path.
- Add `game/plugin-design.md` with Creation Kit records needed:
  - Quest,
  - NPC Actor,
  - ActorBase,
  - Alias,
  - Topic/Scene placeholder,
  - activator or dialogue entry point,
  - sound descriptor strategy.
- Add `game/install-dev.md` explaining manual developer install steps, but do not run them automatically.
- If adding scripts that copy files to Fallout folders, make them dry-run by default.

Acceptance criteria:

- No live Fallout files are changed.
- Docs give exact future steps for Creation Kit setup.
- Papyrus source remains source-only unless a compiler is available inside the repo/toolchain.

## Phase 6: Optional Native Bridge Research Stub

Tasks:

- Add `native_bridge/README.md` only, unless the F4SE SDK/toolchain is available and explicitly requested.
- Document the expected F4SE plugin responsibilities:
  - expose Papyrus native functions,
  - send HTTP requests to local service,
  - hand response text/audio path back to Papyrus/UI.
- Do not vendor unknown SDKs or binaries.

Acceptance criteria:

- The repo contains a realistic native bridge plan without pretending it already works.

## Phase 7: Git Hygiene

Tasks:

- Before each commit:
  - run `git status --short`,
  - confirm changed files are inside repo,
  - run compile/smoke checks.
- Commit messages should be short and concrete.
- Push after validated milestones.

Suggested commits:

- `Add service validation and session APIs`
- `Improve persona prompt and fallback dialogue`
- `Add desktop overlay client`
- `Add persona pack scaffolding`
- `Document Fallout integration path`

## Suggested First Command Sequence

```powershell
cd fo4-persona-lab
git status --short --branch
python -m compileall .
```

Then implement Phase 1 first. Do not jump into Fallout game files.

## Definition Of Done For This Round

The round is complete when:

- Steve Jobs can be selected in the browser UI and overlay UI.
- typed conversation works indefinitely with persistent sessions,
- voiced responses work with SAPI and gracefully fail without blocking text,
- the persona pack process is documented,
- Fallout integration has safe source/docs only,
- all changes are committed and pushed to GitHub.
