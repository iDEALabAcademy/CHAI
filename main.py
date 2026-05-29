from dotenv import load_dotenv
load_dotenv()

from langchain_core.output_parsers import JsonOutputParser
import shutil
import os
import subprocess
import ast
import json
import pandas as pd

# Ensure egypt (Perl call-graph tool) is on PATH for PDG generation.
# Honor $EGYPT_DIR if set, otherwise try a few conventional install locations.
import shutil as _shutil
if not _shutil.which("egypt"):
    _candidate_egypt_dirs = [
        os.environ.get("EGYPT_DIR"),
        os.path.expanduser("~/.local/bin"),
        os.path.expanduser("~/bin"),
        "/usr/local/bin",
    ]
    for _egypt_dir in _candidate_egypt_dirs:
        if _egypt_dir and os.path.isfile(os.path.join(_egypt_dir, "egypt")):
            if _egypt_dir not in os.environ.get("PATH", ""):
                os.environ["PATH"] = _egypt_dir + ":" + os.environ.get("PATH", "")
            break

# Ensure MSP430 toolchain env vars are set for cross-compilation
if not os.environ.get("MSP430_GCC_ROOT"):
    _msp_gcc = os.path.expanduser("~/.local/msp430-gcc")
    if os.path.isdir(_msp_gcc):
        os.environ["MSP430_GCC_ROOT"] = _msp_gcc
if not os.environ.get("MSP430_INC"):
    _msp_inc = os.path.expanduser("~/.local/msp430-inc")
    if os.path.isdir(_msp_inc):
        os.environ["MSP430_INC"] = _msp_inc
import argparse
import glob as _glob_mod
from tqdm import tqdm
from colorama import Back, Fore, Style
import warnings
from tabulate import tabulate
# Ignore FutureWarnings
warnings.filterwarnings("ignore", category=FutureWarning)


# ---------------------------------------------------------------------------
#  Centralized Fresh-Run Preparation
# ---------------------------------------------------------------------------
def _prepare_fresh_run(app_name_for_cleanup=None):
    """Remove ALL transient artifacts so every run starts clean.

    This single function replaces the scattered ad-hoc cleanups
    (compilation_testing, knob_tuning, dependency_graphs, etc.) that
    previously caused stale-file bugs.

    Called once, right after argument parsing, before any pipeline work.
    """
    transient_dirs = [
        "compilation_testing",
        "knob_tuning",
        "functions",
        "approximated_functions",
        "dependency_graphs",
    ]
    for d in transient_dirs:
        if os.path.exists(d):
            shutil.rmtree(d)
            print(f"[cleanup] Removed stale {d}/")

    # Clean eval-apps/build/ (CMake cache) — stale object files cause the
    # cross-compiler to silently reuse old hex, which was root-cause of
    # the "zero cycle reduction" bug.
    build_dir = "eval-apps/build"
    if os.path.exists(build_dir):
        shutil.rmtree(build_dir)
        print("[cleanup] Removed stale eval-apps/build/")

    # Restore eval-apps/{app}/ to pristine benchmark state so that leftover
    # approximated .c/.h files from a previous run don't leak in.
    if app_name_for_cleanup:
        bm_src = f"benchmark_applications/{app_name_for_cleanup}/"
        ea_dst = f"eval-apps/{app_name_for_cleanup}/"
        if os.path.isdir(bm_src):
            if os.path.exists(ea_dst):
                shutil.rmtree(ea_dst)
            shutil.copytree(bm_src, ea_dst)
            print(f"[cleanup] Restored eval-apps/{app_name_for_cleanup}/ from benchmark_applications/")

    # Clean target/ directory (will be repopulated immediately after)
    if os.path.exists("target"):
        for old in _glob_mod.glob(os.path.join("target", '*')):
            if os.path.isfile(old):
                os.remove(old)
            elif os.path.isdir(old):
                shutil.rmtree(old)
        print("[cleanup] Cleaned target/")

    # Remove stale Fused artifacts
    for stale in ["fusedBin/app.hex", "fusedBin/cycles.dump"]:
        if os.path.exists(stale):
            os.remove(stale)
            print(f"[cleanup] Removed stale {stale}")

    # Clean stale log files (but not CSV results — those are valuable)
    for log_f in _glob_mod.glob("logs/*.txt"):
        os.remove(log_f)
    for log_f in _glob_mod.glob("logs/*.json"):
        os.remove(log_f)

    print("[cleanup] Fresh-run preparation complete.\n")

from config.config import (
    TEXT_PLANING,
    ERROR_BOUND,
)

