"""
Hardware Profile Loader
========================

Loads hardware specifications from JSON files to enable hardware-aware
approximation planning in CheckMate.

A HardwareProfile describes the capabilities and constraints of the target
deployment platform (e.g., MSP430, ARM Cortex-A53).  The pipeline uses this
information to filter out infeasible approximation techniques before they
reach the LLM.
"""

import json
import os
from utils.utils import Dprint


class HardwareProfile:
    """Structured representation of a target hardware platform."""

    def __init__(self, name: str, ram_kb: float, has_fpu: bool,
                 has_simd: bool, energy_budget_mj: float, clock_mhz: float):
        self.name = name
        self.ram_kb = ram_kb
        self.has_fpu = has_fpu
        self.has_simd = has_simd
        self.energy_budget_mj = energy_budget_mj
        self.clock_mhz = clock_mhz

    def __repr__(self):
        return (f"HardwareProfile(name={self.name!r}, ram_kb={self.ram_kb}, "
                f"has_fpu={self.has_fpu}, has_simd={self.has_simd}, "
                f"energy_budget_mj={self.energy_budget_mj}, "
                f"clock_mhz={self.clock_mhz})")

    def summary(self) -> str:
        """One-line human-readable summary for log output."""
        fpu = "FPU" if self.has_fpu else "no-FPU"
        simd = "SIMD" if self.has_simd else "no-SIMD"
        return (f"{self.name} — {self.ram_kb} KB RAM, {self.clock_mhz} MHz, "
                f"{fpu}, {simd}, {self.energy_budget_mj} mJ budget")

    def startup_line(self) -> str:
        """Compact [HW] log line printed at startup."""
        return (f"[HW] name={self.name}, clock={self.clock_mhz}MHz, "
                f"ram={self.ram_kb}KB, fpu={int(self.has_fpu)}, "
                f"simd={int(self.has_simd)}")


def load_hardware_profile(json_path: str) -> HardwareProfile:
    """
    Parse a hardware profile JSON file and return a HardwareProfile object.

    Expected JSON schema::

        {
            "name": "MSP430",
            "ram_kb": 10,
            "has_fpu": false,
            "has_simd": false,
            "energy_budget_mj": 5,
            "clock_mhz": 16
        }

    Raises:
        FileNotFoundError: if *json_path* does not exist.
        KeyError: if a required field is missing.
    """
    if not os.path.exists(json_path):
        raise FileNotFoundError(f"Hardware profile not found: {json_path}")

    with open(json_path, "r") as f:
        data = json.load(f)

    required_keys = ["name", "ram_kb", "has_fpu", "has_simd",
                     "energy_budget_mj", "clock_mhz"]
    for key in required_keys:
        if key not in data:
            raise KeyError(f"Hardware profile missing required key: '{key}'")

    # --- Type validation -----------------------------------------------
    _type_specs = {
        "name":            str,
        "ram_kb":          (int, float),
        "has_fpu":         (bool, int),
        "has_simd":        (bool, int),
        "energy_budget_mj":(int, float),
        "clock_mhz":       (int, float),
    }
    for key, expected in _type_specs.items():
        val = data[key]
        if not isinstance(val, expected):
            raise TypeError(
                f"Hardware profile field '{key}' must be "
                f"{expected}, got {type(val).__name__} ({val!r})"
            )
    # Numeric sanity
    if float(data["ram_kb"]) <= 0:
        raise ValueError("ram_kb must be > 0")
    if float(data["clock_mhz"]) <= 0:
        raise ValueError("clock_mhz must be > 0")

    profile = HardwareProfile(
        name=data["name"],
        ram_kb=float(data["ram_kb"]),
        has_fpu=bool(data["has_fpu"]),
        has_simd=bool(data["has_simd"]),
        energy_budget_mj=float(data["energy_budget_mj"]),
        clock_mhz=float(data["clock_mhz"]),
    )

    Dprint(f"[HW Profile] Loaded: {profile.summary()}")
    return profile


# ---------------------------------------------------------------------------
# Default profile — used when no --hardware flag is supplied
# ---------------------------------------------------------------------------

DEFAULT_PROFILE = HardwareProfile(
    name="MSP430",
    ram_kb=10,
    has_fpu=False,
    has_simd=False,
    energy_budget_mj=5,
    clock_mhz=16,
)
