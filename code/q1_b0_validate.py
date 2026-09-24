# Academic Figure Skill Asset Confirmation (verified against assets/figures/)
# (a) FIR frequency response → LineTrend/plot_sweep.py (incompatible fixed optimization data) → param inherit
# (b) FIR impulse response → LineTrend/plot_sweep.py (incompatible fixed optimization data) → param inherit
# RULE: "native run" = load pre-rendered PNG via Image.open().ax.imshow().
#       "param inherit" = drawing function below that copies Class A/B/C values.
#       If a panel says "native run" and you write a drawing function, you broke the contract.

# Academic Figure Skill Typography Baseline — COPY VERBATIM, place at TOP of script
import matplotlib as mpl
mpl.rcParams.update({
    "font.family": "sans-serif",
    "font.sans-serif": ["Arial", "Helvetica", "Liberation Sans"],
    "font.size": 8,
    "axes.titlesize": 8,
    "axes.labelsize": 8,
    "xtick.labelsize": 7,
    "ytick.labelsize": 7,
    "legend.fontsize": 8,
    "figure.titlesize": 9,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "axes.linewidth": 0.6,
    "xtick.direction": "out",
    "ytick.direction": "out",
    "xtick.major.width": 0.6,
    "ytick.major.width": 0.6,
    "legend.frameon": False,
})

# Academic Figure Skill Nature/Cell/Science Color Palette -- COPY VERBATIM
CATEGORICAL = ["#2166AC", "#B2182B", "#1B7837", "#F1A340", "#762A83", "#666666"]
CATEGORICAL_EXTENDED = [
    "#2166AC", "#B2182B", "#1B7837", "#F1A340", "#762A83", "#666666",
    "#4393C3", "#D6604D", "#5AAE61", "#B35806", "#9970AB", "#999999",
]
DIVERGING   = ["#2166AC", "#F7F7F7", "#B2182B"]
SEQUENTIAL  = ["#F7FBFF", "#6BAED6", "#08306B"]
ACCENT_RED  = "#B2182B"
GREY        = "#999999"
BLACK       = "#222222"

# Academic Figure Skill Export Baseline — COPY VERBATIM
mpl.rcParams.update({
    "pdf.fonttype": 42,         # TrueType font embedding
    "svg.fonttype": "none",     # editable text in SVG
    "savefig.bbox": "tight",    # trim whitespace
    "savefig.dpi": 300,
})

def save_cns_figure(fig, filename):
    """Standard Academic Figure Skill export: vector PDF + 300dpi PNG preview."""
    fig.savefig(f"{filename}.pdf", bbox_inches="tight", dpi=300)
    fig.savefig(f"{filename}.png", bbox_inches="tight", dpi=300)


mpl.use("Agg")
import argparse
import csv
import hashlib
import json
import os
import platform
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from scipy import __version__ as scipy_version
from scipy.signal import freqz, lfilter

from q1_audit import FS, H, SUPPORT_START, SUPPORT_STOP, hard_mask
from q1_preprocess import b0_epoch


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def frequency_response(taps):
    frequency, response = freqz(taps, worN=8192, fs=FS)
    gain = np.abs(response)
    gain_db = 20 * np.log10(np.maximum(gain, 1e-15))
    passband = (frequency >= 1) & (frequency <= 20)
    exact = freqz(taps, worN=np.array([1, 20, 30, 50, 60], dtype=float), fs=FS)[1]
    point_db = 20 * np.log10(np.abs(exact))
    summary = {
        "passband_1_20_min_db": float(gain_db[passband].min()),
        "passband_1_20_max_db": float(gain_db[passband].max()),
        "passband_1_20_ripple_db": float(np.ptp(gain_db[passband])),
        "passband_1_20_min_gain": float(gain[passband].min()),
        "passband_1_20_max_gain": float(gain[passband].max()),
        "points_db": {str(int(f)): float(db) for f, db in zip([1, 20, 30, 50, 60], point_db)},
        "points_gain": {str(int(f)): float(abs(g)) for f, g in zip([1, 20, 30, 50, 60], exact)},
        "grid_hz": float(frequency[1] - frequency[0]),
        "taps_sum": float(taps.sum()),
        "symmetric_max_abs_error": float(np.max(np.abs(taps - taps[::-1]))),
    }
    return frequency, gain, gain_db, summary


