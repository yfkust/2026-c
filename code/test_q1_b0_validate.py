"""Deterministic checks for B0 frequency and frozen pure-simulation metrics."""

import json
import unittest
from pathlib import Path

import numpy as np
from scipy.signal import firwin

from q1_audit import FS, H, SUPPORT_START, SUPPORT_STOP, hard_mask
from q1_b0_validate import frequency_response, run_scenarios, synthesize, waveform_metrics


CONFIG = json.loads((Path(__file__).with_name("q1_b0_scenarios.json")).read_text())


class B0ValidationTest(unittest.TestCase):
    def test_frequency_gain_and_cutoff_definition(self):
        taps = firwin(2 * H + 1, 30, fs=FS, window="hamming")
        frequency, gain, _, summary = frequency_response(taps)
        self.assertEqual(len(frequency), 8192)
        self.assertEqual(len(gain), 8192)
        self.assertAlmostEqual(summary["taps_sum"], 1, places=12)
        self.assertLess(summary["symmetric_max_abs_error"], 1e-15)
        self.assertAlmostEqual(summary["points_gain"]["30"], 0.5, delta=0.01)
        self.assertGreater(summary["points_gain"]["20"], summary["points_gain"]["30"])
        self.assertLess(summary["points_gain"]["50"], 0.01)

    def test_frozen_scenarios_and_clip_boundary(self):
        scenarios = CONFIG["scenarios"]
        self.assertEqual(len(scenarios), 18)
        self.assertEqual(CONFIG["repeats_per_scenario"], 100)
        by_id = {scenario["id"]: scenario for scenario in scenarios}
        self.assertEqual(len(by_id), 18)
        for name, rejected in (("clip_one_sample", True), ("clip_80_samples", True),
                               ("clip_outside_support", False)):
            raw_scenario = by_id[name]
            _, raw, _, _ = synthesize(raw_scenario, np.random.default_rng(3),
                                      CONFIG["samples"], CONFIG["cue_onset"], CONFIG["sensor_dither_rms_ru"])
            valid, _ = hard_mask(raw)
            onset = CONFIG["cue_onset"]
            self.assertEqual(not valid[:, onset + SUPPORT_START:onset + SUPPORT_STOP].all(), rejected)

    def test_no_peak_metrics_have_no_peak_latency(self):
        scenario = next(s for s in CONFIG["scenarios"] if s["id"] == "no_peak_white")
        zero = np.zeros(307)
        metrics = waveform_metrics(zero, zero, scenario, 0.0, 1.0, CONFIG)
        self.assertIsNone(metrics["amplitude_error_ru"])
        self.assertIsNone(metrics["latency_error_samples"])
        self.assertIsNone(metrics["nrmse"])
        self.assertFalse(metrics["false_positive_peak"])
        # The complete frozen scenario should produce 100 accepted trials, not a fitted result.
        taps = firwin(2 * H + 1, 30, fs=FS, window="hamming")
        small = {**CONFIG, "scenarios": [scenario]}
        rows, summary, truth, _ = run_scenarios(small, taps)
        self.assertEqual(truth.shape, (1, 100, 3, 307))
        self.assertEqual(len(rows), 900)
        self.assertTrue(all(row["rejected_trials"] == 0 for row in summary))


if __name__ == "__main__":
    unittest.main()
