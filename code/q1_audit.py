"""Question 1 event, quality, and leakage-aware split audit (no EEG filtering)."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
from scipy import __version__ as scipy_version
from scipy.io import loadmat

FS = 256
CHANNELS = ("Fz", "F3", "F4")
H = 32  # 65-tap candidate FIR; audit only its raw input support
SUPPORT_START = -128 - H
SUPPORT_STOP = 384 + H  # exclusive
BASELINE = slice(-51, 0)
FLAT_SAMPLES = 64
KAPPA = 6.0
METRICS = ("ptp", "jump", "baseline_scale")
RECORDS = (
    "VisualCogA_Task-1.mat",
    "VisualCogA_Task-2.mat",
    "VisualCogB_Task-1.mat",
    "VisualCogB_Task-2.mat",
)


def runs(values: np.ndarray) -> list[tuple[int, int, float]]:
    """Maximal nonzero constant-value runs, with exclusive end indices."""
    changes = np.flatnonzero(np.diff(values) != 0) + 1
    edges = np.r_[0, changes, len(values)]
    return [
        (int(a), int(b), float(values[a]))
        for a, b in zip(edges[:-1], edges[1:])
        if values[a] != 0
    ]


def cue_events(cue: np.ndarray) -> tuple[list[dict], list[dict]]:
    events, anomalies = [], []
    for start, stop, value in runs(cue):
        reason = None
        if value not in (-1.0, 1.0):
            reason = "unknown_cue_code"
        elif start == 0:
            reason = "left_censored"
        elif stop == len(cue):
            reason = "right_censored"
        elif cue[start - 1] != 0 or cue[stop] != 0:
            reason = "invalid_transition"
        row = {"onset": start, "offset": stop, "sign": int(value) if value in (-1, 1) else value}
        if reason:
            anomalies.append({**row, "reason": reason})
        else:
            events.append(row)
    return events, anomalies


def load_record(path: Path) -> tuple[np.ndarray, list[str]]:
    mat = loadmat(path, squeeze_me=True)
    if not {"data", "DataLabel", "SampleRate"}.issubset(mat):
        raise ValueError(f"{path}: missing required MAT variables")
    data = np.asarray(mat["data"])
    labels = [str(x).strip() for x in np.atleast_1d(mat["DataLabel"])]
    if data.ndim != 2 or data.shape[0] != 10 or data.shape[1] < 2:
        raise ValueError(f"{path}: expected 10×N data, got {data.shape}")
    if len(labels) != 10 or tuple(labels[:3]) != CHANNELS:
        raise ValueError(f"{path}: unexpected channel labels: {labels}")
    if not labels[7].startswith("VisCue") or not labels[9].startswith("TimeStamp"):
        raise ValueError(f"{path}: unexpected event/timestamp labels")
    if ("Task-1" in path.name and not labels[8].startswith("Action")) or (
        "Task-2" in path.name and not labels[8].startswith("TgtAct")
    ):
        raise ValueError(f"{path}: unexpected channel 9 label")
    if float(np.asarray(mat["SampleRate"]).item()) != FS:
        raise ValueError(f"{path}: unexpected sample rate")
    if not np.issubdtype(data.dtype, np.number) or not np.isfinite(data).all():
        raise ValueError(f"{path}: nonfinite or nonnumeric data")
    time = data[9]
    if not np.allclose(np.diff(time), 1 / FS, rtol=0, atol=1e-9):
        raise ValueError(f"{path}: irregular timestamps")
    return data, labels


def robust_scale(values: np.ndarray) -> float:
    return float(1.4826 * np.median(np.abs(values - np.median(values))))


def hard_mask(raw: np.ndarray) -> tuple[np.ndarray, list[dict]]:
    mask = np.isfinite(raw) & (np.abs(raw) < 1000)
    flats = []
    for channel, row in enumerate(raw):
        changes = np.flatnonzero(np.diff(row) != 0) + 1
        edges = np.r_[0, changes, len(row)]
        for start, stop in zip(edges[:-1], edges[1:]):
            if stop - start >= FLAT_SAMPLES:
                mask[channel, start:stop] = False
                flats.append({"channel": CHANNELS[channel], "onset": int(start), "offset": int(stop), "value": float(row[start])})
    return mask, flats


def build_rows(name: str, data: np.ndarray) -> tuple[list[dict], list[dict], list[dict], np.ndarray]:
    cue, act, time = data[7], data[8], data[9]
    events, anomalies = cue_events(cue)
    mask, flats = hard_mask(data[:3])
    state_runs = runs(act)
    event_rows, quality_rows = [], []
    for i, event in enumerate(events):
        onset = event["onset"]
        stop = events[i + 1]["onset"] if i + 1 < len(events) else len(cue)
        state = [
            {"onset": a, "offset": b, "code": value}
            for a, b, value in state_runs if onset <= a < stop
        ]
        marker = [s for s in state if abs(s["code"]) == 2]
        support_a, support_b = onset + SUPPORT_START, onset + SUPPORT_STOP
        boundary = support_a >= 0 and support_b <= len(cue)
        state_overlap = bool(np.any(act[support_a:support_b] != 0)) if boundary else False
        reasons = []
        if not boundary:
            reasons.append("support_boundary")
        if state_overlap:
            reasons.append("state9_overlap")
        event_rows.append({
            "record_id": name, "task": 1 if "Task-1" in name else 2,
            "trial_id": f"{name}:{i:03d}", "trial_index": i,
            "cue_onset": onset, "cue_offset": event["offset"],
            "cue_time_s": float(time[onset]), "cue_duration_s": (event["offset"] - onset) / FS,
            "cue_sign": event["sign"], "support_start": support_a,
            "support_stop": support_b, "state9_runs": json.dumps(state, separators=(",", ":")),
            "state9_overlap": state_overlap,
            "response_marker_index": marker[0]["onset"] if len(marker) == 1 and "Task-2" in name else "",
            "behavior_semantics": "unknown" if "Task-1" in name else "candidate_target_and_response_marker",
        })
        for channel, raw in enumerate(data[:3]):
            row_reasons = list(reasons)
            clip = flat = 0
            q = {"ptp": None, "jump": None, "baseline_scale": None, "drift_abs": None}
            if boundary:
                segment = raw[support_a:support_b]
                clip = int(np.count_nonzero(np.abs(segment) >= 1000))
                flat = sum(max(0, min(b, support_b) - max(a, support_a)) for f in flats
                           for a, b in [(f["onset"], f["offset"])] if f["channel"] == CHANNELS[channel])
                if clip:
                    row_reasons.append("clip_or_out_of_range")
                if flat:
                    row_reasons.append("flat_run")
                if np.all(mask[channel, support_a:support_b]):
                    q["ptp"] = float(np.ptp(segment))
                    q["jump"] = float(np.max(np.abs(np.diff(segment))))
                    q["baseline_scale"] = robust_scale(raw[onset - 51:onset])
                    q["drift_abs"] = float(abs(np.median(raw[onset - 128:onset + 384])))
            quality_rows.append({
                "record_id": name, "trial_id": event_rows[-1]["trial_id"],
                "channel": CHANNELS[channel], "hard_ok": not row_reasons,
                "clip_samples_in_support": clip, "flat_samples_in_support": flat,
                **q, "rejection_reasons": "|".join(sorted(set(row_reasons))),
            })
    return event_rows, quality_rows, anomalies, mask


def fit_qc(training: list[dict], raw: np.ndarray, supports: dict[str, tuple[int, int]]) -> dict:
    """Fit every threshold using training trials only. Never reads test rows."""
    fitted = {}
    for channel, label in enumerate(CHANNELS):
        rows = [r for r in training if r["channel"] == label and r["hard_ok"]]
        spans = [raw[channel, supports[r["trial_id"]][0]:supports[r["trial_id"]][1]] for r in rows]
        scale = robust_scale(np.concatenate(spans)) if spans else 0.0
        if scale <= 0:
            fitted[label] = {"epsilon": None, "status": "degenerate_channel", "metrics": {}}
            continue
        epsilon = 1e-6 * scale
        metric_fit = {}
        for metric in METRICS:
            vals = np.log(np.array([r[metric] for r in rows]) + epsilon)
            mad = robust_scale(vals)
            metric_fit[metric] = {"median": float(np.median(vals)), "scale": mad,
                                  "status": "ok" if mad > 0 else "degenerate_qc_scale"}
        fitted[label] = {"epsilon": epsilon, "status": "ok", "metrics": metric_fit}
    return fitted


def apply_qc(rows: list[dict], fitted: dict) -> dict[str, list[str]]:
    reasons: dict[str, list[str]] = {}
    for row in rows:
        trial = row["trial_id"]
        reasons.setdefault(trial, [])
        if not row["hard_ok"]:
            reasons[trial].extend(filter(None, row["rejection_reasons"].split("|")))
            continue
        cfg = fitted[row["channel"]]
        if cfg["status"] != "ok":
            reasons[trial].append("degenerate_channel")
            continue
        for metric in METRICS:
            cfg_m = cfg["metrics"][metric]
            if cfg_m["status"] != "ok":
                continue
            z = (np.log(row[metric] + cfg["epsilon"]) - cfg_m["median"]) / cfg_m["scale"]
            if z > KAPPA:
                reasons[trial].append(f"soft_qc:{row['channel']}:{metric}")
    return {trial: sorted(set(r)) for trial, r in reasons.items()}


def make_folds(events: list[dict], quality: list[dict], raw: np.ndarray) -> list[dict]:
    if len(events) != 100:
        raise ValueError(f"expected 100 cue trials for five fixed 20-trial blocks, got {len(events)}")
    by_trial = {e["trial_id"]: (e["support_start"], e["support_stop"]) for e in events}
    folds = []
    for fold in range(5):
        test_idx = set(range(20 * fold, 20 * (fold + 1)))
        purged_idx = {j for j in (20 * fold - 1, 20 * (fold + 1)) if 0 <= j < 100}
        train_idx = [i for i in range(100) if i not in test_idx | purged_idx]
        test_spans = [by_trial[events[i]["trial_id"]] for i in sorted(test_idx)]
        overlap_idx = [i for i in train_idx if any(
            by_trial[events[i]["trial_id"]][0] < b and a < by_trial[events[i]["trial_id"]][1]
            for a, b in test_spans
        )]
        train_idx = [i for i in train_idx if i not in overlap_idx]
        train_ids = [events[i]["trial_id"] for i in train_idx]
        test_ids = [events[i]["trial_id"] for i in sorted(test_idx)]
        hard_train_ids = {t for t in train_ids if all(r["hard_ok"] for r in quality if r["trial_id"] == t)}
        fit = fit_qc([r for r in quality if r["trial_id"] in hard_train_ids], raw, by_trial)
        evaluated = apply_qc([r for r in quality if r["trial_id"] in set(train_ids + test_ids)], fit)
        folds.append({
            "fold": fold, "train_ids": train_ids, "test_ids": test_ids,
            "purged_ids": [events[i]["trial_id"] for i in sorted(purged_idx | set(overlap_idx))],
            "qc_fit_trial_ids": [t for t in train_ids if t in hard_train_ids],
            "qc_parameters": fit, "trial_reasons": evaluated,
            "train_quality_pass": [t for t in train_ids if not evaluated[t]],
            "test_quality_pass": [t for t in test_ids if not evaluated[t]],
        })
    return folds


def write_csv(path: Path, rows: list[dict]) -> None:
    if not rows:
        return
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def audit(data_dir: Path, output_dir: Path) -> dict:
    if output_dir.exists():
        raise FileExistsError(f"output exists: {output_dir}; choose a new run directory")
    loaded = []
    for filename in RECORDS:
        path = data_dir / filename
        data, labels = load_record(path)
        events, quality, anomalies, _ = build_rows(filename[:-4], data)
        folds = make_folds(events, quality, data[:3])
        loaded.append((path, data, labels, events, quality, anomalies, folds))
    output_dir.mkdir(parents=True)
    event_rows, quality_rows, splits, summary = [], [], {}, {}
    for path, data, labels, events, quality, anomalies, folds in loaded:
        key = path.stem
        event_rows.extend(events)
        quality_rows.extend(quality)
        splits[key] = folds
        hard_ok = {e["trial_id"] for e in events if all(
            r["hard_ok"] for r in quality if r["trial_id"] == e["trial_id"]
        )}
        summary[key] = {"samples": int(data.shape[1]), "cue_count": len(events),
                        "cue_left": sum(e["cue_sign"] == -1 for e in events),
                        "cue_right": sum(e["cue_sign"] == 1 for e in events),
                        "hard_quality_pass": len(hard_ok),
                        "outer_test_quality_pass": [len(f["test_quality_pass"]) for f in folds],
                        "cue_anomalies": anomalies}
    write_csv(output_dir / "events.csv", event_rows)
    write_csv(output_dir / "quality.csv", quality_rows)
    (output_dir / "splits.json").write_text(json.dumps(splits, ensure_ascii=False, indent=2) + "\n")
    (output_dir / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n")
    manifest = {
        "schema_version": "Q1-audit-v1", "model_design": "Q1-design-v1", "python": sys.version.split()[0],
        "numpy": np.__version__, "scipy": scipy_version,
        "command": "python code/q1_audit.py --data-dir data --output-dir " + str(output_dir),
        "config": {"fs": FS, "h": H, "support": [SUPPORT_START, SUPPORT_STOP],
                   "flat_samples": FLAT_SAMPLES, "kappa": KAPPA, "block_trials": 20, "purge_trials": 1},
        "source_sha256": {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p, *_ in loaded},
        "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    }
    (output_dir / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=Path("data"))
    parser.add_argument("--output-dir", type=Path, default=Path("code/outputs/q1_audit"))
    args = parser.parse_args()
    print(json.dumps(audit(args.data_dir, args.output_dir), ensure_ascii=False, indent=2))
