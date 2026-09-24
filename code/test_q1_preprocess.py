"""Synthetic B0 contract checks; no project EEG or formal experiment."""

import unittest

import numpy as np
from scipy.signal import firwin

from q1_audit import FS, H, SUPPORT_START, SUPPORT_STOP, hard_mask
from q1_preprocess import BASELINE, CORE, b0_epoch


class B0ContractTest(unittest.TestCase):
    def setUp(self):
        self.taps = firwin(2 * H + 1, 30, fs=FS, window="hamming")
        self.onset = 1000

    def test_support_indices_and_erp_ready_shape(self):
        raw = np.zeros((3, 3000))
        raw[0, self.onset + SUPPORT_START] = 1
        raw[1, self.onset + SUPPORT_STOP - 1] = 1
        core, extended, baseline = b0_epoch(raw, self.onset, np.ones_like(raw, dtype=bool), self.taps)
        self.assertEqual((core.shape, extended.shape, baseline.shape), ((3, 307), (3, 512), (3,)))
        self.assertAlmostEqual(extended[0, 0], self.taps[0])
        self.assertAlmostEqual(extended[1, -1], self.taps[-1])
        np.testing.assert_array_equal(core, extended[:, CORE])
        np.testing.assert_allclose(extended[:, BASELINE].mean(axis=1), 0, atol=1e-14)
        for channel, j in ((0, 0), (1, 511)):
            k = j - 128
            direct = sum(self.taps[lag + H] * raw[channel, self.onset + k - lag]
                         for lag in range(-H, H + 1))
            self.assertAlmostEqual(extended[channel, j] + baseline[channel], direct)

    def test_synthetic_amplitude_latency_waveform_and_50hz(self):
        n = np.arange(3000)
        gaussian = 4 * np.exp(-0.5 * ((n - (self.onset + 90)) / 12) ** 2)
        raw = np.zeros((3, 3000))
        raw[0] = 7 + gaussian
        raw[1] = 2 + np.sin(2 * np.pi * 50 * (n - self.onset) / FS)
        core, extended, _ = b0_epoch(raw, self.onset, np.ones_like(raw, dtype=bool), self.taps)
        clean = gaussian[self.onset - 51:self.onset + 256]
        amplitude_error = float(core[0].max() - clean.max())
        latency_error_samples = int(np.argmax(core[0]) - np.argmax(clean))
        waveform_nrmse = float(np.linalg.norm(core[0] - clean) / np.linalg.norm(clean))
        self.assertGreater(abs(amplitude_error), 1e-4)
        self.assertLess(abs(amplitude_error), 0.2)
        self.assertEqual(latency_error_samples, 0)
        self.assertGreater(waveform_nrmse, 0)
        self.assertLess(waveform_nrmse, 0.05)
        self.assertLess(np.sqrt(np.mean(core[1, 51:251] ** 2)), 0.05)
        np.testing.assert_allclose(extended[:, BASELINE].mean(axis=1), 0, atol=1e-12)

    def test_saturation_rejected_and_no_other_trial_input(self):
        rng = np.random.default_rng(20260924)
        raw = rng.normal(size=(3, 4000))
        raw[0, self.onset + 40] = 1000
        valid, _ = hard_mask(raw)
        with self.assertRaisesRegex(ValueError, "hard-invalid"):
            b0_epoch(raw, self.onset, valid, self.taps)
        raw[0, self.onset + 40] = 0
        valid, _ = hard_mask(raw)
        original = b0_epoch(raw, self.onset, valid, self.taps)[0]
        changed = raw.copy()
        changed[:, self.onset + SUPPORT_STOP:self.onset + SUPPORT_STOP + 100] += 1e6
        changed[:, :self.onset + SUPPORT_START] -= 1e6
        np.testing.assert_array_equal(original, b0_epoch(changed, self.onset, valid, self.taps)[0])
        # B0 receives no cue label or training template; only this trial's fixed support.


if __name__ == "__main__":
    unittest.main()