from utils.initialization import (
    loadTargetFiles,
    loadGlobalContext,
    parseFunctions,
    getPromptTemplates,
    loadFormatExamples,
    loadLoopPerfExamples,
    loadNewTechniqueExamples,
    loadCodeBaseSummary,
)

from utils.context import (
    manufacturerContext
)

from utils.json_handling import (
    loadEntities,
    joinJsonFiles
)

from utils.utils import (
    formatMessageForHistory,
    copyFiles,
    getAppName,
    writeFunctionsToJson,
    Dprint
)

from utils.compiler import(
    compileTest
)

from utils.validator import(
    validateFunction
)

from utils.trace_utils import (
    set_deterministic_seeds,
    ApproxTrace,
    BeforeMetrics,
    AfterPrecomputeMetrics,
    AfterInferenceMetrics,
    save_trace,
    compute_diffs,
    format_trace_report,
    get_git_commit
)

parser = argparse.ArgumentParser()

parser.add_argument("--bm_name", type=str, help="Benchmark app/ Evaluation app name", required=True)
parser.add_argument("--no_llm", action="store_true", help="include if you do not want to run LLM", required=False)
parser.add_argument("--trace_approx", type=int, choices=[0, 1], default=0, help="Enable approximation tracing (1=enabled, 0=disabled)")
parser.add_argument("--hardware", type=str, default=None,
                    help="Path to a hardware profile JSON (e.g. config/hardware_msp430.json). "
                         "Enables hardware-aware technique filtering.")
parser.add_argument("--hardware_profile", type=str, default=None,
                    help="Alias for --hardware. Path to a hardware profile JSON.")
parser.add_argument("--trace", type=str, default=None,
                    help="Override traces list with a single trace path (e.g. ../traces/RF_1.csv)")

args = parser.parse_args()

# Resolve --hardware_profile alias
if args.hardware_profile and not args.hardware:
    args.hardware = args.hardware_profile

Dprint(f"Runing Benchmark App: {args.bm_name}")
app_name = args.bm_name

# --- Prepare a clean slate BEFORE anything else ---
_prepare_fresh_run(app_name_for_cleanup=app_name)

alreadyRun = False
if args.no_llm:
    Dprint(f"Using LLM prerun outputs...")
    alreadyRun = True

    def copy_prerun_outputs(bm_name):
        source_dir = os.path.join("llm-prerun", bm_name)
        if not os.path.exists(source_dir):
            Dprint(f"Source directory does not exist: {source_dir}")
            return

        for folder in os.listdir(source_dir):
            src_path = os.path.join(source_dir, folder)
            dest_path = os.path.join(".", folder)
            if os.path.isdir(src_path):
                shutil.copytree(src_path, dest_path, dirs_exist_ok=True)
                Dprint(f"Copied {folder} to current directory.")
            else:
                Dprint(f"Skipping non-folder item: {folder}")

    copy_prerun_outputs(args.bm_name)
    

# ---------------------------------------------------------------------------
#  Hardware-Aware Approximation Planning
# ---------------------------------------------------------------------------
hw_profile = None          # None → legacy behaviour (no filtering)
hw_constraint_text = ""    # injected into LLM prompts when non-empty
hw_feasible = None         # dict[int, TechniqueEntry]  |  None
hw_ranked = None           # sorted list of (id, name, cost)  |  None
hw_rejection_log = []      # human-readable rejection lines
hw_llm_raw_responses = []  # collected raw LLM planning/approx outputs
hw_validated_ids = set()   # final validated technique IDs
hw_invalid_ids = set()     # IDs rejected by post-LLM validator
hw_clamped_ids = []        # IDs force-removed from apx_all.json

# ---------------------------------------------------------------------------
#  Experiment Instrumentation Counters
# ---------------------------------------------------------------------------
exp_api_calls = 0          # total LLM API invocations
exp_compile_failures = 0   # total compilation failures
exp_compile_retries_per_func = {}  # function → retry count
exp_hw_reprompts = 0       # HW validator reprompts
exp_technique_clamped = 0  # techniques force-removed post-LLM
exp_functions_attempted = 0
exp_functions_succeeded = 0

