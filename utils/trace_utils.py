"""
Approximation Decision Trace Module

Captures and traces which approximation technique was selected, what knob values
were used, and what changes were applied compared to baseline.

Structure:
- ApproxTrace: Dataclass containing trace information
- save_trace(): Saves trace to JSON file
- compute_diffs(): Compares baseline vs approximation metrics
- format_trace_report(): Pretty-prints trace report to stdout
"""

import json
import os
from dataclasses import dataclass, asdict
from typing import Dict, Any, Optional
from datetime import datetime
import numpy as np


@dataclass
class BeforeMetrics:
    """Metrics captured BEFORE approximation is applied"""
    app_name: str
    input_shape: tuple
    total_raw_samples: int
    window_size: int
    window_stride: int


@dataclass
class AfterPrecomputeMetrics:
    """Metrics captured AFTER approximation is applied, before feature extraction"""
    effective_samples: int
    was_reconstructed: bool
    technique_specific: Dict[str, Any]  # FFT, decimation, spatial, etc.


@dataclass
class AfterInferenceMetrics:
    """Metrics captured AFTER inference"""
    runtime_ms: float
    num_windows: int
    predictions_length: int
    accuracy_proxy: Optional[float] = None


@dataclass
class MetricsDiff:
    """Difference between baseline and approximation metrics"""
    samples_diff: Dict[str, int]
    samples_ratio: float
    windows_diff: Dict[str, int]
    windows_ratio: float
    runtime_diff_ms: float
    runtime_ratio: float
    runtime_speedup_pct: float
    feature_dim_diff: Optional[Dict[str, int]] = None
    feature_dim_ratio: Optional[float] = None
    predictions_mean_diff: Optional[float] = None
    predictions_std_diff: Optional[float] = None


@dataclass
class ApproxTrace:
    """Complete approximation trace information"""
    timestamp: str
    selected_technique: str
    technique_id: int
    knobs: Dict[str, Any]
    before_metrics: BeforeMetrics
    after_precompute_metrics: AfterPrecomputeMetrics
    after_inference_metrics: AfterInferenceMetrics
    diffs: MetricsDiff
    git_commit: Optional[str] = None


_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def get_git_commit() -> Optional[str]:
    """Get current git commit hash if available"""
    try:
        import subprocess
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=_REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except:
        pass
    return None


def save_trace(trace: ApproxTrace, output_dir: str = os.path.join(_REPO_ROOT, "trace_results")) -> str:
    """
    Save trace to JSON file
    
    Args:
        trace: ApproxTrace object
        output_dir: Directory to save trace file
        
    Returns:
        Path to saved trace file
    """
    os.makedirs(output_dir, exist_ok=True)
    
    timestamp_str = trace.timestamp.replace(":", "-").replace(" ", "_")
    output_path = os.path.join(output_dir, f"trace_{timestamp_str}.json")
    
    # Convert to dict, handling nested dataclasses
    trace_dict = asdict(trace)
    
    # Convert tuples to lists for JSON serialization
    def convert_tuples(obj):
        if isinstance(obj, dict):
            return {k: convert_tuples(v) for k, v in obj.items()}
        elif isinstance(obj, (list, tuple)):
            return [convert_tuples(item) for item in obj]
        return obj
    
    trace_dict = convert_tuples(trace_dict)
    
    with open(output_path, 'w') as f:
        json.dump(trace_dict, f, indent=2)
    
    return output_path


