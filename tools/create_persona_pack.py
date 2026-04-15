from __future__ import annotations

from pathlib import Path
import argparse
import json
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from fo4_persona_lab.models import slugify


def _manifest(name: str, persona_id: str) -> dict:
    return {
        "persona_id": persona_id,
        "display_name": name,
        "short_bio": f"Public summary for {name}.",
        "fallout_hook": f"Explain why {name} is present in the Commonwealth.",
        "public_facts": ["List only public verifiable facts."],
        "speech_style": ["Describe cadence and tone in practical terms."],
        "appearance_cues": ["Head/face/clothing cues for Creation Kit and LooksMenu translation."],
        "relationship_seed": "How this persona first relates to the Sole Survivor.",
        "goals": ["What this persona wants to achieve in Fallout's world."],
        "dislikes": ["What this persona rejects or pushes against."],
        "worldview": "How this persona interprets power, survival, and community.",
        "fallout_role": "Practical in-world role such as strategist, scientist, builder, or fixer.",
        "conversation_examples": [
            {
                "user": "Give one practical player question.",
                "assistant": "Give one concise in-character answer.",
            }
        ],
        "guardrails": [
            "Do not invent private facts.",
            "Admit uncertainty and avoid defamatory claims.",
        ],
        "voice": {
            "mode": "sapi",
            "voice_name": None,
            "prompt": "Natural, grounded, cinematic.",
        },
    }


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def create_pack(name: str) -> Path:
    project_root = Path(__file__).resolve().parents[1]
    packs_root = project_root / "persona_packs"
    persona_id = slugify(name)
    pack_dir = packs_root / persona_id
    if pack_dir.exists():
        raise SystemExit(f"Refusing to overwrite existing pack: {pack_dir}")

    references_dir = pack_dir / "references"
    references_dir.mkdir(parents=True, exist_ok=False)

    manifest = _manifest(name, persona_id)
    _write(pack_dir / "manifest.json", json.dumps(manifest, indent=2))
    _write(
        references_dir / "README.md",
        "\n".join(
            [
                f"# {name} Reference Assets",
                "",
                "Place user-supplied or licensed references here.",
                "Do not commit private photos, paid assets, or restricted likeness materials.",
                "Keep only notes/placeholders in git unless rights are confirmed.",
            ]
        )
        + "\n",
    )
    _write(
        pack_dir / "appearance-notes.md",
        "\n".join(
            [
                f"# {name} Appearance Notes",
                "",
                "## Head and Face",
                "- Capture jawline, brow, nose, and eye spacing cues from multiple angles.",
                "",
                "## Hair and Clothing",
                "- List era-appropriate alternatives that fit Fallout's art direction.",
                "",
                "## In-Game Translation",
                "- Map cues to LooksMenu sliders and Creation Kit ActorBase settings.",
            ]
        )
        + "\n",
    )
    _write(
        pack_dir / "voice-notes.md",
        "\n".join(
            [
                f"# {name} Voice Notes",
                "",
                "- Describe cadence, pacing, emphasis, and emotional range.",
                "- Keep guidance focused on public persona, not private claims.",
                "- Record licensing/consent status for any non-default voice assets.",
            ]
        )
        + "\n",
    )
    _write(
        pack_dir / "creation-kit-notes.md",
        "\n".join(
            [
                f"# {name} Creation Kit Notes",
                "",
                "## Records",
                "- ActorBase and placed Actor references",
                "- Quest alias bindings",
                "- Dialogue topic entry points",
                "",
                "## Audio Plan",
                "- Sound Descriptor IDs",
                "- Subtitle and idle animation handling",
                "",
                "## Validation",
                "- Spawn test",
                "- Dialogue trigger test",
                "- Bridge callback test",
            ]
        )
        + "\n",
    )

    return pack_dir


def main() -> None:
    parser = argparse.ArgumentParser(description="Create a FO4 Persona Lab persona pack scaffold.")
    parser.add_argument("name", help="Display name for the persona.")
    args = parser.parse_args()
    pack_dir = create_pack(args.name)
    print(f"Created persona pack scaffold at {pack_dir}")


if __name__ == "__main__":
    main()
