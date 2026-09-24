"""Small contract checks for the Question 1 audit, without project data."""

import copy
import unittest

import numpy as np

from q1_audit import CHANNELS, apply_qc, build_rows, cue_events, hard_mask, make_folds


class AuditContractTest(unittest.TestCase):
    def test_cue_runs_and_task1_unknown_behavior(self):
        data = np.zeros((10, 5000), dtype=float)
        data[9] = np.arange(5000) / 256
        data[7, 1000:1052] = -1
        data[7, 3000:3053] = 1
        data[8, 1600:1700] = 1
        events, anomalies = cue_events(data[7])
        self.assertEqual([(e["onset"], e["offset"], e["sign"]) for e in events],
                         [(1000, 1052, -1), (3000, 3053, 1)])
        self.assertEqual(anomalies, [])
        rows, quality, _, _ = build_rows("VisualCogA_Task-1", data)
        self.assertEqual(rows[0]["behavior_semantics"], "unknown")
        self.assertEqual(rows[0]["response_marker_index"], "")
        self.assertEqual((rows[0]["support_start"], rows[0]["support_stop"]), (840, 1416))
        self.assertEqual(len(quality), 6)
        other, _, _, _ = build_rows("VisualCogA_Task-2", data)
        self.assertNotEqual(rows[0]["trial_id"], other[0]["trial_id"])

    def test_hard_faults_include_short_and_long_clip(self):
        raw = np.zeros((3, 5000), dtype=float)
        raw[0, 1000] = 1000
        raw[1, 1100:1180] = -1000
        mask, flats = hard_mask(raw)
        self.assertFalse(mask[0, 1000])
        self.assertFalse(mask[1, 1179])
        self.assertTrue(any(f["channel"] == "F3" and f["offset"] - f["onset"] == 80 for f in flats))
        self.assertFalse(mask[2].any())  # a 5000-sample flatline is invalid
        data = np.zeros((10, 5000), dtype=float)
        data[:3] = np.random.default_rng(7).normal(size=(3, 5000))
        data[7, 1000:1050] = -1
        data[7, 3000:3050] = 1
        data[0, 1000] = 1000
        data[1, 3000:3080] = -1000
        _, quality, _, _ = build_rows("VisualCogA_Task-1", data)
        self.assertIn("clip_or_out_of_range", quality[0]["rejection_reasons"])
        self.assertIn("flat_run", quality[4]["rejection_reasons"])

    def test_fold_support_and_test_data_isolation(self):
        rng = np.random.default_rng(20260924)
        raw = rng.normal(size=(3, 100_000))
        events, quality = [], []
        for i in range(100):
            onset = 500 + 990 * i
            trial = f"r:{i:03d}"
            events.append({"trial_id": trial, "support_start": onset - 160,
                           "support_stop": onset + 416})
            for channel in CHANNELS:
                quality.append({"trial_id": trial, "channel": channel, "hard_ok": True,
                                "ptp": 3.0 + i / 100, "jump": 2.0 + i / 100,
                                "baseline_scale": 1.0 + i / 100, "rejection_reasons": ""})
        folds = make_folds(events, quality, raw)
        self.assertEqual(len(folds), 5)
        for fold in folds:
            train = [events[int(t[-3:])] for t in fold["train_ids"]]
            test = [events[int(t[-3:])] for t in fold["test_ids"]]
            self.assertFalse(set(fold["train_ids"]) & set(fold["test_ids"]))
            self.assertTrue(all(a["support_stop"] <= b["support_start"] or
                                b["support_stop"] <= a["support_start"]
                                for a in train for b in test))
        fit_before = folds[0]["qc_parameters"]
        changed = raw.copy()
        for event in events[:20]:
            changed[:, event["support_start"]:event["support_stop"]] += 1e9
        changed_quality = copy.deepcopy(quality)
        for row in changed_quality:
            if int(row["trial_id"][-3:]) < 20:
                row["ptp"] += 1e9
                row["jump"] += 1e9
        fit_after = make_folds(events, changed_quality, changed)[0]["qc_parameters"]
        self.assertEqual(fit_before, fit_after)
        self.assertEqual(apply_qc(quality[:3], fit_before)["r:000"], [])


if __name__ == "__main__":
    unittest.main()