def compute_diffs(baseline_metrics: Dict[str, Any], approx_metrics: Dict[str, Any]) -> MetricsDiff:
    """
    Compute differences between baseline and approximation metrics
    
    Args:
        baseline_metrics: Metrics from baseline run
        approx_metrics: Metrics from approximation run
        
    Returns:
        MetricsDiff object
    """
    baseline_samples = baseline_metrics.get("total_samples", 0)
    approx_samples = approx_metrics.get("effective_samples", 0)
    
    baseline_windows = baseline_metrics.get("num_windows", 0)
    approx_windows = approx_metrics.get("num_windows", 0)
    
    baseline_feature_dim = baseline_metrics.get("feature_dim", None)
    approx_feature_dim = approx_metrics.get("feature_dim", None)
    
    baseline_runtime = baseline_metrics.get("runtime_ms", 0.0)
    approx_runtime = approx_metrics.get("runtime_ms", 0.0)
    
    baseline_pred_mean = baseline_metrics.get("predictions_mean", None)
    approx_pred_mean = approx_metrics.get("predictions_mean", None)
    
    baseline_pred_std = baseline_metrics.get("predictions_std", None)
    approx_pred_std = approx_metrics.get("predictions_std", None)
    
    # Compute ratios safely
    samples_ratio = approx_samples / baseline_samples if baseline_samples > 0 else 1.0
    windows_ratio = approx_windows / baseline_windows if baseline_windows > 0 else 1.0
    runtime_ratio = approx_runtime / baseline_runtime if baseline_runtime > 0 else 1.0
    runtime_speedup_pct = ((baseline_runtime - approx_runtime) / baseline_runtime * 100) if baseline_runtime > 0 else 0.0
    
    feature_dim_ratio = None
    if baseline_feature_dim and approx_feature_dim:
        feature_dim_ratio = approx_feature_dim / baseline_feature_dim if baseline_feature_dim > 0 else 1.0
    
    pred_mean_diff = None
    if baseline_pred_mean is not None and approx_pred_mean is not None:
        pred_mean_diff = abs(approx_pred_mean - baseline_pred_mean)
    
    pred_std_diff = None
    if baseline_pred_std is not None and approx_pred_std is not None:
        pred_std_diff = abs(approx_pred_std - baseline_pred_std)
    
    return MetricsDiff(
        samples_diff={
            "baseline": baseline_samples,
            "approx": approx_samples,
            "reduction": baseline_samples - approx_samples
        },
        samples_ratio=samples_ratio,
        windows_diff={
            "baseline": baseline_windows,
            "approx": approx_windows,
            "diff": baseline_windows - approx_windows
        },
        windows_ratio=windows_ratio,
        feature_dim_diff={
            "baseline": baseline_feature_dim,
            "approx": approx_feature_dim,
            "reduction": (baseline_feature_dim - approx_feature_dim) if baseline_feature_dim and approx_feature_dim else None
        } if baseline_feature_dim and approx_feature_dim else None,
        feature_dim_ratio=feature_dim_ratio,
        runtime_diff_ms=baseline_runtime - approx_runtime,
        runtime_ratio=runtime_ratio,
        runtime_speedup_pct=runtime_speedup_pct,
        predictions_mean_diff=pred_mean_diff,
        predictions_std_diff=pred_std_diff
    )


