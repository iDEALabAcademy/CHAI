import json
import random
import subprocess
import copy
from skopt import gp_minimize
from skopt.space import Integer, Real
import ast
from tqdm import tqdm


from utils.utils import getAppName, Dprint, itrPrint
from utils.validator import updateKnobValue
from config.globals import TARGET_FILES
from config.config import ERROR_BOUND
from utils.error_analyzer import susanError, lqiError, stringSearchError, fftError, sobelError, arError, bitcountError, radixbmError, segmentbmError, acceptSobelError, acceptActivityrecError
from utils.checkpoints import checkpointOrchestration
from lib.lsp import lsp_patcher

n_calls = 100
cur_call = 0
# progress_bar = tqdm(total=n_calls, desc="Bayesian Optimization Iteration")

def createSearchSpace(pathToJson):

    with open(pathToJson, "r") as file:
        json_content = file.read()

    # Parse the JSON content
    approximation_data = json.loads(json_content)

    space = []
    for approximation_dict in approximation_data:
        raw_ranges = approximation_dict["knobRanges"]
        knob_ranges = ast.literal_eval(raw_ranges) if isinstance(raw_ranges, str) else raw_ranges
        raw_steps = approximation_dict["knobStepSize"]
        knob_step_size = ast.literal_eval(raw_steps) if isinstance(raw_steps, str) else raw_steps

        for i, knob_range in enumerate(knob_ranges):
            for knob_name, range_values in knob_range.items():
                if knob_step_size[i][knob_name] == "Integer":
                    space.append(
                        Integer(range_values[0], range_values[1], name=knob_name)
                    )
                if knob_step_size[i][knob_name] == "Real":
                    space.append(Real(range_values[0], range_values[1], name=knob_name))

    return space


def getBaselineKnobs(pathToJson):
    """Extract baseline (default) knob values from JSON, in the same order as createSearchSpace."""
    import re as _re

    with open(pathToJson, "r") as file:
        approximation_data = json.loads(file.read())

    baseline = []
    for approximation_dict in approximation_data:
        raw_ranges = approximation_dict["knobRanges"]
        knob_ranges = ast.literal_eval(raw_ranges) if isinstance(raw_ranges, str) else raw_ranges
        raw_steps = approximation_dict["knobStepSize"]
        knob_step_size = ast.literal_eval(raw_steps) if isinstance(raw_steps, str) else raw_steps
        code = approximation_dict.get("completeFunction", "")

        for i, knob_range in enumerate(knob_ranges):
            for knob_name, range_values in knob_range.items():
                step_type = knob_step_size[i][knob_name]
                # Extract the default value from the function code
                match = _re.search(rf'{knob_name}\s*=\s*([0-9.eE\-+]+)', code)
                if match:
                    val = float(match.group(1)) if step_type == "Real" else int(float(match.group(1)))
                else:
                    # Fallback: use the "no approximation" end of the range
                    val = float(range_values[0]) if step_type == "Real" else range_values[0]
                # Clamp to range bounds so x0 is always valid
                lo, hi = (float(range_values[0]), float(range_values[1])) if step_type == "Real" else (range_values[0], range_values[1])
                val = max(lo, min(hi, val))
                if step_type == "Integer":
                    val = int(val)
                baseline.append(val)

    return baseline


def runBayesOpt():
    tuning_folder = "knob_tuning/apx_all.json"
    random_state = random.randint(0, 100)
    global cur_call
    cur_call = 0

    search_space = createSearchSpace(tuning_folder)
    if len(search_space) == 0:
        print("[BayesOpt] WARNING: No knob dimensions found — skipping optimization.")
        return float('inf'), []

    # Seed with baseline (no-approximation) point so BayesOpt explores from a known-good region
    baseline_x0 = getBaselineKnobs(tuning_folder)

    res = gp_minimize(
        evaluateKnobs,
        search_space,
        n_calls=n_calls,
        n_initial_points=5,
        x0=[baseline_x0],
        random_state=random_state
    )
    best_score = res.fun

    return best_score, res.x

    # Dprint(best_score)
    # Dprint(res.x)


