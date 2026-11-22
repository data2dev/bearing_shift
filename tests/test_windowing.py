import numpy as np
import pytest

from bearingshift.windowing import WindowSpec, WindowTable, frame, window_snapshot


def test_frame_shapes_and_values():
    x = np.arange(10)
    w = frame(x, 4, 3)
    assert w.shape == (3, 4)
    np.testing.assert_array_equal(w[1], [3, 4, 5, 6])
    assert frame(x, 20, 1).shape == (0, 20)


def test_frame_rejects_bad_args():
    with pytest.raises(ValueError):
        frame(np.zeros((2, 2)), 1, 1)
    with pytest.raises(ValueError):
        frame(np.zeros(5), 0, 1)
    with pytest.raises(ValueError):
        WindowSpec(0, 1)


def test_window_snapshot_attaches_identity():
    x = np.zeros(2000)
    w, t = window_snapshot(x, 1000.0, WindowSpec(0.5, 0.25), "m1", "m1_b2", 7, 420.0)
    assert w.shape == (7, 500)
    assert len(t) == 7
    assert set(t.machine_id) == {"m1"} and set(t.bearing_key) == {"m1_b2"}
    assert set(t.snapshot) == {7} and set(t.time_s) == {420.0}
    np.testing.assert_array_equal(t.window, np.arange(7))


def test_tables_concat():
    _, a = window_snapshot(np.zeros(100), 100.0, WindowSpec(0.5, 0.5), "m1", "b", 0, 0.0)
    _, b = window_snapshot(np.zeros(100), 100.0, WindowSpec(0.5, 0.5), "m2", "b", 0, 0.0)
    c = a.concat(b)
    assert len(c) == 4 and list(c.machine_id) == ["m1", "m1", "m2", "m2"]
    assert len(WindowTable.build([])) == 0