def format_trace_report(trace: ApproxTrace) -> str:
    """
    Format trace as a nicely formatted report string
    
    Args:
        trace: ApproxTrace object
        
    Returns:
        Formatted report string
    """
    report = []
    report.append("\n" + "=" * 80)
    report.append("APPROXIMATION DECISION TRACE REPORT")
    report.append("=" * 80)
    report.append(f"Timestamp: {trace.timestamp}")
    if trace.git_commit:
        report.append(f"Git Commit: {trace.git_commit}")
    
    report.append("\n" + "-" * 80)
    report.append("SELECTED APPROXIMATION")
    report.append("-" * 80)
    report.append(f"Technique: #{trace.technique_id} - {trace.selected_technique}")
    report.append("\nKnob Values:")
    for knob_name, knob_value in trace.knobs.items():
        report.append(f"  {knob_name}: {knob_value}")
    
    report.append("\n" + "-" * 80)
    report.append("BEFORE APPROXIMATION")
    report.append("-" * 80)
    bm = trace.before_metrics
    report.append(f"App Name: {bm.app_name}")
    report.append(f"Input Shape: {bm.input_shape}")
    report.append(f"Total Raw Samples: {bm.total_raw_samples}")
    report.append(f"Window Config: size={bm.window_size}, stride={bm.window_stride}")
    
    report.append("\n" + "-" * 80)
    report.append("AFTER APPROXIMATION (Pre-compute)")
    report.append("-" * 80)
    apm = trace.after_precompute_metrics
    report.append(f"Effective Samples: {apm.effective_samples}")
    report.append(f"Signal Reconstructed: {apm.was_reconstructed}")
    report.append("Technique-Specific Details:")
    for key, value in apm.technique_specific.items():
        if isinstance(value, dict):
            report.append(f"  {key}:")
            for sub_key, sub_value in value.items():
                report.append(f"    {sub_key}: {sub_value}")
        else:
            report.append(f"  {key}: {value}")
    
    report.append("\n" + "-" * 80)
    report.append("AFTER INFERENCE")
    report.append("-" * 80)
    aim = trace.after_inference_metrics
    report.append(f"Runtime: {aim.runtime_ms:.2f} ms")
    report.append(f"Number of Windows: {aim.num_windows}")
    report.append(f"Predictions Length: {aim.predictions_length}")
    if aim.accuracy_proxy is not None:
        report.append(f"Accuracy Proxy: {aim.accuracy_proxy:.4f}")
    
    report.append("\n" + "-" * 80)
    report.append("COMPARISON: BASELINE vs APPROXIMATION")
    report.append("-" * 80)
    diff = trace.diffs
    
    report.append(f"\nSamples:")
    report.append(f"  Baseline: {diff.samples_diff['baseline']}")
    report.append(f"  Approx:   {diff.samples_diff['approx']}")
    report.append(f"  Reduction: {diff.samples_diff['reduction']} ({(1 - diff.samples_ratio) * 100:.1f}%)")
    
    report.append(f"\nWindows:")
    report.append(f"  Baseline: {diff.windows_diff['baseline']}")
    report.append(f"  Approx:   {diff.windows_diff['approx']}")
    report.append(f"  Diff:     {diff.windows_diff['diff']}")
    
    if diff.feature_dim_diff and diff.feature_dim_diff['baseline'] is not None:
        report.append(f"\nFeature Dimension:")
        report.append(f"  Baseline: {diff.feature_dim_diff['baseline']}")
        report.append(f"  Approx:   {diff.feature_dim_diff['approx']}")
        if diff.feature_dim_diff['reduction'] is not None:
            report.append(f"  Reduction: {diff.feature_dim_diff['reduction']}")
    
    report.append(f"\nRuntime:")
    report.append(f"  Baseline: {diff.samples_diff['baseline']} samples → {(diff.runtime_ratio / diff.samples_ratio) * diff.runtime_ratio if diff.samples_ratio else 0:.2f} ms baseline")
    report.append(f"  Approx:   {diff.samples_diff['approx']} samples")
    report.append(f"  Runtime Ratio: {diff.runtime_ratio:.2f}x")
    report.append(f"  Speedup: {diff.runtime_speedup_pct:.1f}%")
    
    if diff.predictions_mean_diff is not None:
        report.append(f"\nPrediction Differences:")
        report.append(f"  Mean Diff: {diff.predictions_mean_diff:.6f}")
        if diff.predictions_std_diff is not None:
            report.append(f"  Std Diff: {diff.predictions_std_diff:.6f}")
    
    report.append("\n" + "=" * 80)
    report.append(f"Trace saved to: trace_results/trace_{trace.timestamp.replace(':', '-').replace(' ', '_')}.json")
    report.append("=" * 80 + "\n")
    
    return "\n".join(report)


def set_deterministic_seeds(seed: int = 42):
    """Set numpy and python random seeds for determinism"""
    import random
    np.random.seed(seed)
    random.seed(seed)


def create_dummy_trace_for_demo() -> ApproxTrace:
    """
    Create a dummy trace for demonstration purposes
    Used by smoke tests
    """
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    before = BeforeMetrics(
        app_name="activity_recognition_demo",
        input_shape=(8192, 3),
        total_raw_samples=8192,
        window_size=128,
        window_stride=64
    )
    
    after_precompute = AfterPrecomputeMetrics(
        effective_samples=4096,
        was_reconstructed=True,
        technique_specific={
            "technique_type": "temporal_decimation",
            "decimation_factor": 2,
            "interpolation_mode": "zero_order_hold"
        }
    )
    
    after_inference = AfterInferenceMetrics(
        runtime_ms=5.23,
        num_windows=127,
        predictions_length=127
    )
    
    baseline_metrics = {
        "total_samples": 8192,
        "num_windows": 127,
        "runtime_ms": 10.42,
        "predictions_mean": 0.85,
        "predictions_std": 0.12
    }
    
    approx_metrics = {
        "effective_samples": 4096,
        "num_windows": 127,
        "runtime_ms": 5.23,
        "predictions_mean": 0.84,
        "predictions_std": 0.13
    }
    
    diffs = compute_diffs(baseline_metrics, approx_metrics)
    
    return ApproxTrace(
        timestamp=now,
        selected_technique="Temporal Decimation",
        technique_id=23,
        knobs={"decimation_factor": 2, "interpolation_mode": 0},
        before_metrics=before,
        after_precompute_metrics=after_precompute,
        after_inference_metrics=after_inference,
        diffs=diffs,
        git_commit=get_git_commit()
    )
