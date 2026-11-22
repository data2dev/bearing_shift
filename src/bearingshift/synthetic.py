"""Synthetic bearing vibration signals for tests and the offline demo.

No real data is ever bundled with BearingShift (see DATA_LICENSES.md). Tests and CI
use these generated signals instead: broadband noise plus shaft harmonics, with an
optional train of decaying resonance impacts repeating at a bearing defect frequency,
amplitude-modulated the way a localised race defect is.
"""

from __future__ import annotations

import numpy as np
from scipy.signal import hilbert


def bearing_signal(
    fs: float = 20_000.0,
    duration: float = 1.0,
    shaft_hz: float = 33.3,
    defect_order: float | None = None,
    severity: float = 0.0,
    resonance_hz: float = 3_000.0,
    damping: float = 600.0,
    noise_std: float = 0.1,
    seed: int | None = None,
) -> np.ndarray:
    """Generate one snapshot of bearing housing acceleration.

    Parameters
    ----------
    fs:
        Sampling rate in Hz.
    duration:
        Snapshot length in seconds.
    shaft_hz:
        Shaft rotation frequency in Hz.
    defect_order:
        Defect frequency as an order of shaft speed (for example BPFO / shaft speed).
        ``None`` or ``severity == 0`` gives a healthy signal.
    severity:
        Impact amplitude relative to ``noise_std``. 0 means healthy.
    resonance_hz:
        Structural resonance excited by each impact.
    damping:
        Exponential decay rate of each impact, in 1/s.
    noise_std:
        Standard deviation of the broadband Gaussian noise.
    seed:
        Seed for reproducibility.
    """
    if fs <= 0 or duration <= 0 or shaft_hz <= 0:
        raise ValueError("fs, duration and shaft_hz must be positive")
    if severity < 0:
        raise ValueError("severity must be non-negative")

    rng = np.random.default_rng(seed)
    n = int(round(fs * duration))
    t = np.arange(n) / fs

    x = noise_std * rng.standard_normal(n)
    # Shaft harmonics (imbalance, misalignment): present in healthy machines too.
    x += 0.05 * np.sin(2 * np.pi * shaft_hz * t)
    x += 0.02 * np.sin(2 * np.pi * 2 * shaft_hz * t + 0.3)

    if defect_order is not None and severity > 0:
        defect_hz = defect_order * shaft_hz
        period = 1.0 / defect_hz
        impulse_len = min(n, int(5.0 / damping * fs))
        tau = np.arange(impulse_len) / fs
        impulse = np.exp(-damping * tau) * np.sin(2 * np.pi * resonance_hz * tau)
        amp = severity * noise_std
        # Small timing jitter (slip) makes impacts quasi-periodic, as in real bearings.
        start = rng.uniform(0, period)
        for t0 in np.arange(start, duration, period):
            t_hit = t0 + rng.normal(0, 0.01 * period)
            i0 = int(round(t_hit * fs))
            if i0 < 0 or i0 >= n:
                continue
            i1 = min(n, i0 + impulse_len)
            x[i0:i1] += amp * impulse[: i1 - i0]
    return x


def envelope_spectrum(x: np.ndarray, fs: float) -> tuple[np.ndarray, np.ndarray]:
    """Return (frequencies, amplitudes) of the envelope spectrum of ``x``."""
    x = np.asarray(x, dtype=float)
    env = np.abs(hilbert(x - x.mean()))
    env -= env.mean()
    amp = np.abs(np.fft.rfft(env)) / len(env)
    freqs = np.fft.rfftfreq(len(env), d=1.0 / fs)
    return freqs, amp


def band_energy(
    freqs: np.ndarray, amp: np.ndarray, centre_hz: float, half_width_hz: float
) -> float:
    """Sum of squared amplitudes in ``centre_hz ± half_width_hz``."""
    mask = np.abs(freqs - centre_hz) <= half_width_hz
    return float(np.sum(amp[mask] ** 2))