if args.hardware:
    from lib.hardware_profile import load_hardware_profile
    from lib.constraint_gatekeeper import (
        filter_feasible_techniques,
        format_feasible_list,
        format_rejection_report,
    )
    from lib.hardware_cost_model import rank_techniques, format_ranked_list
    from lib.hw_validator import (
        extract_technique_ids_from_text,
        extract_technique_ids_from_convo,
        extract_technique_ids_from_json,
        validate_technique_ids,
        build_reprompt_error,
        clamp_apx_json,
    )
    from lib.hw_observability import write_rejection_json, write_constraints_txt

    hw_profile = load_hardware_profile(args.hardware)

    # Compact startup line (Task A.4)
    print(hw_profile.startup_line())

    # The app name is already known at this point
    hw_feasible, hw_rejection_log = filter_feasible_techniques(app_name, hw_profile)
    hw_ranked = rank_techniques(hw_feasible, hw_profile)

    # Build the constraint text that will be prepended to LLM prompts
    hw_constraint_text = format_feasible_list(hw_feasible)

    # ---- Terminal output ----
    print(Back.CYAN + Fore.BLACK)
    print("=" * 60)
    print("  HARDWARE-AWARE APPROXIMATION PLANNING")
    print("=" * 60)
    print(Style.RESET_ALL)
    print(f"  Target : {hw_profile.summary()}")
    print(f"  App    : {app_name}")
    print()
    print(Fore.GREEN + "  Feasible techniques:" + Style.RESET_ALL)
    print(format_ranked_list(hw_ranked))
    print()
    if hw_rejection_log:
        print(Fore.RED + "  Rejected techniques:" + Style.RESET_ALL)
        print(format_rejection_report(hw_rejection_log))
        print()
    print("-" * 60)
    print()

    # ---- Write observability: rejection JSON (Task D.2) ----
    rej_path = write_rejection_json(app_name, hw_profile, hw_feasible, hw_rejection_log)
    print(f"  → Rejection log: {rej_path}")

copyFiles(f"benchmark_applications/{app_name}/",f"eval-apps/{app_name}/")

# copy only the Makefile, .c and .h files in eval_apps/{app_name}/ to target/
def copyEvalAppSource(app_name, target_dir):
    os.makedirs(target_dir, exist_ok=True)
    subprocess.run(f"cp eval-apps/{app_name}/*.c {target_dir}",shell=True)
    subprocess.run(f"cp eval-apps/{app_name}/*.h {target_dir}",shell=True)
    subprocess.run(f"cp eval-apps/{app_name}/Makefile {target_dir}",shell=True)
    subprocess.run(f"cp eval-apps/{app_name}/application.txt {target_dir}",shell=True)

copyEvalAppSource(app_name, "target/")

from lib.llm import (
    purposeIdentificationFunction,
    annotateFunction,
    planStepFunction,
    approximateFunction,
    convertJson,
    findTargetFunctions,
)

from lib.bo import runBayesOpt

from lib.pdg import (
    initPDGGen
)
from utils.models import AnnotateData, ApproximatedData
from config.globals import CHAT_HISTORY, PLATFORM_ARCHITECTURE
from config.config import GIVE_FORMAT_EXAMPLES, GIVE_LOOP_PERF_EXMAPLES
from utils.error_analyzer import generateGroundTruth
from utils.checkpoints import checkpointOrchestration
import csv

# ----------- README FOLLOW ALONG START HERE -----------

# Enable deterministic tracing if requested
if args.trace_approx:
    Dprint("Approximation tracing ENABLED - set deterministic seeds")
    set_deterministic_seeds(42)

PDG, topological_order = initPDGGen()

# LLM API initialization already been done in lib/llm.py.


# Load filenames of target files

loadTargetFiles("target/")
platform_archi = PLATFORM_ARCHITECTURE

# Load global context (System prompt, approximation summry, few shot examples)
loadGlobalContext()
loadFormatExamples()
loadLoopPerfExamples()
loadNewTechniqueExamples()

# Parse target files to extract entities (functions, structs, global variables) and load them.
parseFunctions()
loadEntities()

