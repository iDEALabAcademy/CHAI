import re
code = open("main.c").read()
# Set: LPR=1.0, mag=3, sqit=2, EE=1, CT=8, MC=2, PF=50
code = re.sub(r'float loop_perf_ratio = [^;]+;', 'float loop_perf_ratio = 1.0;', code)
code = re.sub(r'int magnitude_mode = [^;]+;', 'int magnitude_mode = 3;', code)
code = re.sub(r'int sqrt_iterations = [^;]+;', 'int sqrt_iterations = 2;', code)
code = re.sub(r'int early_exit_enabled = [^;]+;', 'int early_exit_enabled = 1;', code)
code = re.sub(r'int confidence_threshold = [^;]+;', 'int confidence_threshold = 8;', code)
code = re.sub(r'int min_comparisons = [^;]+;', 'int min_comparisons = 2;', code)
code = re.sub(r'int perforation_factor = [^;]+;', 'int perforation_factor = 50;', code)
with open("main.c", "w") as f:
    f.write(code)
print("Knobs set: LPR=1.0, mag=3, sqit=2, EE=1, CT=8, MC=2, PF=50")
