"""Run-to-failure data as machines and bearings, on top of ``bearing-datasets``.

``bearing-datasets`` returns a metadata table with one row per signal (one channel of
one recording). For run-to-failure sets it has no universal bearing column, so this
module rebuilds the structure BearingShift evaluates on:

    MachineRun (one run_id: the unit of analysis)
      └─ BearingRecord (one physical bearing, with one signal per snapshot)

Layouts handled (as observed in bearing-datasets metadata):

- XJTU-SY: one bearing per ``run_id``; ``failure`` names the failed component.
- IMS: four bearings per ``run_id``, identified by ``channel`` (``bearing1_x``,
  ``bearing3``, ...); ``failed_bearing`` lists which failed (``bearing_3+bearing_4``).
- Anything with an explicit ``bearing_id`` column.

``pandas`` is only needed here (install the ``data`` extra); the rest of the package
works on NumPy arrays.
"""

from __future__ import annotations

import re
from collections.abc import Iterator, Mapping
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import TYPE_CHECKING, Any

import numpy as np

if TYPE_CHECKING:  # pragma: no cover
    import pandas as pd

# Published bearing geometry, used only when the metadata lacks speed or defect orders.
# IMS: Rexnord ZA-2115 at 2000 rpm (Qiu et al. 2006). XJTU-SY: LDK UER204 (Wang et al. 2020).
FALLBACK_SHAFT_HZ = {"ims": 2000 / 60}
FALLBACK_ORDERS = {
    "ims": {"bpfo": 7.09, "bpfi": 8.91},
    "xjtu_sy": {"bpfo": 3.08, "bpfi": 4.92},
}
XJTU_CONDITION_HZ = {"1": 35.0, "2": 37.5, "3": 40.0}

TIME_COLS = ("time_s", "timestamp", "measured_at", "datetime", "time", "elapsed_s")
SPEED_HZ_COLS = ("shaft_hz", "speed_hz", "rotation_hz")
SPEED_RPM_COLS = ("speed_rpm", "rpm", "shaft_rpm", "speed")
AXIS_COLS = ("axis", "sensor_axis", "direction")
PREFERRED_AXES = ("horizontal", "x", "h", "radial")
ORDER_NAMES = ("bpfo", "bpfi", "bsf", "ftf")


@dataclass(frozen=True, eq=False)
class BearingRecord:
    key: str
    failed: bool | None  # None = unknown
    failure_mode: str  # "survived", a component description, or "unknown"
    signal_ids: tuple[Any, ...]  # one per snapshot, in time order


@dataclass(frozen=True, eq=False)
class MachineRun:
    dataset: str
    machine_id: str
    fs: float
    shaft_hz: float | None
    fault_orders: Mapping[str, float]  # orders of shaft speed
    times_s: np.ndarray  # seconds since the first snapshot, one per snapshot
    bearings: tuple[BearingRecord, ...]
    sources: Mapping[str, str] = field(default_factory=dict)  # where speed/orders came from

    @property
    def n_snapshots(self) -> int:
        return int(self.times_s.size)

    @property
    def failed(self) -> bool | None:
        flags = [b.failed for b in self.bearings]
        if any(f is True for f in flags):
            return True
        if all(f is False for f in flags):
            return False
        return None

    def fault_hz(self, order: str) -> float | None:
        o = self.fault_orders.get(order)
        return None if o is None or self.shaft_hz is None else o * self.shaft_hz


def natural_key(s: object) -> list:
    return [int(t) if t.isdigit() else t for t in re.split(r"(\d+)", str(s))]


def _first_col(columns, candidates) -> str | None:
    lower = {str(c).lower(): c for c in columns}
    for cand in candidates:
        if cand in lower:
            return lower[cand]
    return None


def _positive(v) -> float | None:
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return f if np.isfinite(f) and f > 0 else None