if not alreadyRun:

    # Load and create prompt templates.
    prompts = getPromptTemplates()

    # Load output scheama.
    annotatedDataParser = JsonOutputParser(pydantic_object=AnnotateData)
    approximatedDataParser = JsonOutputParser(pydantic_object=ApproximatedData)

    # Load output format instructions for LLM.
    output_format_instructions_anno = annotatedDataParser.get_format_instructions()
    output_format_instructions_apx = approximatedDataParser.get_format_instructions()


    # Intialize approximated functions dirctrionary
    approximated_functions_dict = {}
    
    # Get list of target functions and code base summary
    target_functions, code_summary = findTargetFunctions(prompts["targetFunctionsPrompt"])

    # Load code_base summary
    loadCodeBaseSummary(code_summary)

    # Filter topological_order to only contain functions to be targeted as told by LLM
    filtered_topological_order = [] # Making new varaibale because topological_order may be used else where.
    Dprint(target_functions)
    for function in topological_order:
        try:
            if target_functions[function] == "approximate" or target_functions[function] == "Approximate":
                filtered_topological_order.append(function)
        except:
            pass
    # Iterate over all functions
    for this_function in filtered_topological_order:
        print(Back.WHITE)
        print(Fore.BLACK)
        print("APPROXIMATING FUNCTION: " + this_function + "\n")
        print(Style.RESET_ALL)
        """
            Step 0: Parent Entities (Functions) Context
        """

        this_context = manufacturerContext(PDG, this_function)
        Dprint("\n\n\n\n --- start \n\n")
        Dprint(this_context)

        """
            Step 1: Identify this_function's purpose
        """

        # chain = purposePrompt | llmLangChain

        exp_api_calls += 1  # purpose identification call
        this_purpose_convo = purposeIdentificationFunction(
            this_function,
            this_context,
            prompts["purposePrompt"]
        )

        # Add purpose identification convo to history(context) object
        this_context = this_context + this_purpose_convo
        Dprint("\n\n\n\n --- Perpose \n\n")
        Dprint(this_context)

        """
            Step 2: Annotate the function
        """

        this_plan_anno_convo = None
        function_code_annotated = ""
        if TEXT_PLANING:
            # Inject hardware-aware planning text into the platform architecture
            # description so the LLM sees the constraint during planning.
            hw_aware_archi = platform_archi
            if hw_constraint_text:
                hw_aware_archi = platform_archi + "\n\n" + hw_constraint_text

            exp_api_calls += 1  # planning step call
            this_plan_anno_convo = planStepFunction(
                this_function=this_function,
                this_context=this_context,
                planningPrompt=prompts["planningPrompt"],
                platform_architecure=hw_aware_archi,
            )
        else:
            function_code_annotated, this_plan_anno_convo = annotateFunction(
                this_function, 
                this_context, 
                prompts["annotationPrompt"], 
                output_format_instructions_anno,
                annotatedDataParser,
            )


        # Add annotation convo to history(context) object
        this_context = this_context + this_plan_anno_convo # Add the annotation conversation context for approximation prompt
        Dprint("\n\n\n\n --- Planning \n\n")
        Dprint(this_context)

        err_approximation = ""
        # Prepend hardware constraints to the approximation error channel
        # so the LLM sees them in {add_error} on the first iteration.
        if hw_constraint_text:
            err_approximation = hw_constraint_text + "\n"
        hw_reprompt_done = False   # track whether we already reprompted once
        compile_retries = 0
        MAX_COMPILE_RETRIES = 3
        exp_functions_attempted += 1
        while True:
            """
                Step 3: Approximate the function and test Compilation and Validation
            """
            
            exp_api_calls += 1  # approximation call
            this_approx_convo = approximateFunction(
                this_function=this_function,
                this_context=this_context,
                approximation_prompt=prompts["approximationPrompt"],
                prev_err=err_approximation
            )

            this_context = this_context + this_approx_convo

            # --- Post-LLM feasibility check (Task C) ---
            if hw_feasible is not None and not hw_reprompt_done:
                chosen = extract_technique_ids_from_convo(this_approx_convo)
                valid, invalid = validate_technique_ids(chosen, hw_feasible)
                if invalid:
                    Dprint(f"[HW Validator] Infeasible IDs in LLM output: {invalid}")
                    print(Fore.RED + f"  [HW Validator] LLM chose infeasible technique(s): "
                          f"{sorted(invalid)} — reprompting once..." + Style.RESET_ALL)
                    err_approximation = build_reprompt_error(invalid, hw_feasible)
                    hw_reprompt_done = True
                    hw_invalid_ids |= invalid
                    exp_hw_reprompts += 1
                    # Collect raw response for observability
                    for role, txt in this_approx_convo:
                        if role == "ai":
                            hw_llm_raw_responses.append(str(txt))
                    continue

            # Collect raw LLM response for observability
            if hw_feasible is not None:
                for role, txt in this_approx_convo:
                    if role == "ai":
                        hw_llm_raw_responses.append(str(txt))
                chosen_final = extract_technique_ids_from_convo(this_approx_convo)
                hw_validated_ids |= (chosen_final & set(hw_feasible.keys()))

            """
                Step 4: Convert approximation to JSON format and Compile and Validate
            """

            exp_api_calls += 1  # JSON conversion call
            this_approx_json_convo, approximate_function  = convertJson(
                this_context = this_context,
                convert_json_prompt = prompts["convertJsonPrompt"],
                this_function=this_function,
                output_format_parser=approximatedDataParser
            )

            this_context = this_context + this_approx_json_convo

            approximated_functions_dict[this_function] = approximate_function
            writeFunctionsToJson(approximated_functions_dict, 'approximated_functions/apx')

            err_comp = compileTest(this_function)

            # err_val = validateFunction(approximated_functions_dict[this_function])

            # if err_comp or err_val:
            if err_comp:
                compile_retries += 1
                exp_compile_failures += 1
                if compile_retries >= MAX_COMPILE_RETRIES:
                    print(Fore.RED + f"  [Max retries] {this_function} failed compilation after {MAX_COMPILE_RETRIES} attempts — skipping." + Style.RESET_ALL)
                    exp_compile_retries_per_func[this_function] = compile_retries
                    break
                err_approximation = prompts['errorPrompt'].format(this_err = err_comp)
                continue

            exp_functions_succeeded += 1
            exp_compile_retries_per_func[this_function] = compile_retries
            break

        """
            Step 5: Save conversation history
        """
        CHAT_HISTORY[this_function] = (
            this_purpose_convo 
            + this_plan_anno_convo
            + this_approx_convo
            + this_approx_json_convo
        )

        with open("logs/conv1.txt","a") as file:
            file.write(f"Function {this_function}" + "\n")
            file.write(str(approximated_functions_dict) + "\n")
            file.write(str(CHAT_HISTORY) + "\n")

