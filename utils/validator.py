import ast
import subprocess
import os
import math

from config.globals import TARGET_FILES
from utils.utils import findFileOfFunc, writeFunctionsToJson, Dprint
from lib.lsp import lsp_patcher


def updateKnobValue(functionDict, newValue, knob):
    """
    Update the value of a knob in the function code.

    Args:
        functionDict (dict): A dictionary containing the function code.
        newValue (any): The new value to assign to the knob.
        knob (str): The name of the knob to update.

    Returns:
        None
    """

    # Read the function code
    function_code = functionDict["completeFunction"]

    function_lines = function_code.split("\n")

    # Find the line number where the knob is defined
    knob_line_number = -1
    knob_line = ""
    for line_number, line in enumerate(function_lines):
        if knob in line:
            knob_line_number = line_number
            knob_line = line
            break

    # Update the knob value
    updated_knob_line = knob_line.split("=")[0] + f"= {newValue};"

    # Dprint(f"The knob line was updated.\n{updated_knob_line}")

    # Update the function code
    function_lines[knob_line_number] = updated_knob_line

    # Merge the function lines
    updated_function_code = "\n".join(function_lines)

    # Update the function dictionary
    functionDict["completeFunction"] = updated_function_code


def compileFunction(path):
    """
    Compile the codebase.

    Args:
        path (str): The path to the codebase.

    Returns:
        int: 0 if the compilation is successful, 1 if it fails.
    """
    try:
        with open(os.path.join(path, "compiler_log.txt"), "w") as output_file:
            subprocess.run(
                "make main",
                shell=True,
                check=True,
                cwd=path,
                stdout=output_file,
                stderr=subprocess.STDOUT,
            )

        # Dprint("Success\n")
        return 0  # Successful compilation
    except Exception as e:
        Dprint(e)
        with open(os.path.join(path, "compiler_log.txt"), "r") as output_file:
            response = output_file.read()

        Dprint(response)
        return 1  # Compilation failed


def executeFunction(application, path):
    """
    Executes a command based on the given application name.

    Args:
        application (str): The name of the application.

    Returns:
        int: 0 if the command is executed successfully, 1 otherwise.
    """
    if application == "susan":
        command = f"./main 2092.pgm output.pgm -e"

        # Execute the command, and return 1 if it fails or there is a runtime error
        try:
            subprocess.run(
                command, shell=True, check=True, cwd=path, stdout=subprocess.DEVNULL
            )
            return 0
        except Exception as e:
            Dprint(e)
            return 1
    else:
        command = f"./main"

        # Execute the command, and return 1 if it fails or there is a runtime error
        try:
            subprocess.run(
                command, shell=True, check=True, cwd=path, stdout=subprocess.DEVNULL
            )
            return 0
        except Exception as e:
            Dprint(e)
            return 1


def validateFunction(functionDict):
    """
    Validates a function by iteratively updating knob values and checking if the function is safe.

    Args:
        functionDict (dict): A dictionary containing information about the function to be validated.

    Returns:
        None
    """

    # Extract knob variables, ranges, and step sizes from functionDict
    raw_vars = functionDict["knobVariables"]
    knob_variables = ast.literal_eval(raw_vars) if isinstance(raw_vars, str) else raw_vars
    raw_ranges = functionDict["knobRanges"]
    knob_ranges = ast.literal_eval(raw_ranges) if isinstance(raw_ranges, str) else raw_ranges
    raw_steps = functionDict["knobStepSize"]
    knob_step_sizes = ast.literal_eval(raw_steps) if isinstance(raw_steps, str) else raw_steps

    functionName = functionDict["functionName"]

    apx_codebase = f"compilation_testing/ApxFiles_{functionName}"
    apx_file = findFileOfFunc(functionName, TARGET_FILES)  # HARD CODED
    apx_file = os.path.join(apx_codebase, apx_file)

    json_file_path = f"apx_{functionName}.json"

    safeFlag = True

    for index, knob in enumerate(knob_variables):
        lower_bound, upper_bound = knob_ranges[index][knob]
        knob_step_size = knob_step_sizes[index][knob]

        # Debug
        # Dprint(f"Working on Knob: {knob}")
        # Dprint(f"Lower Bound: {lower_bound}")
        # Dprint(f"Upper Bound: {upper_bound}")
        # Dprint(f"Step Size: {knob_step_size}")

        # Update the knob value starting from upper bound to lower bound in a binary search fashion
        if knob_step_size == "Integer":
            current_value = math.ceil((upper_bound + lower_bound) / 2)
        elif knob_step_size == "Real":
            current_value = (upper_bound + lower_bound) / 2

        while current_value >= lower_bound:

            # Dprint(f"Updating the knob value to: {current_value}")

            # Update knob value and write to JSON
            updateKnobValue(functionDict, current_value, knob)
            wrapper_dict = {functionName: functionDict}
            writeFunctionsToJson(wrapper_dict, "approximated_functions/apx")

            # Patch the updated function code
            lsp_patcher(apx_codebase,json_file_path)

            # Compile the codebase
            compileFunction(apx_codebase)

            # Execute the file (add for other apps later)
            if "susan" in apx_file:
                successFlag = executeFunction("susan", apx_codebase)
            else:
                successFlag = executeFunction("other_App", apx_codebase)

            if successFlag == 0:
                if knob_step_size == "Integer":
                    current_value = math.ceil((current_value + upper_bound) / 2)
                elif knob_step_size == "Real":
                    current_value = (current_value + upper_bound) / 2
            else:
                upper_bound = current_value
                if knob_step_size == "Integer":
                    current_value = math.floor((current_value + lower_bound) / 2)
                elif knob_step_size == "Real":
                    current_value = (current_value + lower_bound) / 2

            # If the current value is equal to the upper bound, break the loop. The function is safe.
            if current_value >= upper_bound:
                break

            # If the current value is equal to the lower bound, break the loop. The function is unsafe.
            if current_value <= lower_bound:
                # Delete the json from the approximated functions
                safeFlag = False
                Dprint("rasied")
                
                quit()
                os.remove(json_file_path)
                break

        if not safeFlag:
            break

    Dprint(f"Successfully Validated {functionName}")