def component_noise(name, rng, n, t):
    if name == "white":
        wave = rng.standard_normal(n)
    elif name == "ar1":
        wave = lfilter([1], [1, -0.8], rng.standard_normal(n))
    elif name in ("line50", "line60"):
        wave = np.sin(2 * np.pi * int(name[4:]) * t + rng.uniform(0, 2 * np.pi))
    elif name == "drift0p2":
        wave = np.sin(2 * np.pi * 0.2 * t + rng.uniform(0, 2 * np.pi))
    elif name == "transient":
        center = rng.uniform(-0.4, 1.4)
        wave = rng.choice([-1.0, 1.0]) * np.exp(-0.5 * ((t - center) / 0.1) ** 2)
    else:
        raise ValueError(f"unknown noise component: {name}")
    wave = wave - wave.mean()
    return wave / np.sqrt(np.mean(wave**2))


def synthesize(scenario, rng, n, onset, sensor_dither_rms):
    t = (np.arange(n) - onset) / FS
    jitter = float(rng.normal(0, scenario["jitter_sd_s"])) if scenario["jitter_sd_s"] else 0.0
    signal = np.zeros(n)
    for component in scenario["components"]:
        signal += component["amplitude"] * np.exp(
            -0.5 * ((t - component["mu_s"] - jitter) / component["width_s"]) ** 2
        )
    clean = np.repeat(signal[None, :], 3, axis=0)
    names = scenario["noise"]
    noise = np.zeros_like(clean)
    noise_rms = 0.0
    if names:
        support = slice(onset + SUPPORT_START, onset + SUPPORT_STOP)
        signal_rms = float(np.sqrt(np.mean(signal[support] ** 2)))
        noise_rms = float(scenario["noise_rms_ru"] if "noise_rms_ru" in scenario else signal_rms / scenario["snr"])
        common = sum(component_noise(name, rng, n, t) for name in names) / np.sqrt(len(names))
        for channel in range(3):
            independent = sum(component_noise(name, rng, n, t) for name in names) / np.sqrt(len(names))
            wave = 0.5 * common + np.sqrt(0.75) * independent
            noise[channel] = wave * (noise_rms / np.sqrt(np.mean(wave[support] ** 2)))
    raw = clean + noise + sensor_dither_rms * rng.standard_normal(clean.shape)
    noise_rms = float(np.hypot(noise_rms, sensor_dither_rms))
    if "clip" in scenario:
        clip = scenario["clip"]
        start = onset + clip["start_relative"]
        raw[clip["channel"], start:start + clip["length"]] = clip["value"]
    return clean, raw, jitter, noise_rms


def baseline_core(raw, onset):
    baseline = raw[:, onset - 51:onset].mean(axis=1, keepdims=True)
    return raw[:, onset - 51:onset + 256] - baseline


def _local_peak(values, start, stop, threshold):
    sub = values[start:stop]
    return bool(np.any((sub[1:-1] > sub[:-2]) & (sub[1:-1] > sub[2:]) & (sub[1:-1] > threshold)))


def waveform_metrics(values, truth, scenario, jitter, noise_rms, config):
    error = values - truth
    truth_norm = float(np.linalg.norm(truth))
    out = {
        "rmse_ru": float(np.sqrt(np.mean(error**2))),
        "nrmse": float(np.linalg.norm(error) / truth_norm) if truth_norm > 1e-12 else None,
        "correlation": float(np.corrcoef(values, truth)[0, 1])
        if np.std(values) > 1e-12 and np.std(truth) > 1e-12 else None,
        "amplitude_error_ru": None, "latency_error_samples": None, "false_positive_peak": None,
        "residual_nrmse_to_B0_clean": None,
    }
    if scenario["primary"] is None:
        left = int(np.ceil(config["no_peak_window_s"][0] * FS)) + 51
        right = int(np.floor(config["no_peak_window_s"][1] * FS)) + 52
        threshold = max(config["no_peak_threshold_floor_ru"], config["no_peak_threshold_sigma"] * noise_rms)
        out["false_positive_peak"] = _local_peak(values, left, right, threshold)
        return out
    component = scenario["components"][scenario["primary"]]
    center = component["mu_s"] + jitter
    radius = config["peak_search_radius_s"]
    lo = max(0, int(np.ceil((center - radius) * FS)) + 51)
    hi = min(307, int(np.floor((center + radius) * FS)) + 52)
    polarity = np.sign(component["amplitude"])
    true_index = lo + int(np.argmax(polarity * truth[lo:hi]))
    found_index = lo + int(np.argmax(polarity * values[lo:hi]))
    out["amplitude_error_ru"] = float(values[found_index] - truth[true_index])
    out["latency_error_samples"] = int(found_index - true_index)
    return out