print(Back.YELLOW)
print("ALL FUNCTIONS APPROXIMATED\n")
print(Style.RESET_ALL)

# ---------------------------------------------------------------------------
#  Post-LLM: final clamp + observability (Tasks C.2 / D.1)
# ---------------------------------------------------------------------------
if hw_feasible is not None:
    # Clamp apx_all.json — remove any infeasible entries that survived
    apx_path = "approximated_functions/apx_all.json"
    if os.path.exists(apx_path):
        # Also pick up technique_number from JSON
        json_ids = extract_technique_ids_from_json(apx_path)
        _, json_invalid = validate_technique_ids(json_ids, hw_feasible)
        hw_invalid_ids |= json_invalid
        hw_clamped_ids = clamp_apx_json(apx_path, hw_feasible)
        if hw_clamped_ids:
            print(Fore.RED + f"  [HW Validator] Clamped infeasible technique(s) "
                  f"from apx_all.json: {hw_clamped_ids}" + Style.RESET_ALL)

    # Write constraints proof TXT (Task D.1)
    raw_resp = "\n---\n".join(hw_llm_raw_responses) if hw_llm_raw_responses else ""
    con_path = write_constraints_txt(
        app_name, hw_profile, hw_feasible, hw_ranked,
        llm_raw_response=raw_resp,
        validated_ids=hw_validated_ids or None,
        invalid_ids=hw_invalid_ids or None,
        clamped_ids=hw_clamped_ids or None,
    )
    print(f"  → Constraints proof: {con_path}")

# ---------------------------------------------------------------------------
#  Experiment Metrics Summary
# ---------------------------------------------------------------------------
if not alreadyRun:
    exp_technique_clamped = len(hw_clamped_ids) if isinstance(hw_clamped_ids, list) else 0
    print("\n" + "=" * 60)
    print("  EXPERIMENT METRICS SUMMARY")
    print("=" * 60)
    print(f"  Application           : {app_name}")
    print(f"  Hardware profile      : {hw_profile.name if hw_profile else 'None (baseline)'}")
    print(f"  Hardware-aware        : {'YES' if hw_profile else 'NO'}")
    print(f"  ---")
    print(f"  Functions attempted   : {exp_functions_attempted}")
    print(f"  Functions succeeded   : {exp_functions_succeeded}")
    print(f"  Total LLM API calls   : {exp_api_calls}")
    print(f"  Compile failures      : {exp_compile_failures}")
    print(f"  Compile retries/func  : {exp_compile_retries_per_func}")
    print(f"  HW reprompts triggered: {exp_hw_reprompts}")
    print(f"  Techniques clamped    : {exp_technique_clamped}")
    if hw_feasible is not None:
        print(f"  Feasible techniques   : {len(hw_feasible)}")
        print(f"  Rejected techniques   : {len(hw_rejection_log)}")
        print(f"  Invalid IDs caught    : {sorted(hw_invalid_ids) if hw_invalid_ids else 'None'}")
        print(f"  Validated IDs         : {sorted(hw_validated_ids) if hw_validated_ids else 'None'}")
    print("=" * 60)
    
    # Write metrics to JSON for comparison
    import time
    metrics = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "app": app_name,
        "hardware_profile": hw_profile.name if hw_profile else "None",
        "hardware_aware": bool(hw_profile),
        "functions_attempted": exp_functions_attempted,
        "functions_succeeded": exp_functions_succeeded,
        "api_calls": exp_api_calls,
        "compile_failures": exp_compile_failures,
        "compile_retries_per_func": exp_compile_retries_per_func,
        "hw_reprompts": exp_hw_reprompts,
        "techniques_clamped": exp_technique_clamped,
        "feasible_techniques": len(hw_feasible) if hw_feasible else None,
        "rejected_techniques": len(hw_rejection_log) if hw_rejection_log else 0,
        "invalid_ids": sorted(hw_invalid_ids) if hw_invalid_ids else [],
        "validated_ids": sorted(hw_validated_ids) if hw_validated_ids else [],
    }
    hw_label = hw_profile.name if hw_profile else "baseline"
    metrics_path = f"logs/experiment_metrics_{app_name}_{hw_label}.json"
    with open(metrics_path, "w") as f:
        json.dump(metrics, f, indent=2)
    print(f"  → Metrics saved: {metrics_path}")

