"""
Hardware-Aware Observability
=============================

Writes per-run output files that record:

  1. ``outputs/LLM_CONSTRAINTS_<app>_<hwname>.txt``
     — hardware summary, feasible list, ranked list, raw LLM technique
       selection text, and final validated technique IDs.

  2. ``outputs/hardware_rejections_<app>_<hwname>.json``
     — every rejected technique with structured reason.

These files are the "proof" that the menu changed and the LLM was forced
to pick from a hardware-specific menu.
"""

import json
import os
from datetime import datetime
from typing import Dict, List, Optional, Set, Tuple

from lib.hardware_profile import HardwareProfile
from lib.technique_registry import TechniqueEntry, TECHNIQUE_REGISTRY
from lib.constraint_gatekeeper import (
    filter_feasible_techniques,
    format_feasible_list,
)
from lib.hardware_cost_model import rank_techniques, format_ranked_list


_OUTPUTS_DIR = "outputs"


def _ensure_outputs_dir():
    os.makedirs(_OUTPUTS_DIR, exist_ok=True)


# ---------------------------------------------------------------------------
#  Rejection JSON
# ---------------------------------------------------------------------------

def _build_rejection_reason(tech: TechniqueEntry, hw: HardwareProfile) -> Optional[str]:
    """Return a single-line reason string if *tech* is infeasible on *hw*."""
    reasons = []
    if tech.requires_fpu and not hw.has_fpu:
        reasons.append("requires FPU")
    if tech.requires_simd and not hw.has_simd:
        reasons.append("requires SIMD")
    if tech.memory_cost_kb > hw.ram_kb:
        reasons.append(f"needs {tech.memory_cost_kb} KB RAM (only {hw.ram_kb} KB)")
    return "; ".join(reasons) if reasons else None


def write_rejection_json(
    app_name: str,
    hw: HardwareProfile,
    feasible: Dict[int, TechniqueEntry],
    rejection_log: List[str],
) -> str:
    """
    Write ``outputs/hardware_rejections_<app>_<hwname>.json``.

    Returns the path written.
    """
    _ensure_outputs_dir()

    from lib.technique_registry import get_applicable_techniques
    candidates = get_applicable_techniques(app_name)

    entries = []
    for tid, tech in sorted(TECHNIQUE_REGISTRY.items()):
        if tid in feasible:
            continue   # only record rejected
        reason_parts = []
        # Not applicable to this app?
        if tech.applicable_apps is not None and app_name not in tech.applicable_apps:
            reason_parts.append(f"not applicable to {app_name}")
        # HW constraint violation?
        hw_reason = _build_rejection_reason(tech, hw)
        if hw_reason:
            reason_parts.append(hw_reason)
        if not reason_parts:
            # Implicitly rejected because not in candidates (app filter)
            # but no HW issue either
            reason_parts.append(f"not applicable to {app_name}")
        entries.append({
            "technique_id": tid,
            "technique_name": tech.name,
            "reason": "; ".join(reason_parts),
        })

    safe_hw = hw.name.replace(" ", "_").replace("/", "_")
    path = os.path.join(_OUTPUTS_DIR,
                        f"hardware_rejections_{app_name}_{safe_hw}.json")

    payload = {
        "timestamp": datetime.now().isoformat(),
        "hardware": hw.name,
        "app": app_name,
        "total_techniques": len(TECHNIQUE_REGISTRY),
        "feasible_count": len(feasible),
        "rejected_count": len(entries),
        "rejections": entries,
    }
    with open(path, "w") as f:
        json.dump(payload, f, indent=2)

    return path


# ---------------------------------------------------------------------------
#  Constraint / Proof TXT
# ---------------------------------------------------------------------------

def write_constraints_txt(
    app_name: str,
    hw: HardwareProfile,
    feasible: Dict[int, TechniqueEntry],
    ranked: List,
    llm_raw_response: str = "",
    validated_ids: Optional[Set[int]] = None,
    invalid_ids: Optional[Set[int]] = None,
    clamped_ids: Optional[List[int]] = None,
) -> str:
    """
    Write ``outputs/LLM_CONSTRAINTS_<app>_<hwname>.txt``.

    Returns the path written.
    """
    _ensure_outputs_dir()

    safe_hw = hw.name.replace(" ", "_").replace("/", "_")
    path = os.path.join(_OUTPUTS_DIR,
                        f"LLM_CONSTRAINTS_{app_name}_{safe_hw}.txt")

    with open(path, "w") as f:
        f.write("=" * 70 + "\n")
        f.write("  HARDWARE-AWARE APPROXIMATION — CONSTRAINT PROOF\n")
        f.write("=" * 70 + "\n\n")

        # Section 1: Hardware summary
        f.write("HARDWARE PROFILE\n")
        f.write("-" * 40 + "\n")
        f.write(f"  {hw.startup_line()}\n")
        f.write(f"  {hw.summary()}\n\n")

        # Section 2: Feasible technique list
        f.write("FEASIBLE TECHNIQUES\n")
        f.write("-" * 40 + "\n")
        f.write(format_feasible_list(feasible) + "\n\n")

        # Section 3: Ranked list
        if ranked:
            f.write("RANKED BY COST (cheapest first)\n")
            f.write("-" * 40 + "\n")
            f.write(format_ranked_list(ranked) + "\n\n")

        # Section 4: Raw LLM technique-selection response
        f.write("RAW LLM TECHNIQUE-SELECTION RESPONSE\n")
        f.write("-" * 40 + "\n")
        if llm_raw_response:
            f.write(llm_raw_response[:5000] + "\n")
        else:
            f.write("  (not captured — --no_llm mode or LLM not run)\n")
        f.write("\n")

        # Section 5: Validated IDs
        f.write("FINAL VALIDATED TECHNIQUE IDs\n")
        f.write("-" * 40 + "\n")
        if validated_ids is not None:
            f.write(f"  Valid  : {sorted(validated_ids)}\n")
        else:
            f.write("  (validation not performed)\n")
        if invalid_ids:
            f.write(f"  Invalid: {sorted(invalid_ids)} — "
                    "these were rejected by the post-LLM validator\n")
        if clamped_ids:
            f.write(f"  Clamped: {clamped_ids} — "
                    "these were force-removed from apx_all.json\n")
        f.write("\n")

        f.write(f"Generated: {datetime.now().isoformat()}\n")

    return path
