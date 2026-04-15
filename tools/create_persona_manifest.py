from __future__ import annotations

from pathlib import Path
import argparse
import json

from fo4_persona_lab.models import slugify


def build_manifest(name: str) -> dict:
    persona_id = slugify(name)
    return {
        "persona_id": persona_id,
        "display_name": name,
        "short_bio": f"Public summary for {name}.",
        "fallout_hook": f"Explain why {name} exists in the Commonwealth.",
        "public_facts": [
            f"Add public facts about {name}.",
        ],
        "speech_style": [
            "Measured and conversational",
        ],
        "appearance_cues": [
            "Add face, hair, clothing, and posture notes.",
        ],
        "relationship_seed": "How they relate to the Sole Survivor.",
        "guardrails": [
            "Do not invent private facts.",
            "Admit uncertainty when needed."
        ],
        "voice": {
            "mode": "sapi",
            "voice_name": null,
            "prompt": "Natural, grounded, cinematic."
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Create a FO4 Persona Lab manifest.")
    parser.add_argument("name", help="Display name for the persona.")
    args = parser.parse_args()

    project_root = Path(__file__).resolve().parents[1]
    personas_dir = project_root / "personas"
    personas_dir.mkdir(parents=True, exist_ok=True)

    manifest = build_manifest(args.name)
    target = personas_dir / f"{manifest['persona_id']}.json"
    if target.exists():
        raise SystemExit(f"Refusing to overwrite existing manifest: {target}")

    target.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"Wrote {target}")


if __name__ == "__main__":
    main()
