"""Fit/evaluation splits that can't leak, and checks that prove it.

Two modes, both healthy-only (models are only ever fitted on commissioning data):

- ``per_machine``: each machine is fitted on its own commissioning windows and
  evaluated on everything after.
- ``cross_machine``: fit/calibration machines and evaluation machines are disjoint;
  fitting still uses only the commissioning windows of the fit machines.

``check_no_leakage`` raises ``LeakageError`` on any violation. Every evaluation runs it
before scoring, and CI tests that deliberately leaky splits are caught.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping

import numpy as np

from bearingshift.windowing import WindowTable


class LeakageError(AssertionError):
    """A fit/evaluation split uses information it must not have."""


def commissioning_end(
    times_by_machine: Mapping[str, np.ndarray], seconds: float
) -> dict[str, float]:
    """End of the commissioning period per machine, in that machine's time axis."""
    return {m: float(np.min(t)) + seconds for m, t in times_by_machine.items()}


def per_machine_split(
    table: WindowTable, comm_end: Mapping[str, float]
) -> tuple[np.ndarray, np.ndarray]:
    """Fit = commissioning windows of each machine; eval = all later windows."""
    ends = np.array([comm_end[m] for m in table.machine_id], dtype=float)
    fit = table.time_s < ends
    return fit, ~fit


def cross_machine_split(
    table: WindowTable, comm_end: Mapping[str, float], eval_machines: Iterable[str]
) -> tuple[np.ndarray, np.ndarray]:
    """Fit = commissioning windows of non-eval machines; eval = all windows of eval machines."""
    eval_set = set(eval_machines)
    is_eval = np.array([m in eval_set for m in table.machine_id], dtype=bool)
    ends = np.array([comm_end[m] for m in table.machine_id], dtype=float)
    fit = ~is_eval & (table.time_s < ends)
    return fit, is_eval


def check_no_leakage(
    table: WindowTable,
    fit: np.ndarray,
    evaluate: np.ndarray,
    comm_end: Mapping[str, float],
    mode: str,
) -> None:
    """Raise ``LeakageError`` if the split could leak. ``mode``: per_machine | cross_machine."""
    fit = np.asarray(fit, dtype=bool)
    evaluate = np.asarray(evaluate, dtype=bool)
    if fit.shape != (len(table),) or evaluate.shape != (len(table),):
        raise ValueError("masks must have one entry per window")
    if mode not in ("per_machine", "cross_machine"):
        raise ValueError(f"unknown mode '{mode}'")

    if np.any(fit & evaluate):
        raise LeakageError(f"{int(np.sum(fit & evaluate))} windows are in both fit and eval")

    # Healthy-only: every fitted window lies strictly inside its machine's commissioning.
    ends = np.array([comm_end[m] for m in table.machine_id], dtype=float)
    late = fit & (table.time_s >= ends)
    if np.any(late):
        machines = sorted(set(table.machine_id[late]))
        raise LeakageError(f"fit uses post-commissioning windows from machines {machines}")

    if mode == "cross_machine":
        both = set(table.machine_id[fit]) & set(table.machine_id[evaluate])
        if both:
            raise LeakageError(f"machines on both sides of a cross-machine split: {sorted(both)}")
    else:
        # Per machine, evaluation starts after that machine's commissioning period, so a
        # threshold fitted on commissioning never sees evaluated snapshots.
        early = evaluate & (table.time_s < ends)
        if np.any(early):
            machines = sorted(set(table.machine_id[early]))
            raise LeakageError(f"eval includes commissioning windows from machines {machines}")
        # A snapshot can't be split between fit and eval.
        key = list(zip(table.machine_id, table.snapshot, strict=True))
        fit_snaps = {k for k, f in zip(key, fit, strict=True) if f}
        eval_snaps = {k for k, e in zip(key, evaluate, strict=True) if e}
        if fit_snaps & eval_snaps:
            raise LeakageError("a snapshot has windows in both fit and eval")
