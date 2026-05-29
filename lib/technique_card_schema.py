"""
Technique Card Schema
======================

Canonical JSON schema for a Technique Card — the single source of truth
for every approximation technique.  A card drives ALL downstream
artifacts: registry, prompts, few-shot examples, gatekeeper, cost model.

Usage::

    from lib.technique_card_schema import validate_card, normalize_card

    card = json.load(open("techniques/cards/T31_my_technique.json"))
    ok, errors = validate_card(card)
    if ok:
        card = normalize_card(card)
"""

from __future__ import annotations

import copy
import json
from typing import Any, Dict, List, Optional, Tuple

SCHEMA_VERSION = "1.0"

# ── Required top-level fields ────────────────────────────────────────────

_REQUIRED_TOP = [
    "schema_version",
    "technique_id",
    "technique_tag",
    "name",
    "category",
    "description_llm",
    "planning_guidance",
    "few_shot_examples",
    "feasibility",
    "cost_model",
]

_REQUIRED_PLANNING = [
    "when_to_use",
    "when_not_to_use",
    "implementation_rules",
]

_REQUIRED_FEASIBILITY = [
    "requires_fpu",
    "requires_simd",
    "memory_cost_kb",
]

_REQUIRED_COST = [
    "compute_cost_relative",
]

_REQUIRED_FEWSHOT_ENTRY = [
    "user_request",
    "assistant_response_example",
]


# ── JSON Schema (dict form — used for documentation & external tools) ───

JSON_SCHEMA: Dict[str, Any] = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "title": "CheckMate Technique Card",
    "type": "object",
    "required": _REQUIRED_TOP,
    "properties": {
        "schema_version": {"type": "string", "const": SCHEMA_VERSION},
        "technique_id": {"type": "integer", "minimum": 1},
        "technique_tag": {
            "type": "string",
            "pattern": "^T\\d+$",
            "description": "Short tag, e.g. T31",
        },
        "name": {"type": "string", "minLength": 2},
        "category": {"type": "string", "minLength": 2},
        "description_llm": {
            "type": "string",
            "minLength": 10,
            "description": (
                "Natural-language description injected into the "
                "approximation_techniques.txt prompt."
            ),
        },
        "planning_guidance": {
            "type": "object",
            "required": _REQUIRED_PLANNING,
            "properties": {
                "when_to_use": {"type": "string"},
                "when_not_to_use": {"type": "string"},
                "implementation_rules": {
                    "type": "array",
                    "items": {"type": "string"},
                    "minItems": 1,
                },
            },
        },
        "few_shot_examples": {
            "type": "array",
            "items": {
                "type": "object",
                "required": _REQUIRED_FEWSHOT_ENTRY,
                "properties": {
                    "user_request": {"type": "string"},
                    "expected_json_fields": {
                        "type": "object",
                        "description": "Optional expected JSON output fields.",
                    },
                    "assistant_response_example": {"type": "string"},
                },
            },
            "minItems": 1,
        },
        "feasibility": {
            "type": "object",
            "required": _REQUIRED_FEASIBILITY,
            "properties": {
                "requires_fpu": {"type": "boolean"},
                "requires_simd": {"type": "boolean"},
                "memory_cost_kb": {"type": "number", "minimum": 0},
                "applicable_apps": {
                    "oneOf": [
                        {"type": "array", "items": {"type": "string"}},
                        {"type": "null"},
                    ],
                    "description": "null means universally applicable.",
                },
            },
        },
        "cost_model": {
            "type": "object",
            "required": _REQUIRED_COST,
            "properties": {
                "compute_cost_relative": {
                    "type": "number",
                    "minimum": 0,
                },
                "memory_cost_kb": {
                    "type": "number",
                    "minimum": 0,
                    "description": "Redundant with feasibility; kept for ranking.",
                },
            },
        },
    },
}


# ── Validation ───────────────────────────────────────────────────────────

