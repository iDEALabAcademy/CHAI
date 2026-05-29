# CheckMate: Detailed Workflow Document

## Automatic Technique Integration & Hardware-Aware Framework

---

## Table of Contents

1. [Overview](#1-overview)
2. [Part A — Automatic Technique Integration](#2-part-a--automatic-technique-integration)
   - [2.1 Technique Card Schema](#21-technique-card-schema)
   - [2.2 CLI Entry Point — `add_technique.py`](#22-cli-entry-point--add_techniquepy)
   - [2.3 LLM-Based Card Synthesis](#23-llm-based-card-synthesis)
   - [2.4 Schema Validation & Normalization](#24-schema-validation--normalization)
   - [2.5 Card Storage](#25-card-storage)
   - [2.6 Technique Registry Auto-Loading](#26-technique-registry-auto-loading)
   - [2.7 Prompt Asset Injection](#27-prompt-asset-injection)
   - [2.8 Test Gate](#28-test-gate)
   - [2.9 End-to-End Data Flow](#29-end-to-end-data-flow)
3. [Part B — Hardware-Aware Framework](#3-part-b--hardware-aware-framework)
   - [3.1 Hardware Profile](#31-hardware-profile)
   - [3.2 Constraint Gatekeeper](#32-constraint-gatekeeper)
   - [3.3 Hardware Cost Model](#33-hardware-cost-model)
   - [3.4 LLM Prompt Injection](#34-llm-prompt-injection)
   - [3.5 Post-LLM Validation](#35-post-llm-validation)
   - [3.6 Clamping Safety Mechanism](#36-clamping-safety-mechanism)
   - [3.7 Observability Outputs](#37-observability-outputs)
   - [3.8 End-to-End Data Flow](#38-end-to-end-data-flow)
4. [How the Two Subsystems Interact](#4-how-the-two-subsystems-interact)
5. [File Reference](#5-file-reference)

---

## 1. Overview

CheckMate is an LLM-driven approximate computing framework designed for batteryless IoT devices. It takes benchmark C applications, sends each function to an LLM for approximation, and then compiles, validates, and evaluates the resulting approximated code on a simulated intermittent computing platform.

CheckMate has two key subsystems that work together:

1. **Automatic Technique Integration** — A pipeline that allows adding new approximation techniques without manually editing prompt files, registries, or few-shot examples. A single JSON "Technique Card" drives all downstream artifacts automatically.

2. **Hardware-Aware Framework** — A constraint system that filters, ranks, and enforces approximation techniques based on the capabilities and limitations of the target hardware platform (e.g., MSP430 has no FPU, no SIMD, only 10 KB RAM).

These subsystems share a common data structure — the **Technique Registry** (`TECHNIQUE_REGISTRY`) — which serves as the single source of truth for all known approximation techniques and their hardware requirements.

---

## 2. Part A — Automatic Technique Integration

### 2.1 Technique Card Schema

**File:** `lib/technique_card_schema.py`

The Technique Card is a JSON document that serves as the **single source of truth** for an approximation technique. Every downstream artifact — registry entry, prompt text, few-shot examples, feasibility constraints, cost model — is derived from this one card.

#### Schema Structure (Version 1.0)

```json
{
  "schema_version": "1.0",
  "technique_id": 31,
  "technique_tag": "T31",
  "name": "4-Bit Quantization",
  "category": "data-reduction",
  "description_llm": "A 2-5 sentence description injected into the LLM prompt...",
  "planning_guidance": {
    "when_to_use": "When sensor data has limited dynamic range...",
    "when_not_to_use": "When full precision is needed for safety-critical values...",
    "implementation_rules": [
      "Always define APX_QUANT_BITS as a knob macro",
      "Preserve original variable type for output"
    ]
  },
  "few_shot_examples": [
    {
      "user_request": "Approximate this sensor reading function...",
      "assistant_response_example": "// Approximated code with quantization...",
      "expected_json_fields": {}
    }
  ],
  "feasibility": {
    "requires_fpu": false,
    "requires_simd": false,
    "memory_cost_kb": 0.0,
    "applicable_apps": null
  },
  "cost_model": {
    "compute_cost_relative": 0.3,
    "memory_cost_kb": 0.0
  }
}
```

#### Required Fields

| Field | Type | Purpose |
|-------|------|---------|
| `schema_version` | string | Must be `"1.0"` |
| `technique_id` | int (≥ 1) | Unique numeric identifier |
| `technique_tag` | string | Short tag like `"T31"` |
| `name` | string (≥ 2 chars) | Human-readable technique name |
| `category` | string | Classification (e.g., `"data-reduction"`, `"compute-skip"`) |
| `description_llm` | string (≥ 10 chars) | Description injected into the LLM's technique list |
| `planning_guidance` | object | Guidance for LLM's planning step |
| `planning_guidance.when_to_use` | string | Conditions favoring this technique |
| `planning_guidance.when_not_to_use` | string | Conditions against using this technique |
| `planning_guidance.implementation_rules` | string[] (≥ 1) | Concrete do/don't rules |
| `few_shot_examples` | array (≥ 1) | Before/after code examples for the LLM |
| `feasibility` | object | Hardware requirement declarations |
| `feasibility.requires_fpu` | bool | Does this technique need a floating-point unit? |
| `feasibility.requires_simd` | bool | Does this technique need SIMD instructions? |
| `feasibility.memory_cost_kb` | number (≥ 0) | RAM overhead in KB |
| `cost_model` | object | Execution cost parameters |
| `cost_model.compute_cost_relative` | number (≥ 0) | 0.1 (trivial) to 1.0 (heavy) |

#### Optional Fields

| Field | Default | Purpose |
|-------|---------|---------|
| `feasibility.applicable_apps` | `null` (all apps) | List of benchmark names this technique applies to, or `null` for universal |
| `cost_model.memory_cost_kb` | mirrors feasibility | Redundant field kept for ranking use |
| `few_shot_examples[].expected_json_fields` | `{}` | Optional expected JSON output metadata |

---

### 2.2 CLI Entry Point — `add_technique.py`

**File:** `tools/add_technique.py`

The CLI tool provides the top-level entry point for the entire technique integration pipeline. It can be invoked in two ways:

```bash
# Mode 1: LLM-generated card (provide a natural-language description)
python -m tools.add_technique \
  --request "Add 4-bit quantization for integer sensor data"

# Mode 2: Pre-built card (skip LLM, provide an existing JSON file)
python -m tools.add_technique \
  --card techniques/cards/T31_4bit_quantization.json

# Dry-run mode (preview changes without writing files)
python -m tools.add_technique \
  --request "Add bit-plane slicing" --dry-run
```

#### CLI Flags

| Flag | Description |
|------|-------------|
| `--request TEXT` | Natural-language description → triggers LLM synthesis |
| `--card FILE` | Path to existing card JSON → skips LLM |
| `--out DIR` | Override output directory (default: `techniques/cards/`) |
| `--dry-run` | Preview all changes to stdout without writing files |
| `--skip-tests` | Skip pytest gate after integration |
| `--skip-smoke` | Skip optional smoke run |

#### Pipeline Steps (inside `run_add_technique()`)

The function `run_add_technique()` orchestrates five sequential steps:

**Step A — Obtain the Card:**
- If `--card` is provided: load JSON from the file path.
- If `--request` is provided: compute `next_id` (max existing ID + 1), call the LLM via `_invoke_llm_for_card()`.

**Step B — Validate:**
- Call `validate_card(card)` from `technique_card_schema.py`.
- If validation fails, print errors and exit with return code 1.
- If valid, call `normalize_card(card)` to fill optional defaults.

**Step C — Write Artifacts:**
- **C.1 — Card file:** Write `T{id}_{slug}.json` to `techniques/cards/`. If the source card is already in the output directory, skip the write.
- **C.2 — Prompt assets:** Call `load_all_cards()` to reload all cards from disk, then call `update_all_prompt_assets()` to inject auto-generated blocks into the 4 prompt files.
- **C.3 — Registry:** No write needed. The `technique_registry.py` module auto-loads cards from `techniques/cards/` at import time. The next time any module imports the registry, the new card will be present.

**Step D — Run Gates:**
- Unless `--skip-tests` is set, run `pytest tests/ -v --tb=short`.
- Report PASSED or FAILED.

**Step E — Report:**
- Print a summary of all actions taken: card file path, prompt files updated, test results.

---

### 2.3 LLM-Based Card Synthesis

**File:** `tools/add_technique.py` → `_invoke_llm_for_card()`  
**File:** `lib/technique_card_schema.py` → `build_card_generation_prompt()`

When `--request` is used (no pre-built card), the pipeline calls an LLM to synthesize the Technique Card JSON.

#### Prompt Construction

The function `build_card_generation_prompt(user_request, next_id)` generates a two-part prompt:

1. **System Message:** Instructs the LLM to act as "a senior approximate-computing engineer working on CheckMate for batteryless IoT devices." It includes the full JSON Schema and concrete rules:
   - `technique_id`: must be ≥ `next_id`
   - `technique_tag`: `"T"` + technique_id
   - `description_llm`: 2–5 sentences suitable for prompt injection
   - `implementation_rules`: concrete do/don't bullet points
   - `few_shot_examples`: at least 1 entry with before/after C code
   - `feasibility`: be conservative (only `requires_fpu=true` if unavoidable)
   - `cost_model.compute_cost_relative`: 0.1 (trivial) to 1.0 (heavy)

2. **User Message:** `"Add the following approximation technique to CheckMate:\n\n{user_request}\n\nReturn the Technique Card JSON."`

#### LLM Backend

The `_invoke_llm_for_card()` function tries **Anthropic first** (Claude), then falls back to **OpenAI** (GPT-4o):

```
Anthropic (claude-sonnet-4-20250514, temperature=0, max_tokens=4096)
    ↓ on failure
OpenAI (gpt-4o, temperature=0, max_tokens=4096)
    ↓ on failure
RuntimeError("Both LLM backends failed")
```

The raw LLM response is cleaned (markdown fences stripped) and parsed as JSON.

---

### 2.4 Schema Validation & Normalization

**File:** `lib/technique_card_schema.py`

#### Validation (`validate_card`)

The `validate_card(card)` function performs field-by-field checks:

1. **Top-level required keys:** `schema_version`, `technique_id`, `technique_tag`, `name`, `category`, `description_llm`, `planning_guidance`, `few_shot_examples`, `feasibility`, `cost_model`
2. **Schema version:** must equal `"1.0"`
3. **technique_id:** must be a positive integer
4. **technique_tag:** must start with `"T"`
5. **name:** string ≥ 2 characters
6. **category:** string ≥ 2 characters
7. **description_llm:** string ≥ 10 characters
8. **planning_guidance:** must contain `when_to_use`, `when_not_to_use`, `implementation_rules` (non-empty list)
9. **few_shot_examples:** non-empty list; each entry must have `user_request` and `assistant_response_example`
10. **feasibility:** must contain `requires_fpu` (bool), `requires_simd` (bool), `memory_cost_kb` (number ≥ 0)
11. **cost_model:** must contain `compute_cost_relative` (number ≥ 0)

Returns `(True, [])` on success, or `(False, [error_strings])` on failure.

#### Normalization (`normalize_card`)

After validation passes, `normalize_card(card)` fills optional defaults:
- `feasibility.applicable_apps` → `null` (universal)
- `cost_model.memory_cost_kb` → mirrors `feasibility.memory_cost_kb`
- Each `few_shot_examples[]` entry gets an empty `expected_json_fields: {}`

---

### 2.5 Card Storage

Cards are stored as JSON files in `techniques/cards/` with a deterministic filename:

```
techniques/cards/T{id}_{slug}.json

Example: techniques/cards/T31_4bit_quantization.json
```

The slug is generated from the technique name by lowercasing, replacing non-alphanumeric sequences with underscores, and trimming.

---

### 2.6 Technique Registry Auto-Loading

**File:** `lib/technique_registry.py`

The Technique Registry is the central catalogue of all approximation techniques known to CheckMate. It is a Python dictionary mapping technique IDs to `TechniqueEntry` objects.

#### `TechniqueEntry` Class

```python
class TechniqueEntry:
    technique_id: int         # Unique numeric ID (1, 2, ..., 30, 31, ...)
    name: str                 # Human-readable name
    requires_fpu: bool        # Needs floating-point unit?
    requires_simd: bool       # Needs SIMD instructions?
    memory_cost_kb: float     # RAM overhead in KB
    compute_cost_relative: float  # Relative execution cost (0.1 - 1.0)
    applicable_apps: Optional[List[str]]  # None = all apps
    description: str          # Short description
```

#### Built-in Registry (T1–T30)

The registry is initialized with 30 hardcoded entries covering:

- **T1–T20:** General approximation techniques (Loop Perforation, Precision Scaling, Function Memoization, Task Skipping, Quantization, etc.)
- **T21–T30:** CheckMate-specific techniques (Early-Exit, Spatial Downsampling, Temporal Decimation, Pattern Segmentation, Nibble Lookup, etc.)

Each entry declares its hardware requirements. For example:
- **T9 (Dynamic Precision Adjustment):** `requires_fpu=True`
- **T14 (Multi-Fidelity Modeling):** `requires_fpu=True, memory_cost_kb=1.0`
- **T17 (Neural Network Pruning):** `requires_fpu=True, memory_cost_kb=2.0`
- **T22 (Spatial Downsampling):** `applicable_apps=["sobel-iclib", ...]`

#### Auto-Loading Mechanism

At **import time**, the function `_load_cards_into_registry()` runs automatically:

```python
# This line executes when any module does: from lib.technique_registry import ...
_loaded_cards = _load_cards_into_registry(TECHNIQUE_REGISTRY)
```

The function:

1. Scans `techniques/cards/*.json` for all JSON files (sorted alphabetically).
2. For each file, loads the JSON and extracts:
   - `technique_id` from the top-level field
   - `requires_fpu`, `requires_simd`, `memory_cost_kb` from `feasibility`
   - `compute_cost_relative` from `cost_model`
   - `applicable_apps` from `feasibility`
   - `description_llm` as the description
3. Creates a `TechniqueEntry` and **merges** it into `TECHNIQUE_REGISTRY`.

**Key property:** Card-based entries **override** built-in entries with the same `technique_id`. This means you can update a built-in technique's properties by placing a card with the same ID.

#### Helper Functions

- `get_all_techniques()` → returns the full `TECHNIQUE_REGISTRY` dict
- `get_applicable_techniques(app_name)` → filters to techniques where `applicable_apps is None` or `app_name in applicable_apps`
- `load_all_cards(cards_dir)` → loads and returns raw card dicts (used by prompt_updater)
- `get_loaded_card_files()` → returns filenames of cards loaded at import time

---

### 2.7 Prompt Asset Injection

**File:** `lib/prompt_updater.py`

The Prompt Updater injects auto-generated text into CheckMate's 4 prompt files using an **anchor-bounded replacement** strategy. This ensures that:
- Only text between designated anchors is modified
- Everything above and below the anchors is preserved
- If anchors are missing, they are appended at the end of the file

#### Anchor Mechanism

Two pairs of anchors are used:

```
# Standard anchors (for 3 prompt files):
# === AUTO-GENERATED START ===
... auto-generated content ...
# === AUTO-GENERATED END ===

# Few-shot anchors (for the examples file):
### === AUTO-GENERATED FEW-SHOT START ===
... auto-generated few-shot examples ...
### === AUTO-GENERATED FEW-SHOT END ===
```

The `inject_between_anchors(filepath, new_block, start_anchor, end_anchor)` function:
1. Reads the file content
2. Splits on the start anchor
3. Splits on the end anchor
4. Reconstructs: `before_start + start_anchor + new_block + end_anchor + after_end`
5. Writes back to the file

#### Render Functions

Each render function takes a list of card dicts and produces a formatted text block:

| Function | Target File | Content |
|----------|-------------|---------|
| `render_techniques_block(cards)` | `prompts/approximation_techniques.txt` | Numbered list: `"{id}. {name}: {description_llm}"` |
| `render_planning_block(cards)` | `prompts/planning_step.txt` | Per-technique: when to use, when not to use |
| `render_rules_block(cards)` | `prompts/approximate_vPDG1.txt` | Implementation rules as bullet lists |
| `render_fewshot_block(cards)` | `prompts/FewShotExamples/newTechniqueExamples.txt` | Before/after code examples |

#### `update_all_prompt_assets(cards, prompt_dir, dry_run)`

This function orchestrates all 4 injections:

```python
assets = [
    ("prompts/approximation_techniques.txt",  render_techniques_block, START/END anchors),
    ("prompts/planning_step.txt",             render_planning_block,   START/END anchors),
    ("prompts/approximate_vPDG1.txt",         render_rules_block,      START/END anchors),
    ("prompts/FewShotExamples/newTechniqueExamples.txt", render_fewshot_block, FEWSHOT anchors),
]
```

In dry-run mode, it computes what would change but writes nothing.

Returns a list of file paths that were (or would be) modified.

---

### 2.8 Test Gate

After all artifacts are written, the CLI runs `pytest tests/ -v --tb=short` as a quality gate. This catches:
- Schema validation regressions
- Prompt injection errors
- Registry loading failures

The gate can be skipped with `--skip-tests`.

---

### 2.9 End-to-End Data Flow

```
User Request (natural language)
         │
         ▼
  ┌──────────────────────┐
  │  add_technique.py    │ ◄── CLI entry point
  │  (Step A)            │
  └──────┬───────────────┘
         │
         ├─ --request ──────────────────────┐
         │                                  ▼
         │                    ┌──────────────────────────┐
         │                    │  _invoke_llm_for_card()  │
         │                    │  LLM synthesis           │
         │                    │  (Anthropic → OpenAI)    │
         │                    └──────────┬───────────────┘
         │                               │
         │◄──────────────────────────────┘
         │  card dict (JSON)
         ▼
  ┌──────────────────────┐
  │  validate_card()     │ ◄── technique_card_schema.py
  │  (Step B)            │
  │  Field-by-field      │
  │  schema checks       │
  └──────┬───────────────┘
         │ if invalid → exit(1)
         ▼
  ┌──────────────────────┐
  │  normalize_card()    │ ◄── Fill optional defaults
  └──────┬───────────────┘
         │
         ▼
  ┌──────────────────────────────────────────┐
  │  Write Artifacts (Step C)                │
  │                                          │
  │  C.1  Write card to techniques/cards/    │
  │       T{id}_{slug}.json                  │
  │                                          │
  │  C.2  load_all_cards() +                 │
  │       update_all_prompt_assets()         │
  │       → 4 prompt files updated           │
  │                                          │
  │  C.3  Registry auto-loads at next        │
  │       import (no explicit write)         │
  └──────┬───────────────────────────────────┘
         │
         ▼
  ┌──────────────────────┐
  │  pytest gate (Step D)│
  │  tests/ -v --tb=short│
  └──────┬───────────────┘
         │
         ▼
  ┌──────────────────────┐
  │  Report (Step E)     │
  │  Summary of changes  │
  └──────────────────────┘
```

---

## 3. Part B — Hardware-Aware Framework

The Hardware-Aware Framework ensures that the LLM only proposes approximation techniques that are physically feasible on the target deployment hardware. It operates at three enforcement levels:

1. **Pre-LLM:** Filter and rank techniques → inject constraint text into prompts
2. **During-LLM:** Post-LLM validation → reprompt if infeasible techniques detected
3. **Post-LLM:** Hard clamp → force-remove any surviving infeasible entries from JSON

### 3.1 Hardware Profile

**File:** `lib/hardware_profile.py`  
**Config:** `config/hardware_msp430.json`

#### `HardwareProfile` Class

Represents the capabilities and constraints of the target deployment platform:

```python
class HardwareProfile:
    name: str              # e.g. "MSP430"
    ram_kb: float          # Available RAM in KB (e.g. 10)
    has_fpu: bool          # Floating-point unit available?
    has_simd: bool         # SIMD instructions available?
    energy_budget_mj: float # Energy budget in millijoules (e.g. 5)
    clock_mhz: float       # Clock speed in MHz (e.g. 16)
```

#### Loading

`load_hardware_profile(json_path)` reads a JSON file and returns a `HardwareProfile` object. It performs:
- **Existence check:** `FileNotFoundError` if file missing
- **Required key check:** All 6 fields must be present
- **Type validation:** Each field is type-checked against expected types
- **Numeric sanity:** `ram_kb > 0`, `clock_mhz > 0`

#### Default Profile

```python
DEFAULT_PROFILE = HardwareProfile(
    name="MSP430",
    ram_kb=10,
    has_fpu=False,
    has_simd=False,
    energy_budget_mj=5,
    clock_mhz=16,
)
```

This represents the Texas Instruments MSP430FR5994: a 16-bit ultra-low-power microcontroller commonly used in batteryless IoT devices. It has **no FPU**, **no SIMD**, only **10 KB RAM**, and runs at **16 MHz**.

#### Hardware Profile JSON Example

```json
{
    "name": "MSP430",
    "ram_kb": 10,
    "has_fpu": false,
    "has_simd": false,
    "energy_budget_mj": 5,
    "clock_mhz": 16
}
```

---

### 3.2 Constraint Gatekeeper

**File:** `lib/constraint_gatekeeper.py`

The Constraint Gatekeeper is the **pre-LLM filter** that determines which approximation techniques are physically feasible on the target hardware.

#### `filter_feasible_techniques(app_name, hw)`

This function takes the application name and hardware profile, then performs a three-check filter on every applicable technique:

```
For each technique in get_applicable_techniques(app_name):

  1. FPU Check:
     IF technique.requires_fpu AND NOT hw.has_fpu
     → REJECTED ("requires FPU, target has no FPU")

  2. SIMD Check:
     IF technique.requires_simd AND NOT hw.has_simd
     → REJECTED ("requires SIMD, target has no SIMD")

  3. Memory Check:
     IF technique.memory_cost_kb > hw.ram_kb
     → REJECTED ("needs X KB but target has Y KB RAM")

  If all three checks pass → technique is FEASIBLE
```

**Returns:**
- `feasible: Dict[int, TechniqueEntry]` — techniques that passed all checks
- `rejection_log: List[str]` — human-readable rejection reasons

**Example for MSP430 (no FPU, no SIMD, 10 KB RAM):**
- T9 (Dynamic Precision Adjustment): **REJECTED** — requires FPU
- T14 (Multi-Fidelity Modeling): **REJECTED** — requires FPU
- T17 (Neural Network Pruning): **REJECTED** — requires FPU
- T24 (Magnitude-Only FFT): **REJECTED** — requires FPU
- T28 (Hierarchical Feature Extraction): **REJECTED** — requires FPU
- T1 (Loop Perforation): **FEASIBLE** — no FPU/SIMD needed, 0 KB memory
- T21 (Early-Exit): **FEASIBLE** — no FPU/SIMD needed, 0 KB memory

#### `format_feasible_list(feasible)`

Produces a constraint text block for injection into LLM prompts:

```
HARDWARE CONSTRAINT — You may ONLY choose from the following
approximation techniques (all others are infeasible on the
target hardware):

  1. Loop Perforation — Truncate loop iterations to trade accuracy for speed.
  4. Task Skipping — Omit non-critical tasks.
  10. Quantization — Reduce value range.
  21. Early-Exit Approximation — Terminate iterative computation early...
  ...
```

If no techniques are feasible, it returns: `"No hardware-feasible techniques found. Apply only generic code-quality improvements."`

---

### 3.3 Hardware Cost Model

**File:** `lib/hardware_cost_model.py`

The Cost Model ranks feasible techniques by their estimated execution cost on the target hardware. This helps the LLM prefer cheaper techniques.

#### `estimate_cost(tech, hw)`

```
cost_score = compute_factor + memory_pressure * 0.5

where:
  compute_factor  = tech.compute_cost_relative * (100.0 / hw.clock_mhz)
  memory_pressure = tech.memory_cost_kb / hw.ram_kb
```

- **Clock scaling:** Techniques run proportionally slower on slower clocks. A technique with `compute_cost_relative=0.5` costs `0.5 * (100/16) = 3.125` on a 16 MHz MCU vs. `0.5 * (100/1000) = 0.05` on a 1 GHz processor.
- **Memory pressure:** The fraction of available RAM consumed. A technique needing 1 KB on a 10 KB device contributes `(1/10) * 0.5 = 0.05` to the cost, while the same 1 KB on a 256 KB device contributes almost nothing.

#### `rank_techniques(feasible, hw)`

Sorts all feasible techniques by ascending cost score (cheapest first). Returns a list of `(technique_id, name, cost_score)` tuples.

Example output for MSP430:

```
  Rank  ID  Technique                          Cost
  ----------------------------------------------------
     1  29  Radix Variation                    0.6250
     2  26  Bit-Shift EWMA                     0.6250
     3   4  Task Skipping                      0.6250
     4   2  Precision Scaling                   1.2500
     5  21  Early-Exit Approximation            1.2500
     ...
```

---

### 3.4 LLM Prompt Injection

**File:** `main.py` (lines ~230–270, ~415–450)

The hardware constraint text is injected into the LLM's context at **two points**:

#### Point 1: Planning Step (Step 2)

The constraint text is appended to the `platform_architecture` description that the LLM sees during the planning phase:

```python
hw_aware_archi = platform_archi
if hw_constraint_text:
    hw_aware_archi = platform_archi + "\n\n" + hw_constraint_text

this_plan_anno_convo = planStepFunction(
    this_function=this_function,
    this_context=this_context,
    planningPrompt=prompts["planningPrompt"],
    platform_architecure=hw_aware_archi,  # ← constraint injected here
)
```

This means the LLM's planning step already "knows" which techniques are allowed before it starts reasoning about which technique to apply.

#### Point 2: Approximation Step Error Channel (Step 3)

The constraint text is also prepended to the `err_approximation` channel (exposed as `{add_error}` / `prev_err` in the prompt):

```python
if hw_constraint_text:
    err_approximation = hw_constraint_text + "\n"
```

This ensures the LLM sees the constraint again during the actual approximation generation step, reinforcing the allowed-technique list.

---

### 3.5 Post-LLM Validation

**File:** `lib/hw_validator.py`  
**File:** `main.py` (lines ~470–500)

After the LLM generates its approximation output, the validator checks whether the LLM respected the hardware constraints.

#### Technique ID Extraction

Three extraction functions scan different sources for technique references:

1. **`extract_technique_ids_from_text(text)`** — Regex-based extraction from free-form text. Matches patterns like:
   - `"Technique 27"`, `"Technique #27"`, `"technique_number: 27"`
   - `"T27"`, `"T 27"`
   
2. **`extract_technique_ids_from_json(json_path)`** — Extracts `technique_number` fields from `apx_all.json`

3. **`extract_technique_ids_from_convo(convo)`** — Scans the conversation history list `[(role, text), ...]`

#### Validation Flow

```python
# Extract what the LLM chose
chosen = extract_technique_ids_from_convo(this_approx_convo)

# Split into valid and invalid
valid, invalid = validate_technique_ids(chosen, hw_feasible)

if invalid and not hw_reprompt_done:
    # Build error message and reprompt (one retry only)
    err_approximation = build_reprompt_error(invalid, hw_feasible)
    hw_reprompt_done = True
    continue  # → loop back to LLM
```

#### `validate_technique_ids(chosen_ids, feasible)`

Simple set intersection:
- `valid = chosen_ids ∩ feasible_ids`
- `invalid = chosen_ids - feasible_ids`

#### `build_reprompt_error(invalid_ids, feasible)`

Generates an explicit error message:

```
ERROR: Your response referenced infeasible technique(s) that are
NOT supported on the target hardware:

  - Technique 9 — NOT ALLOWED on this hardware
  - Technique 17 — NOT ALLOWED on this hardware

You may ONLY select from these technique IDs; selecting anything
else is invalid:

  1. Loop Perforation
  4. Task Skipping
  10. Quantization
  ...

Please regenerate the approximated code using ONLY techniques
from the allowed list above.
```

**Important:** The reprompt is attempted **at most once** (`hw_reprompt_done` flag). If the LLM still picks infeasible techniques after one reprompt, the clamping mechanism (Section 3.6) handles it.

---

### 3.6 Clamping Safety Mechanism

**File:** `lib/hw_validator.py` → `clamp_apx_json()`  
**File:** `main.py` (lines ~553–560)

The clamp is the **last line of defense** — a hard guarantee that no infeasible technique ever reaches the downstream compilation and evaluation pipeline.

#### How Clamping Works

After all LLM interactions are complete, `main.py` runs:

```python
if hw_feasible is not None:
    apx_path = "approximated_functions/apx_all.json"
    if os.path.exists(apx_path):
        # Extract technique IDs from the JSON
        json_ids = extract_technique_ids_from_json(apx_path)
        _, json_invalid = validate_technique_ids(json_ids, hw_feasible)
        
        # Force-remove infeasible entries
        hw_clamped_ids = clamp_apx_json(apx_path, hw_feasible)
```

#### `clamp_apx_json(json_path, feasible)`

1. Loads `apx_all.json` (a list of approximation entries)
2. For each entry, checks `technique_number` against the feasible set
3. **Drops** any entry whose `technique_number` is not in the feasible set
4. Writes the cleaned list back to the file
5. Returns the list of dropped technique IDs

#### Why Clamping Is Safe

The clamping architecture is safe by design due to how the downstream pipeline works:

1. **`clamp_apx_json()` removes entries at the JSON level** — the `apx_all.json` file no longer contains the infeasible technique.

2. **`knob_tuning/` starts from the original source** — The knob tuning phase copies original (unmodified) benchmark source code into the `knob_tuning/` directory via `copyFiles("target", "knob_tuning")`. It does **not** copy from the LLM output.

3. **`lsp_patcher` only patches surviving entries** — The source patcher reads `apx_all.json` and only modifies functions that have entries in the JSON. Since the clamped technique's entry was removed, its code is never applied.

4. **Bayesian optimizer search space is built from surviving entries** — The optimizer only creates dimensions/knobs for techniques that remain in the JSON. Clamped techniques contribute zero dimensions to the search space.

**Net effect:** The clamped technique's LLM-generated code is silently discarded and never compiled, evaluated, or optimized.

---

### 3.7 Observability Outputs

**File:** `lib/hw_observability.py`

The observability module writes two proof files per run that document exactly which constraints were applied and how the LLM responded.

#### File 1: Rejection JSON

**Path:** `outputs/hardware_rejections_{app}_{hwname}.json`

```json
{
  "timestamp": "2025-06-15T10:30:00",
  "hardware": "MSP430",
  "app": "sobel-iclib",
  "total_techniques": 30,
  "feasible_count": 22,
  "rejected_count": 8,
  "rejections": [
    {
      "technique_id": 9,
      "technique_name": "Dynamic Precision Adjustment",
      "reason": "requires FPU"
    },
    {
      "technique_id": 14,
      "technique_name": "Multi-Fidelity Modeling",
      "reason": "requires FPU"
    }
  ]
}
```

This file is written at startup (before the LLM runs) so it captures the initial constraint state.

#### File 2: Constraint Proof TXT

**Path:** `outputs/LLM_CONSTRAINTS_{app}_{hwname}.txt`

This file is written after the LLM finishes and contains 5 sections:

1. **Hardware Profile** — name, RAM, clock, FPU/SIMD status, energy budget
2. **Feasible Techniques** — the constraint text that was injected into the LLM
3. **Ranked by Cost** — the cheapest-first technique ranking
4. **Raw LLM Technique-Selection Response** — the actual LLM output (truncated to 5000 chars)
5. **Final Validated Technique IDs** — which IDs were valid, invalid, or clamped

This file serves as a complete audit trail proving that:
- The hardware constraints were applied
- The LLM was given a restricted technique menu
- The final output was validated and (if necessary) clamped

#### Experiment Metrics Summary

At the end of each run, `main.py` also prints a structured metrics summary:

```
============================================================
  EXPERIMENT METRICS SUMMARY
============================================================
  Application           : sobel-iclib
  Hardware profile      : MSP430
  Hardware-aware        : YES
  ---
  Functions attempted   : 5
  Functions succeeded   : 4
  Total LLM API calls   : 15
  Compile failures      : 2
  HW reprompts triggered: 1
  Techniques clamped    : 0
  Feasible techniques   : 22
  Rejected techniques   : 8
  Invalid IDs caught    : [9]
  Validated IDs         : [1, 21, 22]
============================================================
```

---

### 3.8 End-to-End Data Flow

```
CLI invocation:  python main.py --bm_name sobel-iclib --hardware config/hardware_msp430.json
                                                            │
                                                            ▼
                                              ┌──────────────────────────┐
                                              │  load_hardware_profile() │
                                              │  hardware_profile.py     │
                                              │                          │
                                              │  → HardwareProfile obj   │
                                              │    MSP430, 10KB, no FPU  │
                                              └────────────┬─────────────┘
                                                           │
                                                           ▼
┌────────────────────────────────────────────────────────────────────────────────┐
│  PRE-LLM PHASE                                                                │
│                                                                                │
│  ┌────────────────────────────────┐     ┌────────────────────────────────────┐ │
│  │  filter_feasible_techniques()  │     │  rank_techniques()                │ │
│  │  constraint_gatekeeper.py      │     │  hardware_cost_model.py           │ │
│  │                                │     │                                    │ │
│  │  30 techniques                 │     │  feasible techniques               │ │
│  │  → app filter → 25 applicable  │────▶│  → sorted by cost (cheapest first) │ │
│  │  → HW filter → 22 feasible    │     │  → hw_ranked list                  │ │
│  │  → 3 rejected (FPU)           │     └────────────────────────────────────┘ │
│  └────────────────────────────────┘                                            │
│                                                                                │
│  format_feasible_list()  ─────────────────▶  hw_constraint_text               │
│  write_rejection_json()  ─────────────────▶  outputs/hardware_rejections_*.json│
└────────────────────────────────────────────────────────────────────────────────┘
                              │
                              │  hw_constraint_text
                              ▼
┌────────────────────────────────────────────────────────────────────────────────┐
│  LLM PHASE (per function)                                                      │
│                                                                                │
│  Step 1: Purpose Identification                                                │
│  ──────────────────────────                                                    │
│  Identify what the function does (no HW constraint here)                       │
│                                                                                │
│  Step 2: Planning                                                              │
│  ──────────────────                                                            │
│  hw_constraint_text injected into platform_architecture                        │
│  LLM plans which technique to use with awareness of allowed set                │
│                                                                                │
│  Step 3: Approximation                                                         │
│  ────────────────────                                                          │
│  hw_constraint_text prepended to error channel {add_error}                     │
│  LLM generates approximated C code                                             │
│                                                                                │
│  ┌─── Post-LLM Validation ───────────────────────────────────┐                 │
│  │  extract_technique_ids_from_convo() → chosen IDs          │                 │
│  │  validate_technique_ids(chosen, feasible)                 │                 │
│  │  IF invalid IDs found AND not already reprompted:         │                 │
│  │    → build_reprompt_error() → retry Step 3 once           │                 │
│  └───────────────────────────────────────────────────────────┘                 │
│                                                                                │
│  Step 4: JSON Conversion                                                       │
│  ──────────────────────                                                        │
│  Convert approximation to apx_all.json format                                  │
│  Compile test → if fail, retry (up to 3 times)                                 │
└────────────────────────────────────────────────────────────────────────────────┘
                              │
                              │  apx_all.json written
                              ▼
┌────────────────────────────────────────────────────────────────────────────────┐
│  POST-LLM PHASE                                                               │
│                                                                                │
│  ┌─── Clamping ────────────────────────────────────────────┐                   │
│  │  extract_technique_ids_from_json(apx_all.json)          │                   │
│  │  validate_technique_ids(json_ids, feasible)             │                   │
│  │  clamp_apx_json(apx_all.json, feasible)                │                   │
│  │  → Remove entries with infeasible technique_number      │                   │
│  │  → Returns list of clamped IDs                          │                   │
│  └─────────────────────────────────────────────────────────┘                   │
│                                                                                │
│  write_constraints_txt()  ────────────────▶  outputs/LLM_CONSTRAINTS_*.txt     │
│  Print Experiment Metrics Summary                                              │
└────────────────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
               ┌──────────────────────────────┐
               │  Downstream Pipeline         │
               │  (Only feasible techniques   │
               │   survive in apx_all.json)   │
               │                              │
               │  → knob_tuning/copy source   │
               │  → lsp_patcher (only patches │
               │    functions in JSON)         │
               │  → BayesOpt (search space    │
               │    from surviving entries)    │
               │  → Fused simulator            │
               └──────────────────────────────┘
```

---

## 4. How the Two Subsystems Interact

The Automatic Technique Integration system and the Hardware-Aware Framework share a critical data path through the **Technique Registry**:

```
                    Technique Card (JSON)
                           │
                           ▼
            ┌──────────────────────────┐
            │   techniques/cards/      │
            │   T31_my_technique.json  │
            └────────────┬─────────────┘
                         │
              ┌──────────┴──────────┐
              │                     │
              ▼                     ▼
    ┌──────────────────┐  ┌──────────────────────┐
    │  prompt_updater  │  │ technique_registry    │
    │  (prompts)       │  │ (TECHNIQUE_REGISTRY)  │
    └──────────────────┘  └──────────┬────────────┘
                                     │
                         ┌───────────┴───────────┐
                         │                       │
                         ▼                       ▼
              ┌────────────────────┐  ┌────────────────────┐
              │ constraint_        │  │ hardware_           │
              │ gatekeeper         │  │ cost_model          │
              │ (filter_feasible)  │  │ (rank_techniques)   │
              └────────┬───────────┘  └────────┬───────────┘
                       │                       │
                       └───────────┬───────────┘
                                   │
                                   ▼
                       ┌─────────────────────┐
                       │  hw_constraint_text  │
                       │  (injected into LLM) │
                       └──────────┬──────────┘
                                  │
                                  ▼
                       ┌─────────────────────┐
                       │  hw_validator        │
                       │  (post-LLM check    │
                       │   + clamping)        │
                       └──────────┬──────────┘
                                  │
                                  ▼
                       ┌─────────────────────┐
                       │  hw_observability    │
                       │  (audit trail)       │
                       └─────────────────────┘
```

**Key interaction:** When a new technique is added via `add_technique.py`:

1. The Technique Card is stored and auto-loaded into the registry at import time.
2. The new technique's `feasibility` fields (`requires_fpu`, `requires_simd`, `memory_cost_kb`) are automatically picked up by the Constraint Gatekeeper.
3. The new technique's `cost_model.compute_cost_relative` is automatically used by the Hardware Cost Model for ranking.
4. The HW Validator can extract and validate the new technique's ID from LLM output.
5. If the new technique is infeasible on the target hardware, it will be:
   - Filtered out by the gatekeeper (never shown to the LLM)
   - Caught by the validator if the LLM somehow references it
   - Clamped from `apx_all.json` if it somehow makes it into the output

**No additional code changes are needed.** Adding a technique card automatically integrates with the entire hardware-aware pipeline.

---

## 5. File Reference

| File | Module | Purpose |
|------|--------|---------|
| `lib/technique_card_schema.py` | Schema | JSON schema definition, `validate_card()`, `normalize_card()`, `build_card_generation_prompt()` |
| `lib/technique_registry.py` | Registry | `TechniqueEntry` class, `TECHNIQUE_REGISTRY` dict (T1–T30 + auto-loaded cards), `get_applicable_techniques()` |
| `lib/prompt_updater.py` | Prompts | `inject_between_anchors()`, render functions, `update_all_prompt_assets()` |
| `tools/add_technique.py` | CLI | End-to-end pipeline: LLM call → validate → write card → update prompts → pytest gate |
| `lib/hardware_profile.py` | HW Profile | `HardwareProfile` class, `load_hardware_profile()`, `DEFAULT_PROFILE` |
| `lib/constraint_gatekeeper.py` | Gatekeeper | `filter_feasible_techniques()` (FPU/SIMD/memory checks), `format_feasible_list()` |
| `lib/hardware_cost_model.py` | Cost Model | `estimate_cost()`, `rank_techniques()` |
| `lib/hw_validator.py` | Validator | `extract_technique_ids_from_*()`, `validate_technique_ids()`, `build_reprompt_error()`, `clamp_apx_json()` |
| `lib/hw_observability.py` | Observability | `write_rejection_json()`, `write_constraints_txt()` |
| `main.py` | Pipeline | Hardware-aware initialization (lines 200–290), LLM loop with HW injection (lines 400–560) |
| `config/hardware_msp430.json` | Config | MSP430 hardware profile JSON |
| `techniques/cards/*.json` | Data | Technique Card JSON files (auto-loaded at import time) |
| `prompts/approximation_techniques.txt` | Prompt | Technique list shown to LLM (auto-updated) |
| `prompts/planning_step.txt` | Prompt | Planning guidance (auto-updated) |
| `prompts/approximate_vPDG1.txt` | Prompt | Implementation rules (auto-updated) |
| `prompts/FewShotExamples/newTechniqueExamples.txt` | Prompt | Few-shot examples (auto-updated) |

---

*Document generated for the CheckMate framework.*