def identify_bearings(meta: pd.DataFrame) -> pd.DataFrame:
    """Copy of ``meta`` with ``machine_id``, ``bearing_key``, ``failed`` and ``failure_mode``."""
    cols = set(meta.columns)
    out = meta.copy()
    num = None
    if "run_id" in cols:
        out["machine_id"] = out["run_id"].astype(str)
    elif "bearing_id" in cols:
        out["machine_id"] = out["bearing_id"].astype(str)
    else:
        raise KeyError("metadata has neither 'run_id' nor 'bearing_id'")

    if "bearing_id" in cols:
        out["bearing_key"] = out["bearing_id"].astype(str)
    else:
        if "channel" in cols:
            num = out["channel"].astype(str).str.extract(r"bearing(\d+)", expand=False)
        if num is not None and num.notna().any():
            if num.isna().any():
                bad = sorted(out.loc[num.isna(), "channel"].astype(str).unique())[:5]
                raise ValueError(f"some channels don't name a bearing: {bad}")
            out["bearing_key"] = out["machine_id"] + "_b" + num
        else:
            out["bearing_key"] = out["machine_id"]

    failure = out["failure"].astype(str) if "failure" in cols else None
    if "failed_bearing" in cols and num is not None and num.notna().all():
        failed = [
            f"bearing_{n}" in str(fb).split("+")
            for n, fb in zip(num, out["failed_bearing"], strict=True)
        ]
    elif failure is not None and (out["bearing_key"] == out["machine_id"]).all():
        failed = [True] * len(out)  # one bearing per run-to-failure record
    else:
        failed = [None] * len(out)
    out["failed"] = failed
    if failure is not None:
        out["failure_mode"] = [
            "survived" if f is False else str(m) for f, m in zip(failed, failure, strict=True)
        ]
    else:
        out["failure_mode"] = ["survived" if f is False else "unknown" for f in failed]
    return out


def _resolve_speed(dataset: str, rows: pd.DataFrame) -> tuple[float | None, str]:
    c = _first_col(rows.columns, SPEED_HZ_COLS)
    if c and (v := _positive(rows[c].iloc[0])):
        return v, f"metadata:{c}"
    c = _first_col(rows.columns, SPEED_RPM_COLS)
    if c and (v := _positive(rows[c].iloc[0])):
        return v / 60.0, f"metadata:{c}"
    if dataset in FALLBACK_SHAFT_HZ:
        return FALLBACK_SHAFT_HZ[dataset], "fallback:published"
    if dataset == "xjtu_sy":
        m = re.search(r"(\d)_\d", str(rows["machine_id"].iloc[0]))
        if m and m.group(1) in XJTU_CONDITION_HZ:
            return XJTU_CONDITION_HZ[m.group(1)], "fallback:condition"
    return None, "missing"


def _resolve_orders(dataset: str, rows: pd.DataFrame) -> tuple[dict[str, float], dict[str, str]]:
    orders, sources = {}, {}
    lower = {str(c).lower(): c for c in rows.columns}
    for name in ORDER_NAMES:
        c = lower.get(name)
        v = _positive(rows[c].iloc[0]) if c is not None else None
        if v is not None and v < 30:  # bearing-datasets stores orders of shaft speed
            orders[name], sources[name] = v, f"metadata:{c}"
        elif name in FALLBACK_ORDERS.get(dataset, {}):
            orders[name], sources[name] = FALLBACK_ORDERS[dataset][name], "fallback:published"
    return orders, sources


def _times_seconds(rows: pd.DataFrame) -> np.ndarray:
    c = _first_col(rows.columns, TIME_COLS)
    if c is None:
        raise KeyError(f"metadata has no time column (looked for {TIME_COLS})")
    s = rows[c]
    if np.issubdtype(s.dtype, np.number):
        t = s.to_numpy(dtype=float)
    else:
        import pandas as pd

        t = pd.to_datetime(s).astype("int64").to_numpy() / 1e9
    return t