def validate_card(card: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """
    Validate a technique card dict against the canonical schema.

    Returns ``(True, [])`` on success, or ``(False, [error1, ...])``
    with human-readable error messages.
    """
    errors: List[str] = []

    # --- top-level required keys ---
    for key in _REQUIRED_TOP:
        if key not in card:
            errors.append(f"Missing required top-level field: '{key}'")

    if errors:
        return False, errors  # bail early — can't check deeper

    # --- schema_version ---
    if card["schema_version"] != SCHEMA_VERSION:
        errors.append(
            f"Unsupported schema_version: '{card['schema_version']}' "
            f"(expected '{SCHEMA_VERSION}')"
        )

    # --- technique_id ---
    if not isinstance(card["technique_id"], int) or card["technique_id"] < 1:
        errors.append("technique_id must be a positive integer")

    # --- technique_tag ---
    tag = card.get("technique_tag", "")
    if not isinstance(tag, str) or not tag.startswith("T"):
        errors.append("technique_tag must be a string starting with 'T' (e.g. T31)")

    # --- name ---
    if not isinstance(card.get("name"), str) or len(card["name"]) < 2:
        errors.append("name must be a string of at least 2 characters")

    # --- category ---
    if not isinstance(card.get("category"), str) or len(card["category"]) < 2:
        errors.append("category must be a string of at least 2 characters")

    # --- description_llm ---
    if not isinstance(card.get("description_llm"), str) or len(card["description_llm"]) < 10:
        errors.append("description_llm must be a string of at least 10 characters")

    # --- planning_guidance ---
    pg = card.get("planning_guidance", {})
    if not isinstance(pg, dict):
        errors.append("planning_guidance must be a dict")
    else:
        for key in _REQUIRED_PLANNING:
            if key not in pg:
                errors.append(f"planning_guidance missing required field: '{key}'")
        rules = pg.get("implementation_rules", [])
        if not isinstance(rules, list) or len(rules) < 1:
            errors.append(
                "planning_guidance.implementation_rules must be "
                "a non-empty list of strings"
            )

    # --- few_shot_examples ---
    fse = card.get("few_shot_examples", [])
    if not isinstance(fse, list) or len(fse) < 1:
        errors.append("few_shot_examples must be a non-empty list")
    else:
        for i, ex in enumerate(fse):
            if not isinstance(ex, dict):
                errors.append(f"few_shot_examples[{i}] must be a dict")
                continue
            for key in _REQUIRED_FEWSHOT_ENTRY:
                if key not in ex:
                    errors.append(
                        f"few_shot_examples[{i}] missing required field: '{key}'"
                    )

    # --- feasibility ---
    feas = card.get("feasibility", {})
    if not isinstance(feas, dict):
        errors.append("feasibility must be a dict")
    else:
        for key in _REQUIRED_FEASIBILITY:
            if key not in feas:
                errors.append(f"feasibility missing required field: '{key}'")
        if "requires_fpu" in feas and not isinstance(feas["requires_fpu"], bool):
            errors.append("feasibility.requires_fpu must be a boolean")
        if "requires_simd" in feas and not isinstance(feas["requires_simd"], bool):
            errors.append("feasibility.requires_simd must be a boolean")
        if "memory_cost_kb" in feas:
            if not isinstance(feas["memory_cost_kb"], (int, float)):
                errors.append("feasibility.memory_cost_kb must be a number")
            elif feas["memory_cost_kb"] < 0:
                errors.append("feasibility.memory_cost_kb must be >= 0")

    # --- cost_model ---
    cm = card.get("cost_model", {})
    if not isinstance(cm, dict):
        errors.append("cost_model must be a dict")
    else:
        for key in _REQUIRED_COST:
            if key not in cm:
                errors.append(f"cost_model missing required field: '{key}'")
        if "compute_cost_relative" in cm:
            if not isinstance(cm["compute_cost_relative"], (int, float)):
                errors.append("cost_model.compute_cost_relative must be a number")
            elif cm["compute_cost_relative"] < 0:
                errors.append("cost_model.compute_cost_relative must be >= 0")

    return (len(errors) == 0), errors


# ── Normalisation (fill defaults) ────────────────────────────────────────

def normalize_card(card: Dict[str, Any]) -> Dict[str, Any]:
    """
    Return a copy of *card* with missing optional fields filled with
    safe defaults.  Assumes ``validate_card`` has already passed.
    """
    c = copy.deepcopy(card)

    # Default applicable_apps → None (all apps)
    c.setdefault("feasibility", {}).setdefault("applicable_apps", None)

    # Default cost_model.memory_cost_kb mirrors feasibility
    c.setdefault("cost_model", {}).setdefault(
        "memory_cost_kb",
        c["feasibility"].get("memory_cost_kb", 0),
    )

    # Ensure each few-shot example has expected_json_fields
    for ex in c.get("few_shot_examples", []):
        ex.setdefault("expected_json_fields", {})

    return c


# ── Card → TechniqueEntry adapter ────────────────────────────────────────

def card_to_technique_entry(card: Dict[str, Any]):
    """
    Convert a validated card dict to a
    ``lib.technique_registry.TechniqueEntry``.  Import is deferred
    to avoid circular dependencies.
    """
    from lib.technique_registry import TechniqueEntry

    feas = card["feasibility"]
    return TechniqueEntry(
        technique_id=card["technique_id"],
        name=card["name"],
        requires_fpu=feas.get("requires_fpu", False),
        requires_simd=feas.get("requires_simd", False),
        memory_cost_kb=feas.get("memory_cost_kb", 0.0),
        compute_cost_relative=card["cost_model"].get(
            "compute_cost_relative", 1.0
        ),
        applicable_apps=feas.get("applicable_apps"),
        description=card.get("description_llm", card["name"]),
    )


# ── LLM generation prompt ───────────────────────────────────────────────

CARD_GENERATION_SYSTEM_PROMPT = """\
You are a senior approximate-computing engineer working on the CheckMate \
framework for batteryless IoT devices.  When asked to add a new approximation \
technique you MUST return a single JSON object conforming EXACTLY to the \
Technique Card schema below.  Return ONLY the JSON — no markdown fences, \
no prose before or after.

=== SCHEMA (version {version}) ===

{schema_json}

=== RULES ===
- technique_id: pick the next available integer (>= {next_id}).
- technique_tag: "T" + technique_id  (e.g. T31).
- description_llm: 2-5 sentences suitable for injecting into the LLM prompt.
- planning_guidance.implementation_rules: concrete do/don't bullet points.
- few_shot_examples: at least 1 entry with before/after C code.
- feasibility: be conservative — set requires_fpu=true only if unavoidable.
- cost_model.compute_cost_relative: 0.1 (trivial) .. 1.0 (heavy).
"""


def build_card_generation_prompt(
    user_request: str,
    next_id: int,
) -> Tuple[str, str]:
    """
    Build (system_message, user_message) for the LLM to generate a card.
    """
    schema_json = json.dumps(JSON_SCHEMA, indent=2)
    system = CARD_GENERATION_SYSTEM_PROMPT.format(
        version=SCHEMA_VERSION,
        schema_json=schema_json,
        next_id=next_id,
    )
    user_msg = (
        f"Add the following approximation technique to CheckMate:\n\n"
        f"{user_request}\n\n"
        f"Return the Technique Card JSON."
    )
    return system, user_msg
