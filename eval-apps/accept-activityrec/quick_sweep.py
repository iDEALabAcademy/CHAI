import subprocess, re

TEMPLATE = open("main.c").read()

def set_knobs(lpr, mag, sqit, ee, ct, mc, pf):
    code = TEMPLATE
    code = re.sub(r'float loop_perf_ratio = [^;]+;', f'float loop_perf_ratio = {lpr};', code)
    code = re.sub(r'int magnitude_mode = [^;]+;', f'int magnitude_mode = {mag};', code)
    code = re.sub(r'int sqrt_iterations = [^;]+;', f'int sqrt_iterations = {sqit};', code)
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

print(f"{'LPR':>5} {'MAG':>3} {'SQI':>3} {'EE':>2} {'CT':>3} {'MC':>3} {'PF':>3} | {'Error%':>8} {'Still':>5} {'Mov':>5}")
print("-" * 65)

# Test key combinations: mag=3 (integer sqrt), mag=1 (Manhattan), mag=2 (Chebyshev) 
# with LPR=1.0 which we know preserves featurize accuracy
for mag in [0, 1, 2, 3]:
    for sqit in [4, 3, 2, 1]:
        for pf in [100, 50, 25]:
            set_knobs(1.0, mag, sqit, 1, 8, 2, pf)
            mape, s, m = run_and_get_error()
            if mape is not None:
                print(f" 1.00 {mag:>3d} {sqit:>3d}  1   8   2 {pf:>3d} | {mape*100:>7.3f}% {s:>5d} {m:>5d}")

# Also test LPR=0.75 with mag=3
print("\n--- LPR=0.75, mag=3 ---")
for sqit in [4, 3, 2, 1]:
    for pf in [100, 50]:
        set_knobs(0.75, 3, sqit, 1, 8, 2, pf)
        mape, s, m = run_and_get_error()
        if mape is not None:
            print(f" 0.75   3 {sqit:>3d}  1   8   2 {pf:>3d} | {mape*100:>7.3f}% {s:>5d} {m:>5d}")

# Restore
set_knobs(0.6929820938512683, 3, 4, 1, 8, 3, 45)
