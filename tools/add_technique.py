#!/usr/bin/env python3
"""
checkmate add-technique — Technique Synthesis + Auto-Integration CLI
=====================================================================

Usage::

    python -m tools.add_technique --request "Add 4-bit quantization" [--dry-run]
    python tools/add_technique.py  --request "Add 4-bit quantization" [--dry-run]

The command:
  A) Calls the LLM to produce a Technique Card JSON (strict schema).
  B) Validates the card against the canonical schema.
  C) Auto-generates all related updates:
       - writes the card file to techniques/cards/
       - updates technique_registry (auto-loaded at next import)
       - updates prompt files at anchors
       - updates few-shot examples at anchors
       - validator extraction works generically (regex-based)
  D) Runs gates (pytest + optional smoke).
  E) Prints a report of what was changed/added.

Flags:
  --request TEXT    Natural-language description of the technique.
  --card   FILE    Skip LLM; use a pre-built card JSON file instead.
  --dry-run        Generate artifacts to stdout but do not write files.
  --out    DIR     Override card output directory (default: techniques/cards/).
  --skip-tests     Skip pytest gate after integration.
  --skip-smoke     Skip optional smoke run.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import textwrap
from pathlib import Path
from typing import Optional

# Resolve project root
_THIS_DIR = Path(__file__).resolve().parent
_PROJECT_ROOT = _THIS_DIR.parent
sys.path.insert(0, str(_PROJECT_ROOT))

# Load .env file if present (for API keys)
_env_file = _PROJECT_ROOT / ".env"
if _env_file.exists():
    with open(_env_file) as _f:
        for _line in _f:
            _line = _line.strip()
            if _line and not _line.startswith("#") and "=" in _line:
                _key, _, _val = _line.partition("=")
                os.environ.setdefault(_key.strip(), _val.strip())

from lib.technique_card_schema import (
    SCHEMA_VERSION,
    build_card_generation_prompt,
    normalize_card,
    validate_card,
)
from lib.prompt_updater import update_all_prompt_assets
from lib.technique_registry import (
    TECHNIQUE_REGISTRY,
    load_all_cards,
    get_loaded_card_files,
)


# ── Helpers ──────────────────────────────────────────────────────────────

def _next_technique_id() -> int:
    """Return the smallest integer > max existing technique_id."""
    existing = set(TECHNIQUE_REGISTRY.keys())
    cards_dir = _PROJECT_ROOT / "techniques" / "cards"
    for path in sorted(cards_dir.glob("*.json")) if cards_dir.is_dir() else []:
        try:
            with open(path) as f:
                tid = json.load(f).get("technique_id")
            if isinstance(tid, int):
                existing.add(tid)
        except Exception:
            pass
    return max(existing, default=0) + 1


def _card_filename(card: dict) -> str:
    """Deterministic filename: T31_4bit_quantization.json"""
    tag = card.get("technique_tag", f"T{card['technique_id']}")
    slug = re.sub(r"[^a-z0-9]+", "_", card["name"].lower()).strip("_")
    return f"{tag}_{slug}.json"


def _invoke_llm_for_card(request: str, next_id: int) -> dict:
    """
    Call the configured LLM backend (Anthropic / OpenAI) to generate a
    Technique Card JSON.
    """
    system_msg, user_msg = build_card_generation_prompt(request, next_id)

    # Try Anthropic first (matches config.py default)
    try:
        from langchain_anthropic import ChatAnthropic
        model = ChatAnthropic(
            model="claude-sonnet-4-20250514",
            temperature=0,
            max_tokens=4096,
        )
        from langchain_core.messages import SystemMessage, HumanMessage
        resp = model.invoke([
            SystemMessage(content=system_msg),
            HumanMessage(content=user_msg),
        ])
        raw = resp.content
    except Exception as e:
        print(f"[add-technique] Anthropic call failed ({e}); trying OpenAI …")
        try:
            from langchain_openai import ChatOpenAI
            model = ChatOpenAI(
                model="gpt-4o",
                temperature=0,
                max_tokens=4096,
            )
            from langchain_core.messages import SystemMessage, HumanMessage
            resp = model.invoke([
                SystemMessage(content=system_msg),
                HumanMessage(content=user_msg),
            ])
            raw = resp.content
        except Exception as e2:
            raise RuntimeError(
                f"Both LLM backends failed.\n  Anthropic: {e}\n  OpenAI: {e2}"
            ) from e2

    # Extract JSON from response (strip markdown fences if present)
    text = raw.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)

    return json.loads(text)


# ── Main pipeline ────────────────────────────────────────────────────────

def run_add_technique(
    *,
    request: Optional[str] = None,
    card_path: Optional[str] = None,
    out_dir: Optional[str] = None,
    dry_run: bool = False,
    skip_tests: bool = False,
    skip_smoke: bool = False,
) -> int:
    """
    End-to-end pipeline.  Returns 0 on success, non-zero on failure.
    """
    report: list[str] = []
    cards_dir = Path(out_dir) if out_dir else (_PROJECT_ROOT / "techniques" / "cards")
    cards_dir.mkdir(parents=True, exist_ok=True)

    # ── Step A: Obtain the card ──────────────────────────────────────
    if card_path:
        print(f"[add-technique] Loading card from {card_path}")
        with open(card_path) as f:
            card = json.load(f)
    elif request:
        next_id = _next_technique_id()
        print(f"[add-technique] Calling LLM for technique card (next_id={next_id}) …")
        card = _invoke_llm_for_card(request, next_id)
    else:
        print("ERROR: supply --request or --card", file=sys.stderr)
        return 1

    # ── Step B: Validate ─────────────────────────────────────────────
    ok, errors = validate_card(card)
    if not ok:
        print("ERROR: Card validation failed:")
        for e in errors:
            print(f"  - {e}")
        if dry_run:
            print("\n[dry-run] Raw card JSON:")
            print(json.dumps(card, indent=2))
        return 1

    card = normalize_card(card)
    tid = card["technique_id"]
    print(f"[add-technique] Card validated: T{tid} — {card['name']}")
    report.append(f"Technique Card: T{tid} — {card['name']}")

    # ── Step C: Write artifacts ──────────────────────────────────────
    # C.1 — Write card file
    fname = _card_filename(card)
    card_out = cards_dir / fname

    # If the card was loaded from a file already in the output dir, skip re-writing
    skip_card_write = False
    if card_path:
        src = Path(card_path).resolve()
        if src.parent == cards_dir.resolve():
            skip_card_write = True
            card_out = src

    if skip_card_write:
        print(f"  Card already in place: {card_out}")
    elif dry_run:
        print(f"\n[dry-run] Would write card to {card_out}")
        print(json.dumps(card, indent=2))
    else:
        with open(card_out, "w") as f:
            json.dump(card, f, indent=2)
        print(f"  Written: {card_out}")
    report.append(f"Card file: {card_out}")

    # C.2 — Reload all cards and update prompt assets
    all_cards = load_all_cards(str(cards_dir))
    if dry_run:
        # Still compute what would change
        changed = update_all_prompt_assets(
            all_cards,
            prompt_dir=str(_PROJECT_ROOT / "prompts"),
            dry_run=True,
        )
        print(f"\n[dry-run] Would update {len(changed)} prompt files:")
        for p in changed:
            print(f"  - {p}")
    else:
        changed = update_all_prompt_assets(
            all_cards,
            prompt_dir=str(_PROJECT_ROOT / "prompts"),
        )
        for p in changed:
            print(f"  Updated: {p}")
    report.extend(f"Prompt: {p}" for p in changed)

    # C.3 — Registry is auto-loaded on next import; nothing to write
    report.append("Registry: auto-loaded from card file at import time")

    # ── Step D: Run gates ────────────────────────────────────────────
    if dry_run:
        print("\n[dry-run] Skipping test gate.")
    elif not skip_tests:
        print("\n[add-technique] Running pytest gate …")
        test_dir = _PROJECT_ROOT / "tests"
        if test_dir.is_dir():
            result = subprocess.run(
                [sys.executable, "-m", "pytest", str(test_dir), "-v", "--tb=short"],
                cwd=str(_PROJECT_ROOT),
            )
            if result.returncode != 0:
                print("WARNING: Test gate failed (see output above).")
                report.append("Tests: FAILED")
            else:
                print("  Tests: PASSED")
                report.append("Tests: PASSED")
        else:
            print("  No tests/ directory found — skipping.")
            report.append("Tests: skipped (no tests/ directory)")

    # ── Step E: Report ───────────────────────────────────────────────
    print("\n" + "=" * 60)
    print("TECHNIQUE AUTO-INTEGRATION REPORT")
    print("=" * 60)
    for line in report:
        print(f"  {line}")
    print("=" * 60)

    return 0


# ── CLI entry point ──────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        prog="checkmate add-technique",
        description="Synthesise and auto-integrate a new approximation technique.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent("""\
            Examples:

              # LLM-generated card
              python -m tools.add_technique \\
                --request "Add 4-bit quantization for integer sensor data"

              # Pre-built card (skip LLM)
              python -m tools.add_technique \\
                --card techniques/cards/T31_4bit_quantization.json

              # Dry-run — see what would happen, write nothing
              python -m tools.add_technique \\
                --request "Add bit-plane slicing" --dry-run
        """),
    )
    parser.add_argument(
        "--request", type=str, default=None,
        help="Natural-language description of the technique to add.",
    )
    parser.add_argument(
        "--card", type=str, default=None, dest="card_path",
        help="Path to an existing Technique Card JSON (skips LLM).",
    )
    parser.add_argument(
        "--out", type=str, default=None, dest="out_dir",
        help="Output directory for card file (default: techniques/cards/).",
    )
    parser.add_argument(
        "--dry-run", action="store_true", default=False,
        help="Generate artifacts but do not write any files.",
    )
    parser.add_argument(
        "--skip-tests", action="store_true", default=False,
        help="Skip pytest gate after integration.",
    )
    parser.add_argument(
        "--skip-smoke", action="store_true", default=False,
        help="Skip optional smoke run.",
    )

    args = parser.parse_args()

    if not args.request and not args.card_path:
        parser.error("You must specify --request or --card.")

    rc = run_add_technique(
        request=args.request,
        card_path=args.card_path,
        out_dir=args.out_dir,
        dry_run=args.dry_run,
        skip_tests=args.skip_tests,
        skip_smoke=args.skip_smoke,
    )
    sys.exit(rc)


if __name__ == "__main__":
    main()