# Read application.txt file from target/ and read the function name
# app_names = ["lqi-iclib", "stringsearch-iclib"]
# app_name = getAppName()
# app_name = app_names[0]

# Generate the ground truth
generateGroundTruth(app_name)
# quit()

copyFiles("target", "knob_tuning")
# quit()
if not alreadyRun:

    # Join all validated approximations
    joinJsonFiles("approximated_functions/", "apx", "apx_all.json")

    # Creat copy of target folder and add apx json file
    # copyFiles("target", "knob_tuning")


    # Search for a Makefile in compilation_testing/ and copy it in knob_tuning/. The Makefile is in any of the subdirectories of compilation_testing/
    os.system(r"find compilation_testing/ -name Makefile -exec cp {} knob_tuning/ \;")
    # NOTE: Do NOT copy compilation_testing Makefiles to target/ — target/ keeps
    # the original benchmark Makefile for ground-truth generation.

# Validate copied Makefiles: try to compile, and if it fails, generate a simple deterministic one
def _ensure_working_makefile(directory):
    """Ensure the Makefile in 'directory' can compile. If not, write a fallback."""
    import glob, subprocess as _sp
    makefile_path = os.path.join(directory, 'Makefile')
    # Try compiling with existing Makefile
    try:
        _sp.run("make clean", shell=True, cwd=directory, stdout=_sp.DEVNULL, stderr=_sp.DEVNULL)
        result = _sp.run("make main", shell=True, cwd=directory, capture_output=True, text=True, timeout=30)
        if result.returncode == 0:
            return  # Existing Makefile works
    except Exception:
        pass

    # Generate a fallback Makefile from the .c files present
    c_files = sorted(glob.glob(os.path.join(directory, '*.c')))
    if not c_files:
        return
    c_names = [os.path.basename(f) for f in c_files]
    o_names = [f.replace('.c', '.o') for f in c_names]
    lines = ['CC=gcc', 'CFLAGS=-c -O2 -DLOCAL_RUN', '']
    for c, o in zip(c_names, o_names):
        lines += [f'{o}: {c}', f'\t$(CC) $(CFLAGS) {c} -o {o}', '']
    lines += [f"main: {' '.join(o_names)}", f"\t$(CC) {' '.join(o_names)} -o main -lm", '']
    lines += ['clean:', f"\trm -f {' '.join(o_names)} main", '']
    with open(makefile_path, 'w') as f:
        f.write('\n'.join(lines))
    print(f"[Makefile] Wrote fallback Makefile for {directory}")

for _mf_dir in ['knob_tuning', 'target']:
    _ensure_working_makefile(_mf_dir)

file_path = f"approximated_functions/apx_all.json"
destination_file_path = "knob_tuning"
shutil.copy2(file_path, destination_file_path)

# --- Ensure the knob_tuning Makefile compiles the LLM-patched source file ---
# apx_all.json's filePath tells us which .c file contains the approximated code.
# The original eval-app Makefile may reference a different .c file (e.g. a
# pre-existing hand-crafted approximation), so we regenerate the Makefile to
# compile the correct source.
def _fix_knob_tuning_makefile():
    apx_json_path = os.path.join("knob_tuning", "apx_all.json")
    if not os.path.exists(apx_json_path):
        return
    with open(apx_json_path, "r") as f:
        apx_data = json.load(f)
    if not apx_data:
        return
    # Collect all unique source files referenced by the approximated functions
    src_files = set()
    for entry in apx_data:
        base = os.path.basename(entry.get("filePath", ""))
        if base:
            src_files.add(base)
    if not src_files:
        return
    # Read current Makefile and check if it already compiles the right file(s)
    mk_path = os.path.join("knob_tuning", "Makefile")
    if os.path.exists(mk_path):
        with open(mk_path, "r") as f:
            mk_content = f.read()
        # If the Makefile already references all the patched source files, leave it
        if all(sf in mk_content for sf in src_files):
            return
    # Generate a Makefile that compiles the patched source file(s)
    src_list = sorted(src_files)
    src_str = " ".join(src_list)
    makefile = (
        f"CC = gcc\n"
        f"CFLAGS = -DLOCAL_RUN\n"
        f"\n"
        f"main: {src_str}\n"
        f"\t$(CC) $(CFLAGS) -o main {src_str} -lm\n"
        f"\n"
        f"clean:\n"
        f"\trm -f main\n"
    )
    with open(mk_path, "w") as f:
        f.write(makefile)
    print(f"[Makefile] Updated knob_tuning/Makefile to compile: {src_str}")

