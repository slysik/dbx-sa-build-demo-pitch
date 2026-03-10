#!/usr/bin/env python3
"""
populate_excalidraw.py
Reads the Excalidraw template + a filled YAML answers file,
then outputs a new .excalidraw with content cards replaced.

Usage:
  python populate_excalidraw.py answers.yaml
  python populate_excalidraw.py answers.yaml --output my_diagram.excalidraw

The answers.yaml maps section names to lists of card texts.
Only cards you specify are overwritten; omitted sections keep defaults.
"""

import json
import sys
import argparse
from pathlib import Path

# ── Element ID mapping ──────────────────────────────────────────────────
# Each column maps: header text_id (static), then content card text_ids top→bottom.
# We only overwrite content cards (index 1+), never headers (index 0).

COLUMN_TEXT_IDS = {
    "sources": [
        "ff81a28579e84a56bc47",   # HEADER: Sources (static)
        "ca63c804845541758f95",   # Card 1
        "4324ef6f85924b33975d",   # Card 2
        "8697e5d7b53444f3a7f6",   # Card 3
        "697e403994304c90b1df",   # Card 4
        "92d7f0d625384bfcb2bb",   # Card 5
        "dc3373e0f850405b8398",   # Card 6
    ],
    "ingestion": [
        "df5f975d66934c478d89",   # HEADER: Ingestion Patterns (static)
        "3c4bf8ac51e64e559fe7",   # Card 1
        "2a075a0a9096443e9d19",   # Card 2
        "81c869c2b00f43e1b06f",   # Card 3
        "bd7cfa6338cd437a971e",   # Card 4
    ],
    "bronze": [
        "964ce4eed91c450d922a",   # HEADER: Bronze (static)
        "abc35c3f42ee4d6f8fe5",   # Card 1
        "879c8ed0952f46daa9b4",   # Card 2
    ],
    "silver": [
        "5961bc8d434941c0a5d1",   # HEADER: Silver (static)
        "5e764f9c832b4f959133",   # Card 1
        "1cf9437f844e4bd78eea",   # Card 2
        "d2f2122aafb64077bcd9",   # Card 3
        "bfa221b4e2cb4c80a43a",   # Card 4
    ],
    "gold": [
        "92e58561f5354668951f",   # HEADER: Gold (DW Focus) (static)
        "8c8751ee9c2745a6a95f",   # Card 1
        "dc2b798a472d49b6ad8b",   # Card 2
        "39a598c71f6142fdbc94",   # Card 3
        "c43b3fed665e4e61aac7",   # Card 4
    ],
    "compute": [
        "c80555168e6c4b40a2e9",   # HEADER: Compute / Orchestration (static)
        "3484b6ba09a541af80ee",   # Card 1
        "cbf8f9957a7d4f339c9f",   # Card 2
        "111287c9bc8140429ab6",   # Card 3
    ],
    "serve": [
        "e02c37ba5d01460fba32",   # HEADER: Serve / Consume (static)
        "f456348881ce443383d6",   # Card 1
        "8b2004aca87a4b33b34e",   # Card 2
        "57617016606b4b689125",   # Card 3
        "719025050d89460493c7",   # Card 4
    ],
    "domain_products": [
        "4fd616da25dd474fbd8c",   # HEADER: Domain Products (static)
        "dee8d0ca68ee45d088aa",   # Card 1
        "cca82f85dc0d43528b72",   # Card 2
        "f690be7005694ef8aef6",   # Card 3
        "8c8c002f2316438ea9a9",   # Card 4
    ],
}

TITLE_TEXT_ID = "a9ee3b148d3e4bc3bddf"

GUARDRAIL_TEXT_IDS = [
    "311c551e54224314a712",   # Unity Catalog
    "44b9af6377b54e56ba42",   # Lineage + Audit
    "e019d0f9b3164c09b2b4",   # SDLC
    "2b2db40274f04fe4b9cc",   # Observability
    "2663920cc6184d48a7f2",   # Cost Controls
    "6a20d48aebf74672956b",   # Security Posture
]


def load_answers(path: str) -> dict:
    """Load answers from YAML or JSON."""
    text = Path(path).read_text()
    if path.endswith((".yaml", ".yml")):
        try:
            import yaml
            return yaml.safe_load(text)
        except ImportError:
            print("PyYAML not installed. Install with: pip install pyyaml")
            print("Or use a .json answers file instead.")
            sys.exit(1)
    else:
        return json.loads(text)


def populate(template_path: str, answers: dict, output_path: str):
    """Replace text elements in the Excalidraw template with answers."""
    with open(template_path, "r") as f:
        data = json.load(f)

    # Build lookup: element id → element reference
    text_lookup = {}
    for el in data["elements"]:
        if el.get("type") == "text":
            text_lookup[el["id"]] = el

    # Update title if provided
    if "title" in answers:
        el = text_lookup.get(TITLE_TEXT_ID)
        if el:
            el["text"] = answers["title"]
            el["originalText"] = answers["title"]

    # Update each column's content cards
    for section_key, id_list in COLUMN_TEXT_IDS.items():
        if section_key not in answers:
            continue
        cards = answers[section_key]
        # id_list[0] is the header (skip), id_list[1:] are content cards
        content_ids = id_list[1:]
        for i, card_id in enumerate(content_ids):
            el = text_lookup.get(card_id)
            if el and i < len(cards):
                new_text = cards[i]
                el["text"] = new_text
                el["originalText"] = new_text

    # Update guardrails if provided
    if "guardrails" in answers:
        for i, gid in enumerate(GUARDRAIL_TEXT_IDS):
            el = text_lookup.get(gid)
            if el and i < len(answers["guardrails"]):
                new_text = answers["guardrails"][i]
                el["text"] = new_text
                el["originalText"] = new_text

    with open(output_path, "w") as f:
        json.dump(data, f)

    print(f"✅ Populated diagram saved to: {output_path}")


def main():
    parser = argparse.ArgumentParser(
        description="Populate Excalidraw template with discovery answers"
    )
    parser.add_argument("answers", help="Path to answers file (YAML or JSON)")
    parser.add_argument(
        "--template",
        default="template.excalidraw",
        help="Path to Excalidraw template (default: template.excalidraw)",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Output path (default: populated_<answers_stem>.excalidraw)",
    )
    args = parser.parse_args()

    answers = load_answers(args.answers)
    output = args.output or f"populated_{Path(args.answers).stem}.excalidraw"
    populate(args.template, answers, output)


if __name__ == "__main__":
    main()