def _one_signal_per_snapshot(rows: pd.DataFrame) -> pd.DataFrame:
    """Keep one channel per (bearing, recording), preferring a horizontal/x axis."""
    axis = _first_col(rows.columns, AXIS_COLS)
    if axis:
        rank = ~rows[axis].astype(str).str.lower().isin(PREFERRED_AXES)
        rows = rows.assign(_rank=rank.to_numpy()).sort_values("_rank", kind="stable")
    return rows.drop_duplicates(["bearing_key", "recording_id"], keep="first")


def build_runs(meta: pd.DataFrame, dataset: str) -> list[MachineRun]:
    """Turn ``bearing-datasets`` metadata into one ``MachineRun`` per machine."""
    for required in ("signal_id", "recording_id", "fs"):
        if required not in meta.columns:
            raise KeyError(f"metadata has no '{required}' column")
    meta = _one_signal_per_snapshot(identify_bearings(meta))
    runs = []
    for machine_id, rows in sorted(meta.groupby("machine_id"), key=lambda kv: natural_key(kv[0])):
        # Snapshot timeline: recordings present for every bearing, ordered by time.
        per_rec = rows.groupby("recording_id")["bearing_key"].nunique()
        n_bearings = rows["bearing_key"].nunique()
        complete = per_rec[per_rec == n_bearings].index
        rows = rows[rows["recording_id"].isin(complete)]
        rec = rows.drop_duplicates("recording_id")[["recording_id"]].copy()
        rec["_t"] = _times_seconds(rows.drop_duplicates("recording_id"))
        rec = rec.sort_values(["_t", "recording_id"], kind="stable")
        order = {r: i for i, r in enumerate(rec["recording_id"])}

        bearings = []
        for key, b in sorted(rows.groupby("bearing_key"), key=lambda kv: natural_key(kv[0])):
            b = b.assign(_o=b["recording_id"].map(order)).sort_values("_o")
            bearings.append(
                BearingRecord(
                    key=str(key),
                    failed=None if b["failed"].iloc[0] is None else bool(b["failed"].iloc[0]),
                    failure_mode=str(b["failure_mode"].iloc[0]),
                    signal_ids=tuple(b["signal_id"]),
                )
            )
        fs_values = rows["fs"].unique()
        if len(fs_values) != 1:
            raise ValueError(f"machine {machine_id} mixes sampling rates {fs_values}")
        shaft_hz, speed_src = _resolve_speed(dataset, rows)
        orders, order_src = _resolve_orders(dataset, rows)
        t = rec["_t"].to_numpy(dtype=float)
        runs.append(
            MachineRun(
                dataset=dataset,
                machine_id=str(machine_id),
                fs=float(fs_values[0]),
                shaft_hz=shaft_hz,
                fault_orders=MappingProxyType(orders),
                times_s=t - t[0],
                bearings=tuple(bearings),
                sources=MappingProxyType({"speed": speed_src, **order_src}),
            )
        )
    return runs


def open_dataset(name: str):
    """Open a dataset through ``bearing-datasets`` (requires the ``data`` extra)."""
    try:
        import bearing_datasets as bd
    except ImportError as e:  # pragma: no cover
        raise ImportError("install the 'data' extra: pip install 'bearingshift[data]'") from e
    return bd.open(name)


def load_runs(name: str, ds=None) -> list[MachineRun]:
    """Load all machines of a run-to-failure dataset. ``ds`` overrides ``open_dataset``."""
    ds = ds if ds is not None else open_dataset(name)
    return build_runs(ds.metadata(backend="pandas"), name)


def iter_snapshots(ds, run: MachineRun, bearing_key: str) -> Iterator[np.ndarray]:
    """Yield one bearing's signals in time order, as 1-D float arrays."""
    bearing = next((b for b in run.bearings if b.key == bearing_key), None)
    if bearing is None:
        raise KeyError(f"{run.machine_id} has no bearing '{bearing_key}'")
    for _, x in ds.iter_signals(list(bearing.signal_ids)):
        yield np.asarray(x, dtype=float).ravel()