def validateEarlyExit(code_string, knob_names, knob_ranges):
    """
    Validates that early-exit approximation code follows safety constraints.
    
    Args:
        code_string (str): The approximated code with early-exit
        knob_names (list): List of knob variable names (e.g., ['convergence_threshold_knob'])
        knob_ranges (list): List of [min, max] ranges for each knob
    
    Returns:
        bool: True if code is safe for early-exit, False otherwise
    """
    import re
    
    # Rule 1: Check that convergence metric is computed BEFORE threshold check
    # Pattern: Look for convergence/metric computation (e.g., change = fabs(...))
    metric_patterns = [
        r'(change|error|distance|diff|metric)\s*=',  # Metric assignment
        r'fabs\s*\(',  # Absolute value computation
        r'sqrt\s*\(',  # Square root (often used in distance metrics)
    ]
    
    metric_found = any(re.search(pattern, code_string, re.IGNORECASE) for pattern in metric_patterns)
    if not metric_found:
        Dprint("Warning: No convergence metric computation found in early-exit code")
        return False
    
    # Rule 2: Check for safe exit patterns (break or return)
    safe_exit_patterns = [r'break\s*;', r'return\s*;', r'return\s+[\w\d_]+\s*;']
    safe_exit_found = any(re.search(pattern, code_string) for pattern in safe_exit_patterns)
    if not safe_exit_found:
        Dprint("Error: No safe exit statement (break or return) found in early-exit code")
        return False
    
    # Rule 3: Check for unsafe patterns (while True, infinite loops, hardware-specific code)
    unsafe_patterns = [
        r'while\s*\(\s*1\s*\)',  # while(1) infinite loop
        r'while\s*\(\s*true\s*\)',  # while(true) 
        r'for\s*\(\s*;\s*;\s*\)',  # for(;;) infinite loop
        r'__asm__|asm\s*\{',  # Inline assembly
        r'volatile\s+',  # Volatile (hardware-specific)
    ]
    
    for pattern in unsafe_patterns:
        if re.search(pattern, code_string, re.IGNORECASE):
            Dprint(f"Error: Unsafe pattern found in early-exit code: {pattern}")
            return False
    
    # Rule 4: Validate knob ranges (threshold should be in reasonable bounds)
    for knob_name, knob_range in zip(knob_names, knob_ranges):
        if len(knob_range) != 2:
            Dprint(f"Error: Invalid knob range for {knob_name}: {knob_range}")
            return False
        
        min_val, max_val = knob_range
        if min_val >= max_val:
            Dprint(f"Error: Knob range invalid for {knob_name}: min={min_val}, max={max_val}")
            return False
        
        # Check for pathological ranges (e.g., threshold causing division by zero)
        if 'threshold' in knob_name.lower() and min_val == max_val:
            Dprint(f"Warning: Zero-range threshold knob {knob_name} may be ineffective")
            return False
    
    Dprint(f"Early-exit validation passed for knobs: {knob_names}")
    return True

