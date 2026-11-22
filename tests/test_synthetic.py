import numpy as np
import pytest

import bearingshift
from bearingshift.synthetic import band_energy, bearing_signal, envelope_spectrum

FS = 20_000.0
SHAFT_HZ = 33.3
BPFO_ORDER = 3.58


def test_version_is_set():
    assert isinstance(bearingshift.__version__, str)
    assert bearingshift.__version__.count(".") == 2


def test_shape_and_reproducibility():
    a = bearing_signal(fs=FS, duration=0.5, seed=1)
    b = bearing_signal(fs=FS, duration=0.5, seed=1)
    assert a.shape == (10_000,)
    np.testing.assert_array_equal(a, b)


def test_healthy_when_severity_zero():
    a = bearing_signal(fs=FS, defect_order=BPFO_ORDER, severity=0.0, seed=2)
    b = bearing_signal(fs=FS, defect_order=None, seed=2)
    np.testing.assert_array_equal(a, b)


def test_faulty_signal_has_envelope_peak_at_bpfo():
    bpfo_hz = BPFO_ORDER * SHAFT_HZ
    healthy = bearing_signal(fs=FS, shaft_hz=SHAFT_HZ, seed=3)
    faulty = bearing_signal(fs=FS, shaft_hz=SHAFT_HZ, defect_order=BPFO_ORDER, severity=8.0, seed=3)

    e_healthy = band_energy(*envelope_spectrum(healthy, FS), bpfo_hz, 3.0)
    e_faulty = band_energy(*envelope_spectrum(faulty, FS), bpfo_hz, 3.0)
    assert e_faulty > 10 * e_healthy

    freqs, amp = envelope_spectrum(faulty, FS)
    band = (freqs > 20) & (freqs < 500)
    peak_hz = freqs[band][np.argmax(amp[band])]
    assert abs(peak_hz - bpfo_hz) < 3.0


@pytest.mark.parametrize(
    "kwargs",
    [{"fs": 0}, {"duration": -1}, {"shaft_hz": 0}, {"severity": -0.1}],
)
def test_rejects_invalid_arguments(kwargs):
    with pytest.raises(ValueError):
        bearing_signal(**kwargs)
