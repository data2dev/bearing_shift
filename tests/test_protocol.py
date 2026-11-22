import dataclasses

import numpy as np
import pytest

from bearingshift.protocol import (
    PROTOCOL,
    PROTOCOL_VERSION,
    commissioning_mask,
    onset_index,
    sustained_departure,
)


def test_protocol_is_frozen():
    with pytest.raises(dataclasses.FrozenInstanceError):
        PROTOCOL.k_sigma = 3.0  # type: ignore[misc]
    with pytest.raises(TypeError):
        PROTOCOL.commissioning_s["ims"] = 1.0  # type: ignore[index]
    assert PROTOCOL.version == PROTOCOL_VERSION


def test_protocol_values_match_roadmap():
    # If this fails you changed the protocol: bump PROTOCOL_VERSION and add a changelog entry.
    assert PROTOCOL_VERSION == 1
    assert PROTOCOL.commissioning_seconds("ims") == 24 * 3600
    assert PROTOCOL.commissioning_seconds("xjtu_sy") == 600
    assert (PROTOCOL.k_sigma, PROTOCOL.persist) == (5.0, 3)
    assert PROTOCOL.onset_orders == ("bpfo", "bpfi")
    assert set(PROTOCOL.required_baselines) == {"rms", "envelope"}


def test_unknown_dataset_has_no_commissioning():
    with pytest.raises(KeyError, match="bump the version"):
        PROTOCOL.commissioning_seconds("nope")


def test_commissioning_is_time_based_not_fraction_of_life():
    # Same sampling interval, very different run lengths: same commissioning size.
    short = np.arange(30) * 60.0
    long = np.arange(3000) * 60.0
    assert commissioning_mask(short, "xjtu_sy").sum() == 10
    assert commissioning_mask(long, "xjtu_sy").sum() == 10


def test_commissioning_needs_enough_snapshots():
    with pytest.raises(ValueError, match="fewer than the minimum"):
        commissioning_mask(np.arange(30) * 300.0, "xjtu_sy")  # 2 snapshots in 10 min


def test_sustained_departure_requires_persistence():
    c = np.zeros(40, bool)
    c[:20] = True
    v = np.r_[np.random.default_rng(0).normal(0, 1, 20), np.zeros(20)]
    v[25] = 100  # single spike: no alarm
    assert sustained_departure(v, c) is None
    v[30:33] = 100  # three in a row: alarm at the third
    assert sustained_departure(v, c) == 32


def test_sustained_departure_ignores_commissioning():
    c = np.zeros(30, bool)
    c[:20] = True
    v = np.random.default_rng(1).normal(0, 1, 30)
    v[:3] = 50  # big values inside commissioning never count as an alarm
    assert sustained_departure(v, c) is None


def test_onset_is_earliest_across_bearings_and_ignores_other_orders():
    n = 60
    c = np.zeros(n, bool)
    c[:20] = True
    noise = np.random.default_rng(2).normal(0, 1, (4, n))
    a_bpfo, a_bpfi, b_bpfo, b_ftf = noise
    a_bpfi[45:] += 50  # bearing a, BPFI, rises at 45
    b_bpfo[38:] += 50  # bearing b, BPFO, rises at 38
    b_ftf[25:] += 50  # FTF is not an onset order: ignored
    series = {
        ("a", "bpfo"): a_bpfo,
        ("a", "bpfi"): a_bpfi,
        ("b", "bpfo"): b_bpfo,
        ("b", "ftf"): b_ftf,
    }
    assert onset_index(series, c) == 40


def test_onset_undefined_when_nothing_departs():
    c = np.zeros(50, bool)
    c[:20] = True
    s = {("a", "bpfo"): np.random.default_rng(3).normal(0, 1, 50)}
    assert onset_index(s, c) is None