def run_scenarios(config, taps):
    n, onset, repeats = config["samples"], config["cue_onset"], config["repeats_per_scenario"]
    if config["fs"] != FS or repeats < 100 or onset + SUPPORT_START < 0 or onset + SUPPORT_STOP > n:
        raise ValueError("simulation config violates fixed B0 support or 100 repeats")
    if config["no_peak_window_s"] != [0.25, 0.5] or config["peak_search_radius_s"] != 0.08:
        raise ValueError("metric windows differ from frozen Q1-B0-synthetic-v1 contract")
    rows, truth_rows, filtered_truth_rows = [], [], []
    summary = []
    for index, scenario in enumerate(config["scenarios"]):
        rng = np.random.default_rng(config["seed"] + 1000 * index)
        rejected = 0
        scenario_truth, scenario_filtered_truth = [], []
        for repeat in range(repeats):
            clean, raw, jitter, noise_rms = synthesize(scenario, rng, n, onset, config["sensor_dither_rms_ru"])
            truth = baseline_core(clean, onset)
            clean_b0, _, _ = b0_epoch(clean, onset, np.ones_like(clean, dtype=bool), taps)
            scenario_truth.append(truth)
            scenario_filtered_truth.append(clean_b0)
            valid, _ = hard_mask(raw)
            rejected_trial = not valid[:, onset + SUPPORT_START:onset + SUPPORT_STOP].all()
            if rejected_trial:
                rejected += 1
            else:
                b0, _, _ = b0_epoch(raw, onset, valid, taps)
                raw_core = baseline_core(raw, onset)
                for channel in range(3):
                    for method, values in (("raw", raw_core[channel]), ("B0_clean", clean_b0[channel]), ("B0", b0[channel])):
                        rows.append({"scenario": scenario["id"], "repeat": repeat, "channel": channel,
                                     "method": method, "noise_rms_ru": noise_rms, "jitter_s": jitter,
                                     **waveform_metrics(values, truth[channel], scenario, jitter, noise_rms, config)})
                    residual = b0[channel] - clean_b0[channel]
                    rows[-1]["residual_nrmse_to_B0_clean"] = (
                        float(np.linalg.norm(residual) / np.linalg.norm(clean_b0[channel]))
                        if np.linalg.norm(clean_b0[channel]) > 1e-12 else None
                    )
        truth_rows.append(np.stack(scenario_truth))
        filtered_truth_rows.append(np.stack(scenario_filtered_truth))
        scenario_rows = [row for row in rows if row["scenario"] == scenario["id"]]
        for method in ("raw", "B0_clean", "B0"):
            selected = [row for row in scenario_rows if row["method"] == method]
            def median(field):
                vals = [row[field] for row in selected if row[field] is not None]
                return float(np.median(vals)) if vals else None
            summary.append({"scenario": scenario["id"], "method": method, "repeats": repeats,
                            "accepted_trials": repeats - rejected, "rejected_trials": rejected,
                            "rejection_rate": rejected / repeats, "measurements": len(selected),
                            "median_abs_amplitude_error_ru": median_abs(selected, "amplitude_error_ru"),
                            "median_abs_latency_error_samples": median_abs(selected, "latency_error_samples"),
                            "median_nrmse": median("nrmse"), "median_correlation": median("correlation"),
                            "median_rmse_ru": median("rmse_ru"),
                            "false_positive_rate": float(np.mean([row["false_positive_peak"] for row in selected]))
                            if selected and selected[0]["false_positive_peak"] is not None else None,
                            "median_residual_nrmse_to_B0_clean": median("residual_nrmse_to_B0_clean")
                            if method == "B0" else None})
    return rows, summary, np.stack(truth_rows), np.stack(filtered_truth_rows)


def median_abs(rows, field):
    vals = [abs(row[field]) for row in rows if row[field] is not None]
    return float(np.median(vals)) if vals else None


def write_csv(path, rows):
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def draw_frequency(frequency, gain_db, summary, output_dir):
    fig, axes = plt.subplots(1, 2, figsize=(183 / 25.4, 65 / 25.4), layout="constrained")
    axes[0].plot(frequency, gain_db, color=CATEGORICAL[0], linewidth=1.3)
    axes[0].axvline(30, color=ACCENT_RED, linestyle="--", linewidth=0.8)
    axes[0].set(xlim=(0, 80), ylim=(-100, 5), xlabel="Frequency (Hz)", ylabel="Gain (dB)", title="Full response")
    axes[0].text(31, -8, "30 Hz: −6 dB", color=ACCENT_RED, fontsize=7)
    axes[1].plot(frequency, gain_db, color=CATEGORICAL[0], linewidth=1.3)
    axes[1].set(xlim=(1, 20), ylim=(-0.01, 0.03), xlabel="Frequency (Hz)", ylabel="Gain (dB)", title="1–20 Hz passband")
    axes[1].text(0.02, 0.95, f"Ripple {summary['passband_1_20_ripple_db']:.3f} dB",
                 transform=axes[1].transAxes, color=BLACK, fontsize=7)
    save_cns_figure(fig, str(output_dir / "fir_frequency_response"))
    plt.close(fig)


