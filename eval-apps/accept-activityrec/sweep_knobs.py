#!/usr/bin/env python3
"""Sweep knob space to find combos with <0.3% error"""
import subprocess, re, itertools

TEMPLATE = open("main.c").read()

# Knob positions in the file
def set_knobs(lpr, mag, sqit, ee, ct, mc, pf):
    code = TEMPLATE
    # featurize knobs
    code = re.sub(r'float loop_perf_ratio = [^;]+;', f'float loop_perf_ratio = {lpr};', code)
    code = re.sub(r'int magnitude_mode = [^;]+;', f'int magnitude_mode = {mag};', code)
    code = re.sub(r'int sqrt_iterations = [^;]+;', f'int sqrt_iterations = {sqit};', code)
    # classify knobs
    code = re.sub(r'int early_exit_enabled = [^;]+;', f'int early_exit_enabled = {ee};', code)
    code = re.sub(r'int confidence_threshold = [^;]+;', f'int confidence_threshold = {ct};', code)
    code = re.sub(r'int min_comparisons = [^;]+;', f'int min_comparisons = {mc};', code)
    code = re.sub(r'int perforation_factor = [^;]+;', f'int perforation_factor = {pf};', code)
    with open("main.c", "w") as f:
        f.write(code)

def run_and_get_error():
    subprocess.run("make clean && make main", shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    result = subprocess.run("./main", shell=True, capture_output=True, text=True)
    out = result.stdout.strip()
    try:
        still, moving = map(int, out.split(","))
    except:
        return None, None, None
    gt_still, gt_moving = 41, 472
    mape_still = abs(gt_still - still) / gt_still
    mape_moving = abs(gt_moving - moving) / gt_moving
    mape = (mape_still + mape_moving) / 2
    return mape, still, moving

# Sweep: focus on conservative knobs near baseline
print(f"{'LPR':>5} {'MAG':>3} {'SQI':>3} {'EE':>2} {'CT':>3} {'MC':>3} {'PF':>3} | {'Error%':>8} {'Still':>5} {'Mov':>5}")
print("-" * 65)

results = []
for lpr in [1.0, 0.95, 0.9, 0.85, 0.75]:
    for mag in [0, 3]:  # 0=original sqrtf, 3=int newton
        for sqit in [4, 3, 2]:
            for ee in [0, 1]:
                for pf in [100, 90, 80, 70, 60, 50]:
                    ct = 8
                    mc = 2
                    set_knobs(lpr, mag, sqit, ee, ct, mc, pf)
                    mape, s, m = run_and_get_error()
                    if mape is not None:
                        results.append((mape, lpr, mag, sqit, ee, ct, mc, pf, s, m))
                        if mape < 0.05:  # Print promising ones
                            print(f"{lpr:>5.2f} {mag:>3d} {sqit:>3d} {ee:>2d} {ct:>3d} {mc:>3d} {pf:>3d} | {mape*100:>7.3f}% {s:>5d} {m:>5d}")

# Sort by error and print top 10
results.sort(key=lambda x: x[0])
print("\n--- TOP 15 LOWEST ERROR COMBOS ---")
print(f"{'LPR':>5} {'MAG':>3} {'SQI':>3} {'EE':>2} {'CT':>3} {'MC':>3} {'PF':>3} | {'Error%':>8} {'Still':>5} {'Mov':>5}")
for mape, lpr, mag, sqit, ee, ct, mc, pf, s, m in results[:15]:
    print(f"{lpr:>5.2f} {mag:>3d} {sqit:>3d} {ee:>2d} {ct:>3d} {mc:>3d} {pf:>3d} | {mape*100:>7.3f}% {s:>5d} {m:>5d}")

# Restore original knobs
set_knobs(0.6929820938512683, 3, 4, 1, 8, 3, 45)
