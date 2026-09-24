"""Fixed Q1 B0 FIR and per-trial baseline; no ERP or model fitting."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
from scipy import __version__ as scipy_version
from scipy.signal import firwin

from q1_audit import CHANNELS, FS, H, RECORDS, SUPPORT_START, SUPPORT_STOP, hard_mask, load_record

EXTENDED = 512
CORE = slice(77, 384)
BASELINE = slice(77, 128)


def b0_epoch(raw: np.ndarray, onset: int, valid: np.ndarray, taps: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Return (3×307 core, 3×512 extended, 3 baseline constants) in raw units."""
    start, stop = onset + SUPPORT_START, onset + SUPPORT_STOP
    if raw.ndim != 2 or raw.shape[0] != len(CHANNELS) or valid.shape != raw.shape:
        raise ValueError("expected matching 3×N raw and hard-valid mask")
    if taps.shape != (2 * H + 1,) or start < 0 or stop > raw.shape[1]:
        raise ValueError("invalid FIR taps or raw input support")
    if not valid[:, start:stop].all():
        raise ValueError("hard-invalid sample in FIR input support; trial rejected")
    support = raw[:, start:stop]
    filtered = np.stack([np.convolve(row, taps, mode="valid") for row in support])
    if filtered.shape != (len(CHANNELS), EXTENDED):
        raise AssertionError("FIR output support mismatch")
    baseline = filtered[:, BASELINE].mean(axis=1)
    extended = filtered - baseline[:, None]
    return extended[:, CORE], extended, baseline


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def preprocess(data_dir: Path, audit_dir: Path, output_dir: Path) -> dict:
    if output_dir.exists():
        raise FileExistsError(f"output exists: {output_dir}; choose a new run directory")
    audit_files = ("events.csv", "quality.csv", "splits.json", "manifest.json")
    audit_manifest = json.loads((audit_dir / "manifest.json").read_text())
    if audit_manifest["schema_version"] != "Q1-audit-v1" or audit_manifest["config"]["support"] != [SUPPORT_START, SUPPORT_STOP]:
        raise ValueError("audit schema or FIR support differs from B0 contract")
    with (audit_dir / "events.csv").open(newline="", encoding="utf-8") as handle:
        events = list(csv.DictReader(handle))
    with (audit_dir / "quality.csv").open(newline="", encoding="utf-8") as handle:
        quality = list(csv.DictReader(handle))
    splits = json.loads((audit_dir / "splits.json").read_text())
    ids = [event["trial_id"] for event in events]
    if len(ids) != 400 or len(set(ids)) != 400:
        raise ValueError("expected 400 globally unique audit trial IDs")
    quality_by_id: dict[str, list[dict]] = {}
    for row in quality:
        quality_by_id.setdefault(row["trial_id"], []).append(row)
    if set(quality_by_id) != set(ids) or any(
        {row["channel"] for row in quality_by_id[trial]} != set(CHANNELS) or len(quality_by_id[trial]) != 3
        for trial in ids
    ):
        raise ValueError("audit quality rows do not map 1:3 onto events")
    taps = firwin(2 * H + 1, 30, fs=FS, window="hamming")
    if not np.isclose(taps.sum(), 1, atol=1e-12) or not np.allclose(taps, taps[::-1], atol=1e-15):
        raise AssertionError("B0 FIR must be normalized and symmetric")

    output_ids, record_ids, signs, cores, baselines, test_folds, outer_pass = [], [], [], [], [], [], []
    summary = {}
    for filename in RECORDS:
        path = data_dir / filename
        if _sha256(path) != audit_manifest["source_sha256"][filename]:
            raise ValueError(f"{filename}: source differs from audited MAT")
        data, _ = load_record(path)
        raw = data[:3]
        valid, _ = hard_mask(raw)
        record = path.stem
        record_events = [event for event in events if event["record_id"] == record]
        if len(record_events) != 100:
            raise ValueError(f"{record}: expected 100 audited events")
        fold_of, pass_ids = {}, set()
        if len(splits[record]) != 5:
            raise ValueError(f"{record}: expected five outer folds")
        for fold in splits[record]:
            tests = fold["test_ids"]
            passed = set(fold["test_quality_pass"])
            if not passed <= set(tests) or any(trial in fold_of for trial in tests):
                raise ValueError(f"{record}: invalid outer test assignment")
            fold_of.update({trial: fold["fold"] for trial in tests})
            pass_ids.update(passed)
        if set(fold_of) != {event["trial_id"] for event in record_events}:
            raise ValueError(f"{record}: incomplete outer test assignment")
        kept = kept_pass = 0
        for event in record_events:
            trial = event["trial_id"]
            hard_ok = all(row["hard_ok"] == "True" for row in quality_by_id[trial])
            if trial in pass_ids and not hard_ok:
                raise ValueError(f"{trial}: fold accepts a hard-rejected trial")
            if not hard_ok:
                continue
            onset = int(event["cue_onset"])
            if (int(event["support_start"]), int(event["support_stop"])) != (onset + SUPPORT_START, onset + SUPPORT_STOP):
                raise ValueError(f"{trial}: audited support differs from B0 contract")
            core, _, baseline = b0_epoch(raw, onset, valid, taps)
            output_ids.append(trial)
            record_ids.append(record)
            signs.append(int(event["cue_sign"]))
            cores.append(core)
            baselines.append(baseline)
            test_folds.append(fold_of[trial])
            outer_pass.append(trial in pass_ids)
            kept += 1
            kept_pass += trial in pass_ids
        summary[record] = {"hard_pass_epochs": kept, "outer_test_quality_pass_epochs": kept_pass}

    output_dir.mkdir(parents=True)
    np.savez_compressed(
        output_dir / "epochs_b0.npz",
        epochs=np.stack(cores), trial_ids=np.asarray(output_ids), record_ids=np.asarray(record_ids),
        cue_sign=np.asarray(signs, dtype=np.int8), time_s=np.arange(-51, 256) / FS,
        baseline_ru=np.stack(baselines), outer_test_fold=np.asarray(test_folds, dtype=np.int8),
        outer_test_quality_pass=np.asarray(outer_pass, dtype=bool), taps=taps,
    )
    manifest = {
        "schema_version": "Q1-B0-v1", "unit": "raw_record_units", "method": "B0",
        "selection": "hard-pass only; intersect trial_ids with fold train_quality_pass/test_quality_pass before ERP",
        "config": {"fs": FS, "fir_taps": len(taps), "cutoff_hz": 30, "window": "hamming",
                   "support": [SUPPORT_START, SUPPORT_STOP], "baseline_relative": [-51, 0],
                   "core_relative": [-51, 256], "causal": False},
        "command": f"python code/q1_preprocess.py --data-dir {data_dir} --audit-dir {audit_dir} --output-dir {output_dir}",
        "python": sys.version.split()[0], "numpy": np.__version__, "scipy": scipy_version,
        "audit_sha256": {name: _sha256(audit_dir / name) for name in audit_files},
        "script_sha256": _sha256(Path(__file__)), "summary": summary,
    }
    (output_dir / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=Path("data"))
    parser.add_argument("--audit-dir", type=Path, default=Path("code/outputs/q1_audit"))
    parser.add_argument("--output-dir", type=Path, default=Path("code/outputs/q1_b0"))
    args = parser.parse_args()
    print(json.dumps(preprocess(args.data_dir, args.audit_dir, args.output_dir), ensure_ascii=False, indent=2))