def draw_impulse(taps, output_dir):
    fig, ax = plt.subplots(figsize=(89 / 25.4, 65 / 25.4), layout="constrained")
    lag = np.arange(-H, H + 1)
    ax.plot(lag, taps, color=CATEGORICAL[0], linewidth=1.2)
    ax.axhline(0, color=GREY, linewidth=0.5)
    ax.set(xlim=(-H, H), xlabel="Lag (samples)", ylabel="Coefficient", title="65-tap symmetric impulse response")
    save_cns_figure(fig, str(output_dir / "fir_impulse_response"))
    plt.close(fig)


def validate(config_path, b0_path, output_dir):
    if output_dir.exists():
        raise FileExistsError(f"output exists: {output_dir}; choose a new validation directory")
    config = json.loads(config_path.read_text())
    if config["schema_version"] != "Q1-B0-synthetic-v1":
        raise ValueError("unexpected scenario schema")
    ids = [scenario["id"] for scenario in config["scenarios"]]
    if len(ids) != len(set(ids)) or not ids:
        raise ValueError("scenario IDs must be nonempty and unique")
    with np.load(b0_path, allow_pickle=False) as artifact:
        taps = artifact["taps"]
    if taps.shape != (2 * H + 1,) or not np.allclose(taps, taps[::-1], atol=1e-15):
        raise ValueError("B0 artifact taps differ from model contract")
    frequency, gain, gain_db, freq_summary = frequency_response(taps)
    rows, summary, truth, filtered_truth = run_scenarios(config, taps)
    output_dir.mkdir(parents=True)
    write_csv(output_dir / "frequency_response.csv", [
        {"frequency_hz": float(f), "gain": float(g), "gain_db": float(db)}
        for f, g, db in zip(frequency, gain, gain_db)
    ])
    (output_dir / "frequency_summary.json").write_text(json.dumps(freq_summary, indent=2) + "\n")
    write_csv(output_dir / "trial_metrics.csv", rows)
    write_csv(output_dir / "scenario_summary.csv", summary)
    np.savez_compressed(output_dir / "clean_truth.npz", clean_core=truth, b0_clean_core=filtered_truth,
                        scenario_ids=np.asarray(ids), time_s=np.arange(-51, 256) / FS)
    draw_frequency(frequency, gain_db, freq_summary, output_dir)
    draw_impulse(taps, output_dir)
    manifest = {
        "schema_version": "Q1-B0-validation-v1", "simulation_only": True,
        "command": (" ".join(f"{key}={os.environ[key]}" for key in ("MPLCONFIGDIR", "XDG_CACHE_HOME") if key in os.environ)
                    + f" python code/q1_b0_validate.py --config {config_path} --b0 {b0_path} --output-dir {output_dir}").strip(),
        "parameters": {"repeats_per_scenario": config["repeats_per_scenario"], "seed": config["seed"],
                       "scenario_count": len(ids), "noise": config["noise_model"],
                       "peak_search_radius_s": config["peak_search_radius_s"],
                       "no_peak_window_s": config["no_peak_window_s"],
                       "no_peak_threshold_sigma": config["no_peak_threshold_sigma"],
                       "no_peak_threshold_floor_ru": config["no_peak_threshold_floor_ru"],
                       "sensor_dither_rms_ru": config["sensor_dither_rms_ru"]},
        "input_sha256": {str(config_path): sha256(config_path), str(b0_path): sha256(b0_path)},
        "script_sha256": sha256(Path(__file__)), "preprocess_script_sha256": sha256(Path(__file__).with_name("q1_preprocess.py")),
        "python": platform.python_version(), "numpy": np.__version__, "scipy": scipy_version,
        "matplotlib": mpl.__version__, "exclusion": "clipped trials: rejection only, no reconstruction metrics",
    }
    (output_dir / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
    return freq_summary, summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=Path("code/q1_b0_scenarios.json"))
    parser.add_argument("--b0", type=Path, default=Path("code/outputs/q1_b0/epochs_b0.npz"))
    parser.add_argument("--output-dir", type=Path, default=Path("code/outputs/q1_b0_validation"))
    args = parser.parse_args()
    frequency_summary, results = validate(args.config, args.b0, args.output_dir)
    print(json.dumps({"frequency": frequency_summary, "scenarios": len(results) // 3}, indent=2))
