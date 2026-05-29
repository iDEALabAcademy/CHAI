"""
Hardware Cost Model Plugin
===========================

Estimates the *execution cost* of each surviving technique on the target
hardware and ranks them from cheapest to most expensive.

The cost score for a technique is::

    cost_score = compute_cost_relative * (100 / clock_mhz)

Lower scores are better (less overhead on the target platform).

The ranked list can be fed to the LLM so it prefers cheaper techniques
first, or it can simply inform the terminal output.
"""

from typing import Dict, List, Tuple

from lib.hardware_profile import HardwareProfile
from lib.technique_registry import TechniqueEntry
from utils.utils import Dprint


# ---------------------------------------------------------------------------
#  Cost estimation
# ---------------------------------------------------------------------------

def estimate_cost(tech: TechniqueEntry, hw: HardwareProfile) -> float:
    """
    Produce a scalar cost score for running *tech* on *hw*.

    The score captures the notion that a technique with high
    ``compute_cost_relative`` will be proportionally more expensive on a
    slower clock, and that memory pressure is also a concern.

    Returns
    -------
    float
        Non-negative cost score (lower is better).
    """
    # Base clock-scaled cost
    compute_factor = tech.compute_cost_relative * (100.0 / hw.clock_mhz)

    # Memory pressure penalty: fraction of available RAM consumed
    mem_pressure = (tech.memory_cost_kb / hw.ram_kb) if hw.ram_kb > 0 else 0.0

    # FPU penalty: if the technique *officially* doesn't need FPU but the
    # technique's description hints at float work, software emulation adds
    # overhead.  For registry entries that *require* FPU, we have already
    # filtered them in the gatekeeper — so no extra penalty here.
    # (Kept as a future extension point.)

    cost = compute_factor + mem_pressure * 0.5   # weighted sum

    return round(cost, 4)


# ---------------------------------------------------------------------------
#  Ranking
# ---------------------------------------------------------------------------

def rank_techniques(
    feasible: Dict[int, TechniqueEntry],
    hw: HardwareProfile,
) -> List[Tuple[int, str, float]]:
    """
    Rank the *feasible* techniques by ascending cost on *hw*.

    Returns
    -------
    list of (technique_id, name, cost_score)
        Sorted cheapest-first.
    """
    scored: List[Tuple[int, str, float]] = []
    for tid, tech in feasible.items():
        score = estimate_cost(tech, hw)
        scored.append((tid, tech.name, score))

    scored.sort(key=lambda x: x[2])

    Dprint("[Cost Model] Ranked techniques (cheapest first):")
    for tid, name, score in scored:
        Dprint(f"  T{tid:02d} {name}: cost = {score}")

    return scored


def format_ranked_list(
    ranked: List[Tuple[int, str, float]],
) -> str:
    """
    Produce a human-readable ranked table for the terminal log.
    """
    lines = ["  Rank  ID  Technique                          Cost"]
    lines.append("  " + "-" * 52)
    for rank, (tid, name, score) in enumerate(ranked, start=1):
        lines.append(f"  {rank:>4}  {tid:>2}  {name:<35s} {score:.4f}")
    return "\n".join(lines)