def evaluateKnobs(*params):

    global TARGET_FILES
    global cur_call
    
    cur_call += 1

    knobs_list = copy.copy(params[0])
    # knobs_list = [1, 1.0]

    # Dprint(knobs_list)

    with open("knob_tuning/apx_all.json", "r") as file:
        json_content = file.read()

    # Parse the JSON content
    approximation_data = json.loads(json_content)

    for approximation_dict in approximation_data:
        raw_vars = approximation_dict["knobVariables"]
        knob_variables = ast.literal_eval(raw_vars) if isinstance(raw_vars, str) else raw_vars
        # Dprint(knob_variables)

        for var in knob_variables:
            new_value = knobs_list.pop(0)
            # Dprint(var)
            # Dprint(new_value)
            updateKnobValue(approximation_dict, new_value, var)

    # json.dump(approximation_data, fp="knob_tuning/apx_all.json")

    # Save approximation_data in knob_tuning/apx_all.json, write your own logic here
    # open("knob_tuning/apx_all.json", "w").write(json.dumps(approximation_data))
    open("knob_tuning/apx_all.json", "w").write(json.dumps(approximation_data, indent=2))

    lsp_patcher("knob_tuning/", "apx_all.json")

    app_name = getAppName()

    # Get the Error
    if app_name == "susan":
        error = susanError("knob_tuning")
    elif app_name == "sobel-iclib":
        error = sobelError("knob_tuning")
    elif app_name == "lqi-iclib" or app_name == "link-estimator":
        error = lqiError("knob_tuning")
    elif app_name == "stringsearch-iclib":
        error = stringSearchError("knob_tuning")
    elif app_name == "fft-iclib":
        error = fftError("knob_tuning")
    elif app_name == "ar-iclib":
        error = arError("knob_tuning")
    elif app_name == "bc-iclib":
        error = bitcountError("knob_tuning")
    elif app_name == "radix-bm":
        error = radixbmError("knob_tuning")
    elif app_name == "segment-bm":
        error = segmentbmError("knob_tuning")
    elif app_name == "accept-sobel":
        error = acceptSobelError("knob_tuning")
    elif app_name == "accept-activityrec":
        error = acceptActivityrecError("knob_tuning")
    else:
        Dprint(f"WARNING: Unknown app_name '{app_name}' — returning penalty error 1.0")
        error = 1.0

    Dprint(f"Error Returned from Eval Func: {error}")

    # Hard 30% error bound: reject configs that exceed the threshold
    # by returning a large penalty so BayesOpt steers away from them
    if error > ERROR_BOUND:
        Dprint(f"Error {error:.4f} exceeds bound {ERROR_BOUND} — returning penalty")
        itrPrint(f"> Error: {error} [REJECTED — exceeds {ERROR_BOUND}]")
        return 100.0  # large penalty value

    Dprint(f"Error After Bound Check: {error}")

    # logs/trace_capacitor.txt contains the trace and capacitor size
    with open("logs/trace_capacitor.txt", "r") as f:
        trace, capacitor = f.read().split(",")

    # Read the original checkpoints from logs/original_checkpoints.txt
    with open("logs/original_checkpoints.txt", "r") as f:
        original_checkpoints = int(f.read())

    # Get the Checkpoints
    checkpoints = checkpointOrchestration("knob_tuning/",app_name)

    # Guard: if build/simulation failed, return penalty so BayesOpt skips this config
    if checkpoints is None:
        Dprint("[evaluateKnobs] checkpointOrchestration returned None — penalizing")
        return 100.0  # same penalty as error-bound violation

    checkpoints_reduction = checkpoints / original_checkpoints

    Dprint("Checkpoint Reduction: ",checkpoints_reduction)

    trace_name = trace.split("/")[-1].split(".")[0]
    capacitor_number = capacitor.split("e")[0]
    # Appends the knobs_list, error and checkpoints to the file, logs/{appName}_{capacitor}_{trace}.csv
    with open(f"logs/{app_name}_{capacitor_number}_{trace_name}.csv", "a") as f:
        f.write(f"'{params[0]}',{error},{checkpoints}\n")
        # f.write(f"{str([1,1.0])},{error},{checkpoints}\n")

    optimization_metric = error + checkpoints_reduction

    Dprint("Optimization_metric: ", optimization_metric)

    Dprint(f"------------------------ iteration done ------------------------")

    itrPrint((f"Baysian Itraion: {cur_call}/{n_calls}",f"> Error: {error}", f"> Checkpoint Reduction: {checkpoints_reduction}", f"> Optimization Metric: {optimization_metric}"))

    return optimization_metric