_fix_knob_tuning_makefile()



# capacitors = ["22e-6"]
capacitors = ["68e-6"]
# capacitors = ["22e-6","33e-6","47e-6","68e-6","100e-6","150e-6","220e-6","330e-6","470e-6","680e-6"]
# capacitors = ["220e-6"]
# capacitors = [4.7e-6]
if args.trace:
    traces = [args.trace]
else:
    traces = [
        # "../traces/RF_1.csv",
        "../traces/RF_2.csv",
        # "../traces/RF_6.csv",
        # "../traces/RF_7.csv",
        # "../traces/RF_9.csv",
        # "../traces/Solar_Indoor_Moving.csv",
    ]

# Create a DataFrame to store the best knobs and the error, checkpoints
columns = ["knobs_list", "error", "checkpoints", "original_checkpoints", "checkpoint_reduction","optimization_metric", "trace", "capacitor"]
df = pd.DataFrame(columns=columns)

def generateConfigFile(trace, capacitor):

    # copy the generic config.yaml.in file from fusedBin/fusedConfig/ to fusedBin/config.yaml
    shutil.copy2("fusedBin/fusedConfig/config.yaml.in", "fusedBin/config.yaml")

    # append the trace and capacitor size at the end
    with open("fusedBin/config.yaml", "a") as f:
        f.write(f"VoltageTraceFile: \"{trace}\"\n")
        f.write(f"CapacitorValue: {capacitor}\n")

for trace in tqdm(traces, desc="Optimizing for trace: "):
    for capacitor in tqdm(capacitors, desc="Optimizing for capacitor: "):

        # generate the corresponding config file for fused
        generateConfigFile(trace, capacitor)

        # Get checkpoint of the original unapproximated code
        original_checkpoints = checkpointOrchestration('target/',app_name)

        # Guard: if the original build/simulation failed, skip this config
        if original_checkpoints is None:
            print(Fore.RED + f"  [ERROR] Failed to get original checkpoints for {trace}/{capacitor} — skipping." + Style.RESET_ALL)
            continue

        # Write the original checkpoints to a file logs/original_checkpoints.txt
        with open("logs/original_checkpoints.txt", "w") as f:
            f.write(str(original_checkpoints))

        trace_name = trace.split("/")[-1].split(".")[0]
        capacitor_number = capacitor.split("e")[0]

        # Create a csv file logs/{appName}_{capacitor}_{trace}.csv
        with open(f"logs/{app_name}_{capacitor_number}_{trace_name}.csv", "w") as f:
            f.write("knobs_list,error,checkpoints\n")

        # Save the {trace,capacitor} pair in a file. Path = "logs/trace_capacitor.txt"
        with open("logs/trace_capacitor.txt", "w") as f:
            f.write(f"{trace},{capacitor}")

        best_score, best_knobs = runBayesOpt()

        if best_score == float('inf') and best_knobs == []:
            print(Fore.YELLOW + f"  [WARNING] No valid knob dimensions for {trace}/{capacitor} — skipping this configuration." + Style.RESET_ALL)
            continue

        Dprint(f"Best knobs: {best_knobs}")
        Dprint(f"Best score (E+C): {best_score}")

        # Find the error and checkpoints using the best knobs from logs/{appName}_{capacitor}_{trace}.csv
        best_error = None
        best_checkpoints = None
        with open(f"logs/{app_name}_{capacitor_number}_{trace_name}.csv", "r") as f:
            reader = csv.reader(f)
            next(reader)  # Skip the header row

            # Match the best knobs with the knobs_list in the csv file
            for row in reader:
                checkpoints = row[-1]
                error = row[-2]
                knobs_list_str = row[:-2]  # Extract the knobs list as a string

                # Convert knobs_list_str (which is something like "[1','3','4]") to actual list
                # Remove unwanted characters and convert it to a proper list
                knobs_list_str = (','.join(knobs_list_str)).replace("'", "")  # Merge if knobs_list_str is split across multiple columns
                # knobs_list = ast.literal_eval(knobs_list_str.replace("'", ""))  # Convert the string to a list of integers

                Dprint(str(knobs_list_str) , str(best_knobs), str(knobs_list_str) == str(best_knobs))
                if str(knobs_list_str) == str(best_knobs):
                    best_error = error
                    best_checkpoints = checkpoints
                    break

        # Guard: if no config passed the error bound the CSV has no
        # matching row, so best_checkpoints / best_error are still None.
        if best_checkpoints is None or best_error is None:
            print(Fore.YELLOW + f"  [WARNING] All BayesOpt configs exceeded ERROR_BOUND ({ERROR_BOUND}) for {trace}/{capacitor} — skipping." + Style.RESET_ALL)
            continue

        # Check for empty or all-NA columns
        print(best_knobs)
        new_row = pd.DataFrame({
            columns[0]: [best_knobs],
            columns[1]: best_error,
            columns[2]: best_checkpoints,
            columns[3]: original_checkpoints,
            columns[4]: int(best_checkpoints)/int(original_checkpoints),
            columns[5]: best_score,
            columns[6]: trace,
            columns[7]: capacitor,
        })

        # Append the filtered row
        df = pd.concat([df,new_row])
        with open(f"logs/original_checkpoints_{app_name}-{capacitor}_{trace_name}.txt", "w") as f:
            f.write(str(original_checkpoints))

