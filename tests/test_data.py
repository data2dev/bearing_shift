import numpy as np
import pytest
from conftest import FakeDataset, ims_like, xjtu_like

from bearingshift.data import build_runs, identify_bearings, iter_snapshots, load_runs


def test_ims_machines_and_bearings(ims_meta):
    runs = build_runs(ims_meta, "ims")
    assert [r.machine_id for r in runs] == ["test1", "test2"]
    for r in runs:
        assert [b.key for b in r.bearings] == [f"{r.machine_id}_b{i}" for i in range(1, 5)]
        assert r.n_snapshots == 20
        assert all(len(b.signal_ids) == 20 for b in r.bearings)
        assert r.failed is True
    t1 = {b.key: b for b in runs[0].bearings}
    assert [t1[f"test1_b{i}"].failed for i in range(1, 5)] == [False, False, True, True]
    assert t1["test1_b1"].failure_mode == "survived"
    assert t1["test1_b3"].failure_mode == "bearing failed"


def test_ims_picks_x_axis_when_two_axes(ims_meta):
    run = build_runs(ims_meta, "ims")[0]
    assert all(s.endswith("_x") for s in run.bearings[0].signal_ids)


def test_time_ordering_despite_shuffled_metadata(xjtu_meta):
    for run in build_runs(xjtu_meta, "xjtu_sy"):
        assert np.all(np.diff(run.times_s) > 0)
        assert run.times_s[0] == 0
        ids = run.bearings[0].signal_ids
        assert list(ids) == sorted(ids)  # zero-padded snapshot numbers sort in time order
        assert all(s.endswith("/horizontal") for s in ids)


def test_xjtu_one_bearing_per_machine_all_failed(xjtu_meta):
    runs = build_runs(xjtu_meta, "xjtu_sy")
    assert [r.machine_id for r in runs] == ["Bearing1_1", "Bearing2_3"]
    assert all(len(r.bearings) == 1 and r.failed for r in runs)
    assert runs[1].bearings[0].failure_mode == "cage"


def test_speed_and_orders_from_metadata(xjtu_meta):
    r = build_runs(xjtu_meta, "xjtu_sy")[0]
    assert r.shaft_hz == pytest.approx(35.0)
    assert r.fault_hz("bpfo") == pytest.approx(3.08307 * 35.0)
    assert r.sources["speed"] == "metadata:speed_rpm"
    assert r.sources["bpfo"] == "metadata:bpfo"


def test_fallbacks_when_metadata_lacks_speed_and_orders(xjtu_meta):
    meta = xjtu_meta.drop(columns=["speed_rpm", "bpfo", "bpfi"])
    r = build_runs(meta, "xjtu_sy")[1]  # Bearing2_x -> condition 2 -> 37.5 Hz
    assert r.shaft_hz == 37.5
    assert r.fault_orders["bpfo"] == 3.08
    assert r.sources["speed"] == "fallback:condition"


def test_incomplete_recordings_are_dropped():
    meta = ims_like(n_snapshots=10)
    drop = (
        (meta["run_id"] == "test2")
        & (meta["recording_id"].str.endswith("02.00.00"))
        & (meta["channel"] == "bearing4")
    )
    run = build_runs(meta[~drop], "ims")[1]
    assert run.n_snapshots == 9
    assert all(len(b.signal_ids) == 9 for b in run.bearings)


def test_missing_required_columns():
    with pytest.raises(KeyError, match="time column"):
        build_runs(xjtu_like().drop(columns=["time_s"]), "xjtu_sy")
    with pytest.raises(KeyError, match="signal_id"):
        build_runs(xjtu_like().drop(columns=["signal_id"]), "xjtu_sy")
    with pytest.raises(KeyError, match="run_id"):
        identify_bearings(xjtu_like().drop(columns=["run_id"]))


def test_load_and_iterate_with_fake_dataset(xjtu_meta):
    ds = FakeDataset(xjtu_meta)
    run = load_runs("xjtu_sy", ds=ds)[0]
    xs = list(iter_snapshots(ds, run, run.bearings[0].key))
    assert len(xs) == run.n_snapshots
    assert all(x.ndim == 1 and x.size == 2560 for x in xs)
    with pytest.raises(KeyError):
        next(iter_snapshots(ds, run, "nope"))
