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

print("FIXED INTEGER SQRT (bit-shift initial guess)")
print(f"{'LPR':>5} {'MAG':>3} {'SQI':>3} {'EE':>2} {'PF':>3} | {'Error%':>8} {'Still':>5} {'Mov':>5}")
print("-" * 55)

# Test mag=3 with fixed sqrt, various iterations
for sqit in [1, 2, 3, 4]:
    for pf in [100, 50, 25]:
        set_knobs(1.0, 3, sqit, 1, 8, 2, pf)
        mape, s, m = run_and_get_error()
        if mape is not None:
            marker = " <-- LOW!" if mape < 0.003 else ""
            print(f" 1.00   3 {sqit:>3d}  1 {pf:>3d} | {mape*100:>7.3f}% {s:>5d} {m:>5d}{marker}")

# Also test with LPR < 1 and mag=3
print("\n--- LPR < 1, mag=3, sqit=4 ---")
for lpr in [0.75, 0.5]:
    for pf in [100, 50]:
        set_knobs(lpr, 3, 4, 1, 8, 2, pf)
        mape, s, m = run_and_get_error()
        if mape is not None:
            marker = " <-- LOW!" if mape < 0.003 else ""
            print(f" {lpr:.2f}   3   4  1 {pf:>3d} | {mape*100:>7.3f}% {s:>5d} {m:>5d}{marker}")

# Restore 
set_knobs(0.6929820938512683, 3, 4, 1, 8, 3, 45)