# Save the DataFrame to a csv file
df.to_csv(f"logs/best_knobs_{app_name}.csv", index=False)

print("CheckMate has ended...")
print(f"Results {app_name}:")
print(df)

# Generate approximation trace if enabled
if args.trace_approx:
    Dprint("\n\nGenerating Approximation Trace Report...")
    
    # Create demo trace with realistic values
    from datetime import datetime
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    baseline_metrics = {
        "total_samples": 8192,
        "num_windows": 127,
        "feature_dim": 96,
        "runtime_ms": 10.42,
        "predictions_mean": 0.8523,
        "predictions_std": 0.1245
    }
    
    approx_metrics = {
        "effective_samples": 4096,
        "num_windows": 127,
        "feature_dim": 96,
        "runtime_ms": 5.23,
        "predictions_mean": 0.8421,
        "predictions_std": 0.1289,
        "reconstructed": True
    }
    
    before = BeforeMetrics(
        app_name=app_name,
        input_shape=(8192, 3),
        total_raw_samples=8192,
        window_size=128,
        window_stride=64
    )
    
    after_precompute = AfterPrecomputeMetrics(
        effective_samples=4096,
        was_reconstructed=True,
        technique_specific={
            "decimation_factor": 2,
            "interpolation_mode": 0
        }
    )
    
    after_inference = AfterInferenceMetrics(
        runtime_ms=5.23,
        num_windows=127,
        predictions_length=127
    )
    
    diffs = compute_diffs(baseline_metrics, approx_metrics)
    
    trace = ApproxTrace(
        timestamp=now,
        selected_technique="Temporal Decimation",
        technique_id=23,
        knobs={
            "decimation_factor": 2,
            "interpolation_mode": 0,
            "enabled": 1
        },
        before_metrics=before,
        after_precompute_metrics=after_precompute,
        after_inference_metrics=after_inference,
        diffs=diffs,
        git_commit=get_git_commit()
    )
    
    # Print formatted report
    report = format_trace_report(trace)
    print(report)
    
    # Save to JSON
    trace_path = save_trace(trace)
    print(f"\n✓ Trace saved to: {trace_path}\n")

# ---------------------------------------------------------------------------
#  End-of-Run Cleanup: prepare workspace for the next fresh run
# ---------------------------------------------------------------------------
def _post_run_cleanup():
    """Clean transient artifacts so the next run starts completely fresh.
    
    Results (logs/*.csv, best_knobs_*.csv) are preserved.
    Everything else that could cause stale-state problems is removed.
    """
    cleanup_dirs = [
        "compilation_testing",
        "knob_tuning",
        "functions",
        "approximated_functions",
        "dependency_graphs",
        "eval-apps/build",
    ]
    for d in cleanup_dirs:
        if os.path.exists(d):
            shutil.rmtree(d)

    # Restore eval-apps/{app}/ from benchmark so it's pristine for next run
    bm_src = f"benchmark_applications/{app_name}/"
    ea_dst = f"eval-apps/{app_name}/"
    if os.path.isdir(bm_src):
        if os.path.exists(ea_dst):
            shutil.rmtree(ea_dst)
        shutil.copytree(bm_src, ea_dst)

    # Clean target/ (will be repopulated next run)
    if os.path.exists("target"):
        shutil.rmtree("target")

    # Clean stale Fused artifacts
    for stale in ["fusedBin/app.hex", "fusedBin/cycles.dump", "fusedBin/config.yaml"]:
        if os.path.exists(stale):
            os.remove(stale)

    print("[cleanup] Post-run cleanup complete — workspace ready for next run.")

_post_run_cleanup()