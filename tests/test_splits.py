"""Leakage checks: correct splits pass, deliberately leaky ones are caught."""

import numpy as np
import pytest

from bearingshift.splits import (
    LeakageError,
    check_no_leakage,
    commissioning_end,
    cross_machine_split,
    per_machine_split,
)
from bearingshift.windowing import WindowTable


@pytest.fixture
def table():
    # 3 machines x 10 snapshots (60 s apart) x 2 windows each.
    entries = [
        (m, f"{m}_b1", s, 60.0 * s, w) for m in ("A", "B", "C") for s in range(10) for w in range(2)
    ]
    return WindowTable.build(entries)


@pytest.fixture
def comm_end(table):
    times = {m: table.time_s[table.machine_id == m] for m in ("A", "B", "C")}
    return commissioning_end(times, seconds=180.0)  # first 3 snapshots


def test_per_machine_split_is_clean(table, comm_end):
    fit, ev = per_machine_split(table, comm_end)
    assert fit.sum() == 3 * 3 * 2 and ev.sum() == 3 * 7 * 2
    check_no_leakage(table, fit, ev, comm_end, "per_machine")


def test_cross_machine_split_is_clean(table, comm_end):
    fit, ev = cross_machine_split(table, comm_end, eval_machines=["C"])
    assert set(table.machine_id[fit]) == {"A", "B"} and set(table.machine_id[ev]) == {"C"}
    check_no_leakage(table, fit, ev, comm_end, "cross_machine")


def test_catches_fit_on_post_commissioning_data(table, comm_end):
    fit, ev = per_machine_split(table, comm_end)
    fit = fit.copy()
    ev = ev.copy()
    i = np.flatnonzero((table.machine_id == "B") & (table.snapshot == 8))[0]
    fit[i], ev[i] = True, False
    with pytest.raises(LeakageError, match="post-commissioning.*B"):
        check_no_leakage(table, fit, ev, comm_end, "per_machine")


def test_catches_random_window_split(table, comm_end):
    # The classic leak: shuffle windows into train/test regardless of machine or time.
    fit = np.random.default_rng(0).random(len(table)) < 0.7
    with pytest.raises(LeakageError):
        check_no_leakage(table, fit, ~fit, comm_end, "per_machine")


def test_catches_machine_on_both_sides(table, comm_end):
    fit, ev = cross_machine_split(table, comm_end, eval_machines=["C"])
    ev = ev | ((table.machine_id == "A") & (table.snapshot > 5))
    with pytest.raises(LeakageError, match="both sides.*A"):
        check_no_leakage(table, fit, ev, comm_end, "cross_machine")


def test_catches_overlapping_masks(table, comm_end):
    fit, _ = per_machine_split(table, comm_end)
    with pytest.raises(LeakageError, match="both fit and eval"):
        check_no_leakage(table, fit, np.ones(len(table), bool), comm_end, "per_machine")


def test_catches_evaluating_on_commissioning(table, comm_end):
    fit, ev = per_machine_split(table, comm_end)
    ev = ev.copy()
    fit = fit.copy()
    i = np.flatnonzero((table.machine_id == "A") & (table.snapshot == 0))[0]
    fit[i], ev[i] = False, True
    with pytest.raises(LeakageError, match="eval includes commissioning"):
        check_no_leakage(table, fit, ev, comm_end, "per_machine")


def test_rejects_bad_inputs(table, comm_end):
    fit, ev = per_machine_split(table, comm_end)
    with pytest.raises(ValueError):
        check_no_leakage(table, fit[:-1], ev, comm_end, "per_machine")
    with pytest.raises(ValueError):
        check_no_leakage(table, fit, ev, comm_end, "random")
