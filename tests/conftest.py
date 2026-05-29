"""
conftest.py — shared fixtures for CheckMate tests
"""

import json
import os
import shutil
import tempfile

import pytest

# Ensure project root is on sys.path
import sys

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)


# ── Fixtures ─────────────────────────────────────────────────────────────

SAMPLE_VALID_CARD = {
    "schema_version": "1.0",
    "technique_id": 99,
    "technique_tag": "T99",
    "name": "Test Technique",
    "category": "Testing",
    "description_llm": (
        "A test technique that does nothing useful but has all required "
        "fields for validation."
    ),
    "planning_guidance": {
        "when_to_use": "When writing tests.",
        "when_not_to_use": "In production.",
        "implementation_rules": [
            "Do NOT panic.",
            "Always return deterministic results.",
        ],
    },
    "few_shot_examples": [
        {
            "user_request": "Apply test technique to foo().",
            "expected_json_fields": {
                "knobVariables": "['test_knob']",
                "knobRanges": "[{'test_knob': [0, 10]}]",
            },
            "assistant_response_example": (
                "```c\nvoid foo() {\n"
                "    /*Knob Variables Declaration Start*/\n"
                "    int test_knob = 0;\n"
                "    /*Knob Variables Declaration End*/\n"
                "}\n```"
            ),
        }
    ],
    "feasibility": {
        "requires_fpu": False,
        "requires_simd": False,
        "memory_cost_kb": 0.5,
        "applicable_apps": None,
    },
    "cost_model": {
        "compute_cost_relative": 0.3,
        "memory_cost_kb": 0.5,
    },
}


@pytest.fixture
def valid_card():
    """Return a deep copy of a minimal valid Technique Card dict."""
    import copy
    return copy.deepcopy(SAMPLE_VALID_CARD)


@pytest.fixture
def tmp_cards_dir(valid_card):
    """
    Create a temporary directory with one valid card file.
    Yields the path; cleans up afterwards.
    """
    d = tempfile.mkdtemp(prefix="checkmate_cards_")
    card_path = os.path.join(d, "T99_test_technique.json")
    with open(card_path, "w") as f:
        json.dump(valid_card, f, indent=2)
    yield d
    shutil.rmtree(d, ignore_errors=True)


@pytest.fixture
def tmp_prompts_dir():
    """
    Create a temporary prompts directory mirroring the real layout,
    with starter anchors.
    """
    d = tempfile.mkdtemp(prefix="checkmate_prompts_")
    fewshot_dir = os.path.join(d, "FewShotExamples")
    os.makedirs(fewshot_dir)

    files = {
        os.path.join(d, "approximation_techniques.txt"): (
            "Existing techniques here.\n"
            "# === AUTO-GENERATED START ===\n"
            "# === AUTO-GENERATED END ===\n"
        ),
        os.path.join(d, "planning_step.txt"): (
            "Planning step preamble.\n"
            "# === AUTO-GENERATED START ===\n"
            "# === AUTO-GENERATED END ===\n"
        ),
        os.path.join(d, "approximate_vPDG1.txt"): (
            "Approx vPDG1 preamble.\n"
            "# === AUTO-GENERATED START ===\n"
            "# === AUTO-GENERATED END ===\n"
        ),
        os.path.join(fewshot_dir, "newTechniqueExamples.txt"): (
            "Existing examples.\n"
            "### === AUTO-GENERATED FEW-SHOT START ===\n"
            "### === AUTO-GENERATED FEW-SHOT END ===\n"
        ),
    }
    for path, content in files.items():
        with open(path, "w") as f:
            f.write(content)

    yield d
    shutil.rmtree(d, ignore_errors=True)
