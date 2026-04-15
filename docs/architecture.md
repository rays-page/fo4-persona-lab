# Architecture Notes

## Goal

Support a Fallout 4 NPC that:

- looks like a real person,
- speaks in a believable public-facing voice,
- accepts typed player input,
- keeps long-running memory,
- and replies with generated speech.

## System Split

### 1. Persona Pack

Each person needs a manifest plus assets:

- JSON manifest with facts, tone, guardrails, and relationship seed
- reference images for face sculpting and texture work
- optional voice prompt or licensed voice model

### 2. External Dialogue Service

This project provides that layer now.

Responsibilities:

- build the persona prompt,
- hold session memory,
- call the dialogue model,
- call TTS,
- return reply text and an audio file.

### 3. Fallout 4 Mod Layer

This still needs Creation Kit and likely an F4SE bridge.

Responsibilities:

- select the target NPC or spawn one,
- open typed dialogue UI,
- forward the player text to the service,
- receive reply text and audio,
- drive subtitles, talk idles, and sound playback.

## Hard Engine Constraint

Fallout 4 Papyrus scripts cannot make arbitrary HTTP requests on their own.

That means a production build needs one of these:

- a native F4SE plugin that bridges HTTP,
- a custom Scaleform menu plus native bridge,
- or an external overlay app that handles text entry and service calls.

## Best Build Order

1. Get persona quality right in the service layer.
2. Build one single NPC in Creation Kit.
3. Add typed UI.
4. Add sound descriptors and animation sync.
5. Add automated persona import pipeline for new people.

## Believability Strategy

For celebrities and public figures, believable dialogue comes from:

- public-fact grounding,
- voice and tone notes,
- a strong relationship seed,
- aggressive refusal to invent private facts,
- and enough session memory to maintain continuity.

## Likeness Strategy

The model cannot make Fallout 4 facegen by itself. A practical pipeline is:

1. collect reference images,
2. build the head in LooksMenu or Creation Kit,
3. export facegen,
4. generate or paint textures outside the game,
5. ship them as part of the persona pack.
